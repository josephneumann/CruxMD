"""Task repository.

High-level task operations that use the TaskProjection for fast indexed queries
while storing canonical data as FHIR Task resources.
"""

from __future__ import annotations

import uuid
from typing import TYPE_CHECKING

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.models.fhir import FhirResource
from app.models.projections.task import TaskProjection
from app.projections.registry import ProjectionRegistry
from app.repositories.fhir import FhirRepository
from app.schemas.task import (
    TaskCategory,
    TaskResponse,
    TaskStatus,
    TaskCategory as TaskCategorySchema,
    TaskStatus as TaskStatusSchema,
    TaskType as TaskTypeSchema,
)

if TYPE_CHECKING:
    from app.schemas.task import TaskCreate, TaskUpdate


def projection_to_response(resource: FhirResource, projection: TaskProjection) -> TaskResponse:
    """Convert a FhirResource and TaskProjection to API response schema.

    Args:
        resource: The FhirResource containing the canonical FHIR Task JSON.
        projection: The TaskProjection with indexed fields.

    Returns:
        TaskResponse for API response.
    """
    return TaskResponse(
        id=resource.id,
        type=TaskTypeSchema(projection.task_type) if projection.task_type else TaskTypeSchema.CUSTOM,
        category=TaskCategorySchema(projection.category) if projection.category else TaskCategorySchema.ROUTINE,
        status=TaskStatusSchema(projection.status),
        priority=projection.priority,
        priority_score=projection.priority_score,
        title=projection.title,
        description=projection.description,
        patient_id=resource.patient_id,
        session_id=uuid.UUID(projection.session_id) if projection.session_id else None,
        focus_resource_id=uuid.UUID(projection.focus_resource_id) if projection.focus_resource_id else None,
        provenance=projection.provenance,
        context_config=projection.context_config,
        due_on=projection.due_on,
        created_at=resource.created_at,
        modified_at=projection.projected_at,
    )


class TaskNotFoundError(ValueError):
    """Raised when a task is not found."""

    pass


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

        Raises:
            RuntimeError: If Task projection is not registered.
        """
        self.db = db
        self.fhir_repo = FhirRepository(db)

        config = ProjectionRegistry.get("Task")
        if not config:
            raise RuntimeError("Task projection not registered. Call register_task_projection() at startup.")
        self._serializer = config.serializer_class

    def _base_task_query(self) -> Select[tuple[FhirResource]]:
        """Build base query for task listing."""
        return (
            select(FhirResource)
            .join(TaskProjection)
            .options(joinedload(FhirResource.task_projection))
            .where(FhirResource.resource_type == "Task")
        )

    def _apply_ordering(self, query: Select[tuple[FhirResource]]) -> Select[tuple[FhirResource]]:
        """Apply standard task ordering (by priority score, then created date)."""
        return query.order_by(
            TaskProjection.priority_score.desc().nullslast(),
            FhirResource.created_at.desc(),
        )

    async def create(self, task_data: TaskCreate) -> tuple[FhirResource, TaskProjection]:
        """Create a new task as FHIR resource with projection."""
        fhir_data = self._serializer.to_fhir(task_data)

        resource = await self.fhir_repo.save_from_data(
            resource_type="Task",
            fhir_data=fhir_data,
            patient_id=task_data.patient_id,
        )

        await self.db.refresh(resource, ["task_projection"])
        return resource, resource.task_projection

    async def get_by_id(self, task_id: uuid.UUID) -> tuple[FhirResource, TaskProjection] | None:
        """Get task by ID."""
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

    async def update(self, task_id: uuid.UUID, task_data: TaskUpdate) -> tuple[FhirResource, TaskProjection]:
        """Update a task.

        Raises:
            TaskNotFoundError: If task not found.
        """
        result = await self.get_by_id(task_id)
        if not result:
            raise TaskNotFoundError(f"Task {task_id} not found")

        resource, _ = result
        updates = task_data.model_dump(exclude_unset=True)
        resource.data = self._serializer.update_fhir_data(resource.data, updates)

        await self.fhir_repo.update(resource)
        await self.db.refresh(resource, ["task_projection"])

        return resource, resource.task_projection

    async def delete(self, task_id: uuid.UUID) -> bool:
        """Delete a task."""
        return await self.fhir_repo.delete(task_id)

    async def get_queue(
        self,
        patient_id: uuid.UUID | None = None,
        include_completed: bool = False,
    ) -> dict[str, list[tuple[FhirResource, TaskProjection]]]:
        """Get tasks organized by category for the queue sidebar."""
        query = self._base_task_query()

        if patient_id:
            query = query.where(FhirResource.patient_id == patient_id)

        if not include_completed:
            active_statuses = [TaskStatus.PENDING.value, TaskStatus.IN_PROGRESS.value, TaskStatus.PAUSED.value]
            query = query.where(TaskProjection.status.in_(active_statuses))

        query = self._apply_ordering(query)

        result = await self.db.execute(query)
        resources = result.scalars().unique().all()

        grouped: dict[str, list[tuple[FhirResource, TaskProjection]]] = {
            TaskCategory.CRITICAL.value: [],
            TaskCategory.ROUTINE.value: [],
            TaskCategory.SCHEDULE.value: [],
            TaskCategory.RESEARCH.value: [],
        }

        for resource in resources:
            proj = resource.task_projection
            if proj:
                category = proj.category or TaskCategory.ROUTINE.value
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
        """List tasks with filtering using projection table."""
        query = self._base_task_query()
        count_query = (
            select(func.count())
            .select_from(FhirResource)
            .join(TaskProjection)
            .where(FhirResource.resource_type == "Task")
        )

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

        total_result = await self.db.execute(count_query)
        total = total_result.scalar() or 0

        query = self._apply_ordering(query).offset(skip).limit(limit)

        result = await self.db.execute(query)
        resources = result.scalars().unique().all()

        return [(r, r.task_projection) for r in resources if r.task_projection], total
