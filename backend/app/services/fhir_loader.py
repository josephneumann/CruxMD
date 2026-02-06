"""FHIR Bundle loader service for PostgreSQL and Neo4j storage."""

import asyncio
import copy
import json
import logging
import re
import uuid
from typing import Any

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FhirResource
from app.services.compiler import compile_and_store
from app.services.embeddings import EmbeddingService, resource_to_text
from app.services.graph import KnowledgeGraph

logger = logging.getLogger(__name__)

# FHIR extension URL for patient narrative profiles
PROFILE_EXTENSION_URL = (
    "http://cruxmd.ai/fhir/StructureDefinition/patient-narrative-profile"
)


def _strip_numbers_from_name(name_obj: dict[str, Any]) -> dict[str, Any]:
    """Strip trailing digits from FHIR HumanName fields.

    Synthea appends numeric suffixes to patient names (e.g. "Andrés117").
    This cleans given, family, text, and prefix/suffix fields.
    """
    strip = lambda s: re.sub(r"\d+", "", s).strip() if isinstance(s, str) else s

    for field in ("family", "text"):
        if field in name_obj:
            name_obj[field] = strip(name_obj[field])

    for field in ("given", "prefix", "suffix"):
        if field in name_obj and isinstance(name_obj[field], list):
            name_obj[field] = [strip(v) for v in name_obj[field]]

    return name_obj


def _clean_patient_names(resource: dict[str, Any]) -> dict[str, Any]:
    """Clean Synthea numeric suffixes from a Patient resource's name array."""
    if resource.get("resourceType") != "Patient":
        return resource
    for name_obj in resource.get("name", []):
        _strip_numbers_from_name(name_obj)
    return resource


async def load_bundle(
    db: AsyncSession,
    graph: KnowledgeGraph,
    bundle: dict[str, Any],
) -> uuid.UUID:
    """
    Load a FHIR bundle into PostgreSQL and Neo4j.

    Ordered writes: PostgreSQL first (source of truth), then Neo4j (derived view).
    Uses upsert semantics for idempotency with batch lookups for performance.

    Args:
        db: Async SQLAlchemy session.
        graph: KnowledgeGraph instance for Neo4j operations.
        bundle: FHIR Bundle dict with "entry" array of resources.

    Returns:
        The canonical patient UUID (PostgreSQL-generated).
    """
    entries = bundle.get("entry", [])
    if not entries:
        raise ValueError("Bundle contains no entries")

    # Extract all resources from bundle entries
    resources_data: list[dict[str, Any]] = []
    for entry in entries:
        resource = entry.get("resource", {})
        if resource and resource.get("resourceType"):
            _clean_patient_names(resource)
            resources_data.append(resource)

    if not resources_data:
        raise ValueError("Bundle contains no valid resources")

    # Find Patient resource and determine canonical ID
    patient_fhir_id: str | None = None
    for resource in resources_data:
        if resource.get("resourceType") == "Patient":
            patient_fhir_id = resource.get("id", "")
            break

    if patient_fhir_id is None:
        raise ValueError("Bundle must contain a Patient resource")

    # Check if patient already exists
    existing_patient = await _find_existing_patient(db, patient_fhir_id)
    patient_id = existing_patient.id if existing_patient else uuid.uuid4()

    # Batch lookup: find all existing resources in one query
    existing_resources = await _find_existing_resources_batch(db, resources_data)
    existing_by_key = {
        (r.fhir_id, r.resource_type): r for r in existing_resources
    }

    # Track all FhirResource objects for embedding generation
    all_fhir_resources: list[FhirResource] = []

    # Process all resources with batch lookup results
    for resource in resources_data:
        resource_type = resource.get("resourceType", "")
        fhir_id = resource.get("id", "")

        # Determine patient_id for this resource
        # All resources get linked to the patient
        resource_patient_id = patient_id

        # Check if resource already exists using batch lookup results
        existing = existing_by_key.get((fhir_id, resource_type))
        if existing:
            # Update existing resource
            existing.data = resource
            existing.patient_id = resource_patient_id
            all_fhir_resources.append(existing)
        else:
            # Create new resource
            if resource_type == "Patient":
                # Patient's id = patient_id for consistency
                fhir_resource = FhirResource(
                    id=patient_id,
                    fhir_id=fhir_id,
                    resource_type=resource_type,
                    patient_id=resource_patient_id,
                    data=resource,
                )
            else:
                # Other resources get auto-generated id
                fhir_resource = FhirResource(
                    fhir_id=fhir_id,
                    resource_type=resource_type,
                    patient_id=resource_patient_id,
                    data=resource,
                )
            db.add(fhir_resource)
            all_fhir_resources.append(fhir_resource)

    # Flush to get IDs assigned
    await db.flush()

    # Generate embeddings and build graph in parallel (they're independent operations)
    await asyncio.gather(
        _generate_embeddings(all_fhir_resources),
        graph.build_from_fhir(str(patient_id), resources_data),
    )

    # Compile and store patient summary (requires graph + Postgres to be populated)
    try:
        await compile_and_store(patient_id, graph, db)
    except Exception as e:
        logger.warning("Failed to compile patient summary during bundle load: %s", e)

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


