"""Tests for patient API routes."""

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from app.config import settings
from app.routes.patients import router


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def patients_app(mock_db):
    """Create a test app with patients router."""
    app = FastAPI()

    # Override the db dependency
    async def override_get_db():
        yield mock_db

    app.include_router(router)
    app.dependency_overrides = {}

    return app, mock_db


@pytest.fixture
async def patients_client(patients_app):
    """Async test client for patients app."""
    app, mock_db = patients_app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac, mock_db


class TestListPatients:
    """Tests for GET /patients endpoint."""

    @pytest.mark.asyncio
    async def test_list_patients_requires_auth(self, patients_client):
        """List patients should require API key."""
        client, _ = patients_client
        response = await client.get("/patients")
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing API key"

    @pytest.mark.asyncio
    async def test_list_patients_rejects_invalid_key(self, patients_client):
        """List patients should reject invalid API key."""
        client, _ = patients_client
        response = await client.get(
            "/patients",
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"


class TestGetPatient:
    """Tests for GET /patients/{patient_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_patient_requires_auth(self, patients_client):
        """Get patient should require API key."""
        client, _ = patients_client
        patient_id = uuid.uuid4()
        response = await client.get(f"/patients/{patient_id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_patient_invalid_uuid(self, patients_client):
        """Get patient with invalid UUID should return 422."""
        client, _ = patients_client
        response = await client.get(
            "/patients/not-a-uuid",
            headers={"X-API-Key": settings.api_key},
        )
        assert response.status_code == 422


class TestPatientsRouterStructure:
    """Tests for patients router structure."""

    def test_router_has_correct_prefix(self):
        """Router should have /patients prefix."""
        assert router.prefix == "/patients"

    def test_router_has_correct_tags(self):
        """Router should have patients tag."""
        assert "patients" in router.tags

    def test_router_has_list_endpoint(self):
        """Router should have list patients endpoint."""
        routes = [r.path for r in router.routes]
        assert "/patients" in routes

    def test_router_has_get_endpoint(self):
        """Router should have get patient endpoint."""
        routes = [r.path for r in router.routes]
        assert "/patients/{patient_id}" in routes
