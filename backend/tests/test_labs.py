"""Tests for lab results API routes."""

import uuid

import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock, MagicMock

from app.auth import verify_bearer_token
from app.database import get_db
from app.routes.labs import _extract_observation_fields, router
from tests.conftest import stub_verify_bearer_token


# =============================================================================
# Unit tests for _extract_observation_fields
# =============================================================================


class TestExtractObservationFields:
    """Tests for the _extract_observation_fields helper."""

    def test_basic_numeric_observation(self):
        """Extract fields from a standard numeric observation."""
        obs = {
            "code": {
                "coding": [{"code": "718-7", "display": "Hemoglobin"}]
            },
            "valueQuantity": {"value": 14.2, "unit": "g/dL"},
            "effectiveDateTime": "2024-06-15T10:00:00Z",
        }
        result = _extract_observation_fields(obs)
        assert result is not None
        assert result["test"] == "Hemoglobin"
        assert result["loincCode"] == "718-7"
        assert result["value"] == 14.2
        assert result["unit"] == "g/dL"
        assert result["date"] == "2024-06-15"
        assert result["rangeLow"] is None
        assert result["rangeHigh"] is None
        assert result["interpretation"] is None

    def test_returns_none_for_non_numeric(self):
        """Non-numeric observations (no valueQuantity.value) return None."""
        obs = {
            "code": {"coding": [{"code": "72166-2", "display": "Tobacco status"}]},
            "valueCodeableConcept": {
                "coding": [{"display": "Never smoker"}]
            },
        }
        assert _extract_observation_fields(obs) is None

    def test_returns_none_for_missing_value(self):
        """Observation with valueQuantity but no value returns None."""
        obs = {
            "code": {"coding": [{"code": "718-7", "display": "Hemoglobin"}]},
            "valueQuantity": {"unit": "g/dL"},
        }
        assert _extract_observation_fields(obs) is None

    def test_with_reference_range(self):
        """Extract reference range when present in FHIR data."""
        obs = {
            "code": {"coding": [{"code": "718-7", "display": "Hemoglobin"}]},
            "valueQuantity": {"value": 14.2, "unit": "g/dL"},
            "effectiveDateTime": "2024-06-15T10:00:00Z",
            "referenceRange": [
                {
                    "low": {"value": 12.0, "unit": "g/dL"},
                    "high": {"value": 17.5, "unit": "g/dL"},
                }
            ],
        }
        result = _extract_observation_fields(obs)
        assert result["rangeLow"] == 12.0
        assert result["rangeHigh"] == 17.5

    def test_with_interpretation(self):
        """Extract HL7 interpretation code when present."""
        obs = {
            "code": {"coding": [{"code": "718-7", "display": "Hemoglobin"}]},
            "valueQuantity": {"value": 6.5, "unit": "g/dL"},
            "effectiveDateTime": "2024-06-15T10:00:00Z",
            "interpretation": [
                {"coding": [{"code": "LL", "display": "Critical low"}]}
            ],
        }
        result = _extract_observation_fields(obs)
        assert result["interpretation"] == "LL"

    def test_fallback_test_name_from_text(self):
        """Use code.text when coding array is empty."""
        obs = {
            "code": {"text": "Custom Test"},
            "valueQuantity": {"value": 42, "unit": "mg/dL"},
            "effectiveDateTime": "2024-01-01",
        }
        result = _extract_observation_fields(obs)
        assert result["test"] == "Custom Test"
        assert result["loincCode"] is None

    def test_date_truncation(self):
        """Date is truncated to YYYY-MM-DD."""
        obs = {
            "code": {"coding": [{"code": "718-7", "display": "Hemoglobin"}]},
            "valueQuantity": {"value": 14.0, "unit": "g/dL"},
            "effectiveDateTime": "2024-12-25T14:30:00.000Z",
        }
        result = _extract_observation_fields(obs)
        assert result["date"] == "2024-12-25"

    def test_missing_effective_datetime(self):
        """Missing effectiveDateTime produces empty string date."""
        obs = {
            "code": {"coding": [{"code": "718-7", "display": "Hemoglobin"}]},
            "valueQuantity": {"value": 14.0, "unit": "g/dL"},
        }
        result = _extract_observation_fields(obs)
        assert result["date"] == ""

    def test_empty_reference_range_list(self):
        """Empty referenceRange list produces null range values."""
        obs = {
            "code": {"coding": [{"code": "718-7", "display": "Hemoglobin"}]},
            "valueQuantity": {"value": 14.0, "unit": "g/dL"},
            "effectiveDateTime": "2024-01-01",
            "referenceRange": [],
        }
        result = _extract_observation_fields(obs)
        assert result["rangeLow"] is None
        assert result["rangeHigh"] is None


# =============================================================================
# Router structure tests
# =============================================================================


class TestLabsRouterStructure:
    """Tests for labs router structure."""

    def test_router_has_correct_prefix(self):
        assert router.prefix == "/patients"

    def test_router_has_correct_tags(self):
        assert "labs" in router.tags

    def test_router_has_labs_endpoint(self):
        routes = [r.path for r in router.routes]
        assert "/patients/{patient_id}/labs" in routes


# =============================================================================
# API endpoint tests
# =============================================================================


@pytest.fixture
def mock_db():
    return AsyncMock()


@pytest.fixture
def labs_app(mock_db):
    app = FastAPI()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[verify_bearer_token] = stub_verify_bearer_token
    app.include_router(router)
    return app, mock_db


@pytest_asyncio.fixture
async def labs_client(labs_app):
    app, mock_db = labs_app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac, mock_db


class TestGetPatientLabs:
    """Tests for GET /patients/{patient_id}/labs endpoint."""

    @pytest.mark.asyncio
    async def test_invalid_uuid_returns_422(self, labs_client):
        client, _ = labs_client
        response = await client.get(
            "/patients/not-a-uuid/labs",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_patient_not_found_returns_404(self, labs_client):
        client, mock_db = labs_client
        # Patient lookup returns nothing
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result

        patient_id = str(uuid.uuid4())
        response = await client.get(
            f"/patients/{patient_id}/labs",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Patient not found"
