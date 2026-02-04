"""remove_paused_status

Revision ID: remove_paused_status
Revises: simplify_session_model
Create Date: 2026-02-03

Remove 'paused' value from session_status enum.
Sessions are either active or completed - no intermediate state needed.
"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "remove_paused_status"
down_revision: Union[str, Sequence[str], None] = "simplify_session_model"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove 'paused' from session_status enum."""
    # First, update any paused sessions to active
    op.execute("UPDATE sessions SET status = 'active' WHERE status = 'paused'")

    # PostgreSQL doesn't allow removing enum values directly.
    # We need to: drop default, create new enum, update column, drop old enum, restore default.

    # Drop the default value first
    op.execute("ALTER TABLE sessions ALTER COLUMN status DROP DEFAULT")

    # Create new enum type without 'paused'
    op.execute("CREATE TYPE session_status_new AS ENUM ('active', 'completed')")

    # Update the column to use the new type
    op.execute("""
        ALTER TABLE sessions
        ALTER COLUMN status TYPE session_status_new
        USING status::text::session_status_new
    """)

    # Drop the old enum type
    op.execute("DROP TYPE session_status")

    # Rename new enum to the original name
    op.execute("ALTER TYPE session_status_new RENAME TO session_status")

    # Restore the default
    op.execute("ALTER TABLE sessions ALTER COLUMN status SET DEFAULT 'active'")


def downgrade() -> None:
    """Add 'paused' back to session_status enum."""
    # Drop the default value first
    op.execute("ALTER TABLE sessions ALTER COLUMN status DROP DEFAULT")

    # Create new enum type with 'paused'
    op.execute("CREATE TYPE session_status_new AS ENUM ('active', 'paused', 'completed')")

    # Update the column to use the new type
    op.execute("""
        ALTER TABLE sessions
        ALTER COLUMN status TYPE session_status_new
        USING status::text::session_status_new
    """)

    # Drop the old enum type
    op.execute("DROP TYPE session_status")

    # Rename new enum to the original name
    op.execute("ALTER TYPE session_status_new RENAME TO session_status")

    # Restore the default
    op.execute("ALTER TABLE sessions ALTER COLUMN status SET DEFAULT 'active'")
