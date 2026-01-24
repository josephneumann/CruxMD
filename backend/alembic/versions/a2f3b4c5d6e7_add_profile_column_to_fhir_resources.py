"""add_profile_column_to_fhir_resources

Revision ID: a2f3b4c5d6e7
Revises: 02debf75f518
Create Date: 2026-01-24

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "a2f3b4c5d6e7"
down_revision: Union[str, Sequence[str], None] = "02debf75f518"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add profile column to fhir_resources table."""
    op.add_column(
        "fhir_resources",
        sa.Column("profile", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    )


def downgrade() -> None:
    """Remove profile column from fhir_resources table."""
    op.drop_column("fhir_resources", "profile")
