"""Tests for patient data API routes (labs, medications, conditions, timeline)."""

import uuid
from datetime import date
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.database import get_db
from app.models import FhirResource
from app.routes.data import (
    TIMELINE_RESOURCE_TYPES,
    _extract_date_from_resource,
    _get_clinical_status,
    _get_loinc_codes_from_resource,
    router,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def data_app(mock_db):
    """Create a test app with data router."""
    app = FastAPI()

    async def override_get_db():
        yield mock_db

    app.include_router(router)
    app.dependency_overrides[get_db] = override_get_db

    return app, mock_db


@pytest.fixture
async def data_client(data_app):
    """Async test client for data app."""
    app, mock_db = data_app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac, mock_db


def _make_fhir_resource(
    resource_type: str,
    fhir_id: str,
    data: dict,
    patient_uuid: uuid.UUID | None = None,
) -> MagicMock:
    """Helper to create a mock FhirResource."""
    resource = MagicMock(spec=FhirResource)
    resource.id = uuid.uuid4()
    resource.fhir_id = fhir_id
    resource.resource_type = resource_type
    resource.data = data
    resource.patient_id = patient_uuid
    return resource


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def sample_observation_with_loinc() -> dict:
    """Sample Observation with LOINC code."""
    return {
        "resourceType": "Observation",
        "id": "obs-loinc-001",
        "subject": {"reference": "Patient/patient-test-123"},
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "2339-0",
                    "display": "Glucose [Mass/volume] in Blood",
                }
            ]
        },
        "status": "final",
        "effectiveDateTime": "2024-06-15T10:30:00Z",
        "valueQuantity": {"value": 95, "unit": "mg/dL"},
    }


@pytest.fixture
def sample_observation_older() -> dict:
    """Sample older Observation for date filtering tests."""
    return {
        "resourceType": "Observation",
        "id": "obs-older-001",
        "subject": {"reference": "Patient/patient-test-123"},
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "8480-6",
                    "display": "Blood pressure",
                }
            ]
        },
        "status": "final",
        "effectiveDateTime": "2023-01-15T10:30:00Z",
        "valueQuantity": {"value": 105, "unit": "mg/dL"},
    }


@pytest.fixture
def sample_patient_data() -> dict:
    """Sample FHIR Patient resource."""
    return {
        "resourceType": "Patient",
        "id": "patient-test-123",
        "name": [{"given": ["Jane"], "family": "Smith"}],
        "birthDate": "1985-03-20",
        "gender": "female",
    }


@pytest.fixture
def sample_condition_data() -> dict:
    """Sample FHIR Condition resource."""
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
        "onsetDateTime": "2024-01-15",
    }


@pytest.fixture
def sample_condition_inactive() -> dict:
    """Sample inactive FHIR Condition."""
    return {
        "resourceType": "Condition",
        "id": "condition-inactive",
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
    }


@pytest.fixture
def sample_medication_data() -> dict:
    """Sample FHIR MedicationRequest resource."""
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
        "authoredOn": "2024-01-10",
    }


@pytest.fixture
def sample_medication_stopped() -> dict:
    """Sample stopped FHIR MedicationRequest."""
    return {
        "resourceType": "MedicationRequest",
        "id": "medication-stopped",
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
        "status": "stopped",
    }


@pytest.fixture
def sample_encounter_data() -> dict:
    """Sample FHIR Encounter resource."""
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


# =============================================================================
# Unit Tests for Helper Functions
# =============================================================================


class TestExtractDateFromResource:
    """Tests for _extract_date_from_resource helper."""

    def test_extract_date_from_observation(self, sample_observation_with_loinc):
        """Should extract effectiveDateTime from Observation."""
        result = _extract_date_from_resource(sample_observation_with_loinc)
        assert result == date(2024, 6, 15)

    def test_extract_date_from_encounter(self, sample_encounter_data):
        """Should extract period.start from Encounter."""
        result = _extract_date_from_resource(sample_encounter_data)
        assert result == date(2024, 1, 15)

    def test_extract_date_from_condition(self, sample_condition_data):
        """Should extract onsetDateTime from Condition."""
        result = _extract_date_from_resource(sample_condition_data)
        assert result == date(2024, 1, 15)

    def test_extract_date_from_medication(self, sample_medication_data):
        """Should extract authoredOn from MedicationRequest."""
        result = _extract_date_from_resource(sample_medication_data)
        assert result == date(2024, 1, 10)

    def test_extract_date_returns_none_for_missing(self):
        """Should return None when no date fields present."""
        resource = {"resourceType": "Observation", "status": "final"}
        result = _extract_date_from_resource(resource)
        assert result is None


