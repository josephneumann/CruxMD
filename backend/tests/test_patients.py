"""Tests for patient API routes."""

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from app.auth import verify_bearer_token
from app.database import get_db
from app.routes.patients import router
from tests.conftest import stub_verify_bearer_token


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def patients_app(mock_db):
    """Create a test app with patients router."""
    app = FastAPI()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[verify_bearer_token] = stub_verify_bearer_token
    app.include_router(router)

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


class TestGetPatient:
    """Tests for GET /patients/{patient_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_patient_invalid_uuid(self, patients_client):
        """Get patient with invalid UUID should return 422."""
        client, _ = patients_client
        response = await client.get(
            "/patients/not-a-uuid",
            headers={"Authorization": "Bearer test-token"},
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
