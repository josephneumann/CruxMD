"""Tests for the Chat API endpoints.

Tests the POST /api/chat and POST /api/chat/stream endpoints covering:
- Authentication (API key validation)
- Request validation
- Patient existence checks
- Integration with ContextEngine and AgentService
- Error handling
- SSE streaming
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.config import settings
from app.database import Base, get_db
from app.main import app
from app.models import FhirResource
from app.schemas import AgentResponse, FollowUp, Insight
from app.schemas.context import (
    ContextMeta,
    PatientContext,
    RetrievedLayer,
    VerifiedLayer,
)


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def sample_patient_data() -> dict:
    """Sample FHIR Patient resource data."""
    return {
        "resourceType": "Patient",
        "id": "patient-123",
        "name": [{"given": ["John"], "family": "Doe"}],
        "birthDate": "1960-05-15",
        "gender": "male",
    }


@pytest.fixture
def sample_agent_response() -> AgentResponse:
    """Sample AgentResponse for mocking."""
    return AgentResponse(
        narrative="This patient has Type 2 diabetes mellitus, well controlled on current therapy.",
        insights=[
            Insight(
                type="info",
                title="HbA1c Level",
                content="Recent HbA1c of 7.2% indicates good glycemic control.",
            ),
        ],
        follow_ups=[
            FollowUp(question="What is the patient's blood pressure trend?", intent="vitals"),
            FollowUp(question="Are there any medication adjustments needed?", intent="treatment"),
        ],
    )


@pytest.fixture
def sample_patient_context(sample_patient_data: dict) -> PatientContext:
    """Sample PatientContext for mocking."""
    return PatientContext(
        meta=ContextMeta(patient_id="test-id", query="test query"),
        patient=sample_patient_data,
        verified=VerifiedLayer(),
        retrieved=RetrievedLayer(),
        constraints=[],
    )


@pytest_asyncio.fixture
async def patient_in_db(test_engine, sample_patient_data: dict) -> uuid.UUID:
    """Create a patient in the test database and return its UUID."""
    session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    patient_uuid = uuid.uuid4()

    async with session_maker() as session:
        patient = FhirResource(
            id=patient_uuid,
            fhir_id="patient-123",
            resource_type="Patient",
            data=sample_patient_data,
        )
        session.add(patient)
        await session.commit()

    return patient_uuid


# =============================================================================
# Request Validation Tests
# =============================================================================


class TestChatValidation:
    """Tests for chat request validation."""

    @pytest.mark.asyncio
    async def test_chat_empty_message_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that empty message returns 422 validation error."""
        response = await client.post(
            "/api/chat",
            json={
                "patient_id": str(uuid.uuid4()),
                "message": "",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_missing_patient_id_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that missing patient_id returns 422 validation error."""
        response = await client.post(
            "/api/chat",
            json={
                "message": "What medications is this patient taking?",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_invalid_patient_id_format_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that invalid UUID format returns 422 validation error."""
        response = await client.post(
            "/api/chat",
            json={
                "patient_id": "not-a-uuid",
                "message": "What medications is this patient taking?",
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_missing_message_returns_422(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that missing message returns 422 validation error."""
        response = await client.post(
            "/api/chat",
            json={
                "patient_id": str(uuid.uuid4()),
            },
            headers=auth_headers,
        )

        assert response.status_code == 422


# =============================================================================
# Patient Existence Tests
# =============================================================================


class TestChatPatientExistence:
    """Tests for patient existence validation."""

    @pytest.mark.asyncio
    async def test_chat_patient_not_found_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that non-existent patient returns 404."""
        response = await client.post(
            "/api/chat",
            json={
                "patient_id": str(uuid.uuid4()),
                "message": "What medications is this patient taking?",
            },
            headers=auth_headers,
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Patient not found"


# =============================================================================
# Successful Chat Tests
# =============================================================================


class TestChatSuccess:
    """Tests for successful chat interactions."""

    @pytest.mark.asyncio
    async def test_chat_success_minimal_request(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_agent_response: AgentResponse,
        sample_patient_context: PatientContext,
    ):
        """Test successful chat with minimal request."""
        with patch("app.routes.chat.ContextEngine") as mock_context_engine_class, \
             patch("app.routes.chat.AgentService") as mock_agent_service_class, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_class, \
             patch("app.routes.chat.EmbeddingService") as mock_embedding_class, \
             patch("app.routes.chat.VectorSearchService"):

            # Setup mocks
            mock_graph = AsyncMock()
            mock_graph_class.return_value = mock_graph

            mock_embedding = AsyncMock()
            mock_embedding_class.return_value = mock_embedding

            mock_context_engine = AsyncMock()
            mock_context_engine.build_context_with_patient = AsyncMock(
                return_value=sample_patient_context
            )
            mock_context_engine_class.return_value = mock_context_engine

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_service_class.return_value = mock_agent

            response = await client.post(
                "/api/chat",
                json={
                    "patient_id": str(patient_in_db),
                    "message": "What medications is this patient taking?",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Verify response structure
            assert "conversation_id" in data
            assert "response" in data
            assert data["response"]["narrative"] == sample_agent_response.narrative

    @pytest.mark.asyncio
    async def test_chat_generates_conversation_id_when_not_provided(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_agent_response: AgentResponse,
        sample_patient_context: PatientContext,
    ):
        """Test that conversation_id is generated when not provided."""
        with patch("app.routes.chat.ContextEngine") as mock_context_engine_class, \
             patch("app.routes.chat.AgentService") as mock_agent_service_class, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_class, \
             patch("app.routes.chat.EmbeddingService") as mock_embedding_class, \
             patch("app.routes.chat.VectorSearchService"):

            mock_graph_class.return_value = AsyncMock()
            mock_embedding_class.return_value = AsyncMock()

            mock_context_engine = AsyncMock()
            mock_context_engine.build_context_with_patient = AsyncMock(
                return_value=sample_patient_context
            )
            mock_context_engine_class.return_value = mock_context_engine

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_service_class.return_value = mock_agent

            response = await client.post(
                "/api/chat",
                json={
                    "patient_id": str(patient_in_db),
                    "message": "What medications is this patient taking?",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            # Verify conversation_id is a valid UUID
            conversation_id = data["conversation_id"]
            uuid.UUID(conversation_id)  # Will raise if invalid

    @pytest.mark.asyncio
    async def test_chat_uses_provided_conversation_id(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_agent_response: AgentResponse,
        sample_patient_context: PatientContext,
    ):
        """Test that provided conversation_id is used."""
        provided_conversation_id = uuid.uuid4()

        with patch("app.routes.chat.ContextEngine") as mock_context_engine_class, \
             patch("app.routes.chat.AgentService") as mock_agent_service_class, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_class, \
             patch("app.routes.chat.EmbeddingService") as mock_embedding_class, \
             patch("app.routes.chat.VectorSearchService"):

            mock_graph_class.return_value = AsyncMock()
            mock_embedding_class.return_value = AsyncMock()

            mock_context_engine = AsyncMock()
            mock_context_engine.build_context_with_patient = AsyncMock(
                return_value=sample_patient_context
            )
            mock_context_engine_class.return_value = mock_context_engine

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_service_class.return_value = mock_agent

            response = await client.post(
                "/api/chat",
                json={
                    "patient_id": str(patient_in_db),
                    "message": "What medications is this patient taking?",
                    "conversation_id": str(provided_conversation_id),
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            data = response.json()

            assert data["conversation_id"] == str(provided_conversation_id)

    @pytest.mark.asyncio
    async def test_chat_with_conversation_history(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_agent_response: AgentResponse,
        sample_patient_context: PatientContext,
    ):
        """Test chat with conversation history."""
        with patch("app.routes.chat.ContextEngine") as mock_context_engine_class, \
             patch("app.routes.chat.AgentService") as mock_agent_service_class, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_class, \
             patch("app.routes.chat.EmbeddingService") as mock_embedding_class, \
             patch("app.routes.chat.VectorSearchService"):

            mock_graph_class.return_value = AsyncMock()
            mock_embedding_class.return_value = AsyncMock()

            mock_context_engine = AsyncMock()
            mock_context_engine.build_context_with_patient = AsyncMock(
                return_value=sample_patient_context
            )
            mock_context_engine_class.return_value = mock_context_engine

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_service_class.return_value = mock_agent

            response = await client.post(
                "/api/chat",
                json={
                    "patient_id": str(patient_in_db),
                    "message": "What about their blood pressure?",
                    "conversation_history": [
                        {"role": "user", "content": "Tell me about this patient"},
                        {"role": "assistant", "content": "This is a 65-year-old male patient..."},
                    ],
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

            # Verify history was passed to agent
            mock_agent.generate_response.assert_called_once()
            call_kwargs = mock_agent.generate_response.call_args.kwargs
            assert call_kwargs["history"] == [
                {"role": "user", "content": "Tell me about this patient"},
                {"role": "assistant", "content": "This is a 65-year-old male patient..."},
            ]


# =============================================================================
# Error Handling Tests
# =============================================================================


class TestChatErrorHandling:
    """Tests for error handling in chat endpoint."""

    @pytest.mark.asyncio
    async def test_chat_runtime_error_returns_500(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_patient_context: PatientContext,
    ):
        """Test that RuntimeError from agent returns 500."""
        with patch("app.routes.chat.ContextEngine") as mock_context_engine_class, \
             patch("app.routes.chat.AgentService") as mock_agent_service_class, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_class, \
             patch("app.routes.chat.EmbeddingService") as mock_embedding_class, \
             patch("app.routes.chat.VectorSearchService"):

            mock_graph_class.return_value = AsyncMock()
            mock_embedding_class.return_value = AsyncMock()

            mock_context_engine = AsyncMock()
            mock_context_engine.build_context_with_patient = AsyncMock(
                return_value=sample_patient_context
            )
            mock_context_engine_class.return_value = mock_context_engine

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(
                side_effect=RuntimeError("LLM response could not be parsed")
            )
            mock_agent_service_class.return_value = mock_agent

            response = await client.post(
                "/api/chat",
                json={
                    "patient_id": str(patient_in_db),
                    "message": "What medications is this patient taking?",
                },
                headers=auth_headers,
            )

            assert response.status_code == 500
            assert "Failed to generate response" in response.json()["detail"]

    @pytest.mark.asyncio
    async def test_chat_value_error_returns_400(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_patient_context: PatientContext,
    ):
        """Test that ValueError from agent returns 400."""
        with patch("app.routes.chat.ContextEngine") as mock_context_engine_class, \
             patch("app.routes.chat.AgentService") as mock_agent_service_class, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_class, \
             patch("app.routes.chat.EmbeddingService") as mock_embedding_class, \
             patch("app.routes.chat.VectorSearchService"):

            mock_graph_class.return_value = AsyncMock()
            mock_embedding_class.return_value = AsyncMock()

            mock_context_engine = AsyncMock()
            mock_context_engine.build_context_with_patient = AsyncMock(
                return_value=sample_patient_context
            )
            mock_context_engine_class.return_value = mock_context_engine

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(
                side_effect=ValueError("message cannot be empty")
            )
            mock_agent_service_class.return_value = mock_agent

            response = await client.post(
                "/api/chat",
                json={
                    "patient_id": str(patient_in_db),
                    "message": "Test message",  # Will be mocked to fail
                },
                headers=auth_headers,
            )

            assert response.status_code == 400
            assert "Invalid request parameters" in response.json()["detail"]


# =============================================================================
# Input Validation Tests (Security Hardening)
# =============================================================================


class TestChatInputValidation:
    """Tests for enhanced input validation."""

    @pytest.mark.asyncio
    async def test_chat_rejects_invalid_role(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that invalid role values are rejected."""
        response = await client.post(
            "/api/chat",
            json={
                "patient_id": str(uuid.uuid4()),
                "message": "Test message",
                "conversation_history": [
                    {"role": "system", "content": "You are helpful"}  # Invalid role
                ],
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_rejects_oversized_message(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that messages exceeding max length are rejected."""
        response = await client.post(
            "/api/chat",
            json={
                "patient_id": str(uuid.uuid4()),
                "message": "x" * 10001,  # Exceeds MAX_MESSAGE_LENGTH
            },
            headers=auth_headers,
        )

        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_chat_accepts_max_length_message(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_agent_response: AgentResponse,
        sample_patient_context: PatientContext,
    ):
        """Test that messages at max length are accepted."""
        with patch("app.routes.chat.ContextEngine") as mock_context_engine_class, \
             patch("app.routes.chat.AgentService") as mock_agent_service_class, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_class, \
             patch("app.routes.chat.EmbeddingService") as mock_embedding_class, \
             patch("app.routes.chat.VectorSearchService"):

            mock_graph_class.return_value = AsyncMock()
            mock_embedding_class.return_value = AsyncMock()

            mock_context_engine = AsyncMock()
            mock_context_engine.build_context_with_patient = AsyncMock(
                return_value=sample_patient_context
            )
            mock_context_engine_class.return_value = mock_context_engine

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_service_class.return_value = mock_agent

            response = await client.post(
                "/api/chat",
                json={
                    "patient_id": str(patient_in_db),
                    "message": "x" * 10000,  # Exactly MAX_MESSAGE_LENGTH
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_chat_rejects_too_many_history_messages(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that conversation history exceeding limit is rejected."""
        # Create 51 messages (exceeds MAX_CONVERSATION_HISTORY of 50)
        history = [
            {"role": "user" if i % 2 == 0 else "assistant", "content": f"Message {i}"}
            for i in range(51)
        ]

        response = await client.post(
            "/api/chat",
            json={
                "patient_id": str(uuid.uuid4()),
                "message": "Test message",
                "conversation_history": history,
            },
            headers=auth_headers,
        )

        assert response.status_code == 422


# =============================================================================
# Integration Tests
# =============================================================================


class TestChatIntegration:
    """Integration tests for chat endpoint service coordination."""

    @pytest.mark.asyncio
    async def test_chat_calls_context_engine_with_correct_params(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_agent_response: AgentResponse,
        sample_patient_context: PatientContext,
        sample_patient_data: dict,
    ):
        """Test that ContextEngine is called with correct parameters."""
        with patch("app.routes.chat.ContextEngine") as mock_context_engine_class, \
             patch("app.routes.chat.AgentService") as mock_agent_service_class, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_class, \
             patch("app.routes.chat.EmbeddingService") as mock_embedding_class, \
             patch("app.routes.chat.VectorSearchService"):

            mock_graph_class.return_value = AsyncMock()
            mock_embedding_class.return_value = AsyncMock()

            mock_context_engine = AsyncMock()
            mock_context_engine.build_context_with_patient = AsyncMock(
                return_value=sample_patient_context
            )
            mock_context_engine_class.return_value = mock_context_engine

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_service_class.return_value = mock_agent

            test_message = "What medications is this patient taking?"

            response = await client.post(
                "/api/chat",
                json={
                    "patient_id": str(patient_in_db),
                    "message": test_message,
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

            # Verify ContextEngine was called with correct params
            mock_context_engine.build_context_with_patient.assert_called_once()
            call_kwargs = mock_context_engine.build_context_with_patient.call_args.kwargs
            assert call_kwargs["patient_id"] == str(patient_in_db)
            assert call_kwargs["query"] == test_message

    @pytest.mark.asyncio
    async def test_chat_calls_agent_service_with_context_and_message(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_agent_response: AgentResponse,
        sample_patient_context: PatientContext,
    ):
        """Test that AgentService is called with context and message."""
        with patch("app.routes.chat.ContextEngine") as mock_context_engine_class, \
             patch("app.routes.chat.AgentService") as mock_agent_service_class, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_class, \
             patch("app.routes.chat.EmbeddingService") as mock_embedding_class, \
             patch("app.routes.chat.VectorSearchService"):

            mock_graph_class.return_value = AsyncMock()
            mock_embedding_class.return_value = AsyncMock()

            mock_context_engine = AsyncMock()
            mock_context_engine.build_context_with_patient = AsyncMock(
                return_value=sample_patient_context
            )
            mock_context_engine_class.return_value = mock_context_engine

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_service_class.return_value = mock_agent

            test_message = "What medications is this patient taking?"

            response = await client.post(
                "/api/chat",
                json={
                    "patient_id": str(patient_in_db),
                    "message": test_message,
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

            # Verify AgentService was called with correct params
            mock_agent.generate_response.assert_called_once()
            call_kwargs = mock_agent.generate_response.call_args.kwargs
            assert call_kwargs["context"] == sample_patient_context
            assert call_kwargs["message"] == test_message
            assert call_kwargs["history"] is None

    @pytest.mark.asyncio
    async def test_chat_cleans_up_services_on_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_agent_response: AgentResponse,
        sample_patient_context: PatientContext,
    ):
        """Test that services are cleaned up after successful request."""
        with patch("app.routes.chat.ContextEngine") as mock_context_engine_class, \
             patch("app.routes.chat.AgentService") as mock_agent_service_class, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_class, \
             patch("app.routes.chat.EmbeddingService") as mock_embedding_class, \
             patch("app.routes.chat.VectorSearchService"):

            mock_graph = AsyncMock()
            mock_graph_class.return_value = mock_graph

            mock_embedding = AsyncMock()
            mock_embedding_class.return_value = mock_embedding

            mock_context_engine = AsyncMock()
            mock_context_engine.build_context_with_patient = AsyncMock(
                return_value=sample_patient_context
            )
            mock_context_engine_class.return_value = mock_context_engine

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_service_class.return_value = mock_agent

            response = await client.post(
                "/api/chat",
                json={
                    "patient_id": str(patient_in_db),
                    "message": "Test message",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

            # Verify cleanup was called
            mock_graph.close.assert_called_once()
            mock_embedding.close.assert_called_once()
            mock_agent.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_cleans_up_services_on_error(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_patient_context: PatientContext,
    ):
        """Test that services are cleaned up even on error."""
        with patch("app.routes.chat.ContextEngine") as mock_context_engine_class, \
             patch("app.routes.chat.AgentService") as mock_agent_service_class, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_class, \
             patch("app.routes.chat.EmbeddingService") as mock_embedding_class, \
             patch("app.routes.chat.VectorSearchService"):

            mock_graph = AsyncMock()
            mock_graph_class.return_value = mock_graph

            mock_embedding = AsyncMock()
            mock_embedding_class.return_value = mock_embedding

            mock_context_engine = AsyncMock()
            mock_context_engine.build_context_with_patient = AsyncMock(
                return_value=sample_patient_context
            )
            mock_context_engine_class.return_value = mock_context_engine

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(
                side_effect=RuntimeError("LLM error")
            )
            mock_agent_service_class.return_value = mock_agent

            response = await client.post(
                "/api/chat",
                json={
                    "patient_id": str(patient_in_db),
                    "message": "Test message",
                },
                headers=auth_headers,
            )

            assert response.status_code == 500

            # Verify cleanup was still called
            mock_graph.close.assert_called_once()
            mock_embedding.close.assert_called_once()
            mock_agent.close.assert_called_once()


# =============================================================================
# Streaming Endpoint Tests
# =============================================================================


def _parse_sse_events(body: str) -> list[dict]:
    """Parse SSE event stream body into list of {event, data} dicts."""
    events = []
    for block in body.strip().split("\n\n"):
        event = {}
        for line in block.strip().split("\n"):
            if line.startswith("event: "):
                event["event"] = line[7:]
            elif line.startswith("data: "):
                event["data"] = json.loads(line[6:])
        if event:
            events.append(event)
    return events


async def _mock_stream_generator():
    """Mock async generator yielding reasoning, narrative, and done events."""
    yield ("reasoning", json.dumps({"delta": "Thinking..."}))
    yield ("narrative", json.dumps({"delta": "The patient"}))
    yield ("narrative", json.dumps({"delta": " has diabetes."}))
    yield ("done", AgentResponse(
        narrative="The patient has diabetes.",
        insights=[],
        follow_ups=[],
    ).model_dump_json())


class TestChatStream:
    """Tests for the POST /api/chat/stream SSE endpoint."""

    @pytest.mark.asyncio
    async def test_stream_patient_not_found_returns_404(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test that non-existent patient returns 404 (before streaming starts)."""
        response = await client.post(
            "/api/chat/stream",
            json={
                "patient_id": str(uuid.uuid4()),
                "message": "Tell me about this patient",
            },
            headers=auth_headers,
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_stream_success_emits_sse_events(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_patient_context: PatientContext,
    ):
        """Test successful streaming returns reasoning, narrative, and done SSE events."""
        with patch("app.routes.chat.ContextEngine") as mock_ce_cls, \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls, \
             patch("app.routes.chat.EmbeddingService") as mock_emb_cls, \
             patch("app.routes.chat.VectorSearchService"):

            mock_graph_cls.return_value = AsyncMock()
            mock_emb_cls.return_value = AsyncMock()

            mock_ce = AsyncMock()
            mock_ce.build_context_with_patient = AsyncMock(return_value=sample_patient_context)
            mock_ce_cls.return_value = mock_ce

            mock_agent = AsyncMock()
            mock_agent.generate_response_stream = MagicMock(return_value=_mock_stream_generator())
            mock_agent_cls.return_value = mock_agent

            response = await client.post(
                "/api/chat/stream",
                json={
                    "patient_id": str(patient_in_db),
                    "message": "Tell me about this patient",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            assert response.headers["content-type"].startswith("text/event-stream")

            events = _parse_sse_events(response.text)
            event_types = [e["event"] for e in events]

            assert "reasoning" in event_types
            assert "narrative" in event_types
            assert "done" in event_types

            # Verify done event contains conversation_id and response
            done_event = next(e for e in events if e["event"] == "done")
            assert "conversation_id" in done_event["data"]
            assert "response" in done_event["data"]
            assert done_event["data"]["response"]["narrative"] == "The patient has diabetes."

    @pytest.mark.asyncio
    async def test_stream_error_emits_error_event(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_patient_context: PatientContext,
    ):
        """Test that errors during streaming emit an error SSE event."""

        async def _failing_stream():
            yield ("reasoning", json.dumps({"delta": "Thinking..."}))
            raise RuntimeError("LLM crashed")

        with patch("app.routes.chat.ContextEngine") as mock_ce_cls, \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls, \
             patch("app.routes.chat.EmbeddingService") as mock_emb_cls, \
             patch("app.routes.chat.VectorSearchService"):

            mock_graph_cls.return_value = AsyncMock()
            mock_emb_cls.return_value = AsyncMock()

            mock_ce = AsyncMock()
            mock_ce.build_context_with_patient = AsyncMock(return_value=sample_patient_context)
            mock_ce_cls.return_value = mock_ce

            mock_agent = AsyncMock()
            mock_agent.generate_response_stream = MagicMock(return_value=_failing_stream())
            mock_agent_cls.return_value = mock_agent

            response = await client.post(
                "/api/chat/stream",
                json={
                    "patient_id": str(patient_in_db),
                    "message": "Tell me about this patient",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200
            events = _parse_sse_events(response.text)
            event_types = [e["event"] for e in events]

            assert "error" in event_types
            error_event = next(e for e in events if e["event"] == "error")
            assert "detail" in error_event["data"]

    @pytest.mark.asyncio
    async def test_stream_cleans_up_services(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_patient_context: PatientContext,
    ):
        """Test that services are cleaned up after streaming completes."""
        with patch("app.routes.chat.ContextEngine") as mock_ce_cls, \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls, \
             patch("app.routes.chat.EmbeddingService") as mock_emb_cls, \
             patch("app.routes.chat.VectorSearchService"):

            mock_graph = AsyncMock()
            mock_graph_cls.return_value = mock_graph

            mock_emb = AsyncMock()
            mock_emb_cls.return_value = mock_emb

            mock_ce = AsyncMock()
            mock_ce.build_context_with_patient = AsyncMock(return_value=sample_patient_context)
            mock_ce_cls.return_value = mock_ce

            mock_agent = AsyncMock()
            mock_agent.generate_response_stream = MagicMock(return_value=_mock_stream_generator())
            mock_agent_cls.return_value = mock_agent

            await client.post(
                "/api/chat/stream",
                json={
                    "patient_id": str(patient_in_db),
                    "message": "Tell me about this patient",
                },
                headers=auth_headers,
            )

            mock_graph.close.assert_called_once()
            mock_emb.close.assert_called_once()
            mock_agent.close.assert_called_once()