class TestGetLoincCodesFromResource:
    """Tests for _get_loinc_codes_from_resource helper."""

    def test_extract_single_loinc_code(self, sample_observation_with_loinc):
        """Should extract LOINC code from Observation."""
        result = _get_loinc_codes_from_resource(sample_observation_with_loinc)
        assert result == ["2339-0"]

    def test_returns_empty_for_non_loinc(self, sample_condition_data):
        """Should return empty list for non-LOINC coded resources."""
        result = _get_loinc_codes_from_resource(sample_condition_data)
        assert result == []

    def test_returns_empty_for_missing_code(self):
        """Should return empty list when code is missing."""
        resource = {"resourceType": "Observation"}
        result = _get_loinc_codes_from_resource(resource)
        assert result == []

    def test_extract_multiple_loinc_codes(self):
        """Should extract multiple LOINC codes if present."""
        resource = {
            "resourceType": "Observation",
            "code": {
                "coding": [
                    {"system": "http://loinc.org", "code": "2339-0"},
                    {"system": "http://loinc.org", "code": "8480-6"},
                ]
            },
        }
        result = _get_loinc_codes_from_resource(resource)
        assert result == ["2339-0", "8480-6"]


class TestGetClinicalStatus:
    """Tests for _get_clinical_status helper."""

    def test_extract_condition_status(self, sample_condition_data):
        """Should extract clinical status from Condition."""
        result = _get_clinical_status(sample_condition_data)
        assert result == "active"

    def test_extract_medication_status(self, sample_medication_data):
        """Should extract status from MedicationRequest."""
        result = _get_clinical_status(sample_medication_data)
        assert result == "active"

    def test_returns_none_for_unsupported_type(self, sample_observation_with_loinc):
        """Should return None for unsupported resource types."""
        result = _get_clinical_status(sample_observation_with_loinc)
        assert result is None

    def test_extract_allergy_status(self):
        """Should extract clinical status from AllergyIntolerance."""
        allergy = {
            "resourceType": "AllergyIntolerance",
            "clinicalStatus": {"coding": [{"code": "active"}]},
        }
        result = _get_clinical_status(allergy)
        assert result == "active"


# =============================================================================
# Labs Endpoint Tests
# =============================================================================


