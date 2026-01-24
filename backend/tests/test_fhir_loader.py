"""Tests for FHIR loader service."""

import uuid

import pytest
from sqlalchemy import select

from app.models import FhirResource
from app.services.fhir_loader import get_patient_resources, load_bundle
from tests.conftest import create_bundle


class TestLoadBundle:
    """Tests for load_bundle function."""

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
        self, db_session, graph, sample_patient, sample_condition, sample_medication, sample_observation
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
        assert resource_types == {"Patient", "Condition", "MedicationRequest", "Observation"}

    @pytest.mark.asyncio
    async def test_load_bundle_populates_neo4j_graph(self, db_session, graph, sample_patient, sample_condition):
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
    async def test_load_bundle_no_patient_raises(self, db_session, graph, sample_condition):
        """Test that load_bundle raises when no Patient resource."""
        bundle = create_bundle([sample_condition])
        with pytest.raises(ValueError, match="must contain a Patient"):
            await load_bundle(db_session, graph, bundle)

    @pytest.mark.asyncio
    async def test_load_bundle_is_idempotent(self, db_session, graph, sample_patient, sample_condition):
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


class TestGetPatientResources:
    """Tests for get_patient_resources function."""

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
