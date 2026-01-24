"""Tests for FHIR loader service."""

import uuid

import pytest
from sqlalchemy import select

from app.models import FhirResource
from app.services.fhir_loader import (
    get_patient_profile,
    get_patient_resource,
    get_patient_resources,
    load_bundle,
    load_bundle_with_profile,
    _add_profile_extension,
    PROFILE_EXTENSION_URL,
)
from tests.conftest import create_bundle


@pytest.mark.integration
class TestLoadBundle:
    """Tests for load_bundle function.

    Requires PostgreSQL and Neo4j to be running.
    """

    @pytest.mark.asyncio
    async def test_load_bundle_creates_patient(self, db_session, graph, sample_patient):
        """Test that load_bundle creates a Patient resource in PostgreSQL."""
        bundle = create_bundle([sample_patient])
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
    async def test_load_bundle_creates_related_resources(
        self,
        db_session,
        graph,
        sample_patient,
        sample_condition,
        sample_medication,
        sample_observation,
    ):
        """Test that load_bundle creates related resources with patient_id linkage."""
        bundle = create_bundle(
            [sample_patient, sample_condition, sample_medication, sample_observation]
        )
        patient_id = await load_bundle(db_session, graph, bundle)

        # Verify all resources exist
        result = await db_session.execute(
            select(FhirResource).where(FhirResource.patient_id == patient_id)
        )
        resources = result.scalars().all()
        assert len(resources) == 4

        resource_types = {r.resource_type for r in resources}
        assert resource_types == {
            "Patient",
            "Condition",
            "MedicationRequest",
            "Observation",
        }

    @pytest.mark.asyncio
    async def test_load_bundle_populates_neo4j_graph(
        self, db_session, graph, sample_patient, sample_condition
    ):
        """Test that load_bundle populates Neo4j graph."""
        bundle = create_bundle([sample_patient, sample_condition])
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
    async def test_load_bundle_no_patient_raises(
        self, db_session, graph, sample_condition
    ):
        """Test that load_bundle raises when no Patient resource."""
        bundle = create_bundle([sample_condition])
        with pytest.raises(ValueError, match="must contain a Patient"):
            await load_bundle(db_session, graph, bundle)

    @pytest.mark.asyncio
    async def test_load_bundle_is_idempotent(
        self, db_session, graph, sample_patient, sample_condition
    ):
        """Test that loading same bundle twice doesn't create duplicates."""
        bundle = create_bundle([sample_patient, sample_condition])

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
    async def test_load_bundle_stores_raw_fhir(self, db_session, graph, sample_patient):
        """Test that load_bundle stores raw FHIR JSON data."""
        bundle = create_bundle([sample_patient])
        patient_id = await load_bundle(db_session, graph, bundle)

        result = await db_session.execute(
            select(FhirResource).where(
                FhirResource.patient_id == patient_id,
                FhirResource.resource_type == "Patient",
            )
        )
        patient = result.scalar_one()

        # Data should be the exact FHIR resource
        assert patient.data == sample_patient


@pytest.mark.integration
class TestGetPatientResources:
    """Tests for get_patient_resources function.

    Requires PostgreSQL and Neo4j to be running.
    """

    @pytest.mark.asyncio
    async def test_get_patient_resources_returns_all(
        self, db_session, graph, sample_patient, sample_condition, sample_medication
    ):
        """Test that get_patient_resources returns all resources for a patient."""
        bundle = create_bundle([sample_patient, sample_condition, sample_medication])
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


@pytest.mark.integration
class TestLoadBundleIntegration:
    """Integration tests with real Synthea fixtures.

    Requires PostgreSQL and Neo4j to be running.
    """

    @pytest.mark.asyncio
    async def test_load_synthea_bundle(self, db_session, graph):
        """Test loading a real Synthea bundle fixture."""
        import json
        from pathlib import Path

        fixture_path = (
            Path(__file__).parent.parent.parent
            / "fixtures"
            / "synthea"
            / "patient_bundle_1.json"
        )
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

    def test_create_bundle_with_resources(self, sample_patient, sample_condition):
        """Test creating bundle with resources."""
        bundle = create_bundle([sample_patient, sample_condition])
        assert len(bundle["entry"]) == 2
        assert bundle["entry"][0]["resource"] == sample_patient
        assert bundle["entry"][1]["resource"] == sample_condition


