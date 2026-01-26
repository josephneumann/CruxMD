"""Task API routes.

CRUD endpoints for clinical tasks with filtering by patient, category, and status.
Tasks are stored as FHIR Task resources with projections for fast indexed queries.
"""

import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_api_key
from app.database import get_db
from app.models.fhir import FhirResource
from app.models.projections.task import TaskProjection
from app.projections.extractors.task import register_task_projection
from app.repositories.task import TaskRepository
from app.schemas.task import (
    TaskCategory as TaskCategorySchema,
    TaskCreate,
    TaskListResponse,
    TaskQueueResponse,
    TaskResponse,
    TaskStatus as TaskStatusSchema,
    TaskType as TaskTypeSchema,
    TaskUpdate,
)

router = APIRouter(prefix="/tasks", tags=["tasks"])

# Pagination defaults
DEFAULT_PAGE_SIZE = 50
MAX_PAGE_SIZE = 100

# Register task projection on module load
register_task_projection()


def _to_response(resource: FhirResource, projection: TaskProjection) -> TaskResponse:
    """Convert FhirResource and TaskProjection to TaskResponse.

    Args:
        resource: The FhirResource containing FHIR Task JSON.
        projection: The TaskProjection with extracted/indexed fields.

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
        description=resource.data.get("note", [{}])[0].get("text") if resource.data.get("note") else None,
        patient_id=resource.patient_id,
        session_id=uuid.UUID(projection.session_id) if projection.session_id else None,
        focus_resource_id=uuid.UUID(projection.focus_resource_id) if projection.focus_resource_id else None,
        provenance=projection.provenance,
        context_config=projection.context_config,
        due_on=projection.due_on,
        created_at=resource.created_at,
        modified_at=projection.projected_at,
    )


@router.get("", response_model=TaskListResponse)
async def list_tasks(
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
    skip: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    patient_id: uuid.UUID | None = None,
    category: TaskCategorySchema | None = None,
    status: TaskStatusSchema | None = None,
    type: TaskTypeSchema | None = None,
) -> TaskListResponse:
    """List tasks with optional filtering and pagination.

    Args:
        skip: Number of records to skip (pagination offset).
        limit: Maximum number of records to return.
        patient_id: Filter by patient UUID.
        category: Filter by task category.
        status: Filter by task status.
        type: Filter by task type.

    Returns:
        Paginated list of tasks.
    """
    repo = TaskRepository(db)
    rows, total = await repo.list_tasks(
        patient_id=patient_id,
        status=status.value if status else None,
        category=category.value if category else None,
        task_type=type.value if type else None,
        skip=skip,
        limit=limit,
    )

    return TaskListResponse(
        items=[_to_response(res, proj) for res, proj in rows],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/queue", response_model=TaskQueueResponse)
async def get_task_queue(
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
    patient_id: uuid.UUID | None = None,
    include_completed: bool = False,
) -> TaskQueueResponse:
    """Get tasks organized by category for the task queue sidebar.

    Returns tasks grouped by category (critical, routine, schedule, research),
    ordered by priority score within each category.

    Args:
        patient_id: Optional filter by patient.
        include_completed: Whether to include completed/cancelled tasks.

    Returns:
        Tasks organized by category.
    """
    repo = TaskRepository(db)
    grouped = await repo.get_queue(
        patient_id=patient_id,
        include_completed=include_completed,
    )

    # Count total tasks
    total = sum(len(tasks) for tasks in grouped.values())

    return TaskQueueResponse(
        critical=[_to_response(res, proj) for res, proj in grouped["critical"]],
        routine=[_to_response(res, proj) for res, proj in grouped["routine"]],
        schedule=[_to_response(res, proj) for res, proj in grouped["schedule"]],
        research=[_to_response(res, proj) for res, proj in grouped["research"]],
        total=total,
    )


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
) -> TaskResponse:
    """Get a single task by ID.

    Args:
        task_id: The task UUID.

    Returns:
        The task details.

    Raises:
        HTTPException: 404 if task not found.
    """
    repo = TaskRepository(db)
    result = await repo.get_by_id(task_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    resource, projection = result
    return _to_response(resource, projection)


@router.get("/{task_id}/fhir")
async def get_task_fhir(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
) -> dict:
    """Get the raw FHIR Task JSON for a task.

    Args:
        task_id: The task UUID.

    Returns:
        The FHIR Task resource JSON.

    Raises:
        HTTPException: 404 if task not found.
    """
    repo = TaskRepository(db)
    result = await repo.get_by_id(task_id)

    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    resource, _ = result
    return resource.data


@router.post("", response_model=TaskResponse, status_code=status.HTTP_201_CREATED)
async def create_task(
    task_data: TaskCreate,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
) -> TaskResponse:
    """Create a new task.

    Args:
        task_data: Task creation data.

    Returns:
        The created task.
    """
    repo = TaskRepository(db)
    resource, projection = await repo.create(task_data)
    return _to_response(resource, projection)


@router.patch("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    task_data: TaskUpdate,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
) -> TaskResponse:
    """Update an existing task.

    Args:
        task_id: The task UUID.
        task_data: Fields to update.

    Returns:
        The updated task.

    Raises:
        HTTPException: 404 if task not found.
    """
    repo = TaskRepository(db)

    try:
        resource, projection = await repo.update(task_id, task_data)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return _to_response(resource, projection)


@router.delete("/{task_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_task(
    task_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
) -> None:
    """Delete a task.

    Args:
        task_id: The task UUID.

    Raises:
        HTTPException: 404 if task not found.
    """
    repo = TaskRepository(db)
    deleted = await repo.delete(task_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )
