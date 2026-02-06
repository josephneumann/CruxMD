"""Tests for the Chat API endpoints.

Tests the POST /api/chat and POST /api/chat/stream endpoints covering:
- Authentication (API key validation)
- Request validation
- Patient existence checks
- Integration with compiled summary pipeline and AgentService
- Error handling
- SSE streaming
"""

import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.models import FhirResource
from app.schemas import AgentResponse, FollowUp, Insight


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
def sample_compiled_summary() -> dict:
    """Sample compiled patient summary for mocking."""
    return {
        "patient_orientation": "John Doe, Male, DOB 1960-05-15 (age 65)",
        "compilation_date": "2026-02-06",
        "tier1_active_conditions": [],
        "tier1_unlinked_medications": [],
        "tier1_allergies": [{"note": "None recorded"}],
        "tier1_immunizations": [],
        "tier1_care_plans": [],
        "tier2_recent_encounters": [],
        "tier3_latest_observations": {},
        "safety_constraints": {
            "active_allergies": [{"note": "None recorded"}],
            "drug_interactions_note": "Review active medications for potential interactions.",
        },
    }


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


def _chat_patches():
    """Return the standard set of patches for the v2 chat flow."""
    return {
        "get_compiled_summary": patch("app.routes.chat.get_compiled_summary"),
        "compile_and_store": patch("app.routes.chat.compile_and_store"),
        "build_system_prompt_v2": patch("app.routes.chat.build_system_prompt_v2"),
        "agent_service": patch("app.routes.chat.AgentService"),
        "knowledge_graph": patch("app.routes.chat.KnowledgeGraph"),
    }


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
        sample_compiled_summary: dict,
    ):
        """Test successful chat with minimal request."""
        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=sample_compiled_summary), \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt") as mock_prompt, \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph_cls.return_value = AsyncMock()

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_cls.return_value = mock_agent

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

            # Verify build_system_prompt_v2 was called with compiled summary
            mock_prompt.assert_called_once()
            call_args = mock_prompt.call_args
            assert call_args[0][0] == sample_compiled_summary

    @pytest.mark.asyncio
    async def test_chat_generates_conversation_id_when_not_provided(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_agent_response: AgentResponse,
        sample_compiled_summary: dict,
    ):
        """Test that conversation_id is generated when not provided."""
        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=sample_compiled_summary), \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph_cls.return_value = AsyncMock()

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_cls.return_value = mock_agent

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
        sample_compiled_summary: dict,
    ):
        """Test that provided conversation_id is used."""
        provided_conversation_id = uuid.uuid4()

        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=sample_compiled_summary), \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph_cls.return_value = AsyncMock()

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_cls.return_value = mock_agent

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
        sample_compiled_summary: dict,
    ):
        """Test chat with conversation history."""
        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=sample_compiled_summary), \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph_cls.return_value = AsyncMock()

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_cls.return_value = mock_agent

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
# On-Demand Compilation Tests
# =============================================================================


