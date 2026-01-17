"""Tests for FHIR loader service."""

import os
import uuid

import pytest
import pytest_asyncio
from neo4j import AsyncGraphDatabase
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.database import Base
from app.models import FhirResource
from app.services.fhir_loader import get_patient_resources, load_bundle
from app.services.graph import KnowledgeGraph


# Test fixtures - sample FHIR resources
SAMPLE_PATIENT = {
    "resourceType": "Patient",
    "id": "patient-test-123",
    "name": [{"given": ["Jane"], "family": "Smith"}],
    "birthDate": "1985-03-20",
    "gender": "female",
}

SAMPLE_CONDITION = {
    "resourceType": "Condition",
    "id": "condition-test-456",
    "subject": {"reference": "Patient/patient-test-123"},
    "code": {
        "coding": [
            {
                "system": "http://snomed.info/sct",
                "code": "38341003",
                "display": "Hypertension",
            }
        ]
    },
    "clinicalStatus": {"coding": [{"code": "active"}]},
}

SAMPLE_MEDICATION = {
    "resourceType": "MedicationRequest",
    "id": "medication-test-789",
    "subject": {"reference": "Patient/patient-test-123"},
    "medicationCodeableConcept": {
        "coding": [
            {
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": "197361",
                "display": "Lisinopril 10 MG",
            }
        ]
    },
    "status": "active",
}

SAMPLE_OBSERVATION = {
    "resourceType": "Observation",
    "id": "observation-test-abc",
    "subject": {"reference": "Patient/patient-test-123"},
    "code": {
        "coding": [
            {
                "system": "http://loinc.org",
                "code": "8480-6",
                "display": "Systolic blood pressure",
            }
        ]
    },
    "status": "final",
    "valueQuantity": {"value": 140, "unit": "mmHg"},
}


def create_bundle(resources: list[dict]) -> dict:
    """Create a FHIR bundle from a list of resources."""
    return {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [{"resource": r} for r in resources],
    }


def get_test_database_url() -> str:
    """Get test database URL."""
    return os.environ.get(
        "DATABASE_TEST_URL",
        "postgresql+asyncpg://cruxmd:cruxmd@localhost:5432/cruxmd_test",
    )


def get_neo4j_test_uri() -> str:
    """Get Neo4j URI for tests."""
    return os.environ.get("NEO4J_TEST_URI", "bolt://localhost:7687")


def get_neo4j_test_auth() -> tuple[str, str]:
    """Get Neo4j auth credentials for tests."""
    user = os.environ.get("NEO4J_TEST_USER", "neo4j")
    password = os.environ.get("NEO4J_TEST_PASSWORD", "password")
    return (user, password)


