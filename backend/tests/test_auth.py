"""Tests for API key authentication."""

import pytest
from fastapi import FastAPI, Depends
from httpx import ASGITransport, AsyncClient

from app.auth import verify_api_key
from app.config import settings


@pytest.fixture
def protected_app():
    """Create a test app with a protected endpoint."""
    app = FastAPI()

    @app.get("/protected")
    async def protected_endpoint(api_key: str = Depends(verify_api_key)):
        return {"message": "success", "api_key": api_key}

    return app


@pytest.fixture
async def protected_client(protected_app):
    """Async test client for protected app."""
    async with AsyncClient(
        transport=ASGITransport(app=protected_app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.mark.asyncio
async def test_valid_api_key(protected_client):
    """Test that valid API key allows access."""
    response = await protected_client.get(
        "/protected",
        headers={"X-API-Key": settings.api_key},
    )
    assert response.status_code == 200
    assert response.json()["message"] == "success"


@pytest.mark.asyncio
async def test_missing_api_key(protected_client):
    """Test that missing API key returns 401."""
    response = await protected_client.get("/protected")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing API key"


@pytest.mark.asyncio
async def test_invalid_api_key(protected_client):
    """Test that invalid API key returns 401."""
    response = await protected_client.get(
        "/protected",
        headers={"X-API-Key": "wrong-key"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid API key"
