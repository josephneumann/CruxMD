"""Session model for conversation persistence and handoff.

Sessions represent conversation containers linked to a patient.
Sessions support parent-child relationships for handoff.
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


class SessionStatus(str, enum.Enum):
    """Session lifecycle states."""

    ACTIVE = "active"
    COMPLETED = "completed"


class Session(Base):
    """Conversation session linked to a patient.

    Parent-child relationships enable handoff.
    """

    __tablename__ = "sessions"

    # === Identity ===
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # === Classification ===
    status: Mapped[SessionStatus] = mapped_column(
        Enum(
            SessionStatus,
            name="session_status",
            create_constraint=True,
            values_callable=lambda x: [e.value for e in x],
        ),
        nullable=False,
        default=SessionStatus.ACTIVE,
        index=True,
    )

    # === References ===
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fhir_resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    parent_session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Parent session for handoff chain",
    )

    # === Content ===
    name: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="User-editable session name",
    )
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
        return f"<Session(id={self.id}, status={self.status})>"
