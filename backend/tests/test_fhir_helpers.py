"""Tests for shared FHIR helper utilities."""


from app.utils.fhir_helpers import (
    extract_clinical_status,
    extract_display_name,
    extract_encounter_fhir_id,
    extract_first_coding,
    extract_observation_value,
    extract_reference_id,
    extract_reference_ids,
)


class TestExtractReferenceId:
    """Tests for extract_reference_id function."""

    def test_extracts_from_urn_uuid(self):
        """Test extraction from urn:uuid format."""
        result = extract_reference_id("urn:uuid:abc-123-def")
        assert result == "abc-123-def"

    def test_extracts_from_resource_reference(self):
        """Test extraction from ResourceType/id format."""
        result = extract_reference_id("Patient/patient-123")
        assert result == "patient-123"

    def test_extracts_from_encounter_reference(self):
        """Test extraction from Encounter reference."""
        result = extract_reference_id("Encounter/enc-456")
        assert result == "enc-456"

    def test_returns_none_for_none(self):
        """Test returns None for None input."""
        result = extract_reference_id(None)
        assert result is None

    def test_returns_none_for_empty_string(self):
        """Test returns None for empty string."""
        result = extract_reference_id("")
        assert result is None

    def test_returns_plain_id_unchanged(self):
        """Test returns plain ID without prefix unchanged."""
        result = extract_reference_id("plain-id-no-prefix")
        assert result == "plain-id-no-prefix"


class TestExtractReferenceIds:
    """Tests for extract_reference_ids function."""

    def test_extracts_multiple_references(self):
        """Test extraction from list of reference objects."""
        refs = [
            {"reference": "Patient/p1"},
            {"reference": "Patient/p2"},
            {"reference": "urn:uuid:abc"},
        ]
        result = extract_reference_ids(refs)
        assert result == ["p1", "p2", "abc"]

    def test_filters_empty_references(self):
        """Test filters out empty reference values."""
        refs = [
            {"reference": "Patient/p1"},
            {"reference": ""},
            {"other": "value"},
        ]
        result = extract_reference_ids(refs)
        assert result == ["p1"]

    def test_returns_empty_for_empty_list(self):
        """Test returns empty list for empty input."""
        result = extract_reference_ids([])
        assert result == []


class TestExtractFirstCoding:
    """Tests for extract_first_coding function."""

    def test_extracts_first_coding(self):
        """Test extraction of first coding from CodeableConcept."""
        codeable = {
            "coding": [
                {"system": "http://snomed.info/sct", "code": "123", "display": "Test"},
                {"system": "http://loinc.org", "code": "456", "display": "Other"},
            ]
        }
        result = extract_first_coding(codeable)
        assert result["code"] == "123"
        assert result["display"] == "Test"

    def test_returns_empty_dict_for_empty_coding(self):
        """Test returns empty dict when no codings present."""
        codeable = {"coding": []}
        result = extract_first_coding(codeable)
        assert result == {}

    def test_returns_empty_dict_for_missing_coding(self):
        """Test returns empty dict when coding key missing."""
        codeable = {"text": "Some text"}
        result = extract_first_coding(codeable)
        assert result == {}


class TestExtractDisplayName:
    """Tests for extract_display_name function."""

    def test_extracts_from_condition(self):
        """Test extraction from Condition resource."""
        resource = {
            "resourceType": "Condition",
            "code": {
                "coding": [{"display": "Type 2 diabetes mellitus"}],
            },
        }
        result = extract_display_name(resource)
        assert result == "Type 2 diabetes mellitus"

    def test_extracts_from_medication_request(self):
        """Test extraction from MedicationRequest resource."""
        resource = {
            "resourceType": "MedicationRequest",
            "medicationCodeableConcept": {
                "coding": [{"display": "Metformin 500 MG"}],
            },
        }
        result = extract_display_name(resource)
        assert result == "Metformin 500 MG"

    def test_falls_back_to_text(self):
        """Test fallback to code.text when no coding."""
        resource = {
            "code": {"text": "Some condition text"},
        }
        result = extract_display_name(resource)
        assert result == "Some condition text"

    def test_returns_none_for_no_code(self):
        """Test returns None when no code field present."""
        resource = {"resourceType": "Patient"}
        result = extract_display_name(resource)
        assert result is None

    def test_returns_none_for_empty_code(self):
        """Test returns None for empty code field."""
        resource = {"code": {}}
        result = extract_display_name(resource)
        assert result is None


