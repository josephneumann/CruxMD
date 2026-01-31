"""add_session_model

Revision ID: add_session_model
Revises: add_better_auth_tables
Create Date: 2026-01-31

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "add_session_model"
down_revision: Union[str, Sequence[str], None] = "add_better_auth_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create sessions table with enums and indexes."""
    session_type_enum = postgresql.ENUM(
        "orchestrating",
        "patient_task",
        name="session_type",
        create_type=True,
    )
    session_type_enum.create(op.get_bind(), checkfirst=True)

    session_status_enum = postgresql.ENUM(
        "active",
        "paused",
        "completed",
        name="session_status",
        create_type=True,
    )
    session_status_enum.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("type", session_type_enum, nullable=False),
        sa.Column("status", session_status_enum, nullable=False, server_default="active"),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fhir_resources.id", ondelete="CASCADE"), nullable=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("fhir_resources.id", ondelete="SET NULL"), nullable=True, comment="Task this session is working on (for patient_task type)"),
        sa.Column("parent_session_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("sessions.id", ondelete="SET NULL"), nullable=True, comment="Parent session for handoff chain"),
        sa.Column("summary", sa.Text, nullable=True, comment="Session summary for handoff context"),
        sa.Column("messages", postgresql.JSONB, nullable=False, server_default=sa.text("'[]'::jsonb"), comment="Conversation messages array"),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("last_active_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    op.create_index("ix_sessions_type", "sessions", ["type"])
    op.create_index("ix_sessions_status", "sessions", ["status"])
    op.create_index("ix_sessions_patient_id", "sessions", ["patient_id"])
    op.create_index("ix_sessions_task_id", "sessions", ["task_id"])
    op.create_index("ix_sessions_parent_session_id", "sessions", ["parent_session_id"])
    op.create_index("idx_session_patient_status", "sessions", ["patient_id", "status"])


def downgrade() -> None:
    """Drop sessions table and enums."""
    op.drop_table("sessions")
    op.execute("DROP TYPE IF EXISTS session_type")
    op.execute("DROP TYPE IF EXISTS session_status")
