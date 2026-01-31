"""Session model for conversation persistence and handoff.

Sessions represent conversation containers — either orchestrating sessions
(top-level clinical workflows) or patient_task sessions (focused on a
specific task). Sessions support parent-child relationships for handoff.
"""

from __future__ import annotations

import enum
import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Text, func, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class SessionType(str, enum.Enum):
    """Types of conversation sessions."""

    ORCHESTRATING = "orchestrating"
    PATIENT_TASK = "patient_task"


class SessionStatus(str, enum.Enum):
    """Session lifecycle states."""

    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"


class Session(Base):
    """Conversation session for clinical workflows.

    Supports orchestrating sessions (top-level) and patient_task sessions
    (focused on a specific task). Parent-child relationships enable handoff.
    """

    __tablename__ = "sessions"

    # === Identity ===
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # === Classification ===
    type: Mapped[SessionType] = mapped_column(
        Enum(SessionType, name="session_type", create_constraint=True),
        nullable=False,
        index=True,
    )
    status: Mapped[SessionStatus] = mapped_column(
        Enum(SessionStatus, name="session_status", create_constraint=True),
        nullable=False,
        default=SessionStatus.ACTIVE,
        index=True,
    )

    # === References ===
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fhir_resources.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    task_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fhir_resources.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Task this session is working on (for patient_task type)",
    )
    parent_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Parent session for handoff chain",
    )

    # === Content ===
    summary: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Session summary for handoff context",
    )
    messages: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
        default=list,
        server_default=text("'[]'::jsonb"),
        comment="Conversation messages array",
    )

    # === Timing ===
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
    last_active_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        onupdate=func.now(),
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # === Relationships ===
    parent_session: Mapped[Session | None] = relationship(
        remote_side=[id],
        foreign_keys=[parent_session_id],
    )
    child_sessions: Mapped[list[Session]] = relationship(
        foreign_keys=[parent_session_id],
        viewonly=True,
    )

    __table_args__ = (
        Index("idx_session_patient_status", "patient_id", "status"),
    )

    def __repr__(self) -> str:
        return f"<Session(id={self.id}, type={self.type}, status={self.status})>"
