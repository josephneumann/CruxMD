"""Integration tests for KnowledgeGraph service.

Uses centralized fixtures from conftest.py for database, graph, and test data.
Requires Neo4j to be running.
"""

import json

import pytest

from app.services.graph import KnowledgeGraph

# All tests in this module require Neo4j
pytestmark = pytest.mark.integration


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
    graph: KnowledgeGraph, patient_id: str, sample_patient
):
    """Test patient_exists returns True after patient is created."""
    await graph.build_from_fhir(patient_id, [sample_patient])
    exists = await graph.patient_exists(patient_id)
    assert exists is True


@pytest.mark.asyncio
async def test_build_from_fhir_creates_patient_node(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver, sample_patient
):
    """Test that build_from_fhir creates a Patient node with correct properties."""
    await graph.build_from_fhir(patient_id, [sample_patient])

    async with neo4j_driver.session() as session:
        result = await session.run(
            "MATCH (p:Patient {id: $id}) RETURN p",
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    patient_node = record["p"]
    # Assert values match the fixture
    assert patient_node["given_name"] == sample_patient["name"][0]["given"][0]
    assert patient_node["family_name"] == sample_patient["name"][0]["family"]
    assert patient_node["birth_date"] == sample_patient["birthDate"]
    assert patient_node["gender"] == sample_patient["gender"]
    assert patient_node["fhir_id"] == sample_patient["id"]


@pytest.mark.asyncio
async def test_build_from_fhir_creates_condition_with_relationship(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver, sample_patient, sample_condition
):
    """Test that build_from_fhir creates Condition node with HAS_CONDITION relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_condition])

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
    assert condition_node["fhir_id"] == sample_condition["id"]
    assert condition_node["code"] == sample_condition["code"]["coding"][0]["code"]
    assert condition_node["display"] == sample_condition["code"]["coding"][0]["display"]
    assert condition_node["clinical_status"] == "active"


@pytest.mark.asyncio
async def test_build_from_fhir_creates_medication_with_relationship(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver, sample_patient, sample_medication
):
    """Test that build_from_fhir creates MedicationRequest node with HAS_MEDICATION_REQUEST relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_medication])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_MEDICATION_REQUEST]->(m:MedicationRequest)
            RETURN m
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    med_node = record["m"]
    assert med_node["fhir_id"] == sample_medication["id"]
    assert med_node["code"] == sample_medication["medicationCodeableConcept"]["coding"][0]["code"]
    assert med_node["display"] == sample_medication["medicationCodeableConcept"]["coding"][0]["display"]
    assert med_node["status"] == sample_medication["status"]


@pytest.mark.asyncio
async def test_build_from_fhir_creates_allergy_with_relationship(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver, sample_patient, sample_allergy
):
    """Test that build_from_fhir creates AllergyIntolerance node with HAS_ALLERGY_INTOLERANCE relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_allergy])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_ALLERGY_INTOLERANCE]->(a:AllergyIntolerance)
            RETURN a
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    allergy_node = record["a"]
    assert allergy_node["fhir_id"] == sample_allergy["id"]
    assert allergy_node["code"] == sample_allergy["code"]["coding"][0]["code"]
    assert allergy_node["display"] == sample_allergy["code"]["coding"][0]["display"]
    assert allergy_node["criticality"] == sample_allergy["criticality"]


@pytest.mark.asyncio
async def test_build_from_fhir_creates_observation_with_relationship(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver, sample_patient, sample_observation
):
    """Test that build_from_fhir creates Observation node with HAS_OBSERVATION relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_observation])

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
    assert obs_node["fhir_id"] == sample_observation["id"]
    assert obs_node["code"] == sample_observation["code"]["coding"][0]["code"]
    assert obs_node["display"] == sample_observation["code"]["coding"][0]["display"]
    assert obs_node["value"] == sample_observation["valueQuantity"]["value"]
    assert obs_node["value_unit"] == sample_observation["valueQuantity"]["unit"]


@pytest.mark.asyncio
async def test_build_from_fhir_creates_encounter_with_relationship(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver, sample_patient, sample_encounter
):
    """Test that build_from_fhir creates Encounter node with HAS_ENCOUNTER relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_encounter])

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
    assert encounter_node["fhir_id"] == sample_encounter["id"]
    assert encounter_node["type_code"] == sample_encounter["type"][0]["coding"][0]["code"]
    assert encounter_node["type_display"] == sample_encounter["type"][0]["coding"][0]["display"]
    assert encounter_node["status"] == sample_encounter["status"]
    assert encounter_node["class_code"] == sample_encounter["class"]["code"]


@pytest.mark.asyncio
async def test_build_from_fhir_complete_patient(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_condition,
    sample_medication,
    sample_allergy,
    sample_observation,
    sample_encounter,
):
    """Test building a complete patient graph with all resource types."""
    all_resources = [
        sample_patient,
        sample_condition,
        sample_medication,
        sample_allergy,
        sample_observation,
        sample_encounter,
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
            OPTIONAL MATCH (p)-[:HAS_MEDICATION_REQUEST]->(m:MedicationRequest)
            OPTIONAL MATCH (p)-[:HAS_ALLERGY_INTOLERANCE]->(a:AllergyIntolerance)
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
    graph: KnowledgeGraph, patient_id: str, neo4j_driver, sample_patient, sample_condition
):
    """Test that calling build_from_fhir twice doesn't create duplicates."""
    resources = [sample_patient, sample_condition]

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
    graph: KnowledgeGraph, patient_id: str, neo4j_driver, sample_patient, sample_condition, sample_medication
):
    """Test that clear_patient_graph removes patient and related nodes."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_condition, sample_medication])
    assert await graph.patient_exists(patient_id) is True

    await graph.clear_patient_graph(patient_id)
    assert await graph.patient_exists(patient_id) is False

    # Verify related nodes are also removed
    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (c:Condition {fhir_id: $fhir_id})
            RETURN c
            """,
            fhir_id=sample_condition["id"],
        )
        record = await result.single()
    assert record is None


