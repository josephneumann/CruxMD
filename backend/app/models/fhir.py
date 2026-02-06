"""SQLAlchemy models for FHIR resources."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from pgvector.sqlalchemy import Vector
from sqlalchemy import DateTime, Index, String, Text, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base

if TYPE_CHECKING:
    from app.models.projections.task import TaskProjection


class FhirResource(Base):
    """FHIR resource stored with raw JSON data.

    The canonical patient identifier is the PostgreSQL-generated UUID (id),
    not the Synthea-generated fhir_id.
    """

    __tablename__ = "fhir_resources"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    # Identifiers
    fhir_id: Mapped[str] = mapped_column(String(255), nullable=False)
    resource_type: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    patient_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        index=True,
        nullable=True,
    )

    # The actual FHIR resource - stored as raw JSON per CLAUDE.md
    data: Mapped[dict] = mapped_column(JSONB, nullable=False)

    # Embedding for vector similarity search (OpenAI text-embedding-3-small = 1536 dimensions)
    embedding: Mapped[Any | None] = mapped_column(Vector(1536), nullable=True)

    # Text used to generate the embedding (for debugging/inspection)
    embedding_text: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Compiled patient summary (populated for Patient-type resources only)
    compiled_summary: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    compiled_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )

    # Relationships to projection tables
    task_projection: Mapped["TaskProjection | None"] = relationship(
        back_populates="fhir_resource",
        uselist=False,
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_fhir_type_patient", "resource_type", "patient_id"),
        Index("idx_fhir_data_gin", "data", postgresql_using="gin"),
        # Index for idempotency checks during bundle loading
        Index("idx_fhir_id_type", "fhir_id", "resource_type"),
        # HNSW index for cosine similarity searches on embeddings
        Index(
            "idx_fhir_embedding_hnsw",
            "embedding",
            postgresql_using="hnsw",
            postgresql_with={"m": 16, "ef_construction": 64},
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<FhirResource(id={self.id}, type={self.resource_type}, fhir_id={self.fhir_id})>"
