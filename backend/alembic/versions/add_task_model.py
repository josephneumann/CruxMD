"""add_task_model

Revision ID: add_task_model
Revises: add_embedding_columns
Create Date: 2026-01-26

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "add_task_model"
down_revision: Union[str, Sequence[str], None] = "add_embedding_columns"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create tasks table with enums and indexes."""
    # Create enum types
    task_type_enum = postgresql.ENUM(
        "critical_lab_review",
        "abnormal_result",
        "hospitalization_alert",
        "patient_message",
        "external_result",
        "pre_visit_prep",
        "follow_up",
        "appointment",
        "research_review",
        "order_signature",
        "custom",
        name="task_type",
        create_type=True,
    )
    task_type_enum.create(op.get_bind(), checkfirst=True)

    task_category_enum = postgresql.ENUM(
        "critical",
        "routine",
        "schedule",
        "research",
        name="task_category",
        create_type=True,
    )
    task_category_enum.create(op.get_bind(), checkfirst=True)

    task_status_enum = postgresql.ENUM(
        "pending",
        "in_progress",
        "paused",
        "completed",
        "cancelled",
        "deferred",
        name="task_status",
        create_type=True,
    )
    task_status_enum.create(op.get_bind(), checkfirst=True)

    task_priority_enum = postgresql.ENUM(
        "routine",
        "urgent",
        "asap",
        "stat",
        name="task_priority",
        create_type=True,
    )
    task_priority_enum.create(op.get_bind(), checkfirst=True)

    # Create tasks table
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "type",
            task_type_enum,
            nullable=False,
        ),
        sa.Column(
            "category",
            task_category_enum,
            nullable=False,
        ),
        sa.Column(
            "status",
            task_status_enum,
            nullable=False,
            server_default="pending",
        ),
        sa.Column(
            "priority",
            task_priority_enum,
            nullable=False,
            server_default="routine",
        ),
        sa.Column(
            "priority_score",
            sa.Integer(),
            nullable=True,
            comment="0-100 computed ranking for queue ordering",
        ),
        sa.Column(
            "title",
            sa.String(140),
            nullable=False,
            comment="Short task title (<140 chars)",
        ),
        sa.Column(
            "description",
            sa.Text(),
            nullable=True,
            comment="Detailed description (markdown supported)",
        ),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="Links to conversation session",
        ),
        sa.Column(
            "focus_resource_id",
            postgresql.UUID(as_uuid=True),
            nullable=True,
            comment="FHIR resource being acted on (e.g., the critical lab)",
        ),
        sa.Column(
            "provenance",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="AI reasoning and evidence (AITaskProvenance)",
        ),
        sa.Column(
            "context_config",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
            comment="Sidebar configuration (TaskContextConfig)",
        ),
        sa.Column(
            "due_on",
            sa.Date(),
            nullable=True,
            comment="Due date for time-sensitive tasks",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "modified_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.ForeignKeyConstraint(
            ["patient_id"],
            ["fhir_resources.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["focus_resource_id"],
            ["fhir_resources.id"],
            ondelete="SET NULL",
        ),
    )

    # Create indexes
    op.create_index("ix_tasks_type", "tasks", ["type"], unique=False)
    op.create_index("ix_tasks_category", "tasks", ["category"], unique=False)
    op.create_index("ix_tasks_status", "tasks", ["status"], unique=False)
    op.create_index("ix_tasks_patient_id", "tasks", ["patient_id"], unique=False)
    op.create_index("ix_tasks_session_id", "tasks", ["session_id"], unique=False)
    op.create_index(
        "idx_task_patient_status",
        "tasks",
        ["patient_id", "status"],
        unique=False,
    )
    op.create_index(
        "idx_task_category_status",
        "tasks",
        ["category", "status"],
        unique=False,
    )
    op.create_index(
        "idx_task_priority_score",
        "tasks",
        ["priority_score"],
        unique=False,
    )
    op.create_index(
        "idx_task_provenance_gin",
        "tasks",
        ["provenance"],
        unique=False,
        postgresql_using="gin",
    )


def downgrade() -> None:
    """Drop tasks table and enum types."""
    # Drop indexes
    op.drop_index("idx_task_provenance_gin", table_name="tasks")
    op.drop_index("idx_task_priority_score", table_name="tasks")
    op.drop_index("idx_task_category_status", table_name="tasks")
    op.drop_index("idx_task_patient_status", table_name="tasks")
    op.drop_index("ix_tasks_session_id", table_name="tasks")
    op.drop_index("ix_tasks_patient_id", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_category", table_name="tasks")
    op.drop_index("ix_tasks_type", table_name="tasks")

    # Drop table
    op.drop_table("tasks")

    # Drop enum types
    op.execute("DROP TYPE IF EXISTS task_priority")
    op.execute("DROP TYPE IF EXISTS task_status")
    op.execute("DROP TYPE IF EXISTS task_category")
    op.execute("DROP TYPE IF EXISTS task_type")