class TestFhirLoaderHelpers:
    """Unit tests for fhir_loader helper functions."""

    def test_extract_patient_reference_returns_default(self, sample_condition):
        """Test _extract_patient_reference returns default patient ID."""
        from app.services.fhir_loader import _extract_patient_reference

        default_id = uuid.uuid4()
        result = _extract_patient_reference(sample_condition, default_id)
        assert result == default_id

    def test_sample_patient_has_required_fields(self, sample_patient):
        """Test sample patient has required FHIR fields."""
        assert sample_patient["resourceType"] == "Patient"
        assert "id" in sample_patient
        assert "name" in sample_patient

    def test_sample_condition_has_required_fields(self, sample_condition):
        """Test sample condition has required FHIR fields."""
        assert sample_condition["resourceType"] == "Condition"
        assert "id" in sample_condition
        assert "code" in sample_condition

    def test_sample_medication_has_required_fields(self, sample_medication):
        """Test sample medication has required FHIR fields."""
        assert sample_medication["resourceType"] == "MedicationRequest"
        assert "id" in sample_medication
        assert "medicationCodeableConcept" in sample_medication

    def test_sample_observation_has_required_fields(self, sample_observation):
        """Test sample observation has required FHIR fields."""
        assert sample_observation["resourceType"] == "Observation"
        assert "id" in sample_observation
        assert "code" in sample_observation
        assert "valueQuantity" in sample_observation


class TestPatientProfile:
    """Tests for patient profile functions."""

    @pytest.fixture
    def sample_profile(self) -> dict:
        """Sample patient profile for testing."""
        return {
            "chief_complaints": ["headache", "fatigue"],
            "medical_history_summary": "Patient has history of hypertension",
            "current_medications_summary": "Taking Lisinopril 10mg daily",
            "allergies_summary": "Penicillin allergy",
            "social_history": "Non-smoker, occasional alcohol",
        }

    def test_add_profile_extension_creates_extension(
        self, sample_patient, sample_profile
    ):
        """Test that _add_profile_extension adds FHIR extension to Patient."""
        bundle = create_bundle([sample_patient])
        result = _add_profile_extension(bundle, sample_profile)

        # Find patient in result bundle
        patient = None
        for entry in result["entry"]:
            if entry["resource"]["resourceType"] == "Patient":
                patient = entry["resource"]
                break

        assert patient is not None
        assert "extension" in patient
        assert len(patient["extension"]) == 1
        assert patient["extension"][0]["url"] == PROFILE_EXTENSION_URL

    def test_add_profile_extension_does_not_modify_original(
        self, sample_patient, sample_profile
    ):
        """Test that _add_profile_extension creates a copy and doesn't modify original."""
        bundle = create_bundle([sample_patient])
        original_patient = bundle["entry"][0]["resource"].copy()

        _add_profile_extension(bundle, sample_profile)

        # Original should not have extension
        assert "extension" not in bundle["entry"][0]["resource"] or bundle["entry"][0][
            "resource"
        ].get("extension") == original_patient.get("extension", [])

    def test_add_profile_extension_replaces_existing(
        self, sample_patient, sample_profile
    ):
        """Test that _add_profile_extension replaces existing profile extension."""
        # Add initial extension
        sample_patient["extension"] = [
            {"url": PROFILE_EXTENSION_URL, "valueString": '{"old": "profile"}'}
        ]
        bundle = create_bundle([sample_patient])

        new_profile = {"new": "profile"}
        result = _add_profile_extension(bundle, new_profile)

        patient = result["entry"][0]["resource"]
        profile_exts = [
            e for e in patient["extension"] if e["url"] == PROFILE_EXTENSION_URL
        ]
        assert len(profile_exts) == 1  # Only one profile extension

    def test_add_profile_extension_preserves_other_extensions(
        self, sample_patient, sample_profile
    ):
        """Test that _add_profile_extension preserves non-profile extensions."""
        other_ext = {"url": "http://other.extension", "valueString": "other"}
        sample_patient["extension"] = [other_ext]
        bundle = create_bundle([sample_patient])

        result = _add_profile_extension(bundle, sample_profile)

        patient = result["entry"][0]["resource"]
        assert len(patient["extension"]) == 2
        urls = {e["url"] for e in patient["extension"]}
        assert "http://other.extension" in urls
        assert PROFILE_EXTENSION_URL in urls

    def test_get_patient_profile_extracts_profile(self, sample_patient, sample_profile):
        """Test that get_patient_profile extracts profile from Patient resource."""
        import json

        sample_patient["extension"] = [
            {"url": PROFILE_EXTENSION_URL, "valueString": json.dumps(sample_profile)}
        ]

        result = get_patient_profile(sample_patient)

        assert result is not None
        assert result == sample_profile

    def test_get_patient_profile_returns_none_when_missing(self, sample_patient):
        """Test that get_patient_profile returns None when no profile extension."""
        result = get_patient_profile(sample_patient)
        assert result is None

    def test_get_patient_profile_returns_none_for_empty_extensions(
        self, sample_patient
    ):
        """Test that get_patient_profile handles empty extensions array."""
        sample_patient["extension"] = []
        result = get_patient_profile(sample_patient)
        assert result is None

    def test_get_patient_profile_ignores_other_extensions(self, sample_patient):
        """Test that get_patient_profile ignores non-profile extensions."""
        sample_patient["extension"] = [
            {"url": "http://other.extension", "valueString": "other"}
        ]
        result = get_patient_profile(sample_patient)
        assert result is None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_load_bundle_with_profile(
        self, db_session, graph, sample_patient, sample_profile
    ):
        """Test that load_bundle_with_profile embeds profile in Patient."""
        bundle = create_bundle([sample_patient])
        patient_id = await load_bundle_with_profile(
            db_session, graph, bundle, sample_profile
        )

        assert patient_id is not None

        # Retrieve the patient and verify profile is embedded
        result = await db_session.execute(
            select(FhirResource).where(
                FhirResource.patient_id == patient_id,
                FhirResource.resource_type == "Patient",
            )
        )
        patient_resource = result.scalar_one()

        # Extract profile from stored data
        profile = get_patient_profile(patient_resource.data)
        assert profile is not None
        assert profile == sample_profile

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_load_bundle_with_profile_none_profile(
        self, db_session, graph, sample_patient
    ):
        """Test that load_bundle_with_profile works without profile."""
        bundle = create_bundle([sample_patient])
        patient_id = await load_bundle_with_profile(
            db_session, graph, bundle, profile=None
        )

        assert patient_id is not None

        # Patient should exist without profile extension
        result = await db_session.execute(
            select(FhirResource).where(
                FhirResource.patient_id == patient_id,
                FhirResource.resource_type == "Patient",
            )
        )
        patient_resource = result.scalar_one()
        profile = get_patient_profile(patient_resource.data)
        assert profile is None