class TestGetPatientLabs:
    """Tests for GET /patients/{id}/labs endpoint."""

    @pytest.mark.asyncio
    async def test_labs_requires_auth(self, data_client):
        """Labs endpoint should require API key."""
        client, _ = data_client
        patient_id = uuid.uuid4()
        response = await client.get(f"/patients/{patient_id}/labs")
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing API key"

    @pytest.mark.asyncio
    async def test_labs_rejects_invalid_key(self, data_client):
        """Labs endpoint should reject invalid API key."""
        client, _ = data_client
        patient_id = uuid.uuid4()
        response = await client.get(
            f"/patients/{patient_id}/labs",
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"

    @pytest.mark.asyncio
    async def test_labs_returns_404_for_missing_patient(self, data_client):
        """Labs endpoint should return 404 for non-existent patient."""
        client, mock_db = data_client
        patient_id = uuid.uuid4()

        # Mock patient not found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        response = await client.get(
            f"/patients/{patient_id}/labs",
            headers={"X-API-Key": settings.api_key},
        )
        assert response.status_code == 404
        assert "Patient not found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_labs_returns_observations(
        self, data_client, sample_patient_data, sample_observation_with_loinc
    ):
        """Labs endpoint should return Observation resources."""
        client, mock_db = data_client
        patient_id = uuid.uuid4()

        # Mock patient found, then observations
        patient_resource = _make_fhir_resource("Patient", "p1", sample_patient_data)
        obs_resource = _make_fhir_resource(
            "Observation", "obs1", sample_observation_with_loinc, patient_id
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:  # Patient query
                mock_result.scalar_one_or_none.return_value = patient_resource
            else:  # Observations query
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = [obs_resource]
                mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute.side_effect = side_effect

        response = await client.get(
            f"/patients/{patient_id}/labs",
            headers={"X-API-Key": settings.api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert len(data["items"]) == 1
        assert data["items"][0]["data"]["resourceType"] == "Observation"


# =============================================================================
# Medications Endpoint Tests
# =============================================================================


class TestGetPatientMedications:
    """Tests for GET /patients/{id}/medications endpoint."""

    @pytest.mark.asyncio
    async def test_medications_requires_auth(self, data_client):
        """Medications endpoint should require API key."""
        client, _ = data_client
        patient_id = uuid.uuid4()
        response = await client.get(f"/patients/{patient_id}/medications")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_medications_returns_medication_requests(
        self, data_client, sample_patient_data, sample_medication_data
    ):
        """Medications endpoint should return MedicationRequest resources."""
        client, mock_db = data_client
        patient_id = uuid.uuid4()

        patient_resource = _make_fhir_resource("Patient", "p1", sample_patient_data)
        med_resource = _make_fhir_resource(
            "MedicationRequest", "med1", sample_medication_data, patient_id
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = patient_resource
            else:
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = [med_resource]
                mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute.side_effect = side_effect

        response = await client.get(
            f"/patients/{patient_id}/medications",
            headers={"X-API-Key": settings.api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["data"]["resourceType"] == "MedicationRequest"

    @pytest.mark.asyncio
    async def test_medications_filters_active_only(
        self, data_client, sample_patient_data, sample_medication_data, sample_medication_stopped
    ):
        """Medications endpoint should filter to active only when status=active."""
        client, mock_db = data_client
        patient_id = uuid.uuid4()

        patient_resource = _make_fhir_resource("Patient", "p1", sample_patient_data)
        active_med = _make_fhir_resource(
            "MedicationRequest", "med1", sample_medication_data, patient_id
        )
        stopped_med = _make_fhir_resource(
            "MedicationRequest", "med2", sample_medication_stopped, patient_id
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = patient_resource
            else:
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = [active_med, stopped_med]
                mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute.side_effect = side_effect

        response = await client.get(
            f"/patients/{patient_id}/medications",
            params={"status": "active"},
            headers={"X-API-Key": settings.api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["data"]["status"] == "active"


# =============================================================================
# Conditions Endpoint Tests
# =============================================================================


class TestGetPatientConditions:
    """Tests for GET /patients/{id}/conditions endpoint."""

    @pytest.mark.asyncio
    async def test_conditions_requires_auth(self, data_client):
        """Conditions endpoint should require API key."""
        client, _ = data_client
        patient_id = uuid.uuid4()
        response = await client.get(f"/patients/{patient_id}/conditions")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_conditions_returns_conditions(
        self, data_client, sample_patient_data, sample_condition_data
    ):
        """Conditions endpoint should return Condition resources."""
        client, mock_db = data_client
        patient_id = uuid.uuid4()

        patient_resource = _make_fhir_resource("Patient", "p1", sample_patient_data)
        cond_resource = _make_fhir_resource(
            "Condition", "cond1", sample_condition_data, patient_id
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = patient_resource
            else:
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = [cond_resource]
                mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute.side_effect = side_effect

        response = await client.get(
            f"/patients/{patient_id}/conditions",
            headers={"X-API-Key": settings.api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1
        assert data["items"][0]["data"]["resourceType"] == "Condition"

    @pytest.mark.asyncio
    async def test_conditions_filters_active_only(
        self, data_client, sample_patient_data, sample_condition_data, sample_condition_inactive
    ):
        """Conditions endpoint should filter to active only when status=active."""
        client, mock_db = data_client
        patient_id = uuid.uuid4()

        patient_resource = _make_fhir_resource("Patient", "p1", sample_patient_data)
        active_cond = _make_fhir_resource(
            "Condition", "cond1", sample_condition_data, patient_id
        )
        inactive_cond = _make_fhir_resource(
            "Condition", "cond2", sample_condition_inactive, patient_id
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = patient_resource
            else:
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = [active_cond, inactive_cond]
                mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute.side_effect = side_effect

        response = await client.get(
            f"/patients/{patient_id}/conditions",
            params={"status": "active"},
            headers={"X-API-Key": settings.api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 1


# =============================================================================
# Timeline Endpoint Tests
# =============================================================================


class TestGetPatientTimeline:
    """Tests for GET /patients/{id}/timeline endpoint."""

    @pytest.mark.asyncio
    async def test_timeline_requires_auth(self, data_client):
        """Timeline endpoint should require API key."""
        client, _ = data_client
        patient_id = uuid.uuid4()
        response = await client.get(f"/patients/{patient_id}/timeline")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_timeline_aggregates_multiple_types(
        self,
        data_client,
        sample_patient_data,
        sample_observation_with_loinc,
        sample_condition_data,
        sample_encounter_data,
        sample_medication_data,
    ):
        """Timeline should aggregate multiple resource types."""
        client, mock_db = data_client
        patient_id = uuid.uuid4()

        patient_resource = _make_fhir_resource("Patient", "p1", sample_patient_data)
        obs = _make_fhir_resource(
            "Observation", "obs1", sample_observation_with_loinc, patient_id
        )
        cond = _make_fhir_resource(
            "Condition", "cond1", sample_condition_data, patient_id
        )
        enc = _make_fhir_resource(
            "Encounter", "enc1", sample_encounter_data, patient_id
        )
        med = _make_fhir_resource(
            "MedicationRequest", "med1", sample_medication_data, patient_id
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = patient_resource
            else:
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = [obs, cond, enc, med]
                mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute.side_effect = side_effect

        response = await client.get(
            f"/patients/{patient_id}/timeline",
            headers={"X-API-Key": settings.api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 4

        types_found = {item["resource_type"] for item in data["items"]}
        assert "Observation" in types_found
        assert "Condition" in types_found
        assert "Encounter" in types_found
        assert "MedicationRequest" in types_found

    @pytest.mark.asyncio
    async def test_timeline_rejects_invalid_types(
        self, data_client, sample_patient_data
    ):
        """Timeline should reject invalid resource types."""
        client, mock_db = data_client
        patient_id = uuid.uuid4()

        patient_resource = _make_fhir_resource("Patient", "p1", sample_patient_data)

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = patient_resource
            return mock_result

        mock_db.execute.side_effect = side_effect

        response = await client.get(
            f"/patients/{patient_id}/timeline",
            params={"types": "InvalidType"},
            headers={"X-API-Key": settings.api_key},
        )
        assert response.status_code == 400
        assert "Invalid resource types" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_timeline_includes_date_in_response(
        self, data_client, sample_patient_data, sample_encounter_data
    ):
        """Timeline should include extracted date in response items."""
        client, mock_db = data_client
        patient_id = uuid.uuid4()

        patient_resource = _make_fhir_resource("Patient", "p1", sample_patient_data)
        enc = _make_fhir_resource(
            "Encounter", "enc1", sample_encounter_data, patient_id
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = patient_resource
            else:
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = [enc]
                mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute.side_effect = side_effect

        response = await client.get(
            f"/patients/{patient_id}/timeline",
            headers={"X-API-Key": settings.api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["items"][0]["date"] == "2024-01-15"

    @pytest.mark.asyncio
    async def test_timeline_pagination(
        self, data_client, sample_patient_data, sample_encounter_data, sample_condition_data
    ):
        """Timeline should support pagination."""
        client, mock_db = data_client
        patient_id = uuid.uuid4()

        patient_resource = _make_fhir_resource("Patient", "p1", sample_patient_data)
        enc = _make_fhir_resource(
            "Encounter", "enc1", sample_encounter_data, patient_id
        )
        cond = _make_fhir_resource(
            "Condition", "cond1", sample_condition_data, patient_id
        )

        call_count = 0

        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            mock_result = MagicMock()
            if call_count == 1:
                mock_result.scalar_one_or_none.return_value = patient_resource
            else:
                mock_scalars = MagicMock()
                mock_scalars.all.return_value = [enc, cond]
                mock_result.scalars.return_value = mock_scalars
            return mock_result

        mock_db.execute.side_effect = side_effect

        response = await client.get(
            f"/patients/{patient_id}/timeline",
            params={"limit": 1, "offset": 0},
            headers={"X-API-Key": settings.api_key},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert len(data["items"]) == 1


# =============================================================================
# Router Structure Tests
# =============================================================================


class TestDataRouterStructure:
    """Tests for data router structure."""

    def test_router_has_correct_prefix(self):
        """Router should have /patients prefix."""
        assert router.prefix == "/patients"

    def test_router_has_correct_tags(self):
        """Router should have patient-data tag."""
        assert "patient-data" in router.tags

    def test_router_has_labs_endpoint(self):
        """Router should have labs endpoint."""
        routes = [r.path for r in router.routes]
        assert "/patients/{patient_id}/labs" in routes

    def test_router_has_medications_endpoint(self):
        """Router should have medications endpoint."""
        routes = [r.path for r in router.routes]
        assert "/patients/{patient_id}/medications" in routes

    def test_router_has_conditions_endpoint(self):
        """Router should have conditions endpoint."""
        routes = [r.path for r in router.routes]
        assert "/patients/{patient_id}/conditions" in routes

    def test_router_has_timeline_endpoint(self):
        """Router should have timeline endpoint."""
        routes = [r.path for r in router.routes]
        assert "/patients/{patient_id}/timeline" in routes

    def test_timeline_resource_types_constant(self):
        """TIMELINE_RESOURCE_TYPES should include expected types."""
        expected = {
            "Encounter",
            "Condition",
            "Procedure",
            "MedicationRequest",
            "Observation",
            "DiagnosticReport",
        }
        assert TIMELINE_RESOURCE_TYPES == expected
