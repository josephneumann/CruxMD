"""Pydantic schemas for Session API.

These schemas define request/response formats for the Session API,
including session creation, updates, handoff, and list responses.
"""

from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# === Enums (match SQLAlchemy enums) ===


class SessionType(str, Enum):
    """Types of conversation sessions."""

    ORCHESTRATING = "orchestrating"
    PATIENT_TASK = "patient_task"


class SessionStatus(str, Enum):
    """Session lifecycle states."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


# === API Request/Response Schemas ===


class SessionCreate(BaseModel):
    """Schema for creating a new session."""

    type: SessionType
    patient_id: UUID | None = None
    task_id: UUID | None = None
    parent_session_id: UUID | None = None
    summary: str | None = Field(default=None, max_length=10000)


class SessionUpdate(BaseModel):
    """Schema for updating a session."""

    status: SessionStatus | None = None
    summary: str | None = Field(default=None, max_length=10000)
    messages: list[dict[str, Any]] | None = Field(default=None, max_length=1000)


class SessionHandoff(BaseModel):
    """Schema for creating a session handoff.

    Creates a new child session from an existing parent,
    preserving context through summary.
    """

    type: SessionType
    summary: str = Field(
        max_length=10000,
        description="Context summary to carry into the new session",
    )
    patient_id: UUID | None = None
    task_id: UUID | None = None


class SessionResponse(BaseModel):
    """Schema for session in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: SessionType
    status: SessionStatus
    patient_id: UUID | None = Field(description="FHIR Patient resource ID")
    task_id: UUID | None = Field(description="FHIR Task resource ID (for patient_task sessions)")
    parent_session_id: UUID | None = Field(description="Parent session for handoff chain")
    summary: str | None = Field(description="Session summary for handoff context")
    messages: list[dict[str, Any]] = Field(description="Conversation messages array")
    started_at: datetime
    last_active_at: datetime
    completed_at: datetime | None


class SessionListResponse(BaseModel):
    """Paginated list of sessions."""

    items: list[SessionResponse]
    total: int
    skip: int
    limit: int
