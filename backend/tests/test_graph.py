"""Integration tests for KnowledgeGraph service."""

import os
import uuid

import pytest
import pytest_asyncio
from neo4j import AsyncGraphDatabase

from app.services.graph import KnowledgeGraph


# Test fixtures - sample FHIR resources
SAMPLE_PATIENT = {
    "resourceType": "Patient",
    "id": "patient-fhir-123",
    "name": [{"given": ["John"], "family": "Doe"}],
    "birthDate": "1980-05-15",
    "gender": "male",
}

SAMPLE_CONDITION = {
    "resourceType": "Condition",
    "id": "condition-fhir-456",
    "code": {
        "coding": [
            {
                "system": "http://snomed.info/sct",
                "code": "44054006",
                "display": "Type 2 diabetes mellitus",
            }
        ]
    },
    "clinicalStatus": {
        "coding": [{"code": "active"}]
    },
    "onsetDateTime": "2020-01-15",
}

SAMPLE_MEDICATION = {
    "resourceType": "MedicationRequest",
    "id": "medication-fhir-789",
    "medicationCodeableConcept": {
        "coding": [
            {
                "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                "code": "860975",
                "display": "Metformin 500 MG",
            }
        ]
    },
    "status": "active",
    "authoredOn": "2020-01-15",
}

SAMPLE_ALLERGY = {
    "resourceType": "AllergyIntolerance",
    "id": "allergy-fhir-abc",
    "code": {
        "coding": [
            {
                "system": "http://snomed.info/sct",
                "code": "764146007",
                "display": "Penicillin",
            }
        ]
    },
    "clinicalStatus": {
        "coding": [{"code": "active"}]
    },
    "category": ["medication"],
    "criticality": "high",
}

SAMPLE_OBSERVATION = {
    "resourceType": "Observation",
    "id": "observation-fhir-def",
    "code": {
        "coding": [
            {
                "system": "http://loinc.org",
                "code": "4548-4",
                "display": "Hemoglobin A1c",
            }
        ]
    },
    "status": "final",
    "effectiveDateTime": "2024-01-15",
    "valueQuantity": {
        "value": 7.2,
        "unit": "%",
    },
}

SAMPLE_ENCOUNTER = {
    "resourceType": "Encounter",
    "id": "encounter-fhir-ghi",
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


def get_neo4j_test_uri() -> str:
    """Get Neo4j URI for tests."""
    return os.environ.get("NEO4J_TEST_URI", "bolt://localhost:7687")


def get_neo4j_test_auth() -> tuple[str, str]:
    """Get Neo4j auth credentials for tests."""
    user = os.environ.get("NEO4J_TEST_USER", "neo4j")
    password = os.environ.get("NEO4J_TEST_PASSWORD", "password")
    return (user, password)


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
    # Clear all data before each test
    await kg.clear_all()
    yield kg


@pytest_asyncio.fixture
def patient_id() -> str:
    """Generate a unique patient ID for testing."""
    return str(uuid.uuid4())


@pytest.mark.asyncio
async def test_verify_connectivity(graph: KnowledgeGraph):
    """Test that we can connect to Neo4j."""
    assert await graph.verify_connectivity() is True


@pytest.mark.asyncio
async def test_patient_exists_returns_false_for_nonexistent(
    graph: KnowledgeGraph, patient_id: str
):
    """Test patient_exists returns False when patient doesn't exist."""
    exists = await graph.patient_exists(patient_id)
    assert exists is False


@pytest.mark.asyncio
async def test_patient_exists_returns_true_after_creation(
    graph: KnowledgeGraph, patient_id: str
):
    """Test patient_exists returns True after patient is created."""
    await graph.build_from_fhir(patient_id, [SAMPLE_PATIENT])
    exists = await graph.patient_exists(patient_id)
    assert exists is True


@pytest.mark.asyncio
async def test_build_from_fhir_creates_patient_node(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver
):
    """Test that build_from_fhir creates a Patient node with correct properties."""
    await graph.build_from_fhir(patient_id, [SAMPLE_PATIENT])

    async with neo4j_driver.session() as session:
        result = await session.run(
            "MATCH (p:Patient {id: $id}) RETURN p",
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    patient_node = record["p"]
    assert patient_node["given_name"] == "John"
    assert patient_node["family_name"] == "Doe"
    assert patient_node["birth_date"] == "1980-05-15"
    assert patient_node["gender"] == "male"
    assert patient_node["fhir_id"] == "patient-fhir-123"


@pytest.mark.asyncio
async def test_build_from_fhir_creates_condition_with_relationship(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver
):
    """Test that build_from_fhir creates Condition node with HAS_CONDITION relationship."""
    await graph.build_from_fhir(patient_id, [SAMPLE_PATIENT, SAMPLE_CONDITION])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_CONDITION]->(c:Condition)
            RETURN c
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    condition_node = record["c"]
    assert condition_node["fhir_id"] == "condition-fhir-456"
    assert condition_node["code"] == "44054006"
    assert condition_node["display"] == "Type 2 diabetes mellitus"
    assert condition_node["clinical_status"] == "active"


@pytest.mark.asyncio
async def test_build_from_fhir_creates_medication_with_relationship(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver
):
    """Test that build_from_fhir creates Medication node with TAKES_MEDICATION relationship."""
    await graph.build_from_fhir(patient_id, [SAMPLE_PATIENT, SAMPLE_MEDICATION])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:TAKES_MEDICATION]->(m:Medication)
            RETURN m
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    med_node = record["m"]
    assert med_node["fhir_id"] == "medication-fhir-789"
    assert med_node["code"] == "860975"
    assert med_node["display"] == "Metformin 500 MG"
    assert med_node["status"] == "active"