@pytest.mark.integration
class TestGetPatientResource:
    """Tests for get_patient_resource function.

    Requires PostgreSQL and Neo4j to be running.
    """

    @pytest.mark.asyncio
    async def test_get_patient_resource_returns_patient(
        self, db_session, graph, sample_patient
    ):
        """Test that get_patient_resource returns Patient FhirResource."""
        bundle = create_bundle([sample_patient])
        patient_id = await load_bundle(db_session, graph, bundle)

        # Need to get the actual resource ID (which equals patient_id for Patient)
        result = await db_session.execute(
            select(FhirResource).where(
                FhirResource.patient_id == patient_id,
                FhirResource.resource_type == "Patient",
            )
        )
        patient_db = result.scalar_one()

        # Now use get_patient_resource with the patient's own ID
        resource = await get_patient_resource(db_session, patient_db.id)

        assert resource is not None
        assert resource.resource_type == "Patient"
        assert resource.fhir_id == sample_patient["id"]

    @pytest.mark.asyncio
    async def test_get_patient_resource_returns_none_for_nonexistent(self, db_session):
        """Test that get_patient_resource returns None for nonexistent patient."""
        fake_id = uuid.uuid4()
        resource = await get_patient_resource(db_session, fake_id)
        assert resource is None

    @pytest.mark.asyncio
    async def test_get_patient_resource_returns_none_for_non_patient(
        self, db_session, graph, sample_patient, sample_condition
    ):
        """Test that get_patient_resource returns None when ID is not a Patient resource."""
        bundle = create_bundle([sample_patient, sample_condition])
        patient_id = await load_bundle(db_session, graph, bundle)

        # Get the Condition resource
        result = await db_session.execute(
            select(FhirResource).where(
                FhirResource.patient_id == patient_id,
                FhirResource.resource_type == "Condition",
            )
        )
        condition_resource = result.scalar_one()

        # Trying to get a Patient with a Condition ID should return None
        resource = await get_patient_resource(db_session, condition_resource.id)
        assert resource is None
