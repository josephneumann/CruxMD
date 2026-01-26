"""add description to task_projections

Revision ID: 51aca4ea95b6
Revises: fhir_projection_system
Create Date: 2026-01-26 13:03:07.385433

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "51aca4ea95b6"
down_revision: Union[str, Sequence[str], None] = "fhir_projection_system"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add description column to task_projections."""
    op.add_column(
        "task_projections",
        sa.Column("description", sa.String(length=2000), nullable=True),
    )


def downgrade() -> None:
    """Remove description column from task_projections."""
    op.drop_column("task_projections", "description")
