"""Task API routes.

CRUD endpoints for clinical tasks with filtering by patient, category, and status.
"""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_api_key
from app.database import get_db
from app.models.task import Task, TaskCategory, TaskStatus
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
    # Build base query
    query = select(Task)

    # Apply filters
    if patient_id is not None:
        query = query.where(Task.patient_id == patient_id)
    if category is not None:
        query = query.where(Task.category == category.value)
    if status is not None:
        query = query.where(Task.status == status.value)
    if type is not None:
        query = query.where(Task.type == type.value)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Apply ordering and pagination
    query = query.order_by(
        Task.priority_score.desc().nullslast(),
        Task.created_at.desc(),
    ).offset(skip).limit(limit)

    result = await db.execute(query)
    tasks = result.scalars().all()

    return TaskListResponse(
        items=[TaskResponse.model_validate(task) for task in tasks],
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
    # Build base query for active tasks
    query = select(Task)

    if patient_id is not None:
        query = query.where(Task.patient_id == patient_id)

    if not include_completed:
        query = query.where(
            Task.status.in_([
                TaskStatus.PENDING,
                TaskStatus.IN_PROGRESS,
                TaskStatus.PAUSED,
            ])
        )

    # Order by priority score
    query = query.order_by(
        Task.priority_score.desc().nullslast(),
        Task.created_at.desc(),
    )

    result = await db.execute(query)
    tasks = result.scalars().all()

    # Group by category
    grouped: dict[str, list[TaskResponse]] = {
        "critical": [],
        "routine": [],
        "schedule": [],
        "research": [],
    }

    for task in tasks:
        category_key = task.category.value
        if category_key in grouped:
            grouped[category_key].append(TaskResponse.model_validate(task))

    return TaskQueueResponse(
        critical=grouped["critical"],
        routine=grouped["routine"],
        schedule=grouped["schedule"],
        research=grouped["research"],
        total=len(tasks),
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
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    return TaskResponse.model_validate(task)


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
    task = Task(
        type=task_data.type.value,
        category=task_data.category.value,
        status=TaskStatus.PENDING,
        priority=task_data.priority.value,
        priority_score=task_data.priority_score,
        title=task_data.title,
        description=task_data.description,
        patient_id=task_data.patient_id,
        session_id=task_data.session_id,
        focus_resource_id=task_data.focus_resource_id,
        provenance=task_data.provenance.model_dump() if task_data.provenance else None,
        context_config=task_data.context_config.model_dump() if task_data.context_config else None,
        due_on=task_data.due_on,
    )

    db.add(task)
    await db.flush()
    await db.refresh(task)

    return TaskResponse.model_validate(task)


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
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    # Update fields that are provided
    update_data = task_data.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if field == "status" and value is not None:
            setattr(task, field, value)
        elif field == "priority" and value is not None:
            setattr(task, field, value)
        elif field == "provenance" and value is not None:
            setattr(task, field, value)
        elif field == "context_config" and value is not None:
            setattr(task, field, value)
        elif value is not None:
            setattr(task, field, value)

    task.modified_at = datetime.utcnow()

    await db.flush()
    await db.refresh(task)

    return TaskResponse.model_validate(task)


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
    result = await db.execute(select(Task).where(Task.id == task_id))
    task = result.scalar_one_or_none()

    if task is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Task not found",
        )

    await db.delete(task)