@pytest.mark.asyncio
async def test_handles_missing_optional_fields(graph: KnowledgeGraph, patient_id: str):
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


# Tests for get_verified_conditions
@pytest.mark.asyncio
async def test_get_verified_conditions_returns_active_conditions(
    graph: KnowledgeGraph, patient_id: str, sample_patient, sample_condition
):
    """Test that get_verified_conditions returns only active conditions."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_condition])

    conditions = await graph.get_verified_conditions(patient_id)

    assert len(conditions) == 1
    assert conditions[0]["resourceType"] == "Condition"
    assert conditions[0]["id"] == sample_condition["id"]
    # Verify the full FHIR resource is returned
    assert conditions[0]["code"]["coding"][0]["display"] == sample_condition["code"]["coding"][0]["display"]


@pytest.mark.asyncio
async def test_get_verified_conditions_excludes_inactive(
    graph: KnowledgeGraph, patient_id: str, sample_patient, sample_condition, sample_condition_inactive
):
    """Test that get_verified_conditions excludes inactive conditions."""
    await graph.build_from_fhir(
        patient_id, [sample_patient, sample_condition, sample_condition_inactive]
    )

    conditions = await graph.get_verified_conditions(patient_id)

    # Should only return the active condition
    assert len(conditions) == 1
    assert conditions[0]["id"] == sample_condition["id"]


@pytest.mark.asyncio
async def test_get_verified_conditions_returns_empty_for_nonexistent_patient(
    graph: KnowledgeGraph,
):
    """Test that get_verified_conditions returns empty list for nonexistent patient."""
    conditions = await graph.get_verified_conditions("nonexistent-patient-id")
    assert conditions == []


# Tests for get_verified_medications
@pytest.mark.asyncio
async def test_get_verified_medications_returns_active_medications(
    graph: KnowledgeGraph, patient_id: str, sample_patient, sample_medication
):
    """Test that get_verified_medications returns active medications."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_medication])

    medications = await graph.get_verified_medications(patient_id)

    assert len(medications) == 1
    assert medications[0]["resourceType"] == "MedicationRequest"
    assert medications[0]["id"] == sample_medication["id"]
    # Verify the full FHIR resource is returned
    expected_display = sample_medication["medicationCodeableConcept"]["coding"][0]["display"]
    assert medications[0]["medicationCodeableConcept"]["coding"][0]["display"] == expected_display


@pytest.mark.asyncio
async def test_get_verified_medications_includes_on_hold(
    graph: KnowledgeGraph, patient_id: str, sample_patient, sample_medication, sample_medication_on_hold
):
    """Test that get_verified_medications includes on-hold medications."""
    await graph.build_from_fhir(
        patient_id, [sample_patient, sample_medication, sample_medication_on_hold]
    )

    medications = await graph.get_verified_medications(patient_id)

    # Should return both active and on-hold medications
    assert len(medications) == 2
    med_ids = {m["id"] for m in medications}
    assert sample_medication["id"] in med_ids  # active
    assert sample_medication_on_hold["id"] in med_ids  # on-hold


@pytest.mark.asyncio
async def test_get_verified_medications_excludes_stopped(
    graph: KnowledgeGraph, patient_id: str, sample_patient, sample_medication, sample_medication_stopped
):
    """Test that get_verified_medications excludes stopped medications."""
    await graph.build_from_fhir(
        patient_id, [sample_patient, sample_medication, sample_medication_stopped]
    )

    medications = await graph.get_verified_medications(patient_id)

    # Should only return the active medication, not stopped
    assert len(medications) == 1
    assert medications[0]["id"] == sample_medication["id"]


@pytest.mark.asyncio
async def test_get_verified_medications_returns_empty_for_nonexistent_patient(
    graph: KnowledgeGraph,
):
    """Test that get_verified_medications returns empty list for nonexistent patient."""
    medications = await graph.get_verified_medications("nonexistent-patient-id")
    assert medications == []


