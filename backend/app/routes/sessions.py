"""Session API routes.

CRUD endpoints for conversation sessions with filtering by status and patient.
Includes handoff endpoint for creating child sessions from a parent.
"""

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_bearer_token
from app.constants import DEFAULT_PAGE_SIZE, MAX_PAGE_SIZE
from app.database import get_db
from app.models.session import Session
from app.models.session import SessionStatus as SessionStatusModel
from app.schemas.session import (
    SessionCreate,
    SessionHandoff,
    SessionListResponse,
    SessionResponse,
    SessionStatus as SessionStatusSchema,
    SessionUpdate,
)

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.get("", response_model=SessionListResponse)
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    _user_id: str = Depends(verify_bearer_token),
    skip: int = Query(0, ge=0),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE),
    patient_id: uuid.UUID | None = None,
    status_filter: SessionStatusSchema | None = Query(None, alias="status"),
) -> SessionListResponse:
    """List sessions with optional filtering and pagination.

    Args:
        skip: Number of records to skip (pagination offset).
        limit: Maximum number of records to return.
        patient_id: Filter by patient UUID.
        status_filter: Filter by session status (active, paused, completed).

    Returns:
        Paginated list of sessions ordered by last activity.
    """
    query = select(Session)
    count_query = select(func.count()).select_from(Session)

    if patient_id:
        query = query.where(Session.patient_id == patient_id)
        count_query = count_query.where(Session.patient_id == patient_id)

    if status_filter:
        query = query.where(Session.status == SessionStatusModel(status_filter.value))
        count_query = count_query.where(Session.status == SessionStatusModel(status_filter.value))

    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    query = query.order_by(Session.last_active_at.desc()).offset(skip).limit(limit)
    result = await db.execute(query)
    sessions = result.scalars().all()

    return SessionListResponse(
        items=[SessionResponse.model_validate(s) for s in sessions],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.get("/{session_id}", response_model=SessionResponse)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _user_id: str = Depends(verify_bearer_token),
) -> SessionResponse:
    """Get a single session by ID.

    Args:
        session_id: The session UUID.

    Returns:
        The session details.

    Raises:
        HTTPException: 404 if session not found.
    """
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    return SessionResponse.model_validate(session)


@router.post("", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_session(
    session_data: SessionCreate,
    db: AsyncSession = Depends(get_db),
    _user_id: str = Depends(verify_bearer_token),
) -> SessionResponse:
    """Create a new session.

    Args:
        session_data: Session creation data.

    Returns:
        The created session.
    """
    session = Session(
        patient_id=session_data.patient_id,
        parent_session_id=session_data.parent_session_id,
        summary=session_data.summary,
        messages=[],
    )
    db.add(session)
    await db.flush()
    await db.refresh(session)
    return SessionResponse.model_validate(session)


@router.patch("/{session_id}", response_model=SessionResponse)
async def update_session(
    session_id: uuid.UUID,
    session_data: SessionUpdate,
    db: AsyncSession = Depends(get_db),
    _user_id: str = Depends(verify_bearer_token),
) -> SessionResponse:
    """Update an existing session.

    Supports updating status (pause, complete), summary, and messages.
    Automatically sets completed_at when status changes to completed.

    Args:
        session_id: The session UUID.
        session_data: Fields to update.

    Returns:
        The updated session.

    Raises:
        HTTPException: 404 if session not found.
    """
    result = await db.execute(select(Session).where(Session.id == session_id))
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found",
        )

    updates = session_data.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if field == "status":
            setattr(session, field, SessionStatusModel(value))
            if value == SessionStatusSchema.COMPLETED.value:
                session.completed_at = datetime.now(timezone.utc)
        else:
            setattr(session, field, value)

    await db.flush()
    await db.refresh(session)
    return SessionResponse.model_validate(session)


@router.post("/{session_id}/handoff", response_model=SessionResponse, status_code=status.HTTP_201_CREATED)
async def create_handoff(
    session_id: uuid.UUID,
    handoff_data: SessionHandoff,
    db: AsyncSession = Depends(get_db),
    _user_id: str = Depends(verify_bearer_token),
) -> SessionResponse:
    """Create a handoff from an existing session.

    Pauses the parent session and creates a new child session
    with the provided summary as context. Child inherits patient_id
    from parent unless overridden.

    Args:
        session_id: The parent session UUID.
        handoff_data: Handoff creation data with summary context.

    Returns:
        The newly created child session.

    Raises:
        HTTPException: 404 if parent session not found.
    """
    result = await db.execute(select(Session).where(Session.id == session_id))
    parent = result.scalar_one_or_none()

    if parent is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Parent session not found",
        )

    # Pause the parent
    parent.status = SessionStatusModel.PAUSED

    # Create child session
    child = Session(
        status=SessionStatusModel.ACTIVE,
        patient_id=handoff_data.patient_id or parent.patient_id,
        parent_session_id=session_id,
        summary=handoff_data.summary,
        messages=[],
    )
    db.add(child)
    await db.flush()
    await db.refresh(child)
    return SessionResponse.model_validate(child)
