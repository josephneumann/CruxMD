"""Task model for actionable clinical work items.

Tasks represent work that needs clinical attention - critical lab reviews,
patient messages, pre-visit prep, etc. Each task has AI provenance tracking
and context configuration for the UI sidebar.
"""

import enum
import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaskType(str, enum.Enum):
    """Types of clinical tasks."""

    CRITICAL_LAB_REVIEW = "critical_lab_review"
    ABNORMAL_RESULT = "abnormal_result"
    HOSPITALIZATION_ALERT = "hospitalization_alert"
    PATIENT_MESSAGE = "patient_message"
    EXTERNAL_RESULT = "external_result"
    PRE_VISIT_PREP = "pre_visit_prep"
    FOLLOW_UP = "follow_up"
    APPOINTMENT = "appointment"
    RESEARCH_REVIEW = "research_review"
    ORDER_SIGNATURE = "order_signature"
    CUSTOM = "custom"


class TaskCategory(str, enum.Enum):
    """Task categories for queue organization."""

    CRITICAL = "critical"
    ROUTINE = "routine"
    SCHEDULE = "schedule"
    RESEARCH = "research"


class TaskStatus(str, enum.Enum):
    """Task lifecycle states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DEFERRED = "deferred"


class TaskPriority(str, enum.Enum):
    """FHIR-aligned priority levels."""

    ROUTINE = "routine"
    URGENT = "urgent"
    ASAP = "asap"
    STAT = "stat"


class Task(Base):
    """Clinical task requiring attention.

    Based on FHIR Task resource with CruxMD extensions for AI provenance
    and dynamic context configuration.
    """

    __tablename__ = "tasks"

    # === Identity ===
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # === Classification ===
    type: Mapped[TaskType] = mapped_column(
        Enum(TaskType, name="task_type", create_constraint=True),
        nullable=False,
        index=True,
    )
    category: Mapped[TaskCategory] = mapped_column(
        Enum(TaskCategory, name="task_category", create_constraint=True),
        nullable=False,
        index=True,
    )

    # === Status ===
    status: Mapped[TaskStatus] = mapped_column(
        Enum(TaskStatus, name="task_status", create_constraint=True),
        nullable=False,
        default=TaskStatus.PENDING,
        index=True,
    )

    # === Priority ===
    priority: Mapped[TaskPriority] = mapped_column(
        Enum(TaskPriority, name="task_priority", create_constraint=True),
        nullable=False,
        default=TaskPriority.ROUTINE,
    )
    priority_score: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="0-100 computed ranking for queue ordering",
    )

    # === Content ===
    title: Mapped[str] = mapped_column(
        String(140),
        nullable=False,
        comment="Short task title (<140 chars)",
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Detailed description (markdown supported)",
    )

    # === References ===
    patient_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fhir_resources.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Links to conversation session",
    )
    focus_resource_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fhir_resources.id", ondelete="SET NULL"),
        nullable=True,
        comment="FHIR resource being acted on (e.g., the critical lab)",
    )

    # === CruxMD Extensions ===
    provenance: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="AI reasoning and evidence (AITaskProvenance)",
    )
    context_config: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Sidebar configuration (TaskContextConfig)",
    )

    # === Timing ===
    due_on: Mapped[date | None] = mapped_column(
        nullable=True,
        comment="Due date for time-sensitive tasks",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )
    modified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        onupdate=datetime.utcnow,
    )

    __table_args__ = (
        Index("idx_task_patient_status", "patient_id", "status"),
        Index("idx_task_category_status", "category", "status"),
        Index("idx_task_priority_score", "priority_score"),
        Index("idx_task_provenance_gin", "provenance", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<Task(id={self.id}, type={self.type}, title={self.title[:30]}...)>"