@pytest.mark.asyncio
async def test_build_from_fhir_creates_allergy_with_relationship(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver
):
    """Test that build_from_fhir creates Allergy node with HAS_ALLERGY relationship."""
    await graph.build_from_fhir(patient_id, [SAMPLE_PATIENT, SAMPLE_ALLERGY])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_ALLERGY]->(a:Allergy)
            RETURN a
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    allergy_node = record["a"]
    assert allergy_node["fhir_id"] == "allergy-fhir-abc"
    assert allergy_node["code"] == "764146007"
    assert allergy_node["display"] == "Penicillin"
    assert allergy_node["criticality"] == "high"


@pytest.mark.asyncio
async def test_build_from_fhir_creates_observation_with_relationship(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver
):
    """Test that build_from_fhir creates Observation node with HAS_OBSERVATION relationship."""
    await graph.build_from_fhir(patient_id, [SAMPLE_PATIENT, SAMPLE_OBSERVATION])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_OBSERVATION]->(o:Observation)
            RETURN o
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    obs_node = record["o"]
    assert obs_node["fhir_id"] == "observation-fhir-def"
    assert obs_node["code"] == "4548-4"
    assert obs_node["display"] == "Hemoglobin A1c"
    assert obs_node["value"] == 7.2
    assert obs_node["value_unit"] == "%"


@pytest.mark.asyncio
async def test_build_from_fhir_creates_encounter_with_relationship(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver
):
    """Test that build_from_fhir creates Encounter node with HAS_ENCOUNTER relationship."""
    await graph.build_from_fhir(patient_id, [SAMPLE_PATIENT, SAMPLE_ENCOUNTER])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_ENCOUNTER]->(e:Encounter)
            RETURN e
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    encounter_node = record["e"]
    assert encounter_node["fhir_id"] == "encounter-fhir-ghi"
    assert encounter_node["type_code"] == "185349003"
    assert encounter_node["type_display"] == "Outpatient visit"
    assert encounter_node["status"] == "finished"
    assert encounter_node["class_code"] == "AMB"


@pytest.mark.asyncio
async def test_build_from_fhir_complete_patient(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver
):
    """Test building a complete patient graph with all resource types."""
    all_resources = [
        SAMPLE_PATIENT,
        SAMPLE_CONDITION,
        SAMPLE_MEDICATION,
        SAMPLE_ALLERGY,
        SAMPLE_OBSERVATION,
        SAMPLE_ENCOUNTER,
    ]
    await graph.build_from_fhir(patient_id, all_resources)

    # Verify patient exists
    assert await graph.patient_exists(patient_id) is True

    # Verify all relationships exist
    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})
            OPTIONAL MATCH (p)-[:HAS_CONDITION]->(c:Condition)
            OPTIONAL MATCH (p)-[:TAKES_MEDICATION]->(m:Medication)
            OPTIONAL MATCH (p)-[:HAS_ALLERGY]->(a:Allergy)
            OPTIONAL MATCH (p)-[:HAS_OBSERVATION]->(o:Observation)
            OPTIONAL MATCH (p)-[:HAS_ENCOUNTER]->(e:Encounter)
            RETURN p, c, m, a, o, e
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    assert record["p"] is not None
    assert record["c"] is not None
    assert record["m"] is not None
    assert record["a"] is not None
    assert record["o"] is not None
    assert record["e"] is not None


@pytest.mark.asyncio
async def test_upsert_is_idempotent(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver
):
    """Test that calling build_from_fhir twice doesn't create duplicates."""
    resources = [SAMPLE_PATIENT, SAMPLE_CONDITION]

    # Build twice
    await graph.build_from_fhir(patient_id, resources)
    await graph.build_from_fhir(patient_id, resources)

    # Should still have only one patient and one condition
    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})
            OPTIONAL MATCH (p)-[:HAS_CONDITION]->(c:Condition)
            RETURN count(p) as patient_count, count(c) as condition_count
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record["patient_count"] == 1
    assert record["condition_count"] == 1


@pytest.mark.asyncio
async def test_clear_patient_graph(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver
):
    """Test that clear_patient_graph removes patient and related nodes."""
    await graph.build_from_fhir(
        patient_id, [SAMPLE_PATIENT, SAMPLE_CONDITION, SAMPLE_MEDICATION]
    )
    assert await graph.patient_exists(patient_id) is True

    await graph.clear_patient_graph(patient_id)
    assert await graph.patient_exists(patient_id) is False

    # Verify related nodes are also removed
    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (c:Condition {fhir_id: 'condition-fhir-456'})
            RETURN c
            """
        )
        record = await result.single()
    assert record is None


@pytest.mark.asyncio
async def test_handles_missing_optional_fields(
    graph: KnowledgeGraph, patient_id: str
):
    """Test that resources with missing optional fields don't cause errors."""
    # Minimal patient with no name
    minimal_patient = {
        "resourceType": "Patient",
        "id": "minimal-patient",
    }

    # Condition with minimal data
    minimal_condition = {
        "resourceType": "Condition",
        "id": "minimal-condition",
        "code": {},  # Empty code
    }

    # Should not raise
    await graph.build_from_fhir(patient_id, [minimal_patient, minimal_condition])
    assert await graph.patient_exists(patient_id) is True
