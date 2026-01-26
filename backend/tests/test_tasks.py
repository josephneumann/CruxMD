"""Tests for task API routes."""

import uuid

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from unittest.mock import AsyncMock

from app.config import settings
from app.routes.tasks import router


@pytest.fixture
def mock_db():
    """Create a mock database session."""
    return AsyncMock()


@pytest.fixture
def tasks_app(mock_db):
    """Create a test app with tasks router."""
    app = FastAPI()

    # Override the db dependency
    async def override_get_db():
        yield mock_db

    app.include_router(router)
    app.dependency_overrides = {}

    return app, mock_db


@pytest.fixture
async def tasks_client(tasks_app):
    """Async test client for tasks app."""
    app, mock_db = tasks_app
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as ac:
        yield ac, mock_db


class TestListTasks:
    """Tests for GET /tasks endpoint."""

    @pytest.mark.asyncio
    async def test_list_tasks_requires_auth(self, tasks_client):
        """List tasks should require API key."""
        client, _ = tasks_client
        response = await client.get("/tasks")
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing API key"

    @pytest.mark.asyncio
    async def test_list_tasks_rejects_invalid_key(self, tasks_client):
        """List tasks should reject invalid API key."""
        client, _ = tasks_client
        response = await client.get(
            "/tasks",
            headers={"X-API-Key": "wrong-key"},
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid API key"


class TestGetTaskQueue:
    """Tests for GET /tasks/queue endpoint."""

    @pytest.mark.asyncio
    async def test_queue_requires_auth(self, tasks_client):
        """Task queue should require API key."""
        client, _ = tasks_client
        response = await client.get("/tasks/queue")
        assert response.status_code == 401


class TestGetTask:
    """Tests for GET /tasks/{task_id} endpoint."""

    @pytest.mark.asyncio
    async def test_get_task_requires_auth(self, tasks_client):
        """Get task should require API key."""
        client, _ = tasks_client
        task_id = uuid.uuid4()
        response = await client.get(f"/tasks/{task_id}")
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_get_task_invalid_uuid(self, tasks_client):
        """Get task with invalid UUID should return 422."""
        client, _ = tasks_client
        response = await client.get(
            "/tasks/not-a-uuid",
            headers={"X-API-Key": settings.api_key},
        )
        assert response.status_code == 422


class TestCreateTask:
    """Tests for POST /tasks endpoint."""

    @pytest.mark.asyncio
    async def test_create_task_requires_auth(self, tasks_client):
        """Create task should require API key."""
        client, _ = tasks_client
        response = await client.post("/tasks", json={})
        assert response.status_code == 401


class TestUpdateTask:
    """Tests for PATCH /tasks/{task_id} endpoint."""

    @pytest.mark.asyncio
    async def test_update_task_requires_auth(self, tasks_client):
        """Update task should require API key."""
        client, _ = tasks_client
        task_id = uuid.uuid4()
        response = await client.patch(f"/tasks/{task_id}", json={})
        assert response.status_code == 401


class TestDeleteTask:
    """Tests for DELETE /tasks/{task_id} endpoint."""

    @pytest.mark.asyncio
    async def test_delete_task_requires_auth(self, tasks_client):
        """Delete task should require API key."""
        client, _ = tasks_client
        task_id = uuid.uuid4()
        response = await client.delete(f"/tasks/{task_id}")
        assert response.status_code == 401


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
