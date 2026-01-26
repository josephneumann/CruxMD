"""Task projection model.

Provides indexed access to Task fields extracted from FHIR JSON.
The canonical data lives in fhir_resources.data; this table enables
fast queries by status, category, priority, etc.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.fhir import FhirResource


class TaskProjection(Base):
    """Projection table for FHIR Task resources.

    Extracts commonly queried fields from FHIR Task JSON for indexed access.
    Linked to FhirResource via foreign key with cascade delete.
    """

    __tablename__ = "task_projections"

    # Primary key is also the foreign key to fhir_resources
    fhir_resource_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("fhir_resources.id", ondelete="CASCADE"),
        primary_key=True,
    )

    # Indexed status fields (CruxMD values, not FHIR)
    status: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    priority: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    category: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    task_type: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    priority_score: Mapped[int | None] = mapped_column(Integer, nullable=True, index=True)

    # Content fields
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2000), nullable=True)
    due_on: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Reference fields (stored as strings for flexibility)
    session_id: Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    focus_resource_id: Mapped[str | None] = mapped_column(String(36), nullable=True)

    # CruxMD extensions (kept as JSONB for flexibility)
    provenance: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)
    context_config: Mapped[dict[str, Any] | None] = mapped_column(JSONB, nullable=True)

    # Timestamp for when projection was last synced
    projected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
        nullable=False,
    )

    # Relationship to FhirResource
    fhir_resource: Mapped["FhirResource"] = relationship(
        back_populates="task_projection",
        lazy="joined",
    )

    __table_args__ = (
        # Composite indexes for common query patterns
        Index("ix_task_proj_status_category", "status", "category"),
        Index("ix_task_proj_status_priority", "status", "priority_score"),
        # GIN index on provenance for JSONB queries
        Index("ix_task_proj_provenance_gin", "provenance", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<TaskProjection(fhir_resource_id={self.fhir_resource_id}, title={self.title[:30]}...)>"
