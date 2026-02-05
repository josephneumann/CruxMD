"""Integration tests for KnowledgeGraph service.

Uses centralized fixtures from conftest.py for database, graph, and test data.
Requires Neo4j to be running.
"""

import json

import pytest

from app.services.graph import (
    KnowledgeGraph,
    _extract_reference_id,
    _extract_reference_ids,
    _extract_first_coding,
    _extract_clinical_status,
    _extract_encounter_fhir_id,
    _extract_observation_value,
    _extract_context_encounter_fhir_id,
    _extract_doc_ref_encounter_fhir_id,
    _extract_claim_encounter_fhir_ids,
    _extract_claim_diagnosis_fhir_ids,
)

# All tests in this module require Neo4j
pytestmark = pytest.mark.integration


# =============================================================================
# Unit tests for helper functions
# =============================================================================


class TestExtractReferenceId:
    """Unit tests for _extract_reference_id helper function."""

    def test_extracts_urn_uuid(self):
        """Test extraction from urn:uuid format."""
        ref = "urn:uuid:abc-123-def"
        assert _extract_reference_id(ref) == "abc-123-def"

    def test_extracts_slash_format(self):
        """Test extraction from ResourceType/id format."""
        ref = "Patient/patient-123"
        assert _extract_reference_id(ref) == "patient-123"

    def test_extracts_encounter_slash_format(self):
        """Test extraction from Encounter/id format."""
        ref = "Encounter/encounter-456"
        assert _extract_reference_id(ref) == "encounter-456"

    def test_handles_plain_id(self):
        """Test handling of plain ID without prefix."""
        ref = "plain-id-789"
        assert _extract_reference_id(ref) == "plain-id-789"

    def test_handles_none(self):
        """Test handling of None input."""
        assert _extract_reference_id(None) is None

    def test_handles_empty_string(self):
        """Test handling of empty string input."""
        assert _extract_reference_id("") is None


class TestExtractReferenceIds:
    """Unit tests for _extract_reference_ids helper function."""

    def test_extracts_multiple_references(self):
        """Test extraction from list of reference objects."""
        refs = [
            {"reference": "Condition/cond-1"},
            {"reference": "Condition/cond-2"},
        ]
        assert _extract_reference_ids(refs) == ["cond-1", "cond-2"]

    def test_handles_empty_list(self):
        """Test handling of empty list."""
        assert _extract_reference_ids([]) == []

    def test_filters_none_values(self):
        """Test that None values are filtered out."""
        refs = [
            {"reference": "Condition/cond-1"},
            {"other": "field"},  # No reference key
            {"reference": ""},  # Empty reference
        ]
        assert _extract_reference_ids(refs) == ["cond-1"]


class TestExtractFirstCoding:
    """Unit tests for _extract_first_coding helper function."""

    def test_extracts_first_coding(self):
        """Test extraction of first coding."""
        codeable = {
            "coding": [
                {"code": "123", "display": "Test", "system": "http://test.org"},
                {"code": "456", "display": "Other"},
            ]
        }
        result = _extract_first_coding(codeable)
        assert result["code"] == "123"
        assert result["display"] == "Test"

    def test_handles_empty_coding(self):
        """Test handling of empty coding list."""
        assert _extract_first_coding({"coding": []}) == {}

    def test_handles_missing_coding(self):
        """Test handling of missing coding key."""
        assert _extract_first_coding({}) == {}


class TestExtractClinicalStatus:
    """Unit tests for _extract_clinical_status helper function."""

    def test_extracts_active_status(self):
        """Test extraction of active status."""
        resource = {"clinicalStatus": {"coding": [{"code": "active"}]}}
        assert _extract_clinical_status(resource) == "active"

    def test_handles_missing_status(self):
        """Test handling of missing clinicalStatus."""
        assert _extract_clinical_status({}) == ""


class TestExtractEncounterFhirId:
    """Unit tests for _extract_encounter_fhir_id helper function."""

    def test_extracts_encounter_reference(self):
        """Test extraction of encounter reference."""
        resource = {"encounter": {"reference": "Encounter/enc-123"}}
        assert _extract_encounter_fhir_id(resource) == "enc-123"

    def test_handles_missing_encounter(self):
        """Test handling of missing encounter."""
        assert _extract_encounter_fhir_id({}) is None


class TestExtractObservationValue:
    """Unit tests for _extract_observation_value helper function."""

    def test_extracts_quantity_value(self):
        """Test extraction of valueQuantity."""
        resource = {"valueQuantity": {"value": 120, "unit": "mmHg"}}
        value, unit = _extract_observation_value(resource)
        assert value == 120
        assert unit == "mmHg"

    def test_extracts_codeable_concept_value(self):
        """Test extraction of valueCodeableConcept."""
        resource = {"valueCodeableConcept": {"coding": [{"display": "Positive"}]}}
        value, unit = _extract_observation_value(resource)
        assert value == "Positive"
        assert unit is None

    def test_extracts_string_value(self):
        """Test extraction of valueString."""
        resource = {"valueString": "Normal"}
        value, unit = _extract_observation_value(resource)
        assert value == "Normal"
        assert unit is None

    def test_handles_no_value(self):
        """Test handling of resource with no value."""
        value, unit = _extract_observation_value({})
        assert value is None
        assert unit is None


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
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_condition,
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
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_medication,
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
    assert (
        med_node["code"]
        == sample_medication["medicationCodeableConcept"]["coding"][0]["code"]
    )
    assert (
        med_node["display"]
        == sample_medication["medicationCodeableConcept"]["coding"][0]["display"]
    )
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
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_observation,
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
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
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
    assert (
        encounter_node["type_code"] == sample_encounter["type"][0]["coding"][0]["code"]
    )
    assert (
        encounter_node["type_display"]
        == sample_encounter["type"][0]["coding"][0]["display"]
    )
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
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_condition,
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
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_condition,
    sample_medication,
):
    """Test that clear_patient_graph removes patient and related nodes."""
    await graph.build_from_fhir(
        patient_id, [sample_patient, sample_condition, sample_medication]
    )
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
    assert (
        conditions[0]["code"]["coding"][0]["display"]
        == sample_condition["code"]["coding"][0]["display"]
    )


