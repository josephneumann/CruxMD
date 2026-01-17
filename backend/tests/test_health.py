"""Tests for health check endpoint."""

import pytest


@pytest.mark.asyncio
async def test_health_check(client):
    """Test that health endpoint returns healthy status."""
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


@pytest.mark.asyncio
async def test_root(client):
    """Test that root endpoint returns API info."""
    response = await client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "CruxMD API"
    assert "version" in data
