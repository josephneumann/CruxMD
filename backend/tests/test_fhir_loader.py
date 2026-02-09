"""Tests for FHIR loader service."""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

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
    _enrich_observations,
    _extract_patient_sex,
    _generate_embeddings,
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


class TestObservationEnrichment:
    """Tests for Observation reference range and interpretation enrichment."""

    def _make_bundle_entries(self, patient_gender: str, observations: list[dict]):
        """Build bundle entries list with a Patient + Observations."""
        patient = {
            "resource": {
                "resourceType": "Patient",
                "id": "patient-1",
                "gender": patient_gender,
            }
        }
        entries = [patient]
        for obs in observations:
            entries.append({"resource": obs})
        return entries

    def test_extract_patient_sex(self):
        entries = [
            {"resource": {"resourceType": "Patient", "gender": "male"}},
        ]
        assert _extract_patient_sex(entries) == "male"

    def test_extract_patient_sex_missing(self):
        entries = [{"resource": {"resourceType": "Condition"}}]
        assert _extract_patient_sex(entries) is None

    def test_enriches_observation_with_known_loinc(self):
        obs = {
            "resourceType": "Observation",
            "code": {"coding": [{"code": "718-7", "display": "Hemoglobin"}]},
            "valueQuantity": {"value": 14.5, "unit": "g/dL"},
        }
        entries = self._make_bundle_entries("male", [obs])
        resources = [e["resource"] for e in entries]
        _enrich_observations(entries, resources)

        assert "interpretation" in obs
        assert obs["interpretation"][0]["coding"][0]["code"] == "N"
        assert "referenceRange" in obs
        assert obs["referenceRange"][0]["low"]["value"] == 13.5  # Male range
        assert obs["referenceRange"][0]["low"]["unit"] == "g/dL"

    def test_enriches_with_sex_specific_range(self):
        obs = {
            "resourceType": "Observation",
            "code": {"coding": [{"code": "718-7", "display": "Hemoglobin"}]},
            "valueQuantity": {"value": 11.5, "unit": "g/dL"},
        }
        entries = self._make_bundle_entries("female", [obs])
        resources = [e["resource"] for e in entries]
        _enrich_observations(entries, resources)

        # 11.5 is below female low (12.0) -> L
        assert obs["interpretation"][0]["coding"][0]["code"] == "L"
        assert obs["referenceRange"][0]["low"]["value"] == 12.0  # Female range

    def test_skips_unknown_loinc(self):
        obs = {
            "resourceType": "Observation",
            "code": {"coding": [{"code": "99999-9"}]},
            "valueQuantity": {"value": 5.0},
        }
        entries = self._make_bundle_entries("male", [obs])
        resources = [e["resource"] for e in entries]
        _enrich_observations(entries, resources)

        assert "interpretation" not in obs
        assert "referenceRange" not in obs

    def test_skips_qualitative_observation(self):
        obs = {
            "resourceType": "Observation",
            "code": {"coding": [{"code": "72166-2"}]},
            "valueCodeableConcept": {"coding": [{"display": "Never smoker"}]},
        }
        entries = self._make_bundle_entries("male", [obs])
        resources = [e["resource"] for e in entries]
        _enrich_observations(entries, resources)

        assert "interpretation" not in obs
        assert "referenceRange" not in obs

    def test_skips_non_observation_resources(self):
        condition = {
            "resourceType": "Condition",
            "code": {"coding": [{"code": "718-7"}]},
        }
        entries = self._make_bundle_entries("male", [])
        resources = [entries[0]["resource"], condition]
        _enrich_observations(entries, resources)

        assert "interpretation" not in condition

    def test_high_interpretation(self):
        obs = {
            "resourceType": "Observation",
            "code": {"coding": [{"code": "8480-6", "display": "Systolic BP"}]},
            "valueQuantity": {"value": 145, "unit": "mmHg"},
        }
        entries = self._make_bundle_entries("male", [obs])
        resources = [e["resource"] for e in entries]
        _enrich_observations(entries, resources)

        assert obs["interpretation"][0]["coding"][0]["code"] == "H"

    def test_fhir_conformant_interpretation_structure(self):
        obs = {
            "resourceType": "Observation",
            "code": {"coding": [{"code": "718-7"}]},
            "valueQuantity": {"value": 14.5, "unit": "g/dL"},
        }
        entries = self._make_bundle_entries("male", [obs])
        resources = [e["resource"] for e in entries]
        _enrich_observations(entries, resources)

        interp = obs["interpretation"]
        assert isinstance(interp, list)
        assert len(interp) == 1
        coding = interp[0]["coding"][0]
        assert "system" in coding
        assert "code" in coding
        assert "display" in coding

    def test_fhir_conformant_reference_range_structure(self):
        obs = {
            "resourceType": "Observation",
            "code": {"coding": [{"code": "718-7"}]},
            "valueQuantity": {"value": 14.5, "unit": "g/dL"},
        }
        entries = self._make_bundle_entries("male", [obs])
        resources = [e["resource"] for e in entries]
        _enrich_observations(entries, resources)

        ref = obs["referenceRange"]
        assert isinstance(ref, list)
        assert len(ref) == 1
        assert "low" in ref[0] and "high" in ref[0]
        assert "value" in ref[0]["low"]


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