class TestChatOnDemandCompilation:
    """Tests for on-demand compilation fallback when no cached summary exists."""

    @pytest.mark.asyncio
    async def test_chat_compiles_on_demand_when_no_cached_summary(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_agent_response: AgentResponse,
        sample_compiled_summary: dict,
    ):
        """Test that compile_and_store is called when get_compiled_summary returns None."""
        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=None) as mock_get, \
             patch("app.routes.chat.compile_and_store", new_callable=AsyncMock, return_value=sample_compiled_summary) as mock_compile, \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph_cls.return_value = AsyncMock()

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_cls.return_value = mock_agent

            response = await client.post(
                "/api/chat",
                json={
                    "patient_id": str(patient_in_db),
                    "message": "What medications is this patient taking?",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

            # Verify get_compiled_summary was called first
            mock_get.assert_called_once()

            # Verify compile_and_store was called as fallback
            mock_compile.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_skips_compilation_when_cached_summary_exists(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_agent_response: AgentResponse,
        sample_compiled_summary: dict,
    ):
        """Test that compile_and_store is NOT called when cached summary exists."""
        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=sample_compiled_summary) as mock_get, \
             patch("app.routes.chat.compile_and_store", new_callable=AsyncMock) as mock_compile, \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph_cls.return_value = AsyncMock()

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_cls.return_value = mock_agent

            response = await client.post(
                "/api/chat",
                json={
                    "patient_id": str(patient_in_db),
                    "message": "What medications is this patient taking?",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

            # Verify get_compiled_summary was called
            mock_get.assert_called_once()

            # Verify compile_and_store was NOT called
            mock_compile.assert_not_called()


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
        sample_compiled_summary: dict,
    ):
        """Test that RuntimeError from agent returns 500."""
        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=sample_compiled_summary), \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph_cls.return_value = AsyncMock()

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(
                side_effect=RuntimeError("LLM response could not be parsed")
            )
            mock_agent_cls.return_value = mock_agent

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
        sample_compiled_summary: dict,
    ):
        """Test that ValueError from agent returns 400."""
        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=sample_compiled_summary), \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph_cls.return_value = AsyncMock()

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(
                side_effect=ValueError("message cannot be empty")
            )
            mock_agent_cls.return_value = mock_agent

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
        sample_compiled_summary: dict,
    ):
        """Test that messages at max length are accepted."""
        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=sample_compiled_summary), \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph_cls.return_value = AsyncMock()

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_cls.return_value = mock_agent

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
    async def test_chat_loads_compiled_summary_for_patient(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_agent_response: AgentResponse,
        sample_compiled_summary: dict,
    ):
        """Test that get_compiled_summary is called with the correct patient_id."""
        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=sample_compiled_summary) as mock_get, \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph_cls.return_value = AsyncMock()

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_cls.return_value = mock_agent

            response = await client.post(
                "/api/chat",
                json={
                    "patient_id": str(patient_in_db),
                    "message": "What medications is this patient taking?",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

            # Verify get_compiled_summary was called with the patient_id
            mock_get.assert_called_once()
            call_args = mock_get.call_args
            assert call_args[0][0] == patient_in_db

    @pytest.mark.asyncio
    async def test_chat_passes_system_prompt_to_agent(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_agent_response: AgentResponse,
        sample_compiled_summary: dict,
    ):
        """Test that AgentService receives the system_prompt and patient_id."""
        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=sample_compiled_summary), \
             patch("app.routes.chat.build_system_prompt_v2", return_value="test system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph_cls.return_value = AsyncMock()

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_cls.return_value = mock_agent

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
            assert call_kwargs["system_prompt"] == "test system prompt"
            assert call_kwargs["patient_id"] == str(patient_in_db)
            assert call_kwargs["message"] == test_message
            assert call_kwargs["history"] is None

    @pytest.mark.asyncio
    async def test_chat_cleans_up_services_on_success(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_agent_response: AgentResponse,
        sample_compiled_summary: dict,
    ):
        """Test that services are cleaned up after successful request."""
        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=sample_compiled_summary), \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph = AsyncMock()
            mock_graph_cls.return_value = mock_graph

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_cls.return_value = mock_agent

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
            mock_agent.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_cleans_up_services_on_error(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_compiled_summary: dict,
    ):
        """Test that services are cleaned up even on error."""
        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=sample_compiled_summary), \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph = AsyncMock()
            mock_graph_cls.return_value = mock_graph

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(
                side_effect=RuntimeError("LLM error")
            )
            mock_agent_cls.return_value = mock_agent

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
            mock_agent.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_chat_passes_graph_and_db_to_agent_for_tools(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_agent_response: AgentResponse,
        sample_compiled_summary: dict,
    ):
        """Test that graph and db are passed to agent for tool execution."""
        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=sample_compiled_summary), \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph = AsyncMock()
            mock_graph_cls.return_value = mock_graph

            mock_agent = AsyncMock()
            mock_agent.generate_response = AsyncMock(return_value=sample_agent_response)
            mock_agent_cls.return_value = mock_agent

            response = await client.post(
                "/api/chat",
                json={
                    "patient_id": str(patient_in_db),
                    "message": "Test message",
                },
                headers=auth_headers,
            )

            assert response.status_code == 200

            # Verify graph and db were passed to agent
            call_kwargs = mock_agent.generate_response.call_args.kwargs
            assert call_kwargs["graph"] is mock_graph
            assert call_kwargs["db"] is not None


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
        sample_compiled_summary: dict,
    ):
        """Test successful streaming returns reasoning, narrative, and done SSE events."""
        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=sample_compiled_summary), \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph_cls.return_value = AsyncMock()

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
        sample_compiled_summary: dict,
    ):
        """Test that errors during streaming emit an error SSE event."""

        async def _failing_stream():
            yield ("reasoning", json.dumps({"delta": "Thinking..."}))
            raise RuntimeError("LLM crashed")

        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=sample_compiled_summary), \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph_cls.return_value = AsyncMock()

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
        sample_compiled_summary: dict,
    ):
        """Test that services are cleaned up after streaming completes."""
        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=sample_compiled_summary), \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph = AsyncMock()
            mock_graph_cls.return_value = mock_graph

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
            mock_agent.close.assert_called_once()

    @pytest.mark.asyncio
    async def test_stream_on_demand_compilation(
        self,
        client: AsyncClient,
        auth_headers: dict,
        patient_in_db: uuid.UUID,
        sample_compiled_summary: dict,
    ):
        """Test that streaming also triggers on-demand compilation when needed."""
        with patch("app.routes.chat.get_compiled_summary", new_callable=AsyncMock, return_value=None) as mock_get, \
             patch("app.routes.chat.compile_and_store", new_callable=AsyncMock, return_value=sample_compiled_summary) as mock_compile, \
             patch("app.routes.chat.build_system_prompt_v2", return_value="system prompt"), \
             patch("app.routes.chat.AgentService") as mock_agent_cls, \
             patch("app.routes.chat.KnowledgeGraph") as mock_graph_cls:

            mock_graph_cls.return_value = AsyncMock()

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

            # Verify on-demand compilation happened
            mock_get.assert_called_once()
            mock_compile.assert_called_once()
