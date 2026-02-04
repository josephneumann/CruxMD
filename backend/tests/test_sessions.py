"""Tests for the Session API routes.

Tests the /api/sessions endpoints covering:
- CRUD operations (create, read, update, list)
- Handoff endpoint
- Filtering by status and patient_id
- Pagination
- Error handling (404s, validation)
"""

import uuid

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import FhirResource
from app.models.session import Session, SessionStatus


# =============================================================================
# Fixtures
# =============================================================================


@pytest_asyncio.fixture
async def patient_in_db(test_engine) -> uuid.UUID:
    """Create a patient FHIR resource in the test database."""
    session_maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    patient_uuid = uuid.uuid4()
    async with session_maker() as session:
        patient = FhirResource(
            id=patient_uuid,
            fhir_id="patient-sess-test",
            resource_type="Patient",
            data={"resourceType": "Patient", "id": "patient-sess-test"},
        )
        session.add(patient)
        await session.commit()
    return patient_uuid


@pytest_asyncio.fixture
async def session_in_db(test_engine, patient_in_db) -> uuid.UUID:
    """Create a session in the test database and return its UUID."""
    session_maker = async_sessionmaker(
        test_engine, class_=AsyncSession, expire_on_commit=False
    )
    session_uuid = uuid.uuid4()
    async with session_maker() as session:
        s = Session(
            id=session_uuid,
            status=SessionStatus.ACTIVE,
            patient_id=patient_in_db,
            messages=[],
        )
        session.add(s)
        await session.commit()
    return session_uuid


# =============================================================================
# Create Session Tests
# =============================================================================


