"""simplify_session_model

Revision ID: simplify_session_model
Revises: add_session_model
Create Date: 2026-02-03

Remove task_id and type from sessions table.
Make patient_id required (NOT NULL).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "simplify_session_model"
down_revision: Union[str, Sequence[str], None] = "add_session_model"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove task_id and type, make patient_id required."""
    # Drop the task_id index and column
    op.drop_index("ix_sessions_task_id", table_name="sessions")
    op.drop_column("sessions", "task_id")

    # Drop the type index and column
    op.drop_index("ix_sessions_type", table_name="sessions")
    op.drop_column("sessions", "type")

    # Drop the session_type enum
    op.execute("DROP TYPE IF EXISTS session_type")

    # Delete any sessions that have NULL patient_id before making it required
    op.execute("DELETE FROM sessions WHERE patient_id IS NULL")

    # Make patient_id NOT NULL
    op.alter_column(
        "sessions",
        "patient_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )


def downgrade() -> None:
    """Restore task_id and type columns."""
    # Make patient_id nullable again
    op.alter_column(
        "sessions",
        "patient_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )

    # Recreate session_type enum
    session_type_enum = postgresql.ENUM(
        "orchestrating",
        "patient_task",
        name="session_type",
        create_type=False,
    )
    session_type_enum.create(op.get_bind(), checkfirst=True)

    # Add type column back with default value
    op.add_column(
        "sessions",
        sa.Column(
            "type",
            session_type_enum,
            nullable=False,
            server_default="orchestrating",
        ),
    )
    op.create_index("ix_sessions_type", "sessions", ["type"])

    # Add task_id column back
    op.add_column(
        "sessions",
        sa.Column(
            "task_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("fhir_resources.id", ondelete="SET NULL"),
            nullable=True,
            comment="Task this session is working on (for patient_task type)",
        ),
    )
    op.create_index("ix_sessions_task_id", "sessions", ["task_id"])
