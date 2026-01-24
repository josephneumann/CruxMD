"""Integration tests for API endpoints.

Tests the full API request/response cycle through FastAPI,
including authentication, validation, and database operations.
Some tests require PostgreSQL and Neo4j to be running.
"""

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.config import settings
from app.main import app


@pytest.fixture
async def api_client():
    """Async HTTP client for testing the full FastAPI app."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as client:
        yield client


@pytest.fixture
def auth_headers():
    """Headers with valid API key for authenticated requests."""
    return {"X-API-Key": settings.api_key}


# =============================================================================
# Health & Root Endpoints
# =============================================================================


class TestHealthEndpoints:
    """Tests for health check and root endpoints."""

    @pytest.mark.asyncio
    async def test_health_returns_healthy(self, api_client):
        """Health endpoint should return healthy status."""
        response = await api_client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "healthy"}

    @pytest.mark.asyncio
    async def test_root_returns_api_info(self, api_client):
        """Root endpoint should return API information."""
        response = await api_client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "CruxMD API"
        assert "version" in data
        assert data["docs"] == "/docs"


# =============================================================================
# Authentication Tests
# =============================================================================


class TestAuthentication:
    """Tests for API key authentication across all protected endpoints."""

    @pytest.mark.asyncio
    async def test_patients_requires_auth(self, api_client):
        """GET /api/patients should require authentication."""
        response = await api_client.get("/api/patients")
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing API key"

    @pytest.mark.asyncio
    async def test_patient_detail_requires_auth(self, api_client):
        """GET /api/patients/{id} should require authentication."""
        response = await api_client.get(f"/api/patients/{uuid.uuid4()}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_fhir_load_bundle_requires_auth(self, api_client):
        """POST /api/fhir/load-bundle should require authentication."""
        response = await api_client.post(
            "/api/fhir/load-bundle",
            json={"resourceType": "Bundle", "entry": []},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_invalid_api_key_rejected(self, api_client):
        """Invalid API key should be rejected with 401."""
        response = await api_client.get(
            "/api/patients",
            headers={"X-API-Key": "invalid-key"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"


# =============================================================================
# FHIR Bundle Loading API Tests
# =============================================================================


class TestFhirLoadBundleApi:
    """Tests for POST /api/fhir/load-bundle endpoint."""

    @pytest.mark.asyncio
    async def test_rejects_non_bundle_resource(self, api_client, auth_headers):
        """Should reject requests where resourceType is not Bundle."""
        response = await api_client.post(
            "/api/fhir/load-bundle",
            json={"resourceType": "Patient", "id": "test"},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "resourceType must be 'Bundle'" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_rejects_empty_entries(self, api_client, auth_headers):
        """Should reject bundles with no entries."""
        response = await api_client.post(
            "/api/fhir/load-bundle",
            json={"resourceType": "Bundle", "type": "transaction", "entry": []},
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "no entries found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_rejects_entries_without_resources(self, api_client, auth_headers):
        """Should reject bundles with entries lacking valid resources."""
        response = await api_client.post(
            "/api/fhir/load-bundle",
            json={
                "resourceType": "Bundle",
                "type": "transaction",
                "entry": [{"fullUrl": "urn:uuid:123"}],  # No resource key
            },
            headers=auth_headers,
        )
        assert response.status_code == 400
        assert "no valid resources found" in response.json()["detail"]

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_loads_patient_bundle_successfully(
        self, api_client, auth_headers, test_engine, sample_patient
    ):
        """Should successfully load a bundle with a Patient resource."""
        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [{"resource": sample_patient}],
        }
        response = await api_client.post(
            "/api/fhir/load-bundle",
            json=bundle,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["message"] == "Bundle loaded successfully"
        assert data["resources_loaded"] == 1
        assert data["patient_id"] is not None

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_loads_bundle_with_multiple_resources(
        self, api_client, auth_headers, test_engine, sample_patient, sample_condition, sample_medication
    ):
        """Should load bundle with Patient and related resources."""
        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [
                {"resource": sample_patient},
                {"resource": sample_condition},
                {"resource": sample_medication},
            ],
        }
        response = await api_client.post(
            "/api/fhir/load-bundle",
            json=bundle,
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["resources_loaded"] == 3
        assert data["patient_id"] is not None


# =============================================================================
# Patients API Tests
# =============================================================================


@pytest.mark.integration
class TestPatientsApi:
    """Tests for /api/patients endpoints.

    Requires PostgreSQL to be running.
    """

    @pytest.mark.asyncio
    async def test_list_patients_empty(self, api_client, auth_headers, test_engine):
        """Should return empty list when no patients exist."""
        response = await api_client.get("/api/patients", headers=auth_headers)
        assert response.status_code == 200
        assert response.json() == []

    @pytest.mark.asyncio
    async def test_list_patients_after_load(
        self, api_client, auth_headers, test_engine, sample_patient
    ):
        """Should return patients after loading a bundle."""
        # Load a patient first
        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [{"resource": sample_patient}],
        }
        load_response = await api_client.post(
            "/api/fhir/load-bundle",
            json=bundle,
            headers=auth_headers,
        )
        assert load_response.status_code == 200

        # Now list patients
        response = await api_client.get("/api/patients", headers=auth_headers)
        assert response.status_code == 200
        patients = response.json()
        assert len(patients) >= 1
        # Find our patient
        patient = next(
            (p for p in patients if p["fhir_id"] == sample_patient["id"]), None
        )
        assert patient is not None
        assert patient["data"]["name"][0]["family"] == "Smith"

    @pytest.mark.asyncio
    async def test_get_patient_by_id(
        self, api_client, auth_headers, test_engine, sample_patient
    ):
        """Should return patient details by ID."""
        # Load a patient first
        bundle = {
            "resourceType": "Bundle",
            "type": "transaction",
            "entry": [{"resource": sample_patient}],
        }
        load_response = await api_client.post(
            "/api/fhir/load-bundle",
            json=bundle,
            headers=auth_headers,
        )
        patient_id = load_response.json()["patient_id"]

        # Get the patient
        response = await api_client.get(
            f"/api/patients/{patient_id}",
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == patient_id
        assert data["fhir_id"] == sample_patient["id"]
        assert data["data"]["resourceType"] == "Patient"

    @pytest.mark.asyncio
    async def test_get_patient_not_found(self, api_client, auth_headers, test_engine):
        """Should return 404 for nonexistent patient."""
        fake_id = uuid.uuid4()
        response = await api_client.get(
            f"/api/patients/{fake_id}",
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Patient not found"


class TestPatientsApiValidation:
    """Validation tests for patients API that don't require database."""

    @pytest.mark.asyncio
    async def test_get_patient_invalid_uuid(self, api_client, auth_headers):
        """Should return 422 for invalid UUID format."""
        response = await api_client.get(
            "/api/patients/not-a-valid-uuid",
            headers=auth_headers,
        )
        assert response.status_code == 422


