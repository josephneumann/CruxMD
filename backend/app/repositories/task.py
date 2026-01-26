"""Task repository.

High-level task operations that use the TaskProjection for fast indexed queries
while storing canonical data as FHIR Task resources.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING, Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.fhir import FhirResource
from app.models.projections.task import TaskProjection
from app.projections.serializers.task import TaskFhirSerializer
from app.repositories.fhir import FhirRepository

if TYPE_CHECKING:
    from app.schemas.task import TaskCreate, TaskUpdate


class TaskRepository:
    """Repository for Task operations.

    Uses FHIR Task resources as the source of truth and TaskProjection
    for fast indexed queries. All writes go through FhirRepository to
    ensure projection sync.
    """

    def __init__(self, db: AsyncSession):
        """Initialize repository with database session.

        Args:
            db: Async SQLAlchemy session.
        """
        self.db = db
        self.fhir_repo = FhirRepository(db)

    async def create(
        self, task_data: TaskCreate
    ) -> tuple[FhirResource, TaskProjection]:
        """Create a new task as FHIR resource with projection.

        Args:
            task_data: TaskCreate schema with task fields.

        Returns:
            Tuple of (FhirResource, TaskProjection).
        """
        # Serialize to FHIR Task JSON
        fhir_data = TaskFhirSerializer.to_fhir(task_data)

        # Save via FhirRepository (handles projection sync)
        resource = await self.fhir_repo.save_from_data(
            resource_type="Task",
            fhir_data=fhir_data,
            patient_id=task_data.patient_id,
        )

        # Refresh to get the projection
        await self.db.refresh(resource, ["task_projection"])

        return resource, resource.task_projection

    async def get_by_id(
        self, task_id: uuid.UUID
    ) -> tuple[FhirResource, TaskProjection] | None:
        """Get task by ID.

        Args:
            task_id: UUID of the task (FhirResource.id).

        Returns:
            Tuple of (FhirResource, TaskProjection) if found, None otherwise.
        """
        result = await self.db.execute(
            select(FhirResource)
            .options(joinedload(FhirResource.task_projection))
            .where(
                FhirResource.id == task_id,
                FhirResource.resource_type == "Task",
            )
        )
        resource = result.scalar_one_or_none()

        if resource and resource.task_projection:
            return resource, resource.task_projection
        return None

    async def update(
        self,
        task_id: uuid.UUID,
        task_data: TaskUpdate,
    ) -> tuple[FhirResource, TaskProjection]:
        """Update a task.

        Args:
            task_id: UUID of the task to update.
            task_data: TaskUpdate schema with fields to update.

        Returns:
            Tuple of (FhirResource, TaskProjection).

        Raises:
            ValueError: If task not found.
        """
        result = await self.get_by_id(task_id)
        if not result:
            raise ValueError(f"Task {task_id} not found")

        resource, _ = result
        fhir_data = resource.data.copy()

        # Update FHIR data from task_data
        update_data = task_data.model_dump(exclude_unset=True)

        # Handle status conversion
        if "status" in update_data and update_data["status"] is not None:
            status_value = update_data["status"]
            if hasattr(status_value, "value"):
                status_value = status_value.value
            fhir_data["status"] = TaskFhirSerializer.get_fhir_status(status_value)

            # Handle deferred flag
            if status_value == "deferred":
                self._set_extension(
                    fhir_data,
                    f"{TaskFhirSerializer.CRUXMD_EXTENSION_BASE}/is-deferred",
                    "valueBoolean",
                    True,
                )
            else:
                self._remove_extension(
                    fhir_data,
                    f"{TaskFhirSerializer.CRUXMD_EXTENSION_BASE}/is-deferred",
                )

        # Handle priority
        if "priority" in update_data and update_data["priority"] is not None:
            priority_value = update_data["priority"]
            if hasattr(priority_value, "value"):
                priority_value = priority_value.value
            fhir_data["priority"] = priority_value

        # Handle priority_score
        if "priority_score" in update_data:
            if update_data["priority_score"] is not None:
                self._set_extension(
                    fhir_data,
                    f"{TaskFhirSerializer.CRUXMD_EXTENSION_BASE}/priority-score",
                    "valueInteger",
                    update_data["priority_score"],
                )
            else:
                self._remove_extension(
                    fhir_data,
                    f"{TaskFhirSerializer.CRUXMD_EXTENSION_BASE}/priority-score",
                )

        # Handle title
        if "title" in update_data and update_data["title"] is not None:
            fhir_data["description"] = update_data["title"]

        # Handle description
        if "description" in update_data:
            if update_data["description"]:
                fhir_data["note"] = [{"text": update_data["description"]}]
            else:
                fhir_data.pop("note", None)

        # Handle due_on
        if "due_on" in update_data:
            if update_data["due_on"]:
                due_str = update_data["due_on"]
                if hasattr(due_str, "isoformat"):
                    due_str = due_str.isoformat()
                fhir_data["restriction"] = {"period": {"end": due_str}}
            else:
                fhir_data.pop("restriction", None)

        # Handle session_id
        if "session_id" in update_data:
            if update_data["session_id"]:
                self._set_extension(
                    fhir_data,
                    f"{TaskFhirSerializer.CRUXMD_EXTENSION_BASE}/session-id",
                    "valueString",
                    str(update_data["session_id"]),
                )
            else:
                self._remove_extension(
                    fhir_data,
                    f"{TaskFhirSerializer.CRUXMD_EXTENSION_BASE}/session-id",
                )

        # Handle provenance
        if "provenance" in update_data:
            import json
            if update_data["provenance"]:
                prov_value = update_data["provenance"]
                if hasattr(prov_value, "model_dump"):
                    prov_value = prov_value.model_dump()
                self._set_extension(
                    fhir_data,
                    f"{TaskFhirSerializer.CRUXMD_EXTENSION_BASE}/task-provenance",
                    "valueString",
                    json.dumps(prov_value),
                )
            else:
                self._remove_extension(
                    fhir_data,
                    f"{TaskFhirSerializer.CRUXMD_EXTENSION_BASE}/task-provenance",
                )

        # Handle context_config
        if "context_config" in update_data:
            import json
            if update_data["context_config"]:
                config_value = update_data["context_config"]
                if hasattr(config_value, "model_dump"):
                    config_value = config_value.model_dump()
                self._set_extension(
                    fhir_data,
                    f"{TaskFhirSerializer.CRUXMD_EXTENSION_BASE}/task-context-config",
                    "valueString",
                    json.dumps(config_value),
                )
            else:
                self._remove_extension(
                    fhir_data,
                    f"{TaskFhirSerializer.CRUXMD_EXTENSION_BASE}/task-context-config",
                )

        # Update the resource
        resource.data = fhir_data
        await self.fhir_repo.update(resource)
        await self.db.refresh(resource, ["task_projection"])

        return resource, resource.task_projection

    async def update_status(
        self,
        task_id: uuid.UUID,
        status: str,
    ) -> tuple[FhirResource, TaskProjection]:
        """Update just the task status.

        Args:
            task_id: UUID of the task.
            status: New CruxMD status value.

        Returns:
            Tuple of (FhirResource, TaskProjection).

        Raises:
            ValueError: If task not found.
        """
        result = await self.get_by_id(task_id)
        if not result:
            raise ValueError(f"Task {task_id} not found")

        resource, _ = result
        fhir_data = resource.data.copy()

        # Convert and set status
        fhir_data["status"] = TaskFhirSerializer.get_fhir_status(status)

        # Handle deferred flag
        if status == "deferred":
            self._set_extension(
                fhir_data,
                f"{TaskFhirSerializer.CRUXMD_EXTENSION_BASE}/is-deferred",
                "valueBoolean",
                True,
            )
        else:
            self._remove_extension(
                fhir_data,
                f"{TaskFhirSerializer.CRUXMD_EXTENSION_BASE}/is-deferred",
            )

        resource.data = fhir_data
        await self.fhir_repo.update(resource)
        await self.db.refresh(resource, ["task_projection"])

        return resource, resource.task_projection

    async def delete(self, task_id: uuid.UUID) -> bool:
        """Delete a task.

        Args:
            task_id: UUID of the task to delete.

        Returns:
            True if deleted, False if not found.
        """
        return await self.fhir_repo.delete(task_id)

    async def get_queue(
        self,
        patient_id: uuid.UUID | None = None,
        include_completed: bool = False,
    ) -> dict[str, list[tuple[FhirResource, TaskProjection]]]:
        """Get tasks organized by category for the queue sidebar.

        Args:
            patient_id: Optional filter by patient.
            include_completed: Whether to include completed/cancelled tasks.

        Returns:
            Dict mapping category to list of (FhirResource, TaskProjection) tuples.
        """
        query = (
            select(FhirResource)
            .join(TaskProjection)
            .options(joinedload(FhirResource.task_projection))
            .where(FhirResource.resource_type == "Task")
        )

        if patient_id:
            query = query.where(FhirResource.patient_id == patient_id)

        if not include_completed:
            query = query.where(
                TaskProjection.status.in_(["pending", "in_progress", "paused"])
            )

        query = query.order_by(
            TaskProjection.priority_score.desc().nullslast(),
            FhirResource.created_at.desc(),
        )

        result = await self.db.execute(query)
        resources = result.scalars().unique().all()

        # Group by category
        grouped: dict[str, list[tuple[FhirResource, TaskProjection]]] = {
            "critical": [],
            "routine": [],
            "schedule": [],
            "research": [],
        }

        for resource in resources:
            proj = resource.task_projection
            if proj:
                category = proj.category or "routine"
                if category in grouped:
                    grouped[category].append((resource, proj))

        return grouped

    async def list_tasks(
        self,
        patient_id: uuid.UUID | None = None,
        status: str | None = None,
        category: str | None = None,
        task_type: str | None = None,
        skip: int = 0,
        limit: int = 50,
    ) -> tuple[list[tuple[FhirResource, TaskProjection]], int]:
        """List tasks with filtering using projection table.

        Args:
            patient_id: Filter by patient UUID.
            status: Filter by CruxMD status.
            category: Filter by category.
            task_type: Filter by task type.
            skip: Pagination offset.
            limit: Pagination limit.

        Returns:
            Tuple of (list of (FhirResource, TaskProjection), total count).
        """
        # Base query
        query = (
            select(FhirResource)
            .join(TaskProjection)
            .options(joinedload(FhirResource.task_projection))
            .where(FhirResource.resource_type == "Task")
        )

        # Count query
        count_query = (
            select(func.count())
            .select_from(FhirResource)
            .join(TaskProjection)
            .where(FhirResource.resource_type == "Task")
        )

        # Apply filters
        if patient_id:
            query = query.where(FhirResource.patient_id == patient_id)
            count_query = count_query.where(FhirResource.patient_id == patient_id)

        if status:
            query = query.where(TaskProjection.status == status)
            count_query = count_query.where(TaskProjection.status == status)

        if category:
            query = query.where(TaskProjection.category == category)
            count_query = count_query.where(TaskProjection.category == category)

        if task_type:
            query = query.where(TaskProjection.task_type == task_type)
            count_query = count_query.where(TaskProjection.task_type == task_type)

        # Get total count
        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        # Apply ordering and pagination
        query = query.order_by(
            TaskProjection.priority_score.desc().nullslast(),
            FhirResource.created_at.desc(),
        ).offset(skip).limit(limit)

        result = await self.db.execute(query)
        resources = result.scalars().unique().all()

        return [(r, r.task_projection) for r in resources if r.task_projection], total

    def _set_extension(
        self,
        fhir_data: dict,
        url: str,
        value_key: str,
        value: Any,
    ) -> None:
        """Set or update an extension in FHIR data.

        Args:
            fhir_data: FHIR resource data dict.
            url: Extension URL.
            value_key: Key for the value (e.g., 'valueString', 'valueInteger').
            value: The value to set.
        """
        if "extension" not in fhir_data:
            fhir_data["extension"] = []

        # Find existing extension
        for ext in fhir_data["extension"]:
            if ext.get("url") == url:
                ext[value_key] = value
                return

        # Add new extension
        fhir_data["extension"].append({"url": url, value_key: value})

    def _remove_extension(self, fhir_data: dict, url: str) -> None:
        """Remove an extension from FHIR data.

        Args:
            fhir_data: FHIR resource data dict.
            url: Extension URL to remove.
        """
        if "extension" not in fhir_data:
            return

        fhir_data["extension"] = [
            ext for ext in fhir_data["extension"] if ext.get("url") != url
        ]

        # Clean up empty extension array
        if not fhir_data["extension"]:
            del fhir_data["extension"]
