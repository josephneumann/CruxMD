"""add_embedding_columns

Revision ID: add_embedding_columns
Revises: add_fhir_id_idx
Create Date: 2026-01-24

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector


# revision identifiers, used by Alembic.
revision: str = "add_embedding_columns"
down_revision: Union[str, Sequence[str], None] = "add_fhir_id_idx"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add pgvector extension and embedding columns to fhir_resources."""
    # Enable pgvector extension (idempotent)
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # Add embedding column for vector similarity search
    op.add_column(
        "fhir_resources",
        sa.Column("embedding", Vector(1536), nullable=True),
    )

    # Add embedding_text column for debugging/inspection
    op.add_column(
        "fhir_resources",
        sa.Column("embedding_text", sa.Text(), nullable=True),
    )

    # Create HNSW index for cosine similarity searches
    # HNSW is faster for queries than IVFFlat, especially at scale
    op.create_index(
        "idx_fhir_embedding_hnsw",
        "fhir_resources",
        ["embedding"],
        unique=False,
        postgresql_using="hnsw",
        postgresql_with={"m": 16, "ef_construction": 64},
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )


def downgrade() -> None:
    """Remove embedding columns and index."""
    op.drop_index("idx_fhir_embedding_hnsw", table_name="fhir_resources")
    op.drop_column("fhir_resources", "embedding_text")
    op.drop_column("fhir_resources", "embedding")
    # Note: We don't drop the pgvector extension as other tables might use it