class TestGenerateEmbeddings:
    """Unit tests for _generate_embeddings helper function."""

    def _create_mock_embedding(self, dimension: int = 1536) -> list[float]:
        """Create a mock embedding vector."""
        return [0.1] * dimension

    def _create_mock_fhir_resource(
        self,
        resource_type: str,
        fhir_id: str,
        data: dict,
    ) -> FhirResource:
        """Create a mock FhirResource for testing."""
        resource = FhirResource(
            id=uuid.uuid4(),
            fhir_id=fhir_id,
            resource_type=resource_type,
            patient_id=uuid.uuid4(),
            data=data,
        )
        return resource

    @pytest.mark.asyncio
    async def test_generate_embeddings_updates_resources(
        self, sample_condition, sample_observation
    ):
        """Test that _generate_embeddings updates FhirResource objects."""
        # Create mock FhirResource objects
        condition_resource = self._create_mock_fhir_resource(
            "Condition", "cond-1", sample_condition
        )
        observation_resource = self._create_mock_fhir_resource(
            "Observation", "obs-1", sample_observation
        )

        # Create mock embedding service
        mock_client = AsyncMock()
        mock_response = MagicMock()
        mock_response.data = [
            MagicMock(embedding=self._create_mock_embedding()),
            MagicMock(embedding=self._create_mock_embedding()),
        ]
        mock_client.embeddings.create = AsyncMock(return_value=mock_response)
        mock_client.close = AsyncMock()

        with patch(
            "app.services.fhir_loader.EmbeddingService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.embed_texts = AsyncMock(
                return_value=[
                    self._create_mock_embedding(),
                    self._create_mock_embedding(),
                ]
            )
            mock_service.close = AsyncMock()
            mock_service_class.return_value = mock_service

            await _generate_embeddings([condition_resource, observation_resource])

            # Verify embeddings were set
            assert condition_resource.embedding is not None
            assert condition_resource.embedding_text is not None
            assert observation_resource.embedding is not None
            assert observation_resource.embedding_text is not None

            # Verify embedding text contains expected content
            assert "Condition:" in condition_resource.embedding_text
            assert "Observation:" in observation_resource.embedding_text

    @pytest.mark.asyncio
    async def test_generate_embeddings_skips_non_embeddable(self):
        """Test that _generate_embeddings skips non-embeddable resource types."""
        # Provenance is not an embeddable type
        provenance_data = {
            "resourceType": "Provenance",
            "id": "prov-1",
            "target": [{"reference": "Patient/pat-1"}],
        }
        provenance_resource = self._create_mock_fhir_resource(
            "Provenance", "prov-1", provenance_data
        )

        with patch(
            "app.services.fhir_loader.EmbeddingService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.embed_texts = AsyncMock(return_value=[])
            mock_service.close = AsyncMock()
            mock_service_class.return_value = mock_service

            await _generate_embeddings([provenance_resource])

            # embed_texts should not be called since Provenance is not embeddable
            mock_service.embed_texts.assert_not_called()

            # Provenance should not have embedding
            assert provenance_resource.embedding is None
            assert provenance_resource.embedding_text is None

    @pytest.mark.asyncio
    async def test_generate_embeddings_handles_empty_list(self):
        """Test that _generate_embeddings handles empty resource list."""
        with patch(
            "app.services.fhir_loader.EmbeddingService"
        ) as mock_service_class:
            await _generate_embeddings([])

            # EmbeddingService should not be instantiated for empty list
            mock_service_class.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_embeddings_graceful_degradation(
        self, sample_condition
    ):
        """Test that _generate_embeddings handles API errors gracefully."""
        condition_resource = self._create_mock_fhir_resource(
            "Condition", "cond-1", sample_condition
        )

        with patch(
            "app.services.fhir_loader.EmbeddingService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.embed_texts = AsyncMock(
                side_effect=Exception("API Error")
            )
            mock_service.close = AsyncMock()
            mock_service_class.return_value = mock_service

            # Should not raise, just log warning
            await _generate_embeddings([condition_resource])

            # Embedding should not be set due to error
            assert condition_resource.embedding is None

    @pytest.mark.asyncio
    async def test_generate_embeddings_closes_service(self, sample_condition):
        """Test that _generate_embeddings closes the embedding service."""
        condition_resource = self._create_mock_fhir_resource(
            "Condition", "cond-1", sample_condition
        )

        with patch(
            "app.services.fhir_loader.EmbeddingService"
        ) as mock_service_class:
            mock_service = MagicMock()
            mock_service.embed_texts = AsyncMock(
                return_value=[self._create_mock_embedding()]
            )
            mock_service.close = AsyncMock()
            mock_service_class.return_value = mock_service

            await _generate_embeddings([condition_resource])

            # Verify close was called
            mock_service.close.assert_called_once()


# =============================================================================
# Tests for load_bundle compilation trigger
# =============================================================================


@pytest.mark.integration
class TestLoadBundleCompilationTrigger:
    """Tests that load_bundle triggers compile_and_store after loading.

    Requires PostgreSQL and Neo4j to be running.
    """

    @pytest.mark.asyncio
    async def test_load_bundle_populates_compiled_summary(
        self, db_session, graph, sample_patient
    ):
        """load_bundle should populate compiled_summary on the Patient row."""
        bundle = create_bundle([sample_patient])
        patient_id = await load_bundle(db_session, graph, bundle)

        result = await db_session.execute(
            select(FhirResource).where(
                FhirResource.patient_id == patient_id,
                FhirResource.resource_type == "Patient",
            )
        )
        patient = result.scalar_one()
        assert patient.compiled_summary is not None
        assert "patient_orientation" in patient.compiled_summary
        assert patient.compiled_at is not None

    @pytest.mark.asyncio
    async def test_reload_bundle_recompiles_summary(
        self, db_session, graph, sample_patient
    ):
        """Reloading a bundle should update compiled_summary."""
        bundle = create_bundle([sample_patient])

        # First load
        patient_id = await load_bundle(db_session, graph, bundle)
        await db_session.flush()

        result = await db_session.execute(
            select(FhirResource).where(
                FhirResource.patient_id == patient_id,
                FhirResource.resource_type == "Patient",
            )
        )
        patient = result.scalar_one()
        first_compiled_at = patient.compiled_at
        assert first_compiled_at is not None

        # Second load (recompile) — idempotent via upsert
        await load_bundle(db_session, graph, bundle)

        # Re-query to get updated row
        result2 = await db_session.execute(
            select(FhirResource).where(
                FhirResource.patient_id == patient_id,
                FhirResource.resource_type == "Patient",
            )
        )
        patient2 = result2.scalar_one()
        assert patient2.compiled_at is not None
        assert patient2.compiled_at >= first_compiled_at

    @pytest.mark.asyncio
    async def test_compilation_failure_does_not_block_load(
        self, db_session, graph, sample_patient
    ):
        """If compilation fails, load_bundle should still succeed."""
        bundle = create_bundle([sample_patient])

        with patch(
            "app.services.fhir_loader.compile_and_store",
            new_callable=AsyncMock,
            side_effect=Exception("Compilation blew up"),
        ):
            patient_id = await load_bundle(db_session, graph, bundle)

        # Bundle load should still succeed
        assert patient_id is not None
        result = await db_session.execute(
            select(FhirResource).where(
                FhirResource.patient_id == patient_id,
                FhirResource.resource_type == "Patient",
            )
        )
        patient = result.scalar_one()
        assert patient is not None
        # compiled_summary should be None since compilation failed
        assert patient.compiled_summary is None