@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine."""
    engine = create_async_engine(get_test_database_url(), echo=False)
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
    except Exception as e:
        await engine.dispose()
        pytest.skip(f"PostgreSQL not available: {e}")
    yield engine
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
    """Create test database session."""
    session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_maker() as session:
        yield session
        await session.rollback()


@pytest_asyncio.fixture
async def neo4j_driver():
    """Create test Neo4j driver."""
    driver = AsyncGraphDatabase.driver(
        get_neo4j_test_uri(),
        auth=get_neo4j_test_auth(),
    )
    try:
        await driver.verify_connectivity()
    except Exception as e:
        pytest.skip(f"Neo4j not available: {e}")
    yield driver
    await driver.close()


@pytest_asyncio.fixture
async def graph(neo4j_driver) -> KnowledgeGraph:
    """KnowledgeGraph instance for testing."""
    kg = KnowledgeGraph(driver=neo4j_driver)
    await kg.clear_all()
    yield kg


class TestLoadBundle:
    """Tests for load_bundle function."""

    @pytest.mark.asyncio
    async def test_load_bundle_creates_patient(self, db_session, graph):
        """Test that load_bundle creates a Patient resource in PostgreSQL."""
        bundle = create_bundle([SAMPLE_PATIENT])
        patient_id = await load_bundle(db_session, graph, bundle)

        assert patient_id is not None
        assert isinstance(patient_id, uuid.UUID)

        # Verify patient exists in database
        result = await db_session.execute(
            select(FhirResource).where(
                FhirResource.resource_type == "Patient",
                FhirResource.patient_id == patient_id,
            )
        )
        patient = result.scalar_one_or_none()
        assert patient is not None
        assert patient.fhir_id == "patient-test-123"
        assert patient.data["name"][0]["family"] == "Smith"

    @pytest.mark.asyncio
    async def test_load_bundle_creates_related_resources(self, db_session, graph):
        """Test that load_bundle creates related resources with patient_id linkage."""
        bundle = create_bundle(
            [SAMPLE_PATIENT, SAMPLE_CONDITION, SAMPLE_MEDICATION, SAMPLE_OBSERVATION]
        )
        patient_id = await load_bundle(db_session, graph, bundle)

        # Verify all resources exist
        result = await db_session.execute(
            select(FhirResource).where(FhirResource.patient_id == patient_id)
        )
        resources = result.scalars().all()
        assert len(resources) == 4

        resource_types = {r.resource_type for r in resources}
        assert resource_types == {"Patient", "Condition", "MedicationRequest", "Observation"}

    @pytest.mark.asyncio
    async def test_load_bundle_populates_neo4j_graph(self, db_session, graph):
        """Test that load_bundle populates Neo4j graph."""
        bundle = create_bundle([SAMPLE_PATIENT, SAMPLE_CONDITION])
        patient_id = await load_bundle(db_session, graph, bundle)

        # Verify patient exists in Neo4j
        exists = await graph.patient_exists(str(patient_id))
        assert exists is True

    @pytest.mark.asyncio
    async def test_load_bundle_empty_bundle_raises(self, db_session, graph):
        """Test that load_bundle raises for empty bundle."""
        bundle = {"resourceType": "Bundle", "type": "transaction", "entry": []}
        with pytest.raises(ValueError, match="no entries"):
            await load_bundle(db_session, graph, bundle)

    @pytest.mark.asyncio
    async def test_load_bundle_no_patient_raises(self, db_session, graph):
        """Test that load_bundle raises when no Patient resource."""
        bundle = create_bundle([SAMPLE_CONDITION])
        with pytest.raises(ValueError, match="must contain a Patient"):
            await load_bundle(db_session, graph, bundle)

    @pytest.mark.asyncio
    async def test_load_bundle_is_idempotent(self, db_session, graph):
        """Test that loading same bundle twice doesn't create duplicates."""
        bundle = create_bundle([SAMPLE_PATIENT, SAMPLE_CONDITION])

        # Load twice
        patient_id_1 = await load_bundle(db_session, graph, bundle)
        await db_session.commit()  # Commit first load
        patient_id_2 = await load_bundle(db_session, graph, bundle)

        # Should return same patient ID
        assert patient_id_1 == patient_id_2

        # Should have only one of each resource
        result = await db_session.execute(
            select(FhirResource).where(FhirResource.patient_id == patient_id_1)
        )
        resources = result.scalars().all()
        assert len(resources) == 2

    @pytest.mark.asyncio
    async def test_load_bundle_stores_raw_fhir(self, db_session, graph):
        """Test that load_bundle stores raw FHIR JSON data."""
        bundle = create_bundle([SAMPLE_PATIENT])
        patient_id = await load_bundle(db_session, graph, bundle)

        result = await db_session.execute(
            select(FhirResource).where(
                FhirResource.patient_id == patient_id,
                FhirResource.resource_type == "Patient",
            )
        )
        patient = result.scalar_one()

        # Data should be the exact FHIR resource
        assert patient.data == SAMPLE_PATIENT


