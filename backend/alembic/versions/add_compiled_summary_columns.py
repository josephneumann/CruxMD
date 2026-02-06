"""add compiled_summary and compiled_at to fhir_resources

Revision ID: add_compiled_summary_columns
Revises: 92f1b9d238fa
Create Date: 2026-02-05

Add compiled_summary (JSONB) and compiled_at (DateTime with timezone)
columns to fhir_resources. These are populated for Patient-type resources only.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


# revision identifiers, used by Alembic.
revision: str = "add_compiled_summary_columns"
down_revision: Union[str, Sequence[str], None] = "92f1b9d238fa"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add compiled_summary and compiled_at columns to fhir_resources."""
    op.add_column(
        "fhir_resources",
        sa.Column("compiled_summary", JSONB, nullable=True),
    )
    op.add_column(
        "fhir_resources",
        sa.Column("compiled_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    """Remove compiled_summary and compiled_at columns."""
    op.drop_column("fhir_resources", "compiled_at")
    op.drop_column("fhir_resources", "compiled_summary")
