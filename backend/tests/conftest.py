"""Pytest configuration and shared fixtures.

This module provides centralized test fixtures for:
- HTTP client for API testing
- PostgreSQL test database sessions
- Neo4j test graph connections
- Common FHIR test data
"""

import json
import os
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from neo4j import AsyncGraphDatabase
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.auth import verify_bearer_token
from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.services.graph import KnowledgeGraph

TEST_USER_ID = "test-user"


async def stub_verify_bearer_token() -> str:
    """Stub auth dependency that returns a fixed test user ID."""
    return TEST_USER_ID


# =============================================================================
# HTTP Client Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def client(test_engine):
    """Async test client for FastAPI app with test database.

    Overrides the app's get_db dependency to use the test database,
    ensuring API tests use the same database as other test fixtures.
    """
    # Create session maker for test database
    test_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db():
        async with test_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    # Override dependencies
    app.dependency_overrides[get_db] = override_get_db

    app.dependency_overrides[verify_bearer_token] = stub_verify_bearer_token

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac

    # Clean up overrides
    app.dependency_overrides.pop(get_db, None)
    app.dependency_overrides.pop(verify_bearer_token, None)


@pytest.fixture
def auth_headers() -> dict[str, str]:
    """Authentication headers for API requests."""
    return {"Authorization": "Bearer test-token"}


# =============================================================================
# Database Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def test_engine():
    """Create test database engine with automatic schema management.

    Creates all tables before tests, drops them after.
    Uses DATABASE_TEST_URL env var if set, otherwise derives from settings.
    """
    # Use env var if set (for CI/CD), otherwise derive from settings
    db_url = os.environ.get("DATABASE_TEST_URL")
    if not db_url:
        base_url = settings.database_url
        db_url = (
            base_url + "_test"
            if base_url.endswith("/cruxmd")
            else base_url.rsplit("/", 1)[0] + "/cruxmd_test"
        )

    engine = create_async_engine(db_url, echo=False)

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

    await engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine) -> AsyncSession:
    """Create test database session with automatic rollback.

    Each test gets a fresh session that rolls back on completion,
    ensuring test isolation.
    """
    session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )
    async with session_maker() as session:
        yield session
        await session.rollback()


# =============================================================================
# Neo4j / Graph Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def neo4j_driver():
    """Create test Neo4j driver with connectivity verification.

    Uses NEO4J_TEST_* env vars if set, otherwise uses settings.
    """
    uri = os.environ.get("NEO4J_TEST_URI", settings.neo4j_uri)
    auth = (
        os.environ.get("NEO4J_TEST_USER", settings.neo4j_user),
        os.environ.get("NEO4J_TEST_PASSWORD", settings.neo4j_password),
    )
    driver = AsyncGraphDatabase.driver(uri, auth=auth)
    await driver.verify_connectivity()
    yield driver
    await driver.close()


@pytest_asyncio.fixture
async def graph(neo4j_driver) -> KnowledgeGraph:
    """KnowledgeGraph instance for testing.

    Clears all data before each test to ensure isolation.
    """
    kg = KnowledgeGraph(driver=neo4j_driver)
    await kg.clear_all()
    yield kg


@pytest.fixture
def patient_id() -> str:
    """Generate a unique patient ID for testing."""
    return str(uuid.uuid4())


# =============================================================================
# Synthea Fixture Loading
# =============================================================================

FIXTURES_DIR = Path(__file__).parent.parent.parent / "fixtures" / "synthea"


@pytest.fixture
def fixtures_dir() -> Path:
    """Return path to Synthea fixtures directory."""
    return FIXTURES_DIR


@pytest.fixture
def sample_bundle() -> dict:
    """Load first patient bundle fixture from Synthea fixtures."""
    with open(FIXTURES_DIR / "patient_bundle_1.json") as f:
        return json.load(f)


@pytest.fixture
def all_bundles() -> list[dict]:
    """Load all patient bundle fixtures from Synthea fixtures."""
    bundles = []
    for path in sorted(FIXTURES_DIR.glob("patient_bundle_*.json")):
        # Exclude .profile.json files
        if path.name.endswith(".profile.json"):
            continue
        with open(path) as f:
            bundles.append(json.load(f))
    return bundles


# =============================================================================
# FHIR Test Data Fixtures
# =============================================================================


@pytest.fixture
def sample_patient() -> dict:
    """Sample FHIR Patient resource for testing."""
    return {
        "resourceType": "Patient",
        "id": "patient-test-123",
        "name": [{"given": ["Jane"], "family": "Smith"}],
        "birthDate": "1985-03-20",
        "gender": "female",
    }


