"""FHIR Bundle loader service for PostgreSQL and Neo4j storage."""

import json
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FhirResource
from app.services.graph import KnowledgeGraph

# FHIR extension URL for patient narrative profiles
PROFILE_EXTENSION_URL = (
    "http://cruxmd.ai/fhir/StructureDefinition/patient-narrative-profile"
)


async def load_bundle(
    db: AsyncSession,
    graph: KnowledgeGraph,
    bundle: dict[str, Any],
    generate_embeddings: bool = True,
) -> uuid.UUID:
    """
    Load a FHIR bundle into PostgreSQL and Neo4j.

    Ordered writes: PostgreSQL first (source of truth), then Neo4j (derived view).
    Uses upsert semantics for idempotency.

    Args:
        db: Async SQLAlchemy session.
        graph: KnowledgeGraph instance for Neo4j operations.
        bundle: FHIR Bundle dict with "entry" array of resources.
        generate_embeddings: Whether to generate embeddings (stubbed for now).

    Returns:
        The canonical patient UUID (PostgreSQL-generated).
    """
    entries = bundle.get("entry", [])
    if not entries:
        raise ValueError("Bundle contains no entries")

    # First pass: find Patient resource and assign canonical ID
    patient_id: uuid.UUID | None = None
    resources_data: list[dict[str, Any]] = []

    for entry in entries:
        resource = entry.get("resource", {})
        if not resource:
            continue

        resource_type = resource.get("resourceType")
        fhir_id = resource.get("id", "")

        if resource_type == "Patient":
            # Check if patient already exists by fhir_id
            existing = await _find_existing_patient(db, fhir_id)
            if existing:
                patient_id = existing.id
            else:
                patient_id = uuid.uuid4()

        resources_data.append(resource)

    if patient_id is None:
        raise ValueError("Bundle must contain a Patient resource")

    # Second pass: store all resources in PostgreSQL
    fhir_resources: list[FhirResource] = []
    for resource in resources_data:
        resource_type = resource.get("resourceType", "")
        fhir_id = resource.get("id", "")

        # Determine if this resource belongs to the patient
        # Patient resource gets patient_id = its own id
        # Other resources get linked to the patient
        if resource_type == "Patient":
            resource_patient_id = patient_id
        else:
            # Extract patient reference if present
            resource_patient_id = _extract_patient_reference(resource, patient_id)

        # Check if resource already exists (for idempotency)
        existing_resource = await _find_existing_resource(db, fhir_id, resource_type)
        if existing_resource:
            # Update existing resource
            existing_resource.data = resource
            existing_resource.patient_id = resource_patient_id
            fhir_resources.append(existing_resource)
        else:
            # Create new resource
            fhir_resource = FhirResource(
                fhir_id=fhir_id,
                resource_type=resource_type,
                patient_id=resource_patient_id,
                data=resource,
            )
            db.add(fhir_resource)
            fhir_resources.append(fhir_resource)

    # Flush to get IDs assigned
    await db.flush()

    # Build Neo4j graph from FHIR resources
    await graph.build_from_fhir(str(patient_id), resources_data)

    # Embeddings generation (stubbed for now)
    if generate_embeddings:
        # TODO: Implement when embeddings service is available
        pass

    return patient_id


async def _find_existing_patient(db: AsyncSession, fhir_id: str) -> FhirResource | None:
    """Find existing Patient resource by fhir_id."""
    result = await db.execute(
        select(FhirResource).where(
            FhirResource.resource_type == "Patient",
            FhirResource.fhir_id == fhir_id,
        )
    )
    return result.scalar_one_or_none()


async def _find_existing_resource(
    db: AsyncSession, fhir_id: str, resource_type: str
) -> FhirResource | None:
    """Find existing resource by fhir_id and resource_type."""
    result = await db.execute(
        select(FhirResource).where(
            FhirResource.fhir_id == fhir_id,
            FhirResource.resource_type == resource_type,
        )
    )
    return result.scalar_one_or_none()


