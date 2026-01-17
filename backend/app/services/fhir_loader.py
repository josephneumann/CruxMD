"""FHIR Bundle loader service for PostgreSQL and Neo4j storage."""

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FhirResource
from app.services.graph import KnowledgeGraph


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
    patient_fhir_id: str | None = None
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
            patient_fhir_id = fhir_id

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


async def _find_existing_patient(
    db: AsyncSession, fhir_id: str
) -> FhirResource | None:
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