async def _find_existing_resources_batch(
    db: AsyncSession, resources: list[dict[str, Any]]
) -> list[FhirResource]:
    """
    Find all existing resources by (fhir_id, resource_type) pairs in a single query.

    This replaces N individual queries with one batch query for better performance.
    Uses the idx_fhir_id_type index.
    """
    if not resources:
        return []

    # Build OR conditions for each (fhir_id, resource_type) pair
    conditions = []
    for resource in resources:
        fhir_id = resource.get("id", "")
        resource_type = resource.get("resourceType", "")
        if fhir_id and resource_type:
            conditions.append(
                and_(
                    FhirResource.fhir_id == fhir_id,
                    FhirResource.resource_type == resource_type,
                )
            )

    if not conditions:
        return []

    result = await db.execute(
        select(FhirResource).where(or_(*conditions))
    )
    return list(result.scalars().all())


async def _generate_embeddings(
    fhir_resources: list[FhirResource],
    embedding_service: EmbeddingService | None = None,
) -> None:
    """
    Generate embeddings for FHIR resources that support embedding.

    Updates the embedding and embedding_text columns on each FhirResource.
    Failures are logged but do not block bundle loading (graceful degradation).

    Args:
        fhir_resources: List of FhirResource objects to generate embeddings for.
        embedding_service: Optional EmbeddingService instance. If not provided,
            a new instance is created and closed after use.
    """
    # Filter to only embeddable resources and generate text
    embeddable: list[tuple[FhirResource, str]] = []
    for fhir_resource in fhir_resources:
        text = resource_to_text(fhir_resource.data)
        if text is not None:
            embeddable.append((fhir_resource, text))

    if not embeddable:
        return

    # Create service if not provided (for dependency injection support)
    owns_service = embedding_service is None
    if owns_service:
        embedding_service = EmbeddingService()

    try:
        # Extract texts for batch embedding
        texts = [text for _, text in embeddable]

        # Generate embeddings in batch
        embeddings = await embedding_service.embed_texts(texts)

        # Update FhirResource objects with embeddings
        for (fhir_resource, text), embedding in zip(embeddable, embeddings):
            fhir_resource.embedding = embedding
            fhir_resource.embedding_text = text

        logger.info(f"Generated embeddings for {len(embeddings)} resources")

    except Exception as e:
        # Log error but don't fail bundle loading
        logger.warning("Failed to generate embeddings: %s", e)

    finally:
        # Only close if we created the service
        if owns_service:
            await embedding_service.close()


async def load_bundle_with_profile(
    db: AsyncSession,
    graph: KnowledgeGraph,
    bundle: dict[str, Any],
    profile: dict[str, Any] | None = None,
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

    Returns:
        The canonical patient UUID (PostgreSQL-generated).
    """
    if profile:
        # Embed profile as FHIR extension on Patient resource before loading
        bundle = _add_profile_extension(bundle, profile)

    return await load_bundle(db, graph, bundle)


def _add_profile_extension(
    bundle: dict[str, Any], profile: dict[str, Any]
) -> dict[str, Any]:
    """
    Add profile as FHIR extension to Patient resource in bundle.

    Creates a copy of the bundle with the profile embedded as a FHIR extension
    on the Patient resource. This maintains FHIR-native architecture.
    """
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
                try:
                    return json.loads(value)
                except json.JSONDecodeError:
                    logger.warning("Failed to parse patient profile JSON")
                    return None
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