def _extract_patient_reference(
    resource: dict[str, Any], default_patient_id: uuid.UUID
) -> uuid.UUID:
    """
    Extract patient reference from FHIR resource.

    Most FHIR resources reference their patient via a "subject" or "patient" field.
    Returns the default_patient_id since we're loading a single-patient bundle.
    """
    # For single-patient bundles, all resources belong to the same patient
    # In a multi-patient system, we'd parse the reference and look up the patient
    return default_patient_id


async def load_bundle_with_profile(
    db: AsyncSession,
    graph: KnowledgeGraph,
    bundle: dict[str, Any],
    profile: dict[str, Any] | None = None,
    generate_embeddings: bool = True,
) -> uuid.UUID:
    """
    Load a FHIR bundle with an optional profile attached to the Patient resource.

    Profiles are stored as FHIR extensions on the Patient resource, maintaining
    FHIR-native architecture. The profile is embedded in the Patient's data
    before loading, so it's stored within the existing `data` JSONB column.

    Args:
        db: Async SQLAlchemy session.
        graph: KnowledgeGraph instance for Neo4j operations.
        bundle: FHIR Bundle dict with "entry" array of resources.
        profile: Optional PatientProfile data to attach as FHIR extension.
        generate_embeddings: Whether to generate embeddings (stubbed for now).

    Returns:
        The canonical patient UUID (PostgreSQL-generated).
    """
    if profile:
        # Embed profile as FHIR extension on Patient resource before loading
        bundle = _add_profile_extension(bundle, profile)

    return await load_bundle(db, graph, bundle, generate_embeddings)


def _add_profile_extension(
    bundle: dict[str, Any], profile: dict[str, Any]
) -> dict[str, Any]:
    """
    Add profile as FHIR extension to Patient resource in bundle.

    Creates a copy of the bundle with the profile embedded as a FHIR extension
    on the Patient resource. This maintains FHIR-native architecture.
    """
    import copy

    bundle = copy.deepcopy(bundle)

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") == "Patient":
            # Initialize extensions array if not present
            if "extension" not in resource:
                resource["extension"] = []

            # Remove any existing profile extension
            resource["extension"] = [
                ext
                for ext in resource["extension"]
                if ext.get("url") != PROFILE_EXTENSION_URL
            ]

            # Add profile as FHIR extension
            resource["extension"].append(
                {
                    "url": PROFILE_EXTENSION_URL,
                    "valueString": json.dumps(profile),
                }
            )
            break

    return bundle


def get_patient_profile(patient_data: dict[str, Any]) -> dict[str, Any] | None:
    """
    Extract patient profile from FHIR Patient resource.

    Profiles are stored as FHIR extensions with a specific URL.

    Args:
        patient_data: FHIR Patient resource dict.

    Returns:
        Profile dict if present, None otherwise.
    """
    for ext in patient_data.get("extension", []):
        if ext.get("url") == PROFILE_EXTENSION_URL:
            value = ext.get("valueString")
            if value:
                return json.loads(value)
    return None


async def get_patient_resources(
    db: AsyncSession, patient_id: uuid.UUID
) -> list[dict[str, Any]]:
    """
    Get all FHIR resources for a patient.

    Args:
        db: Async SQLAlchemy session.
        patient_id: The canonical patient UUID.

    Returns:
        List of raw FHIR resource dicts.
    """
    result = await db.execute(
        select(FhirResource).where(FhirResource.patient_id == patient_id)
    )
    resources = result.scalars().all()
    return [r.data for r in resources]


async def get_patient_resource(
    db: AsyncSession, patient_id: uuid.UUID
) -> FhirResource | None:
    """
    Get Patient FHIR resource by canonical ID.

    Args:
        db: Async SQLAlchemy session.
        patient_id: The canonical patient UUID.

    Returns:
        FhirResource for the Patient, or None if not found.
    """
    result = await db.execute(
        select(FhirResource).where(
            FhirResource.id == patient_id,
            FhirResource.resource_type == "Patient",
        )
    )
    return result.scalar_one_or_none()
