"""initial_fhir_resources

Revision ID: 02debf75f518
Revises:
Create Date: 2026-01-17 15:25:02.787072

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "02debf75f518"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create fhir_resources table."""
    op.create_table(
        "fhir_resources",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("fhir_id", sa.String(255), nullable=False),
        sa.Column("resource_type", sa.String(50), nullable=False),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("data", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    # Single column indexes
    op.create_index(
        "ix_fhir_resources_resource_type",
        "fhir_resources",
        ["resource_type"],
        unique=False,
    )
    op.create_index(
        "ix_fhir_resources_patient_id", "fhir_resources", ["patient_id"], unique=False
    )
    # Composite index for type + patient queries
    op.create_index(
        "idx_fhir_type_patient",
        "fhir_resources",
        ["resource_type", "patient_id"],
        unique=False,
    )
    # GIN index for JSONB queries
    op.create_index(
        "idx_fhir_data_gin",
        "fhir_resources",
        ["data"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Drop fhir_resources table."""
    op.drop_index("idx_fhir_data_gin", table_name="fhir_resources")
    op.drop_index("idx_fhir_type_patient", table_name="fhir_resources")
    op.drop_index("ix_fhir_resources_patient_id", table_name="fhir_resources")
    op.drop_index("ix_fhir_resources_resource_type", table_name="fhir_resources")
    op.drop_table("fhir_resources")