@pytest.fixture
def sample_condition() -> dict:
    """Sample FHIR Condition resource for testing."""
    return {
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


@pytest.fixture
def sample_medication() -> dict:
    """Sample FHIR MedicationRequest resource for testing."""
    return {
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


@pytest.fixture
def sample_observation() -> dict:
    """Sample FHIR Observation resource for testing."""
    return {
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


@pytest.fixture
def sample_allergy() -> dict:
    """Sample FHIR AllergyIntolerance resource for testing."""
    return {
        "resourceType": "AllergyIntolerance",
        "id": "allergy-test-def",
        "subject": {"reference": "Patient/patient-test-123"},
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "764146007",
                    "display": "Penicillin",
                }
            ]
        },
        "clinicalStatus": {"coding": [{"code": "active"}]},
        "category": ["medication"],
        "criticality": "high",
    }


@pytest.fixture
def sample_encounter() -> dict:
    """Sample FHIR Encounter resource for testing."""
    return {
        "resourceType": "Encounter",
        "id": "encounter-test-ghi",
        "subject": {"reference": "Patient/patient-test-123"},
        "type": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "185349003",
                        "display": "Outpatient visit",
                    }
                ]
            }
        ],
        "status": "finished",
        "class": {"code": "AMB"},
        "period": {
            "start": "2024-01-15T09:00:00Z",
            "end": "2024-01-15T09:30:00Z",
        },
    }


# Additional test fixtures for inactive/stopped resources


@pytest.fixture
def sample_condition_inactive() -> dict:
    """Sample inactive FHIR Condition for testing filtering."""
    return {
        "resourceType": "Condition",
        "id": "condition-test-inactive",
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
        "clinicalStatus": {"coding": [{"code": "inactive"}]},
        "onsetDateTime": "2019-03-01",
    }


@pytest.fixture
def sample_medication_stopped() -> dict:
    """Sample stopped FHIR MedicationRequest for testing filtering."""
    return {
        "resourceType": "MedicationRequest",
        "id": "medication-test-stopped",
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
        "status": "stopped",
        "authoredOn": "2019-03-01",
    }


@pytest.fixture
def sample_medication_on_hold() -> dict:
    """Sample on-hold FHIR MedicationRequest for testing filtering."""
    return {
        "resourceType": "MedicationRequest",
        "id": "medication-test-on-hold",
        "subject": {"reference": "Patient/patient-test-123"},
        "medicationCodeableConcept": {
            "coding": [
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "312961",
                    "display": "Aspirin 81 MG",
                }
            ]
        },
        "status": "on-hold",
        "authoredOn": "2023-06-15",
    }


@pytest.fixture
def sample_allergy_inactive() -> dict:
    """Sample inactive FHIR AllergyIntolerance for testing filtering."""
    return {
        "resourceType": "AllergyIntolerance",
        "id": "allergy-test-inactive",
        "subject": {"reference": "Patient/patient-test-123"},
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "91936005",
                    "display": "Allergy to penicillin",
                }
            ]
        },
        "clinicalStatus": {"coding": [{"code": "inactive"}]},
        "category": ["medication"],
        "criticality": "low",
    }


# =============================================================================
# Inter-resource relationship test fixtures
# =============================================================================


@pytest.fixture
def sample_procedure() -> dict:
    """Sample FHIR Procedure resource for testing."""
    return {
        "resourceType": "Procedure",
        "id": "procedure-test-001",
        "subject": {"reference": "Patient/patient-test-123"},
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "386638009",
                    "display": "Physical therapy procedure",
                }
            ]
        },
        "status": "completed",
        "performedDateTime": "2024-01-15T10:00:00Z",
    }


@pytest.fixture
def sample_diagnostic_report() -> dict:
    """Sample FHIR DiagnosticReport resource for testing."""
    return {
        "resourceType": "DiagnosticReport",
        "id": "report-test-001",
        "subject": {"reference": "Patient/patient-test-123"},
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "24323-8",
                    "display": "Comprehensive metabolic panel",
                }
            ]
        },
        "status": "final",
        "effectiveDateTime": "2024-01-15T09:00:00Z",
        "issued": "2024-01-15T11:00:00Z",
    }


@pytest.fixture
def sample_condition_with_encounter() -> dict:
    """Sample FHIR Condition with encounter reference."""
    return {
        "resourceType": "Condition",
        "id": "condition-with-encounter",
        "subject": {"reference": "Patient/patient-test-123"},
        "encounter": {"reference": "Encounter/encounter-test-ghi"},
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
        "onsetDateTime": "2024-01-15T09:15:00Z",
    }


