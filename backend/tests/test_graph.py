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

    assert len(events["conditions"]) == 1
    assert events["conditions"][0]["fhir_id"] == sample_condition_with_encounter["id"]

    assert len(events["medications"]) == 1
    assert events["medications"][0]["fhir_id"] == sample_medication_with_encounter_and_reason["id"]

    assert len(events["observations"]) == 1
    assert events["observations"][0]["fhir_id"] == sample_observation_with_encounter["id"]

    assert len(events["procedures"]) == 1
    assert events["procedures"][0]["fhir_id"] == sample_procedure_with_encounter_and_reason["id"]

    assert len(events["diagnostic_reports"]) == 1
    assert events["diagnostic_reports"][0]["fhir_id"] == sample_diagnostic_report_with_encounter_and_results["id"]


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
    assert meds[0]["fhir_id"] == sample_medication_with_encounter_and_reason["id"]


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
    assert procs[0]["fhir_id"] == sample_procedure_with_encounter_and_reason["id"]


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
    assert obs[0]["fhir_id"] == sample_observation_with_encounter["id"]


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
