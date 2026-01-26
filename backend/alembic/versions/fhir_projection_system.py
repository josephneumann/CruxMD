"""FHIR projection system - migrate tasks to projections

Revision ID: fhir_projection_system
Revises: add_task_model
Create Date: 2026-01-26

This migration:
1. Creates the task_projections table
2. Migrates existing tasks to fhir_resources + task_projections
3. Drops the old tasks table and enum types
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "fhir_projection_system"
down_revision: Union[str, Sequence[str], None] = "add_task_model"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# CruxMD status to FHIR status mapping
STATUS_MAP = {
    "pending": "requested",
    "in_progress": "in-progress",
    "paused": "on-hold",
    "completed": "completed",
    "cancelled": "cancelled",
    "deferred": "on-hold",
}


def upgrade() -> None:
    """Create task_projections table and migrate data from tasks."""

    # 1. Create task_projections table
    op.create_table(
        "task_projections",
        sa.Column("fhir_resource_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("priority", sa.String(20), nullable=False),
        sa.Column("category", sa.String(50), nullable=True),
        sa.Column("task_type", sa.String(50), nullable=True),
        sa.Column("priority_score", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("due_on", sa.Date(), nullable=True),
        sa.Column("session_id", sa.String(36), nullable=True),
        sa.Column("focus_resource_id", sa.String(36), nullable=True),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("context_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column(
            "projected_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("fhir_resource_id"),
        sa.ForeignKeyConstraint(
            ["fhir_resource_id"],
            ["fhir_resources.id"],
            ondelete="CASCADE",
        ),
    )

    # 2. Create indexes on task_projections
    op.create_index("ix_task_proj_status", "task_projections", ["status"])
    op.create_index("ix_task_proj_priority", "task_projections", ["priority"])
    op.create_index("ix_task_proj_category", "task_projections", ["category"])
    op.create_index("ix_task_proj_task_type", "task_projections", ["task_type"])
    op.create_index("ix_task_proj_priority_score", "task_projections", ["priority_score"])
    op.create_index("ix_task_proj_session_id", "task_projections", ["session_id"])
    op.create_index(
        "ix_task_proj_status_category",
        "task_projections",
        ["status", "category"],
    )
    op.create_index(
        "ix_task_proj_status_priority",
        "task_projections",
        ["status", "priority_score"],
    )
    op.create_index(
        "ix_task_proj_provenance_gin",
        "task_projections",
        ["provenance"],
        postgresql_using="gin",
    )

    # 3. Migrate existing tasks to fhir_resources + task_projections
    # This uses raw SQL for efficiency on bulk data migration

    conn = op.get_bind()

    # Build FHIR Task JSON and insert into fhir_resources
    # Using a CTE to generate the FHIR JSON structure
    conn.execute(sa.text("""
        INSERT INTO fhir_resources (id, fhir_id, resource_type, patient_id, data, created_at)
        SELECT
            t.id,
            t.id::text,
            'Task',
            t.patient_id,
            jsonb_build_object(
                'resourceType', 'Task',
                'id', t.id::text,
                'status', CASE t.status
                    WHEN 'pending' THEN 'requested'
                    WHEN 'in_progress' THEN 'in-progress'
                    WHEN 'paused' THEN 'on-hold'
                    WHEN 'completed' THEN 'completed'
                    WHEN 'cancelled' THEN 'cancelled'
                    WHEN 'deferred' THEN 'on-hold'
                    ELSE 'requested'
                END,
                'intent', 'order',
                'priority', t.priority::text,
                'description', t.title,
                'authoredOn', t.created_at,
                'code', jsonb_build_object(
                    'coding', jsonb_build_array(
                        jsonb_build_object(
                            'system', 'https://cruxmd.com/fhir/task-type',
                            'code', t.type::text,
                            'display', INITCAP(REPLACE(t.type::text, '_', ' '))
                        ),
                        jsonb_build_object(
                            'system', 'https://cruxmd.com/fhir/task-category',
                            'code', t.category::text,
                            'display', INITCAP(t.category::text)
                        )
                    )
                ),
                'for', jsonb_build_object('reference', 'Patient/' || t.patient_id::text),
                'extension', (
                    SELECT COALESCE(jsonb_agg(ext) FILTER (WHERE ext IS NOT NULL), '[]'::jsonb)
                    FROM (
                        SELECT jsonb_build_object(
                            'url', 'https://cruxmd.com/fhir/extensions/priority-score',
                            'valueInteger', t.priority_score
                        ) AS ext WHERE t.priority_score IS NOT NULL
                        UNION ALL
                        SELECT jsonb_build_object(
                            'url', 'https://cruxmd.com/fhir/extensions/task-provenance',
                            'valueString', t.provenance::text
                        ) WHERE t.provenance IS NOT NULL
                        UNION ALL
                        SELECT jsonb_build_object(
                            'url', 'https://cruxmd.com/fhir/extensions/task-context-config',
                            'valueString', t.context_config::text
                        ) WHERE t.context_config IS NOT NULL
                        UNION ALL
                        SELECT jsonb_build_object(
                            'url', 'https://cruxmd.com/fhir/extensions/session-id',
                            'valueString', t.session_id::text
                        ) WHERE t.session_id IS NOT NULL
                        UNION ALL
                        SELECT jsonb_build_object(
                            'url', 'https://cruxmd.com/fhir/extensions/is-deferred',
                            'valueBoolean', true
                        ) WHERE t.status = 'deferred'
                    ) extensions
                )
            ) ||
            CASE WHEN t.description IS NOT NULL THEN
                jsonb_build_object('note', jsonb_build_array(jsonb_build_object('text', t.description)))
            ELSE '{}'::jsonb END ||
            CASE WHEN t.due_on IS NOT NULL THEN
                jsonb_build_object('restriction', jsonb_build_object('period', jsonb_build_object('end', t.due_on::text)))
            ELSE '{}'::jsonb END ||
            CASE WHEN t.focus_resource_id IS NOT NULL THEN
                jsonb_build_object('focus', jsonb_build_object('reference', 'Resource/' || t.focus_resource_id::text))
            ELSE '{}'::jsonb END,
            t.created_at
        FROM tasks t
    """))

    # Insert projections for the migrated tasks
    conn.execute(sa.text("""
        INSERT INTO task_projections (
            fhir_resource_id, status, priority, category, task_type,
            priority_score, title, due_on, session_id, focus_resource_id,
            provenance, context_config, projected_at
        )
        SELECT
            t.id,
            t.status::text,
            t.priority::text,
            t.category::text,
            t.type::text,
            t.priority_score,
            t.title,
            t.due_on,
            t.session_id::text,
            t.focus_resource_id::text,
            t.provenance,
            t.context_config,
            now()
        FROM tasks t
    """))

    # 4. Drop old tasks table indexes
    op.drop_index("idx_task_provenance_gin", table_name="tasks")
    op.drop_index("idx_task_priority_score", table_name="tasks")
    op.drop_index("idx_task_category_status", table_name="tasks")
    op.drop_index("idx_task_patient_status", table_name="tasks")
    op.drop_index("ix_tasks_session_id", table_name="tasks")
    op.drop_index("ix_tasks_patient_id", table_name="tasks")
    op.drop_index("ix_tasks_status", table_name="tasks")
    op.drop_index("ix_tasks_category", table_name="tasks")
    op.drop_index("ix_tasks_type", table_name="tasks")

    # 5. Drop tasks table
    op.drop_table("tasks")

    # 6. Drop enum types (no longer needed - projections use strings)
    op.execute("DROP TYPE IF EXISTS task_priority")
    op.execute("DROP TYPE IF EXISTS task_status")
    op.execute("DROP TYPE IF EXISTS task_category")
    op.execute("DROP TYPE IF EXISTS task_type")


def downgrade() -> None:
    """Recreate tasks table and migrate data back from projections."""

    # 1. Recreate enum types
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

    # 2. Recreate tasks table
    op.create_table(
        "tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("type", task_type_enum, nullable=False),
        sa.Column("category", task_category_enum, nullable=False),
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
        sa.Column("priority_score", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(140), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("patient_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("focus_resource_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("provenance", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("context_config", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("due_on", sa.Date(), nullable=True),
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

    # 3. Create indexes on tasks
    op.create_index("ix_tasks_type", "tasks", ["type"])
    op.create_index("ix_tasks_category", "tasks", ["category"])
    op.create_index("ix_tasks_status", "tasks", ["status"])
    op.create_index("ix_tasks_patient_id", "tasks", ["patient_id"])
    op.create_index("ix_tasks_session_id", "tasks", ["session_id"])
    op.create_index("idx_task_patient_status", "tasks", ["patient_id", "status"])
    op.create_index("idx_task_category_status", "tasks", ["category", "status"])
    op.create_index("idx_task_priority_score", "tasks", ["priority_score"])
    op.create_index(
        "idx_task_provenance_gin",
        "tasks",
        ["provenance"],
        postgresql_using="gin",
    )

    # 4. Migrate data back from fhir_resources + task_projections
    conn = op.get_bind()
    conn.execute(sa.text("""
        INSERT INTO tasks (
            id, type, category, status, priority, priority_score,
            title, description, patient_id, session_id, focus_resource_id,
            provenance, context_config, due_on, created_at, modified_at
        )
        SELECT
            fr.id,
            tp.task_type::task_type,
            tp.category::task_category,
            tp.status::task_status,
            tp.priority::task_priority,
            tp.priority_score,
            tp.title,
            fr.data->'note'->0->>'text',
            fr.patient_id,
            tp.session_id::uuid,
            tp.focus_resource_id::uuid,
            tp.provenance,
            tp.context_config,
            tp.due_on,
            fr.created_at,
            tp.projected_at
        FROM fhir_resources fr
        JOIN task_projections tp ON tp.fhir_resource_id = fr.id
        WHERE fr.resource_type = 'Task'
    """))

    # 5. Delete Task resources from fhir_resources
    conn.execute(sa.text("DELETE FROM fhir_resources WHERE resource_type = 'Task'"))

    # 6. Drop task_projections indexes
    op.drop_index("ix_task_proj_provenance_gin", table_name="task_projections")
    op.drop_index("ix_task_proj_status_priority", table_name="task_projections")
    op.drop_index("ix_task_proj_status_category", table_name="task_projections")
    op.drop_index("ix_task_proj_session_id", table_name="task_projections")
    op.drop_index("ix_task_proj_priority_score", table_name="task_projections")
    op.drop_index("ix_task_proj_task_type", table_name="task_projections")
    op.drop_index("ix_task_proj_category", table_name="task_projections")
    op.drop_index("ix_task_proj_priority", table_name="task_projections")
    op.drop_index("ix_task_proj_status", table_name="task_projections")

    # 7. Drop task_projections table
    op.drop_table("task_projections")