@pytest.mark.asyncio
async def test_get_verified_conditions_excludes_inactive(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_condition,
    sample_condition_inactive,
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
    expected_display = sample_medication["medicationCodeableConcept"]["coding"][0][
        "display"
    ]
    assert (
        medications[0]["medicationCodeableConcept"]["coding"][0]["display"]
        == expected_display
    )


@pytest.mark.asyncio
async def test_get_verified_medications_includes_on_hold(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_medication,
    sample_medication_on_hold,
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
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_medication,
    sample_medication_stopped,
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
    assert (
        allergies[0]["code"]["coding"][0]["display"]
        == sample_allergy["code"]["coding"][0]["display"]
    )


@pytest.mark.asyncio
async def test_get_verified_allergies_excludes_inactive(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_allergy,
    sample_allergy_inactive,
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
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_condition,
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
    assert (
        stored_resource["code"]["coding"][0]["display"]
        == sample_condition["code"]["coding"][0]["display"]
    )


@pytest.mark.asyncio
async def test_fhir_resource_stored_on_medication_node(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_medication,
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
async def test_fhir_resource_stored_on_encounter_node(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
):
    """Test that the full FHIR resource is stored on Encounter nodes."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_encounter])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_ENCOUNTER]->(e:Encounter)
            RETURN e.fhir_resource as fhir_resource
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    assert record["fhir_resource"] is not None
    stored_resource = json.loads(record["fhir_resource"])
    assert stored_resource["resourceType"] == "Encounter"
    assert stored_resource["id"] == sample_encounter["id"]


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


# =============================================================================
# Tests for Procedure and DiagnosticReport nodes
# =============================================================================


@pytest.mark.asyncio
async def test_build_from_fhir_creates_procedure_with_relationship(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_procedure,
):
    """Test that build_from_fhir creates Procedure node with HAS_PROCEDURE relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_procedure])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_PROCEDURE]->(pr:Procedure)
            RETURN pr
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    proc_node = record["pr"]
    assert proc_node["fhir_id"] == sample_procedure["id"]
    assert proc_node["code"] == sample_procedure["code"]["coding"][0]["code"]
    assert proc_node["display"] == sample_procedure["code"]["coding"][0]["display"]
    assert proc_node["status"] == sample_procedure["status"]


@pytest.mark.asyncio
async def test_build_from_fhir_creates_diagnostic_report_with_relationship(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_diagnostic_report,
):
    """Test that build_from_fhir creates DiagnosticReport node with HAS_DIAGNOSTIC_REPORT relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_diagnostic_report])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_DIAGNOSTIC_REPORT]->(dr:DiagnosticReport)
            RETURN dr
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    report_node = record["dr"]
    assert report_node["fhir_id"] == sample_diagnostic_report["id"]
    assert report_node["code"] == sample_diagnostic_report["code"]["coding"][0]["code"]
    assert report_node["status"] == sample_diagnostic_report["status"]


# =============================================================================
# Tests for Encounter-centric relationships (Tier 1)
# =============================================================================


@pytest.mark.asyncio
async def test_encounter_diagnosed_condition_relationship(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_condition_with_encounter,
):
    """Test Encounter -[:DIAGNOSED]-> Condition relationship is created."""
    await graph.build_from_fhir(
        patient_id, [sample_patient, sample_encounter, sample_condition_with_encounter]
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (e:Encounter {fhir_id: $encounter_id})-[:DIAGNOSED]->(c:Condition)
            RETURN c.fhir_id as condition_id
            """,
            encounter_id=sample_encounter["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["condition_id"] == sample_condition_with_encounter["id"]


@pytest.mark.asyncio
async def test_encounter_prescribed_medication_relationship(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_condition_with_encounter,
    sample_medication_with_encounter_and_reason,
):
    """Test Encounter -[:PRESCRIBED]-> MedicationRequest relationship is created."""
    await graph.build_from_fhir(
        patient_id,
        [
            sample_patient,
            sample_encounter,
            sample_condition_with_encounter,
            sample_medication_with_encounter_and_reason,
        ],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (e:Encounter {fhir_id: $encounter_id})-[:PRESCRIBED]->(m:MedicationRequest)
            RETURN m.fhir_id as med_id
            """,
            encounter_id=sample_encounter["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["med_id"] == sample_medication_with_encounter_and_reason["id"]


@pytest.mark.asyncio
async def test_encounter_recorded_observation_relationship(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_observation_with_encounter,
):
    """Test Encounter -[:RECORDED]-> Observation relationship is created."""
    await graph.build_from_fhir(
        patient_id, [sample_patient, sample_encounter, sample_observation_with_encounter]
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (e:Encounter {fhir_id: $encounter_id})-[:RECORDED]->(o:Observation)
            RETURN o.fhir_id as obs_id
            """,
            encounter_id=sample_encounter["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["obs_id"] == sample_observation_with_encounter["id"]


@pytest.mark.asyncio
async def test_encounter_performed_procedure_relationship(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_condition_with_encounter,
    sample_procedure_with_encounter_and_reason,
):
    """Test Encounter -[:PERFORMED]-> Procedure relationship is created."""
    await graph.build_from_fhir(
        patient_id,
        [
            sample_patient,
            sample_encounter,
            sample_condition_with_encounter,
            sample_procedure_with_encounter_and_reason,
        ],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (e:Encounter {fhir_id: $encounter_id})-[:PERFORMED]->(pr:Procedure)
            RETURN pr.fhir_id as proc_id
            """,
            encounter_id=sample_encounter["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["proc_id"] == sample_procedure_with_encounter_and_reason["id"]


@pytest.mark.asyncio
async def test_encounter_reported_diagnostic_report_relationship(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_observation_with_encounter,
    sample_diagnostic_report_with_encounter_and_results,
):
    """Test Encounter -[:REPORTED]-> DiagnosticReport relationship is created."""
    await graph.build_from_fhir(
        patient_id,
        [
            sample_patient,
            sample_encounter,
            sample_observation_with_encounter,
            sample_diagnostic_report_with_encounter_and_results,
        ],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (e:Encounter {fhir_id: $encounter_id})-[:REPORTED]->(dr:DiagnosticReport)
            RETURN dr.fhir_id as report_id
            """,
            encounter_id=sample_encounter["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["report_id"] == sample_diagnostic_report_with_encounter_and_results["id"]


# =============================================================================
# Tests for clinical reasoning relationships (Tier 2)
# =============================================================================


@pytest.mark.asyncio
async def test_medication_treats_condition_relationship(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_condition_with_encounter,
    sample_medication_with_encounter_and_reason,
):
    """Test MedicationRequest -[:TREATS]-> Condition relationship is created."""
    await graph.build_from_fhir(
        patient_id,
        [
            sample_patient,
            sample_encounter,
            sample_condition_with_encounter,
            sample_medication_with_encounter_and_reason,
        ],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (m:MedicationRequest {fhir_id: $med_id})-[:TREATS]->(c:Condition)
            RETURN c.fhir_id as condition_id
            """,
            med_id=sample_medication_with_encounter_and_reason["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["condition_id"] == sample_condition_with_encounter["id"]


@pytest.mark.asyncio
async def test_procedure_treats_condition_relationship(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_condition_with_encounter,
    sample_procedure_with_encounter_and_reason,
):
    """Test Procedure -[:TREATS]-> Condition relationship is created."""
    await graph.build_from_fhir(
        patient_id,
        [
            sample_patient,
            sample_encounter,
            sample_condition_with_encounter,
            sample_procedure_with_encounter_and_reason,
        ],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (pr:Procedure {fhir_id: $proc_id})-[:TREATS]->(c:Condition)
            RETURN c.fhir_id as condition_id
            """,
            proc_id=sample_procedure_with_encounter_and_reason["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["condition_id"] == sample_condition_with_encounter["id"]


@pytest.mark.asyncio
async def test_diagnostic_report_contains_result_relationship(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_observation_with_encounter,
    sample_diagnostic_report_with_encounter_and_results,
):
    """Test DiagnosticReport -[:CONTAINS_RESULT]-> Observation relationship is created."""
    await graph.build_from_fhir(
        patient_id,
        [
            sample_patient,
            sample_encounter,
            sample_observation_with_encounter,
            sample_diagnostic_report_with_encounter_and_results,
        ],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (dr:DiagnosticReport {fhir_id: $report_id})-[:CONTAINS_RESULT]->(o:Observation)
            RETURN o.fhir_id as obs_id
            """,
            report_id=sample_diagnostic_report_with_encounter_and_results["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["obs_id"] == sample_observation_with_encounter["id"]


# =============================================================================
# Tests for urn:uuid reference handling
# =============================================================================


@pytest.mark.asyncio
async def test_urn_uuid_encounter_reference_resolved(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_condition_with_urn_uuid_encounter,
):
    """Test that urn:uuid references are correctly resolved to create relationships."""
    await graph.build_from_fhir(
        patient_id,
        [sample_patient, sample_encounter, sample_condition_with_urn_uuid_encounter],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (e:Encounter {fhir_id: $encounter_id})-[:DIAGNOSED]->(c:Condition)
            RETURN c.fhir_id as condition_id
            """,
            encounter_id=sample_encounter["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["condition_id"] == sample_condition_with_urn_uuid_encounter["id"]


# =============================================================================
# Tests for query methods
# =============================================================================


@pytest.mark.asyncio
async def test_get_encounter_events(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_encounter,
    sample_condition_with_encounter,
    sample_medication_with_encounter_and_reason,
    sample_observation_with_encounter,
    sample_procedure_with_encounter_and_reason,
    sample_diagnostic_report_with_encounter_and_results,
):
    """Test get_encounter_events returns all clinical events for an encounter."""
    await graph.build_from_fhir(
        patient_id,
        [
            sample_patient,
            sample_encounter,
            sample_condition_with_encounter,
            sample_medication_with_encounter_and_reason,
            sample_observation_with_encounter,
            sample_procedure_with_encounter_and_reason,
            sample_diagnostic_report_with_encounter_and_results,
        ],
    )

    events = await graph.get_encounter_events(sample_encounter["id"])

    # Traversal methods now return parsed FHIR resources (not node dicts)
    assert len(events["conditions"]) == 1
    assert events["conditions"][0]["id"] == sample_condition_with_encounter["id"]
    assert events["conditions"][0]["resourceType"] == "Condition"

    assert len(events["medications"]) == 1
    assert events["medications"][0]["id"] == sample_medication_with_encounter_and_reason["id"]
    assert events["medications"][0]["resourceType"] == "MedicationRequest"

    assert len(events["observations"]) == 1
    assert events["observations"][0]["id"] == sample_observation_with_encounter["id"]
    assert events["observations"][0]["resourceType"] == "Observation"

    assert len(events["procedures"]) == 1
    assert events["procedures"][0]["id"] == sample_procedure_with_encounter_and_reason["id"]
    assert events["procedures"][0]["resourceType"] == "Procedure"

    assert len(events["diagnostic_reports"]) == 1
    assert events["diagnostic_reports"][0]["id"] == sample_diagnostic_report_with_encounter_and_results["id"]
    assert events["diagnostic_reports"][0]["resourceType"] == "DiagnosticReport"


@pytest.mark.asyncio
async def test_get_encounter_events_empty_for_nonexistent(graph: KnowledgeGraph):
    """Test get_encounter_events returns empty collections for nonexistent encounter."""
    events = await graph.get_encounter_events("nonexistent-encounter")

    assert events["conditions"] == []
    assert events["medications"] == []
    assert events["observations"] == []
    assert events["procedures"] == []
    assert events["diagnostic_reports"] == []


@pytest.mark.asyncio
async def test_get_medications_treating_condition(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_encounter,
    sample_condition_with_encounter,
    sample_medication_with_encounter_and_reason,
):
    """Test get_medications_treating_condition returns medications linked to a condition."""
    await graph.build_from_fhir(
        patient_id,
        [
            sample_patient,
            sample_encounter,
            sample_condition_with_encounter,
            sample_medication_with_encounter_and_reason,
        ],
    )

    meds = await graph.get_medications_treating_condition(sample_condition_with_encounter["id"])

    assert len(meds) == 1
    assert meds[0]["id"] == sample_medication_with_encounter_and_reason["id"]
    assert meds[0]["resourceType"] == "MedicationRequest"


@pytest.mark.asyncio
async def test_get_procedures_for_condition(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_encounter,
    sample_condition_with_encounter,
    sample_procedure_with_encounter_and_reason,
):
    """Test get_procedures_for_condition returns procedures linked to a condition."""
    await graph.build_from_fhir(
        patient_id,
        [
            sample_patient,
            sample_encounter,
            sample_condition_with_encounter,
            sample_procedure_with_encounter_and_reason,
        ],
    )

    procs = await graph.get_procedures_for_condition(sample_condition_with_encounter["id"])

    assert len(procs) == 1
    assert procs[0]["id"] == sample_procedure_with_encounter_and_reason["id"]
    assert procs[0]["resourceType"] == "Procedure"


@pytest.mark.asyncio
async def test_get_diagnostic_report_results(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_encounter,
    sample_observation_with_encounter,
    sample_diagnostic_report_with_encounter_and_results,
):
    """Test get_diagnostic_report_results returns observations in a report."""
    await graph.build_from_fhir(
        patient_id,
        [
            sample_patient,
            sample_encounter,
            sample_observation_with_encounter,
            sample_diagnostic_report_with_encounter_and_results,
        ],
    )

    obs = await graph.get_diagnostic_report_results(
        sample_diagnostic_report_with_encounter_and_results["id"]
    )

    assert len(obs) == 1
    assert obs[0]["id"] == sample_observation_with_encounter["id"]
    assert obs[0]["resourceType"] == "Observation"


# =============================================================================
# Tests for encounter_fhir_id stored on nodes
# =============================================================================


@pytest.mark.asyncio
async def test_condition_stores_encounter_fhir_id(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_condition_with_encounter,
):
    """Test that Condition node stores encounter_fhir_id for relationship building."""
    await graph.build_from_fhir(
        patient_id, [sample_patient, sample_encounter, sample_condition_with_encounter]
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (c:Condition {fhir_id: $condition_id})
            RETURN c.encounter_fhir_id as encounter_id
            """,
            condition_id=sample_condition_with_encounter["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["encounter_id"] == sample_encounter["id"]


@pytest.mark.asyncio
async def test_medication_stores_reason_fhir_ids(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_condition_with_encounter,
    sample_medication_with_encounter_and_reason,
):
    """Test that MedicationRequest node stores reason_fhir_ids for TREATS relationship."""
    await graph.build_from_fhir(
        patient_id,
        [
            sample_patient,
            sample_encounter,
            sample_condition_with_encounter,
            sample_medication_with_encounter_and_reason,
        ],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (m:MedicationRequest {fhir_id: $med_id})
            RETURN m.reason_fhir_ids as reason_ids
            """,
            med_id=sample_medication_with_encounter_and_reason["id"],
        )
        record = await result.single()

    assert record is not None
    assert sample_condition_with_encounter["id"] in record["reason_ids"]


# =============================================================================
# Tests for search_nodes_by_name
# =============================================================================


@pytest.mark.asyncio
async def test_search_nodes_by_name_finds_condition(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_condition,
):
    """Test search_nodes_by_name finds a condition by display name substring."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_condition])

    display = sample_condition["code"]["coding"][0]["display"]
    # Use a substring of the display name
    term = display.split()[0].lower()
    results = await graph.search_nodes_by_name(patient_id, [term])

    assert len(results) >= 1
    fhir_ids = [r["fhir_id"] for r in results]
    assert sample_condition["id"] in fhir_ids
    match = next(r for r in results if r["fhir_id"] == sample_condition["id"])
    assert match["resource_type"] == "Condition"


@pytest.mark.asyncio
async def test_search_nodes_by_name_case_insensitive(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_condition,
):
    """Test search is case-insensitive."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_condition])

    display = sample_condition["code"]["coding"][0]["display"]
    results = await graph.search_nodes_by_name(patient_id, [display.upper()])

    fhir_ids = [r["fhir_id"] for r in results]
    assert sample_condition["id"] in fhir_ids


@pytest.mark.asyncio
async def test_search_nodes_by_name_filters_by_resource_type(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_condition,
    sample_medication,
):
    """Test search respects resource_types filter."""
    await graph.build_from_fhir(
        patient_id, [sample_patient, sample_condition, sample_medication]
    )

    # Search with a broad term but filter to only MedicationRequest
    med_display = sample_medication["medicationCodeableConcept"]["coding"][0]["display"]
    term = med_display.split()[0].lower()
    results = await graph.search_nodes_by_name(
        patient_id, [term], resource_types=["MedicationRequest"]
    )

    resource_types = {r["resource_type"] for r in results}
    assert resource_types <= {"MedicationRequest"}


@pytest.mark.asyncio
async def test_search_nodes_by_name_returns_empty_for_no_match(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_condition,
):
    """Test search returns empty list when no nodes match."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_condition])

    results = await graph.search_nodes_by_name(patient_id, ["zzzznonexistent"])
    assert results == []


@pytest.mark.asyncio
async def test_search_nodes_by_name_empty_terms(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_condition,
):
    """Test search returns empty list for empty query terms."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_condition])

    results = await graph.search_nodes_by_name(patient_id, [])
    assert results == []


# =============================================================================
# Tests for Immunization nodes
# =============================================================================


@pytest.mark.asyncio
async def test_build_from_fhir_creates_immunization_with_relationship(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_immunization,
):
    """Test that build_from_fhir creates Immunization node with HAS_IMMUNIZATION relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_immunization])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_IMMUNIZATION]->(im:Immunization)
            RETURN im
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    imm_node = record["im"]
    assert imm_node["fhir_id"] == sample_immunization["id"]
    assert imm_node["code"] == sample_immunization["vaccineCode"]["coding"][0]["code"]
    assert imm_node["display"] == sample_immunization["vaccineCode"]["coding"][0]["display"]
    assert imm_node["status"] == sample_immunization["status"]


@pytest.mark.asyncio
async def test_get_verified_immunizations_returns_completed(
    graph: KnowledgeGraph, patient_id: str, sample_patient, sample_immunization
):
    """Test that get_verified_immunizations returns only completed immunizations."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_immunization])

    immunizations = await graph.get_verified_immunizations(patient_id)

    assert len(immunizations) == 1
    assert immunizations[0]["resourceType"] == "Immunization"
    assert immunizations[0]["id"] == sample_immunization["id"]


@pytest.mark.asyncio
async def test_get_verified_immunizations_excludes_not_done(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_immunization,
    sample_immunization_not_done,
):
    """Test that get_verified_immunizations excludes not-done immunizations."""
    await graph.build_from_fhir(
        patient_id, [sample_patient, sample_immunization, sample_immunization_not_done]
    )

    immunizations = await graph.get_verified_immunizations(patient_id)

    assert len(immunizations) == 1
    assert immunizations[0]["id"] == sample_immunization["id"]


@pytest.mark.asyncio
async def test_get_verified_immunizations_returns_empty_for_nonexistent_patient(
    graph: KnowledgeGraph,
):
    """Test that get_verified_immunizations returns empty list for nonexistent patient."""
    immunizations = await graph.get_verified_immunizations("nonexistent-patient-id")
    assert immunizations == []


@pytest.mark.asyncio
async def test_encounter_administered_immunization_relationship(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_immunization_with_encounter,
):
    """Test Encounter -[:ADMINISTERED]-> Immunization relationship is created."""
    await graph.build_from_fhir(
        patient_id, [sample_patient, sample_encounter, sample_immunization_with_encounter]
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (e:Encounter {fhir_id: $encounter_id})-[:ADMINISTERED]->(im:Immunization)
            RETURN im.fhir_id as imm_id
            """,
            encounter_id=sample_encounter["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["imm_id"] == sample_immunization_with_encounter["id"]


@pytest.mark.asyncio
async def test_verified_facts_includes_immunizations(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_immunization,
    sample_immunization_not_done,
):
    """Test that get_verified_facts includes immunizations."""
    await graph.build_from_fhir(
        patient_id, [sample_patient, sample_immunization, sample_immunization_not_done]
    )

    facts = await graph.get_verified_facts(patient_id)

    assert "immunizations" in facts
    assert len(facts["immunizations"]) == 1
    assert facts["immunizations"][0]["id"] == sample_immunization["id"]


@pytest.mark.asyncio
async def test_search_nodes_by_name_multiple_terms(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_condition,
    sample_medication,
):
    """Test search with multiple terms finds nodes matching any term."""
    await graph.build_from_fhir(
        patient_id, [sample_patient, sample_condition, sample_medication]
    )

    cond_display = sample_condition["code"]["coding"][0]["display"]
    med_display = sample_medication["medicationCodeableConcept"]["coding"][0]["display"]
    results = await graph.search_nodes_by_name(
        patient_id, [cond_display, med_display]
    )

    fhir_ids = {r["fhir_id"] for r in results}
    assert sample_condition["id"] in fhir_ids
    assert sample_medication["id"] in fhir_ids


# =============================================================================
# Tests for expanded node properties (category, reasonCode, abatement)
# =============================================================================


@pytest.mark.asyncio
async def test_observation_stores_category(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_observation_with_category,
):
    """Test that Observation node stores category from FHIR category[0].coding[0].code."""
    await graph.build_from_fhir(
        patient_id, [sample_patient, sample_observation_with_category]
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (o:Observation {fhir_id: $fhir_id})
            RETURN o.category as category
            """,
            fhir_id=sample_observation_with_category["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["category"] == "vital-signs"


@pytest.mark.asyncio
async def test_observation_category_null_when_absent(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_observation,
):
    """Test that Observation.category is NULL when category field is absent."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_observation])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (o:Observation {fhir_id: $fhir_id})
            RETURN o.category as category
            """,
            fhir_id=sample_observation["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["category"] is None


@pytest.mark.asyncio
async def test_encounter_stores_reason(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter_with_reason,
):
    """Test that Encounter node stores reason_display and reason_code from reasonCode."""
    await graph.build_from_fhir(
        patient_id, [sample_patient, sample_encounter_with_reason]
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (e:Encounter {fhir_id: $fhir_id})
            RETURN e.reason_display as reason_display, e.reason_code as reason_code
            """,
            fhir_id=sample_encounter_with_reason["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["reason_display"] == "Hypertension"
    assert record["reason_code"] == "38341003"


@pytest.mark.asyncio
async def test_encounter_reason_null_when_absent(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
):
    """Test that Encounter reason fields are NULL when reasonCode is absent."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_encounter])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (e:Encounter {fhir_id: $fhir_id})
            RETURN e.reason_display as reason_display, e.reason_code as reason_code
            """,
            fhir_id=sample_encounter["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["reason_display"] is None
    assert record["reason_code"] is None


@pytest.mark.asyncio
async def test_condition_stores_abatement_date(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_condition_with_abatement,
):
    """Test that Condition node stores abatement_date from abatementDateTime."""
    await graph.build_from_fhir(
        patient_id, [sample_patient, sample_condition_with_abatement]
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (c:Condition {fhir_id: $fhir_id})
            RETURN c.abatement_date as abatement_date
            """,
            fhir_id=sample_condition_with_abatement["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["abatement_date"] == "2024-01-24T00:00:00Z"


@pytest.mark.asyncio
async def test_condition_abatement_date_null_when_absent(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_condition,
):
    """Test that Condition.abatement_date is NULL when abatementDateTime is absent."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_condition])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (c:Condition {fhir_id: $fhir_id})
            RETURN c.abatement_date as abatement_date
            """,
            fhir_id=sample_condition["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["abatement_date"] is None


@pytest.mark.asyncio
async def test_encounter_stores_fhir_resource(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
):
    """Test that Encounter node stores fhir_resource (bug fix verification)."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_encounter])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (e:Encounter {fhir_id: $fhir_id})
            RETURN e.fhir_resource as fhir_resource
            """,
            fhir_id=sample_encounter["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["fhir_resource"] is not None
    stored = json.loads(record["fhir_resource"])
    assert stored["resourceType"] == "Encounter"
    assert stored["id"] == sample_encounter["id"]


# =============================================================================
# Tests for CarePlan node type
# =============================================================================


@pytest.mark.asyncio
async def test_build_from_fhir_creates_careplan_with_relationship(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_careplan,
):
    """Test that build_from_fhir creates CarePlan node with HAS_CARE_PLAN relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_careplan])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_CARE_PLAN]->(cp:CarePlan)
            RETURN cp
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    cp_node = record["cp"]
    assert cp_node["fhir_id"] == sample_careplan["id"]
    assert cp_node["display"] == "Assessment and Plan of Treatment"
    assert cp_node["status"] == "active"
    assert cp_node["period_start"] == "2024-01-15T09:00:00Z"


@pytest.mark.asyncio
async def test_careplan_uses_title_over_category(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_careplan_with_title,
):
    """Test that CarePlan prefers title over category display."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_careplan_with_title])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (cp:CarePlan {fhir_id: $fhir_id})
            RETURN cp.display as display
            """,
            fhir_id=sample_careplan_with_title["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["display"] == "Diabetes self-management plan"


@pytest.mark.asyncio
async def test_careplan_stores_fhir_resource(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_careplan,
):
    """Test that the full FHIR resource is stored on CarePlan nodes."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_careplan])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (cp:CarePlan {fhir_id: $fhir_id})
            RETURN cp.fhir_resource as fhir_resource
            """,
            fhir_id=sample_careplan["id"],
        )
        record = await result.single()

    assert record is not None
    stored = json.loads(record["fhir_resource"])
    assert stored["resourceType"] == "CarePlan"
    assert stored["id"] == sample_careplan["id"]


@pytest.mark.asyncio
async def test_careplan_addresses_condition_relationship(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_condition_with_encounter,
    sample_careplan_with_addresses,
):
    """Test CarePlan -[:ADDRESSES]-> Condition relationship is created."""
    await graph.build_from_fhir(
        patient_id,
        [sample_patient, sample_condition_with_encounter, sample_careplan_with_addresses],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (cp:CarePlan {fhir_id: $cp_id})-[:ADDRESSES]->(c:Condition)
            RETURN c.fhir_id as condition_id
            """,
            cp_id=sample_careplan_with_addresses["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["condition_id"] == sample_condition_with_encounter["id"]


@pytest.mark.asyncio
async def test_careplan_stores_addresses_fhir_ids(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_condition_with_encounter,
    sample_careplan_with_addresses,
):
    """Test that CarePlan node stores addresses_fhir_ids for ADDRESSES relationship."""
    await graph.build_from_fhir(
        patient_id,
        [sample_patient, sample_condition_with_encounter, sample_careplan_with_addresses],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (cp:CarePlan {fhir_id: $cp_id})
            RETURN cp.addresses_fhir_ids as addresses_ids
            """,
            cp_id=sample_careplan_with_addresses["id"],
        )
        record = await result.single()

    assert record is not None
    assert sample_condition_with_encounter["id"] in record["addresses_ids"]


# =============================================================================
# Unit tests for new helper functions
# =============================================================================


class TestExtractContextEncounterFhirId:
    """Unit tests for _extract_context_encounter_fhir_id helper."""

    def test_extracts_context_reference(self):
        resource = {"context": {"reference": "Encounter/enc-123"}}
        assert _extract_context_encounter_fhir_id(resource) == "enc-123"

    def test_handles_missing_context(self):
        assert _extract_context_encounter_fhir_id({}) is None

    def test_handles_urn_uuid(self):
        resource = {"context": {"reference": "urn:uuid:enc-456"}}
        assert _extract_context_encounter_fhir_id(resource) == "enc-456"


class TestExtractDocRefEncounterFhirId:
    """Unit tests for _extract_doc_ref_encounter_fhir_id helper."""

    def test_extracts_encounter_from_context_array(self):
        resource = {
            "context": {
                "encounter": [{"reference": "Encounter/enc-789"}]
            }
        }
        assert _extract_doc_ref_encounter_fhir_id(resource) == "enc-789"

    def test_handles_empty_encounter_array(self):
        resource = {"context": {"encounter": []}}
        assert _extract_doc_ref_encounter_fhir_id(resource) is None

    def test_handles_missing_context(self):
        assert _extract_doc_ref_encounter_fhir_id({}) is None


class TestExtractClaimEncounterFhirIds:
    """Unit tests for _extract_claim_encounter_fhir_ids helper."""

    def test_extracts_from_items(self):
        resource = {
            "item": [
                {"encounter": [{"reference": "Encounter/enc-1"}]},
                {"encounter": [{"reference": "Encounter/enc-2"}]},
            ]
        }
        ids = _extract_claim_encounter_fhir_ids(resource)
        assert set(ids) == {"enc-1", "enc-2"}

    def test_deduplicates(self):
        resource = {
            "item": [
                {"encounter": [{"reference": "Encounter/enc-1"}]},
                {"encounter": [{"reference": "Encounter/enc-1"}]},
            ]
        }
        ids = _extract_claim_encounter_fhir_ids(resource)
        assert ids == ["enc-1"]

    def test_handles_empty_items(self):
        assert _extract_claim_encounter_fhir_ids({}) == []


class TestExtractClaimDiagnosisFhirIds:
    """Unit tests for _extract_claim_diagnosis_fhir_ids helper."""

    def test_extracts_diagnosis_references(self):
        resource = {
            "diagnosis": [
                {"diagnosisReference": {"reference": "Condition/cond-1"}},
                {"diagnosisReference": {"reference": "Condition/cond-2"}},
            ]
        }
        ids = _extract_claim_diagnosis_fhir_ids(resource)
        assert ids == ["cond-1", "cond-2"]

    def test_handles_empty_diagnosis(self):
        assert _extract_claim_diagnosis_fhir_ids({}) == []


# =============================================================================
# Tests for new node types
# =============================================================================


@pytest.mark.asyncio
async def test_build_from_fhir_creates_document_reference(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_document_reference,
):
    """Test DocumentReference node creation with HAS_DOCUMENT_REFERENCE relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_document_reference])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_DOCUMENT_REFERENCE]->(d:DocumentReference)
            RETURN d
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    node = record["d"]
    assert node["fhir_id"] == sample_document_reference["id"]
    assert node["type_display"] == "Summary of episode note"
    assert node["status"] == "current"


@pytest.mark.asyncio
async def test_build_from_fhir_creates_imaging_study(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_imaging_study,
):
    """Test ImagingStudy node creation with HAS_IMAGING_STUDY relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_imaging_study])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_IMAGING_STUDY]->(i:ImagingStudy)
            RETURN i
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    node = record["i"]
    assert node["fhir_id"] == sample_imaging_study["id"]
    assert node["procedure_display"] == "Mammography"
    assert node["modality"] == "Digital Radiography"
    assert node["body_site"] == "Breast"


@pytest.mark.asyncio
async def test_build_from_fhir_creates_device(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_device,
):
    """Test Device node creation with HAS_DEVICE relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_device])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_DEVICE]->(d:Device)
            RETURN d
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    node = record["d"]
    assert node["fhir_id"] == sample_device["id"]
    assert node["type_display"] == "Cardiac pacemaker"
    assert node["status"] == "active"


@pytest.mark.asyncio
async def test_build_from_fhir_creates_care_team(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_care_team,
):
    """Test CareTeam node creation with HAS_CARE_TEAM relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_care_team])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_CARE_TEAM]->(ct:CareTeam)
            RETURN ct
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    node = record["ct"]
    assert node["fhir_id"] == sample_care_team["id"]
    assert node["display"] == "Essential hypertension"
    assert node["status"] == "active"


@pytest.mark.asyncio
async def test_build_from_fhir_creates_medication_administration(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_medication_administration,
):
    """Test MedicationAdministration node creation with HAS_MEDICATION_ADMINISTRATION relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_medication_administration])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_MEDICATION_ADMINISTRATION]->(ma:MedicationAdministration)
            RETURN ma
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    node = record["ma"]
    assert node["fhir_id"] == sample_medication_administration["id"]
    assert node["display"] == "sodium fluoride 0.0272 MG/MG Oral Gel"
    assert node["status"] == "completed"


@pytest.mark.asyncio
async def test_build_from_fhir_creates_medication_catalog(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_medication_catalog,
):
    """Test Medication (catalog) node creation without patient edge."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_medication_catalog])

    async with neo4j_driver.session() as session:
        # Verify node exists
        result = await session.run(
            """
            MATCH (med:Medication {fhir_id: $fhir_id})
            RETURN med
            """,
            fhir_id=sample_medication_catalog["id"],
        )
        record = await result.single()

    assert record is not None
    node = record["med"]
    assert node["display"] == "sodium fluoride 0.0272 MG/MG Oral Gel"
    assert node["status"] == "active"

    # Verify NO patient edge
    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[r]->(med:Medication {fhir_id: $fhir_id})
            RETURN type(r) as rel_type
            """,
            id=patient_id,
            fhir_id=sample_medication_catalog["id"],
        )
        record = await result.single()

    assert record is None


@pytest.mark.asyncio
async def test_build_from_fhir_creates_claim(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_claim,
):
    """Test Claim node creation with HAS_CLAIM relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_claim])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_CLAIM]->(cl:Claim)
            RETURN cl
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    node = record["cl"]
    assert node["fhir_id"] == sample_claim["id"]
    assert node["type_code"] == "professional"
    assert node["status"] == "active"
    assert node["primary_service_display"] == "Well child visit"


@pytest.mark.asyncio
async def test_build_from_fhir_creates_eob(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_eob,
):
    """Test ExplanationOfBenefit node creation with HAS_EOB relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_eob])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_EOB]->(eob:ExplanationOfBenefit)
            RETURN eob
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    node = record["eob"]
    assert node["fhir_id"] == sample_eob["id"]
    assert node["type_code"] == "professional"
    assert node["total_amount"] == 704.20
    assert node["payment_amount"] == 0.00
    assert node["claim_fhir_id"] == "claim-test-001"


@pytest.mark.asyncio
async def test_build_from_fhir_creates_supply_delivery(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_supply_delivery,
):
    """Test SupplyDelivery node creation with HAS_SUPPLY_DELIVERY relationship."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_supply_delivery])

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (p:Patient {id: $id})-[:HAS_SUPPLY_DELIVERY]->(sd:SupplyDelivery)
            RETURN sd
            """,
            id=patient_id,
        )
        record = await result.single()

    assert record is not None
    node = record["sd"]
    assert node["fhir_id"] == sample_supply_delivery["id"]
    assert node["item_display"] == "Dental impression material"
    assert node["type_display"] == "Device"
    assert node["status"] == "completed"


# =============================================================================
# Tests for new encounter-centric edges
# =============================================================================


@pytest.mark.asyncio
async def test_encounter_documented_document_reference(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_document_reference_with_encounter,
):
    """Test Encounter -[:DOCUMENTED]-> DocumentReference relationship."""
    await graph.build_from_fhir(
        patient_id,
        [sample_patient, sample_encounter, sample_document_reference_with_encounter],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (e:Encounter {fhir_id: $enc_id})-[:DOCUMENTED]->(d:DocumentReference)
            RETURN d.fhir_id as doc_id
            """,
            enc_id=sample_encounter["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["doc_id"] == sample_document_reference_with_encounter["id"]


@pytest.mark.asyncio
async def test_encounter_imaged_imaging_study(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_imaging_study_with_encounter,
):
    """Test Encounter -[:IMAGED]-> ImagingStudy relationship."""
    await graph.build_from_fhir(
        patient_id,
        [sample_patient, sample_encounter, sample_imaging_study_with_encounter],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (e:Encounter {fhir_id: $enc_id})-[:IMAGED]->(i:ImagingStudy)
            RETURN i.fhir_id as img_id
            """,
            enc_id=sample_encounter["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["img_id"] == sample_imaging_study_with_encounter["id"]


@pytest.mark.asyncio
async def test_encounter_assembled_care_team(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_care_team_with_encounter,
):
    """Test Encounter -[:ASSEMBLED]-> CareTeam relationship."""
    await graph.build_from_fhir(
        patient_id,
        [sample_patient, sample_encounter, sample_care_team_with_encounter],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (e:Encounter {fhir_id: $enc_id})-[:ASSEMBLED]->(ct:CareTeam)
            RETURN ct.fhir_id as ct_id
            """,
            enc_id=sample_encounter["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["ct_id"] == sample_care_team_with_encounter["id"]


@pytest.mark.asyncio
async def test_encounter_given_medication_administration(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_medication_administration_with_encounter,
):
    """Test Encounter -[:GIVEN]-> MedicationAdministration relationship."""
    await graph.build_from_fhir(
        patient_id,
        [sample_patient, sample_encounter, sample_medication_administration_with_encounter],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (e:Encounter {fhir_id: $enc_id})-[:GIVEN]->(ma:MedicationAdministration)
            RETURN ma.fhir_id as ma_id
            """,
            enc_id=sample_encounter["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["ma_id"] == sample_medication_administration_with_encounter["id"]


# =============================================================================
# Tests for new clinical reasoning edges
# =============================================================================


@pytest.mark.asyncio
async def test_medication_administration_treats_condition(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_condition_with_encounter,
    sample_medication_administration_with_reason,
):
    """Test MedicationAdministration -[:TREATS]-> Condition relationship."""
    await graph.build_from_fhir(
        patient_id,
        [
            sample_patient,
            sample_encounter,
            sample_condition_with_encounter,
            sample_medication_administration_with_reason,
        ],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (ma:MedicationAdministration {fhir_id: $ma_id})-[:TREATS]->(c:Condition)
            RETURN c.fhir_id as cond_id
            """,
            ma_id=sample_medication_administration_with_reason["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["cond_id"] == sample_condition_with_encounter["id"]


@pytest.mark.asyncio
async def test_claim_billed_for_encounter(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_condition_with_encounter,
    sample_claim,
):
    """Test Claim -[:BILLED_FOR]-> Encounter relationship."""
    await graph.build_from_fhir(
        patient_id,
        [sample_patient, sample_encounter, sample_condition_with_encounter, sample_claim],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (cl:Claim {fhir_id: $claim_id})-[:BILLED_FOR]->(e:Encounter)
            RETURN e.fhir_id as enc_id
            """,
            claim_id=sample_claim["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["enc_id"] == sample_encounter["id"]


@pytest.mark.asyncio
async def test_claim_claims_diagnosis_condition(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_encounter,
    sample_condition_with_encounter,
    sample_claim,
):
    """Test Claim -[:CLAIMS_DIAGNOSIS]-> Condition relationship."""
    await graph.build_from_fhir(
        patient_id,
        [sample_patient, sample_encounter, sample_condition_with_encounter, sample_claim],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (cl:Claim {fhir_id: $claim_id})-[:CLAIMS_DIAGNOSIS]->(c:Condition)
            RETURN c.fhir_id as cond_id
            """,
            claim_id=sample_claim["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["cond_id"] == sample_condition_with_encounter["id"]


@pytest.mark.asyncio
async def test_eob_explains_claim(
    graph: KnowledgeGraph,
    patient_id: str,
    neo4j_driver,
    sample_patient,
    sample_claim,
    sample_eob,
):
    """Test ExplanationOfBenefit -[:EXPLAINS]-> Claim relationship."""
    await graph.build_from_fhir(
        patient_id,
        [sample_patient, sample_claim, sample_eob],
    )

    async with neo4j_driver.session() as session:
        result = await session.run(
            """
            MATCH (eob:ExplanationOfBenefit {fhir_id: $eob_id})-[:EXPLAINS]->(cl:Claim)
            RETURN cl.fhir_id as claim_id
            """,
            eob_id=sample_eob["id"],
        )
        record = await result.single()

    assert record is not None
    assert record["claim_id"] == sample_claim["id"]


# =============================================================================
# Tests for search_nodes_by_name with new types
# =============================================================================


@pytest.mark.asyncio
async def test_search_nodes_finds_document_reference(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_document_reference,
):
    """Test search_nodes_by_name finds DocumentReference by type_display."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_document_reference])

    results = await graph.search_nodes_by_name(patient_id, ["summary"])
    fhir_ids = [r["fhir_id"] for r in results]
    assert sample_document_reference["id"] in fhir_ids


@pytest.mark.asyncio
async def test_search_nodes_finds_imaging_study(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_imaging_study,
):
    """Test search_nodes_by_name finds ImagingStudy by procedure_display."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_imaging_study])

    results = await graph.search_nodes_by_name(patient_id, ["mammography"])
    fhir_ids = [r["fhir_id"] for r in results]
    assert sample_imaging_study["id"] in fhir_ids


@pytest.mark.asyncio
async def test_search_nodes_finds_device(
    graph: KnowledgeGraph,
    patient_id: str,
    sample_patient,
    sample_device,
):
    """Test search_nodes_by_name finds Device by type_display."""
    await graph.build_from_fhir(patient_id, [sample_patient, sample_device])

    results = await graph.search_nodes_by_name(patient_id, ["pacemaker"])
    fhir_ids = [r["fhir_id"] for r in results]
    assert sample_device["id"] in fhir_ids