# Tests for get_verified_allergies
@pytest.mark.asyncio
async def test_get_verified_allergies_returns_active_allergies(
    graph: KnowledgeGraph, patient_id: str, sample_patient, sample_allergy
):
    """Test that get_verified_allergies returns active allergies."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_allergy])

    allergies = await graph.get_verified_allergies(patient_id)

    assert len(allergies) == 1
    assert allergies[0]["resourceType"] == "AllergyIntolerance"
    assert allergies[0]["id"] == sample_allergy["id"]
    # Verify the full FHIR resource is returned
    assert allergies[0]["code"]["coding"][0]["display"] == sample_allergy["code"]["coding"][0]["display"]


@pytest.mark.asyncio
async def test_get_verified_allergies_excludes_inactive(
    graph: KnowledgeGraph, patient_id: str, sample_patient, sample_allergy, sample_allergy_inactive
):
    """Test that get_verified_allergies excludes inactive allergies."""
    await graph.build_from_fhir(
        patient_id, [sample_patient, sample_allergy, sample_allergy_inactive]
    )

    allergies = await graph.get_verified_allergies(patient_id)

    # Should only return the active allergy
    assert len(allergies) == 1
    assert allergies[0]["id"] == sample_allergy["id"]


@pytest.mark.asyncio
async def test_get_verified_allergies_returns_empty_for_nonexistent_patient(
    graph: KnowledgeGraph,
):
    """Test that get_verified_allergies returns empty list for nonexistent patient."""
    allergies = await graph.get_verified_allergies("nonexistent-patient-id")
    assert allergies == []


# Tests for get_verified_facts
@pytest.mark.asyncio
async def test_get_verified_facts_returns_all_verified_data(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_condition,
    sample_condition_inactive,
    sample_medication,
    sample_medication_on_hold,
    sample_medication_stopped,
    sample_allergy,
    sample_allergy_inactive,
):
    """Test that get_verified_facts returns aggregated verified data."""
    await graph.build_from_fhir(
        patient_id,
        [
            sample_patient,
            sample_condition,
            sample_condition_inactive,  # Should be excluded
            sample_medication,
            sample_medication_on_hold,  # Should be included
            sample_medication_stopped,  # Should be excluded
            sample_allergy,
            sample_allergy_inactive,  # Should be excluded
        ],
    )

    facts = await graph.get_verified_facts(patient_id)

    # Verify structure
    assert "conditions" in facts
    assert "medications" in facts
    assert "allergies" in facts

    # Verify correct filtering
    assert len(facts["conditions"]) == 1
    assert facts["conditions"][0]["id"] == sample_condition["id"]

    assert len(facts["medications"]) == 2
    med_ids = {m["id"] for m in facts["medications"]}
    assert sample_medication["id"] in med_ids
    assert sample_medication_on_hold["id"] in med_ids
    assert sample_medication_stopped["id"] not in med_ids

    assert len(facts["allergies"]) == 1
    assert facts["allergies"][0]["id"] == sample_allergy["id"]


@pytest.mark.asyncio
async def test_get_verified_facts_returns_empty_collections_for_new_patient(
    graph: KnowledgeGraph, patient_id: str, sample_patient
):
    """Test that get_verified_facts returns empty collections for patient with no data."""
    await graph.build_from_fhir(patient_id, [sample_patient])

    facts = await graph.get_verified_facts(patient_id)

    assert facts["conditions"] == []
    assert facts["medications"] == []
    assert facts["allergies"] == []


# Tests for fhir_resource storage
@pytest.mark.asyncio
async def test_fhir_resource_stored_on_condition_node(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver, sample_patient, sample_condition
):
    """Test that the full FHIR resource is stored on Condition nodes."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_condition])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_CONDITION]->(c:Condition)
            RETURN c.fhir_resource as fhir_resource
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    assert record["fhir_resource"] is not None
    # Parse the stored JSON to verify it's the full resource
    stored_resource = json.loads(record["fhir_resource"])
    assert stored_resource["resourceType"] == "Condition"
    assert stored_resource["id"] == sample_condition["id"]
    assert stored_resource["code"]["coding"][0]["display"] == sample_condition["code"]["coding"][0]["display"]


@pytest.mark.asyncio
async def test_fhir_resource_stored_on_medication_node(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver, sample_patient, sample_medication
):
    """Test that the full FHIR resource is stored on MedicationRequest nodes."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_medication])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_MEDICATION_REQUEST]->(m:MedicationRequest)
            RETURN m.fhir_resource as fhir_resource
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    assert record["fhir_resource"] is not None
    stored_resource = json.loads(record["fhir_resource"])
    assert stored_resource["resourceType"] == "MedicationRequest"
    assert stored_resource["id"] == sample_medication["id"]


@pytest.mark.asyncio
async def test_fhir_resource_stored_on_allergy_node(
    graph: KnowledgeGraph, patient_id: str, neo4j_driver, sample_patient, sample_allergy
):
    """Test that the full FHIR resource is stored on AllergyIntolerance nodes."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_allergy])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_ALLERGY_INTOLERANCE]->(a:AllergyIntolerance)
            RETURN a.fhir_resource as fhir_resource
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    assert record["fhir_resource"] is not None
    stored_resource = json.loads(record["fhir_resource"])
    assert stored_resource["resourceType"] == "AllergyIntolerance"
    assert stored_resource["id"] == sample_allergy["id"]
