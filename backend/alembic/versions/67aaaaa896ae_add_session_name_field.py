"""add session name field

Revision ID: 67aaaaa896ae
Revises: remove_paused_status
Create Date: 2026-02-03 20:59:06.944291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '67aaaaa896ae'
down_revision: Union[str, Sequence[str], None] = 'remove_paused_status'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add name column to sessions table."""
    op.add_column('sessions', sa.Column('name', sa.Text(), nullable=True, comment='User-editable session name'))


def downgrade() -> None:
    """Remove name column from sessions table."""
    op.drop_column('sessions', 'name')
