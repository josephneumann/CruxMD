"""add index on session last_active_at

Revision ID: 92f1b9d238fa
Revises: 67aaaaa896ae
Create Date: 2026-02-03 21:54:13.353737

"""
from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '92f1b9d238fa'
down_revision: Union[str, Sequence[str], None] = '67aaaaa896ae'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add index on sessions.last_active_at for sorting queries."""
    op.create_index(
        op.f('ix_sessions_last_active_at'),
        'sessions',
        ['last_active_at'],
        unique=False,
    )


def downgrade() -> None:
    """Remove index on sessions.last_active_at."""
    op.drop_index(op.f('ix_sessions_last_active_at'), table_name='sessions')