class TestExtractClinicalStatus:
    """Tests for extract_clinical_status function."""

    def test_extracts_active_status(self):
        """Test extraction of active clinical status."""
        resource = {
            "clinicalStatus": {
                "coding": [{"code": "active"}],
            },
        }
        result = extract_clinical_status(resource)
        assert result == "active"

    def test_extracts_resolved_status(self):
        """Test extraction of resolved clinical status."""
        resource = {
            "clinicalStatus": {
                "coding": [{"code": "resolved"}],
            },
        }
        result = extract_clinical_status(resource)
        assert result == "resolved"

    def test_returns_empty_for_missing_status(self):
        """Test returns empty string when clinicalStatus missing."""
        resource = {"resourceType": "Condition"}
        result = extract_clinical_status(resource)
        assert result == ""

    def test_returns_empty_for_empty_coding(self):
        """Test returns empty string for empty coding array."""
        resource = {"clinicalStatus": {"coding": []}}
        result = extract_clinical_status(resource)
        assert result == ""


class TestExtractEncounterFhirId:
    """Tests for extract_encounter_fhir_id function."""

    def test_extracts_encounter_id(self):
        """Test extraction of encounter ID from reference."""
        resource = {
            "encounter": {"reference": "Encounter/enc-123"},
        }
        result = extract_encounter_fhir_id(resource)
        assert result == "enc-123"

    def test_extracts_from_urn_uuid(self):
        """Test extraction from urn:uuid format."""
        resource = {
            "encounter": {"reference": "urn:uuid:abc-456"},
        }
        result = extract_encounter_fhir_id(resource)
        assert result == "abc-456"

    def test_returns_none_for_missing_encounter(self):
        """Test returns None when encounter field missing."""
        resource = {"resourceType": "Observation"}
        result = extract_encounter_fhir_id(resource)
        assert result is None

    def test_returns_none_for_empty_encounter(self):
        """Test returns None for empty encounter object."""
        resource = {"encounter": {}}
        result = extract_encounter_fhir_id(resource)
        assert result is None


class TestExtractObservationValue:
    """Tests for extract_observation_value function."""

    def test_extracts_quantity_value(self):
        """Test extraction from valueQuantity."""
        resource = {
            "valueQuantity": {"value": 120.5, "unit": "mg/dL"},
        }
        value, unit = extract_observation_value(resource)
        assert value == 120.5
        assert unit == "mg/dL"

    def test_extracts_codeable_concept_value(self):
        """Test extraction from valueCodeableConcept."""
        resource = {
            "valueCodeableConcept": {
                "coding": [{"display": "Positive"}],
            },
        }
        value, unit = extract_observation_value(resource)
        assert value == "Positive"
        assert unit is None

    def test_extracts_string_value(self):
        """Test extraction from valueString."""
        resource = {
            "valueString": "Normal findings",
        }
        value, unit = extract_observation_value(resource)
        assert value == "Normal findings"
        assert unit is None

    def test_returns_none_for_no_value(self):
        """Test returns (None, None) when no value present."""
        resource = {"resourceType": "Observation", "status": "final"}
        value, unit = extract_observation_value(resource)
        assert value is None
        assert unit is None

    def test_quantity_without_unit(self):
        """Test handles quantity without unit."""
        resource = {
            "valueQuantity": {"value": 42},
        }
        value, unit = extract_observation_value(resource)
        assert value == 42
        assert unit is None
