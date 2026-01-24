"""add_fhir_id_type_index

Revision ID: add_fhir_id_idx
Revises: 02debf75f518
Create Date: 2026-01-24

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "add_fhir_id_idx"
down_revision: Union[str, Sequence[str], None] = "02debf75f518"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add composite index on (fhir_id, resource_type) for idempotency lookups."""
    op.create_index(
        "idx_fhir_id_type",
        "fhir_resources",
        ["fhir_id", "resource_type"],
        unique=False,
    )


def downgrade() -> None:
    """Remove the fhir_id + resource_type composite index."""
    op.drop_index("idx_fhir_id_type", table_name="fhir_resources")
