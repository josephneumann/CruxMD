"""Tests for FHIR API routes."""

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from app.config import settings
from app.routes.fhir import router, BundleLoadResponse


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def fhir_app(mock_db):
    """Create a test app with fhir router."""
    app = FastAPI()
    app.include_router(router)
    return app, mock_db


@pytest.fixture
async def fhir_client(fhir_app):
    """Async test client for fhir app."""
    app, mock_db = fhir_app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac, mock_db


class TestLoadBundle:
    """Tests for POST /fhir/load-bundle endpoint."""

    @pytest.mark.asyncio
    async def test_load_bundle_requires_auth(self, fhir_client):
        """Load bundle should require API key."""
        client, _ = fhir_client
        response = await client.post(
            "/fhir/load-bundle",
            json={"resourceType": "Bundle", "entry": []},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing API key"

    @pytest.mark.asyncio
    async def test_load_bundle_rejects_invalid_key(self, fhir_client):
        """Load bundle should reject invalid API key."""
        client, _ = fhir_client
        response = await client.post(
            "/fhir/load-bundle",
            json={"resourceType": "Bundle", "entry": []},
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_load_bundle_requires_bundle_type(self, fhir_client):
        """Load bundle should validate resourceType is Bundle."""
        client, _ = fhir_client
        response = await client.post(
            "/fhir/load-bundle",
            json={"resourceType": "Patient", "id": "123"},
            headers={"X-API-Key": settings.api_key},
        )
        assert response.status_code == 400
        assert "resourceType must be 'Bundle'" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_load_bundle_requires_entries(self, fhir_client):
        """Load bundle should require at least one entry."""
        client, _ = fhir_client
        response = await client.post(
            "/fhir/load-bundle",
            json={"resourceType": "Bundle", "entry": []},
            headers={"X-API-Key": settings.api_key},
        )
        assert response.status_code == 400
        assert "no entries found" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_load_bundle_requires_valid_resources(self, fhir_client):
        """Load bundle should require valid resources in entries."""
        client, _ = fhir_client
        response = await client.post(
            "/fhir/load-bundle",
            json={
                "resourceType": "Bundle",
                "entry": [{"fullUrl": "urn:uuid:123"}],  # No resource
            },
            headers={"X-API-Key": settings.api_key},
        )
        assert response.status_code == 400
        assert "no valid resources found" in response.json()["detail"]


class TestBundleLoadResponse:
    """Tests for BundleLoadResponse model."""

    def test_response_model_fields(self):
        """BundleLoadResponse should have expected fields."""
        import uuid

        response = BundleLoadResponse(
            message="Test",
            resources_loaded=5,
            patient_id=uuid.uuid4(),
        )
        assert response.message == "Test"
        assert response.resources_loaded == 5
        assert response.patient_id is not None

    def test_response_model_optional_patient_id(self):
        """BundleLoadResponse patient_id should be optional."""
        response = BundleLoadResponse(
            message="Test",
            resources_loaded=0,
        )
        assert response.patient_id is None


class TestFhirRouterStructure:
    """Tests for FHIR router structure."""

    def test_router_has_correct_prefix(self):
        """Router should have /fhir prefix."""
        assert router.prefix == "/fhir"

    def test_router_has_correct_tags(self):
        """Router should have fhir tag."""
        assert "fhir" in router.tags

    def test_router_has_load_bundle_endpoint(self):
        """Router should have load-bundle endpoint."""
        routes = [r.path for r in router.routes]
        assert "/fhir/load-bundle" in routes
