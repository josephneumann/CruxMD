"""Tests for database setup and models."""

import uuid
from datetime import datetime, timezone

import pytest

from app.database import Base, async_session_maker, engine
from app.models import FhirResource


class TestFhirResourceModel:
    """Tests for FhirResource model structure."""

    def test_fhir_resource_tablename(self):
        """FhirResource should use fhir_resources table."""
        assert FhirResource.__tablename__ == "fhir_resources"

    def test_fhir_resource_columns_exist(self):
        """FhirResource should have all required columns."""
        column_names = {c.name for c in FhirResource.__table__.columns}
        expected = {
            "id",
            "fhir_id",
            "resource_type",
            "patient_id",
            "data",
            "created_at",
            "embedding",
            "embedding_text",
            "compiled_summary",
            "compiled_at",
        }
        assert expected == column_names

    def test_fhir_resource_id_is_primary_key(self):
        """id column should be the primary key."""
        id_column = FhirResource.__table__.columns["id"]
        assert id_column.primary_key is True

    def test_fhir_resource_indexes(self):
        """FhirResource should have required indexes."""
        index_names = {idx.name for idx in FhirResource.__table__.indexes}
        # Should have composite index, GIN index, and HNSW embedding index
        assert "idx_fhir_type_patient" in index_names
        assert "idx_fhir_data_gin" in index_names
        assert "idx_fhir_embedding_hnsw" in index_names

    def test_fhir_resource_repr(self):
        """FhirResource repr should include key identifiers."""
        test_id = uuid.uuid4()
        resource = FhirResource(
            id=test_id,
            fhir_id="patient-123",
            resource_type="Patient",
            data={"resourceType": "Patient"},
        )
        repr_str = repr(resource)
        assert str(test_id) in repr_str
        assert "Patient" in repr_str
        assert "patient-123" in repr_str


class TestDatabaseSetup:
    """Tests for database configuration."""

    def test_base_metadata_has_fhir_resources(self):
        """Base.metadata should include fhir_resources table."""
        assert "fhir_resources" in Base.metadata.tables

    def test_engine_url_uses_asyncpg(self):
        """Engine should use asyncpg driver."""
        url_str = str(engine.url)
        assert "asyncpg" in url_str

    def test_async_session_maker_configured(self):
        """Async session maker should be configured."""
        assert async_session_maker is not None


class TestCompiledSummaryPersistence:
    """Tests for compiled_summary and compiled_at column persistence."""

    @pytest.mark.asyncio
    async def test_compiled_fields_default_to_none(self, db_session):
        """FhirResource without compiled fields should default to None."""
        resource = FhirResource(
            fhir_id="patient-no-summary",
            resource_type="Patient",
            data={"resourceType": "Patient", "id": "patient-no-summary"},
        )
        db_session.add(resource)
        await db_session.commit()

        reloaded = await db_session.get(FhirResource, resource.id)
        assert reloaded.compiled_summary is None
        assert reloaded.compiled_at is None

    @pytest.mark.asyncio
    async def test_compiled_fields_round_trip(self, db_session):
        """compiled_summary and compiled_at should persist and reload correctly."""
        summary = {
            "demographics": {"name": "Jane Smith", "age": 41},
            "conditions": ["Hypertension"],
        }
        compiled_time = datetime(2026, 2, 5, 12, 0, 0, tzinfo=timezone.utc)

        resource = FhirResource(
            fhir_id="patient-with-summary",
            resource_type="Patient",
            data={"resourceType": "Patient", "id": "patient-with-summary"},
            compiled_summary=summary,
            compiled_at=compiled_time,
        )
        db_session.add(resource)
        await db_session.commit()

        reloaded = await db_session.get(FhirResource, resource.id)
        assert reloaded.compiled_summary == summary
        assert reloaded.compiled_at == compiled_time


class TestMigrationFile:
    """Tests for migration file validity."""

    def test_migration_file_is_valid_python(self):
        """Migration file should be valid Python that can be parsed."""
        import ast
        from pathlib import Path

        migration_dir = Path(__file__).parent.parent / "alembic" / "versions"
        migration_files = list(migration_dir.glob("*.py"))

        # Should have at least one migration
        assert len(migration_files) >= 1

        # Each migration should be valid Python
        for migration_file in migration_files:
            content = migration_file.read_text()
            # This will raise SyntaxError if invalid
            ast.parse(content)

            # Should contain upgrade and downgrade functions
            assert "def upgrade" in content
            assert "def downgrade" in content
