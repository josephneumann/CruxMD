"""SQLAlchemy models for FHIR resources."""

import uuid
from datetime import datetime

from sqlalchemy import DateTime, Index, String, text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


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

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=text("now()"),
    )

    __table_args__ = (
        Index("idx_fhir_type_patient", "resource_type", "patient_id"),
        Index("idx_fhir_data_gin", "data", postgresql_using="gin"),
    )

    def __repr__(self) -> str:
        return f"<FhirResource(id={self.id}, type={self.resource_type}, fhir_id={self.fhir_id})>"
