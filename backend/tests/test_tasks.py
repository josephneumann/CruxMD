"""Tests for task API routes."""


import pytest
import pytest_asyncio
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from app.auth import verify_bearer_token
from app.database import get_db
from app.routes.tasks import router
from tests.conftest import stub_verify_bearer_token


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def tasks_app(mock_db):
    """Create a test app with tasks router."""
    app = FastAPI()

    async def override_get_db():
        yield mock_db

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[verify_bearer_token] = stub_verify_bearer_token
    app.include_router(router)

    return app, mock_db


@pytest_asyncio.fixture
async def tasks_client(tasks_app):
    """Async test client for tasks app."""
    app, mock_db = tasks_app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac, mock_db


class TestGetTask:
    """Tests for GET /tasks/{task_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_task_invalid_uuid(self, tasks_client):
        """Get task with invalid UUID should return 422."""
        client, _ = tasks_client
        response = await client.get(
            "/tasks/not-a-uuid",
            headers={"Authorization": "Bearer test-token"},
        )
        assert response.status_code == 422


class TestTasksRouterStructure:
    """Tests for tasks router structure."""

    def test_router_has_correct_prefix(self):
        """Router should have /tasks prefix."""
        assert router.prefix == "/tasks"

    def test_router_has_correct_tags(self):
        """Router should have tasks tag."""
        assert "tasks" in router.tags

    def test_router_has_list_endpoint(self):
        """Router should have list tasks endpoint."""
        routes = [r.path for r in router.routes]
        assert "/tasks" in routes

    def test_router_has_queue_endpoint(self):
        """Router should have queue endpoint."""
        routes = [r.path for r in router.routes]
        assert "/tasks/queue" in routes

    def test_router_has_get_endpoint(self):
        """Router should have get task endpoint."""
        routes = [r.path for r in router.routes]
        assert "/tasks/{task_id}" in routes