# =============================================================================
# API Router Structure Tests
# =============================================================================


class TestApiRouterStructure:
    """Tests for API router configuration."""

    def test_fhir_router_prefix(self):
        """FHIR router should have /fhir prefix."""
        from app.routes.fhir import router
        assert router.prefix == "/fhir"

    def test_fhir_router_tags(self):
        """FHIR router should have fhir tag."""
        from app.routes.fhir import router
        assert "fhir" in router.tags

    def test_patients_router_prefix(self):
        """Patients router should have /patients prefix."""
        from app.routes.patients import router
        assert router.prefix == "/patients"

    def test_patients_router_tags(self):
        """Patients router should have patients tag."""
        from app.routes.patients import router
        assert "patients" in router.tags

    def test_app_includes_cors_middleware(self):
        """App should have CORS middleware configured."""
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "CORSMiddleware" in middleware_classes

    def test_app_title(self):
        """App should have correct title."""
        assert app.title == "CruxMD"


# =============================================================================
# Response Model Tests
# =============================================================================


class TestResponseModels:
    """Tests for API response models."""

    def test_bundle_load_response_fields(self):
        """BundleLoadResponse should have expected fields."""
        from app.routes.fhir import BundleLoadResponse

        response = BundleLoadResponse(
            message="Test",
            resources_loaded=5,
            patient_id=uuid.uuid4(),
        )
        assert response.message == "Test"
        assert response.resources_loaded == 5
        assert response.patient_id is not None

    def test_bundle_load_response_optional_patient_id(self):
        """BundleLoadResponse patient_id should be optional."""
        from app.routes.fhir import BundleLoadResponse

        response = BundleLoadResponse(
            message="Test",
            resources_loaded=0,
        )
        assert response.patient_id is None