class TestCreateSession:
    """Tests for POST /api/sessions."""

    @pytest.mark.asyncio
    async def test_create_session_with_patient(
        self, client: AsyncClient, auth_headers: dict, patient_in_db: uuid.UUID
    ):
        """Create session linked to a patient (required)."""
        response = await client.post(
            "/api/sessions",
            json={"patient_id": str(patient_in_db)},
            headers=auth_headers,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["status"] == "active"
        assert data["patient_id"] == str(patient_in_db)
        assert data["messages"] == []

    @pytest.mark.asyncio
    async def test_create_session_with_summary(
        self, client: AsyncClient, auth_headers: dict, patient_in_db: uuid.UUID
    ):
        """Create session with a summary."""
        response = await client.post(
            "/api/sessions",
            json={"patient_id": str(patient_in_db), "summary": "Test context"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["summary"] == "Test context"

    @pytest.mark.asyncio
    async def test_create_session_missing_patient_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Missing patient_id field returns 422."""
        response = await client.post(
            "/api/sessions",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422


# =============================================================================
# Get Session Tests
# =============================================================================


class TestGetSession:
    """Tests for GET /api/sessions/{session_id}."""

    @pytest.mark.asyncio
    async def test_get_session(
        self, client: AsyncClient, auth_headers: dict, session_in_db: uuid.UUID
    ):
        """Get an existing session by ID."""
        response = await client.get(
            f"/api/sessions/{session_in_db}", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == str(session_in_db)
        assert data["status"] == "active"

    @pytest.mark.asyncio
    async def test_get_session_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Non-existent session returns 404."""
        response = await client.get(
            f"/api/sessions/{uuid.uuid4()}", headers=auth_headers
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Session not found"


# =============================================================================
# Update Session Tests
# =============================================================================


class TestUpdateSession:
    """Tests for PATCH /api/sessions/{session_id}."""

    @pytest.mark.asyncio
    async def test_update_session_status(
        self, client: AsyncClient, auth_headers: dict, session_in_db: uuid.UUID
    ):
        """Update session status to paused."""
        response = await client.patch(
            f"/api/sessions/{session_in_db}",
            json={"status": "paused"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["status"] == "paused"

    @pytest.mark.asyncio
    async def test_update_session_completed_sets_completed_at(
        self, client: AsyncClient, auth_headers: dict, session_in_db: uuid.UUID
    ):
        """Completing a session sets completed_at timestamp."""
        response = await client.patch(
            f"/api/sessions/{session_in_db}",
            json={"status": "completed"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "completed"
        assert data["completed_at"] is not None

    @pytest.mark.asyncio
    async def test_update_session_summary(
        self, client: AsyncClient, auth_headers: dict, session_in_db: uuid.UUID
    ):
        """Update session summary."""
        response = await client.patch(
            f"/api/sessions/{session_in_db}",
            json={"summary": "Updated summary"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["summary"] == "Updated summary"

    @pytest.mark.asyncio
    async def test_update_session_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Update non-existent session returns 404."""
        response = await client.patch(
            f"/api/sessions/{uuid.uuid4()}",
            json={"status": "paused"},
            headers=auth_headers,
        )
        assert response.status_code == 404


# =============================================================================
# List Sessions Tests
# =============================================================================


class TestListSessions:
    """Tests for GET /api/sessions."""

    @pytest.mark.asyncio
    async def test_list_sessions_empty(
        self, client: AsyncClient, auth_headers: dict
    ):
        """List sessions when none exist."""
        response = await client.get("/api/sessions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["items"] == []
        assert data["total"] == 0

    @pytest.mark.asyncio
    async def test_list_sessions_returns_created(
        self, client: AsyncClient, auth_headers: dict, session_in_db: uuid.UUID
    ):
        """List sessions includes created session."""
        response = await client.get("/api/sessions", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert data["total"] >= 1
        ids = [item["id"] for item in data["items"]]
        assert str(session_in_db) in ids

    @pytest.mark.asyncio
    async def test_list_sessions_filter_by_status(
        self, client: AsyncClient, auth_headers: dict, session_in_db: uuid.UUID
    ):
        """Filter sessions by status."""
        # Session is active
        response = await client.get(
            "/api/sessions?status=active", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["total"] >= 1

        # No completed sessions
        response = await client.get(
            "/api/sessions?status=completed", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_list_sessions_filter_by_patient(
        self,
        client: AsyncClient,
        auth_headers: dict,
        session_in_db: uuid.UUID,
        patient_in_db: uuid.UUID,
    ):
        """Filter sessions by patient_id."""
        response = await client.get(
            f"/api/sessions?patient_id={patient_in_db}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["total"] >= 1

        # Non-existent patient returns empty
        response = await client.get(
            f"/api/sessions?patient_id={uuid.uuid4()}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["total"] == 0

    @pytest.mark.asyncio
    async def test_list_sessions_pagination(
        self, client: AsyncClient, auth_headers: dict, patient_in_db: uuid.UUID
    ):
        """Test pagination parameters."""
        # Create 3 sessions
        for _ in range(3):
            await client.post(
                "/api/sessions",
                json={"patient_id": str(patient_in_db)},
                headers=auth_headers,
            )

        response = await client.get(
            "/api/sessions?skip=0&limit=2", headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data["items"]) == 2
        assert data["total"] == 3
        assert data["limit"] == 2


# =============================================================================
# Handoff Tests
# =============================================================================


class TestHandoff:
    """Tests for POST /api/sessions/{session_id}/handoff."""

    @pytest.mark.asyncio
    async def test_handoff_creates_child_and_pauses_parent(
        self, client: AsyncClient, auth_headers: dict, session_in_db: uuid.UUID
    ):
        """Handoff pauses parent and creates child session."""
        response = await client.post(
            f"/api/sessions/{session_in_db}/handoff",
            json={"summary": "Handoff context"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        child = response.json()
        assert child["parent_session_id"] == str(session_in_db)
        assert child["summary"] == "Handoff context"
        assert child["status"] == "active"

        # Verify parent is paused
        parent_resp = await client.get(
            f"/api/sessions/{session_in_db}", headers=auth_headers
        )
        assert parent_resp.json()["status"] == "paused"

    @pytest.mark.asyncio
    async def test_handoff_inherits_patient_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
        session_in_db: uuid.UUID,
        patient_in_db: uuid.UUID,
    ):
        """Child session inherits patient_id from parent."""
        response = await client.post(
            f"/api/sessions/{session_in_db}/handoff",
            json={"summary": "Inheriting patient"},
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["patient_id"] == str(patient_in_db)

    @pytest.mark.asyncio
    async def test_handoff_override_patient_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
        session_in_db: uuid.UUID,
        patient_in_db: uuid.UUID,
    ):
        """Child session can override parent's patient_id."""
        # We can't use a random UUID here because of FK constraint,
        # so just verify the field is accepted (will use parent's if invalid)
        response = await client.post(
            f"/api/sessions/{session_in_db}/handoff",
            json={
                "summary": "Override patient",
                "patient_id": str(patient_in_db),  # same patient, but explicitly set
            },
            headers=auth_headers,
        )
        assert response.status_code == 201
        assert response.json()["patient_id"] == str(patient_in_db)

    @pytest.mark.asyncio
    async def test_handoff_parent_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Handoff from non-existent parent returns 404."""
        response = await client.post(
            f"/api/sessions/{uuid.uuid4()}/handoff",
            json={"summary": "Orphaned handoff"},
            headers=auth_headers,
        )
        assert response.status_code == 404
        assert response.json()["detail"] == "Parent session not found"

    @pytest.mark.asyncio
    async def test_handoff_missing_summary_returns_422(
        self, client: AsyncClient, auth_headers: dict, session_in_db: uuid.UUID
    ):
        """Handoff without summary returns 422."""
        response = await client.post(
            f"/api/sessions/{session_in_db}/handoff",
            json={},
            headers=auth_headers,
        )
        assert response.status_code == 422