@pytest.fixture
def sample_medication_with_encounter_and_reason() -> dict:
    """Sample FHIR MedicationRequest with encounter and reasonReference."""
    return {
        "resourceType": "MedicationRequest",
        "id": "medication-with-encounter",
        "subject": {"reference": "Patient/patient-test-123"},
        "encounter": {"reference": "Encounter/encounter-test-ghi"},
        "reasonReference": [
            {"reference": "Condition/condition-with-encounter"}
        ],
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
        "authoredOn": "2024-01-15T09:20:00Z",
    }


@pytest.fixture
def sample_observation_with_encounter() -> dict:
    """Sample FHIR Observation with encounter reference."""
    return {
        "resourceType": "Observation",
        "id": "observation-with-encounter",
        "subject": {"reference": "Patient/patient-test-123"},
        "encounter": {"reference": "Encounter/encounter-test-ghi"},
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
        "effectiveDateTime": "2024-01-15T09:10:00Z",
        "valueQuantity": {"value": 145, "unit": "mmHg"},
    }


@pytest.fixture
def sample_procedure_with_encounter_and_reason() -> dict:
    """Sample FHIR Procedure with encounter and reasonReference."""
    return {
        "resourceType": "Procedure",
        "id": "procedure-with-encounter",
        "subject": {"reference": "Patient/patient-test-123"},
        "encounter": {"reference": "Encounter/encounter-test-ghi"},
        "reasonReference": [
            {"reference": "Condition/condition-with-encounter"}
        ],
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "386638009",
                    "display": "Blood pressure monitoring",
                }
            ]
        },
        "status": "completed",
        "performedDateTime": "2024-01-15T09:25:00Z",
    }


@pytest.fixture
def sample_diagnostic_report_with_encounter_and_results() -> dict:
    """Sample FHIR DiagnosticReport with encounter and result references."""
    return {
        "resourceType": "DiagnosticReport",
        "id": "report-with-encounter",
        "subject": {"reference": "Patient/patient-test-123"},
        "encounter": {"reference": "Encounter/encounter-test-ghi"},
        "result": [
            {"reference": "Observation/observation-with-encounter"}
        ],
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "24323-8",
                    "display": "Comprehensive metabolic panel",
                }
            ]
        },
        "status": "final",
        "effectiveDateTime": "2024-01-15T09:00:00Z",
        "issued": "2024-01-15T11:00:00Z",
    }


@pytest.fixture
def sample_immunization() -> dict:
    """Sample FHIR Immunization resource for testing."""
    return {
        "resourceType": "Immunization",
        "id": "immunization-test-001",
        "subject": {"reference": "Patient/patient-test-123"},
        "vaccineCode": {
            "coding": [
                {
                    "system": "http://hl7.org/fhir/sid/cvx",
                    "code": "140",
                    "display": "Influenza, seasonal, injectable, preservative free",
                }
            ]
        },
        "status": "completed",
        "occurrenceDateTime": "2024-01-15T09:30:00Z",
    }


@pytest.fixture
def sample_immunization_with_encounter() -> dict:
    """Sample FHIR Immunization with encounter reference."""
    return {
        "resourceType": "Immunization",
        "id": "immunization-with-encounter",
        "subject": {"reference": "Patient/patient-test-123"},
        "encounter": {"reference": "Encounter/encounter-test-ghi"},
        "vaccineCode": {
            "coding": [
                {
                    "system": "http://hl7.org/fhir/sid/cvx",
                    "code": "140",
                    "display": "Influenza, seasonal, injectable, preservative free",
                }
            ]
        },
        "status": "completed",
        "occurrenceDateTime": "2024-01-15T09:30:00Z",
    }


@pytest.fixture
def sample_immunization_not_done() -> dict:
    """Sample FHIR Immunization with not-done status for testing filtering."""
    return {
        "resourceType": "Immunization",
        "id": "immunization-test-not-done",
        "subject": {"reference": "Patient/patient-test-123"},
        "vaccineCode": {
            "coding": [
                {
                    "system": "http://hl7.org/fhir/sid/cvx",
                    "code": "08",
                    "display": "Hepatitis B vaccine",
                }
            ]
        },
        "status": "not-done",
        "occurrenceDateTime": "2024-02-01T10:00:00Z",
    }