class TestGetPatientResources:
    """Tests for get_patient_resources function."""

    @pytest.mark.asyncio
    async def test_get_patient_resources_returns_all(self, db_session, graph):
        """Test that get_patient_resources returns all resources for a patient."""
        bundle = create_bundle(
            [SAMPLE_PATIENT, SAMPLE_CONDITION, SAMPLE_MEDICATION]
        )
        patient_id = await load_bundle(db_session, graph, bundle)

        resources = await get_patient_resources(db_session, patient_id)
        assert len(resources) == 3

        resource_types = {r["resourceType"] for r in resources}
        assert resource_types == {"Patient", "Condition", "MedicationRequest"}

    @pytest.mark.asyncio
    async def test_get_patient_resources_empty_for_nonexistent(self, db_session):
        """Test that get_patient_resources returns empty for nonexistent patient."""
        fake_id = uuid.uuid4()
        resources = await get_patient_resources(db_session, fake_id)
        assert resources == []


class TestLoadBundleIntegration:
    """Integration tests with real Synthea fixtures."""

    @pytest.mark.asyncio
    async def test_load_synthea_bundle(self, db_session, graph):
        """Test loading a real Synthea bundle fixture."""
        import json
        from pathlib import Path

        fixture_path = Path(__file__).parent.parent.parent / "fixtures" / "synthea" / "patient_bundle_1.json"
        if not fixture_path.exists():
            pytest.skip("Synthea fixtures not available")

        with open(fixture_path) as f:
            bundle = json.load(f)

        patient_id = await load_bundle(db_session, graph, bundle)
        assert patient_id is not None

        # Verify resources were loaded
        result = await db_session.execute(
            select(FhirResource).where(FhirResource.patient_id == patient_id)
        )
        resources = result.scalars().all()

        # Synthea bundles typically have many resources
        assert len(resources) > 10

        # Verify graph was populated
        exists = await graph.patient_exists(str(patient_id))
        assert exists is True


class TestCreateBundle:
    """Unit tests for bundle creation helper."""

    def test_create_bundle_empty(self):
        """Test creating empty bundle."""
        bundle = create_bundle([])
        assert bundle["resourceType"] == "Bundle"
        assert bundle["type"] == "transaction"
        assert bundle["entry"] == []

    def test_create_bundle_with_resources(self):
        """Test creating bundle with resources."""
        bundle = create_bundle([SAMPLE_PATIENT, SAMPLE_CONDITION])
        assert len(bundle["entry"]) == 2
        assert bundle["entry"][0]["resource"] == SAMPLE_PATIENT
        assert bundle["entry"][1]["resource"] == SAMPLE_CONDITION


class TestFhirLoaderHelpers:
    """Unit tests for fhir_loader helper functions."""

    def test_extract_patient_reference_returns_default(self):
        """Test _extract_patient_reference returns default patient ID."""
        from app.services.fhir_loader import _extract_patient_reference

        default_id = uuid.uuid4()
        result = _extract_patient_reference(SAMPLE_CONDITION, default_id)
        assert result == default_id

    def test_sample_patient_has_required_fields(self):
        """Test sample patient has required FHIR fields."""
        assert SAMPLE_PATIENT["resourceType"] == "Patient"
        assert "id" in SAMPLE_PATIENT
        assert "name" in SAMPLE_PATIENT

    def test_sample_condition_has_required_fields(self):
        """Test sample condition has required FHIR fields."""
        assert SAMPLE_CONDITION["resourceType"] == "Condition"
        assert "id" in SAMPLE_CONDITION
        assert "code" in SAMPLE_CONDITION

    def test_sample_medication_has_required_fields(self):
        """Test sample medication has required FHIR fields."""
        assert SAMPLE_MEDICATION["resourceType"] == "MedicationRequest"
        assert "id" in SAMPLE_MEDICATION
        assert "medicationCodeableConcept" in SAMPLE_MEDICATION

    def test_sample_observation_has_required_fields(self):
        """Test sample observation has required FHIR fields."""
        assert SAMPLE_OBSERVATION["resourceType"] == "Observation"
        assert "id" in SAMPLE_OBSERVATION
        assert "code" in SAMPLE_OBSERVATION
        assert "valueQuantity" in SAMPLE_OBSERVATION
