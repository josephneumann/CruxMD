"""FHIR Resource repository.

Single entry point for FHIR resource persistence with automatic projection sync.
When a resource is saved, the repository checks if a projection is registered
for that resource type and syncs the projection table automatically.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.fhir import FhirResource
from app.projections.registry import ProjectionRegistry


class FhirRepository:
    """Repository for FHIR resource persistence.

    Handles CRUD operations on FhirResource with automatic projection sync
    for resource types that have registered projections.
    """

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session.

        Args:
            db: Async SQLAlchemy session.
        """
        self.db = db

    async def save(self, resource: FhirResource) -> FhirResource:
        """Save FHIR resource and sync projection if configured.

        Args:
            resource: FhirResource to save.

        Returns:
            The saved FhirResource.
        """
        self.db.add(resource)
        await self.db.flush()
        await self._sync_projection(resource)
        return resource

    async def save_from_data(
        self,
        resource_type: str,
        fhir_data: dict,
        patient_id: uuid.UUID | None = None,
    ) -> FhirResource:
        """Create FhirResource from FHIR JSON and save with projection.

        Args:
            resource_type: FHIR resource type (e.g., 'Task', 'Observation').
            fhir_data: Raw FHIR JSON data.
            patient_id: Optional patient reference UUID.

        Returns:
            The created and saved FhirResource.
        """
        resource = FhirResource(
            fhir_id=fhir_data.get("id", str(uuid.uuid4())),
            resource_type=resource_type,
            patient_id=patient_id,
            data=fhir_data,
        )
        return await self.save(resource)

    async def update(self, resource: FhirResource) -> FhirResource:
        """Update FHIR resource and re-sync projection.

        Args:
            resource: FhirResource to update.

        Returns:
            The updated FhirResource.
        """
        await self.db.flush()
        await self._sync_projection(resource)
        return resource

    async def delete(self, resource_id: uuid.UUID) -> bool:
        """Delete FHIR resource (projection cascades via FK).

        Args:
            resource_id: UUID of the resource to delete.

        Returns:
            True if resource was deleted, False if not found.
        """
        resource = await self.get_by_id(resource_id)
        if resource:
            await self.db.delete(resource)
            return True
        return False

    async def get_by_id(self, resource_id: uuid.UUID) -> FhirResource | None:
        """Get FHIR resource by ID.

        Args:
            resource_id: UUID of the resource.

        Returns:
            FhirResource if found, None otherwise.
        """
        result = await self.db.execute(
            select(FhirResource).where(FhirResource.id == resource_id)
        )
        return result.scalar_one_or_none()

    async def get_by_fhir_id(
        self, fhir_id: str, resource_type: str
    ) -> FhirResource | None:
        """Get FHIR resource by FHIR ID and type.

        Args:
            fhir_id: The FHIR resource ID (from the FHIR JSON).
            resource_type: FHIR resource type.

        Returns:
            FhirResource if found, None otherwise.
        """
        result = await self.db.execute(
            select(FhirResource).where(
                FhirResource.fhir_id == fhir_id,
                FhirResource.resource_type == resource_type,
            )
        )
        return result.scalar_one_or_none()

    async def get_by_patient(
        self,
        patient_id: uuid.UUID,
        resource_type: str | None = None,
    ) -> list[FhirResource]:
        """Get all FHIR resources for a patient.

        Args:
            patient_id: Patient UUID.
            resource_type: Optional filter by resource type.

        Returns:
            List of FhirResource objects.
        """
        query = select(FhirResource).where(FhirResource.patient_id == patient_id)
        if resource_type:
            query = query.where(FhirResource.resource_type == resource_type)
        query = query.order_by(FhirResource.created_at.desc())

        result = await self.db.execute(query)
        return list(result.scalars().all())

    async def _sync_projection(self, resource: FhirResource) -> None:
        """Update projection table if configured for this resource type.

        Checks the ProjectionRegistry for a registered projection configuration
        for the resource type. If found, extracts fields from the FHIR data
        and upserts into the projection table.

        Args:
            resource: The FhirResource to sync projection for.
        """
        config = ProjectionRegistry.get(resource.resource_type)
        if not config:
            return

        # Extract fields from FHIR data using configured extractors
        extracted = config.extract(resource.data)

        # Add timestamp
        extracted["projected_at"] = datetime.now(timezone.utc)

        # Create projection instance
        projection = config.model_class(
            fhir_resource_id=resource.id,
            **extracted,
        )

        # Use merge to handle both insert and update
        await self.db.merge(projection)
        await self.db.flush()