@pytest.fixture
def sample_condition_with_urn_uuid_encounter() -> dict:
    """Sample FHIR Condition with urn:uuid encounter reference (Synthea style)."""
    return {
        "resourceType": "Condition",
        "id": "condition-urn-uuid",
        "subject": {"reference": "urn:uuid:patient-test-123"},
        "encounter": {"reference": "urn:uuid:encounter-test-ghi"},
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "44054006",
                    "display": "Type 2 diabetes mellitus",
                }
            ]
        },
        "clinicalStatus": {"coding": [{"code": "active"}]},
    }


# =============================================================================
# Fixtures for expanded node properties (category, reasonCode, abatement)
# =============================================================================


@pytest.fixture
def sample_observation_with_category() -> dict:
    """Sample FHIR Observation with category field for testing category extraction."""
    return {
        "resourceType": "Observation",
        "id": "observation-test-with-category",
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
        "category": [
            {
                "coding": [
                    {
                        "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                        "code": "vital-signs",
                        "display": "Vital Signs",
                    }
                ]
            }
        ],
        "status": "final",
        "valueQuantity": {"value": 120, "unit": "mmHg"},
    }


@pytest.fixture
def sample_encounter_with_reason() -> dict:
    """Sample FHIR Encounter with reasonCode for testing reason extraction."""
    return {
        "resourceType": "Encounter",
        "id": "encounter-test-with-reason",
        "subject": {"reference": "Patient/patient-test-123"},
        "type": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "185349003",
                        "display": "Outpatient visit",
                    }
                ]
            }
        ],
        "status": "finished",
        "class": {"code": "AMB"},
        "period": {
            "start": "2024-03-01T10:00:00Z",
            "end": "2024-03-01T10:30:00Z",
        },
        "reasonCode": [
            {
                "coding": [
                    {
                        "system": "http://snomed.info/sct",
                        "code": "38341003",
                        "display": "Hypertension",
                    }
                ]
            }
        ],
    }


@pytest.fixture
def sample_condition_with_abatement() -> dict:
    """Sample FHIR Condition with abatementDateTime for testing abatement extraction."""
    return {
        "resourceType": "Condition",
        "id": "condition-test-with-abatement",
        "subject": {"reference": "Patient/patient-test-123"},
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "195662009",
                    "display": "Acute viral pharyngitis",
                }
            ]
        },
        "clinicalStatus": {"coding": [{"code": "resolved"}]},
        "onsetDateTime": "2024-01-10T00:00:00Z",
        "abatementDateTime": "2024-01-24T00:00:00Z",
    }


@pytest.fixture
def sample_careplan() -> dict:
    """Sample FHIR CarePlan resource for testing."""
    return {
        "resourceType": "CarePlan",
        "id": "careplan-test-001",
        "subject": {"reference": "Patient/patient-test-123"},
        "status": "active",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://hl7.org/fhir/us/core/CodeSystem/careplan-category",
                        "code": "assess-plan",
                        "display": "Assessment and Plan of Treatment",
                    }
                ]
            }
        ],
        "period": {
            "start": "2024-01-15T09:00:00Z",
        },
    }


@pytest.fixture
def sample_careplan_with_title() -> dict:
    """Sample FHIR CarePlan with title field."""
    return {
        "resourceType": "CarePlan",
        "id": "careplan-test-titled",
        "subject": {"reference": "Patient/patient-test-123"},
        "title": "Diabetes self-management plan",
        "status": "active",
        "period": {
            "start": "2024-01-15T09:00:00Z",
            "end": "2024-07-15T09:00:00Z",
        },
    }


@pytest.fixture
def sample_careplan_with_addresses() -> dict:
    """Sample FHIR CarePlan that addresses a Condition."""
    return {
        "resourceType": "CarePlan",
        "id": "careplan-with-addresses",
        "subject": {"reference": "Patient/patient-test-123"},
        "status": "active",
        "category": [
            {
                "coding": [
                    {
                        "system": "http://hl7.org/fhir/us/core/CodeSystem/careplan-category",
                        "code": "assess-plan",
                        "display": "Assessment and Plan of Treatment",
                    }
                ]
            }
        ],
        "addresses": [
            {"reference": "Condition/condition-with-encounter"},
        ],
        "period": {
            "start": "2024-01-15T09:00:00Z",
        },
    }


# =============================================================================
# Helper Functions (available to tests)
# =============================================================================


def create_bundle(resources: list[dict]) -> dict:
    """Create a FHIR bundle from a list of resources.

    Args:
        resources: List of FHIR resource dictionaries

    Returns:
        FHIR Bundle dictionary
    """
    return {
        "resourceType": "Bundle",
        "type": "transaction",
        "entry": [{"resource": r} for r in resources],
    }
