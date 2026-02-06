"""Tests for the Agent Service.

Tests LLM agent service with mocked OpenAI client to avoid real API calls.
"""

import base64
import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas import AgentResponse, FollowUp, Insight
from app.services.agent import (
    AgentService,
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_MAX_OUTPUT_TOKENS,
    build_system_prompt_v2,
    _format_tier1_conditions,
    _format_tier2_encounters,
    _format_tier3_observations,
    _format_safety_constraints_v2,
    _get_display_name,
    _prune_fhir_resource,
)
from app.services.agent_tools import TOOL_SCHEMAS, execute_tool


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def patient_id() -> str:
    """Generate a unique patient ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_patient() -> dict:
    """Sample FHIR Patient resource."""
    return {
        "resourceType": "Patient",
        "id": "patient-123",
        "name": [{"given": ["John", "Michael"], "family": "Doe"}],
        "birthDate": "1960-05-15",
        "gender": "male",
    }


@pytest.fixture
def sample_condition() -> dict:
    """Sample FHIR Condition resource."""
    return {
        "resourceType": "Condition",
        "id": "condition-456",
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "44054006",
                    "display": "Type 2 diabetes mellitus",
                }
            ]
        },
        "clinicalStatus": {"coding": [{"code": "active"}]},
    }


@pytest.fixture
def sample_medication() -> dict:
    """Sample FHIR MedicationRequest resource."""
    return {
        "resourceType": "MedicationRequest",
        "id": "med-789",
        "medicationCodeableConcept": {
            "coding": [
                {
                    "system": "http://www.nlm.nih.gov/research/umls/rxnorm",
                    "code": "860975",
                    "display": "Metformin 500 MG",
                }
            ]
        },
        "status": "active",
    }


@pytest.fixture
def sample_allergy() -> dict:
    """Sample FHIR AllergyIntolerance resource."""
    return {
        "resourceType": "AllergyIntolerance",
        "id": "allergy-101",
        "code": {
            "coding": [
                {
                    "system": "http://snomed.info/sct",
                    "code": "764146007",
                    "display": "Penicillin",
                }
            ]
        },
        "clinicalStatus": {"coding": [{"code": "active"}]},
        "category": ["medication"],
        "criticality": "high",
    }


@pytest.fixture
def sample_observation() -> dict:
    """Sample FHIR Observation resource."""
    return {
        "resourceType": "Observation",
        "id": "obs-202",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "4548-4",
                    "display": "Hemoglobin A1c",
                }
            ]
        },
        "valueQuantity": {"value": 7.2, "unit": "%"},
    }


@pytest.fixture
def system_prompt() -> str:
    """Pre-built system prompt for testing (replaces PatientContext)."""
    return "You are a clinical reasoning assistant. Patient: John Doe, DOB 1960-05-15."


def create_mock_agent_response() -> AgentResponse:
    """Create a sample AgentResponse for mocking."""
    return AgentResponse(
        narrative="This patient has Type 2 diabetes mellitus.",
        insights=[
            Insight(
                type="info",
                title="HbA1c Level",
                content="Recent HbA1c is above target.",
            ),
        ],
        follow_ups=[
            FollowUp(question="What is the patient's blood pressure trend?", intent="vitals"),
        ],
    )


def create_mock_openai_client(response: AgentResponse | None = None) -> AsyncMock:
    """Create a mock AsyncOpenAI client that returns a structured response."""
    mock_client = AsyncMock()

    if response is None:
        response = create_mock_agent_response()

    mock_response = MagicMock()
    mock_response.output_parsed = response
    mock_response.output_text = response.model_dump_json()

    mock_client.responses.parse = AsyncMock(return_value=mock_response)

    return mock_client


# =============================================================================
# Helper Function Tests
# =============================================================================


class TestGetDisplayName:
    """Tests for _get_display_name helper."""

    def test_extracts_from_coding(self, sample_condition: dict):
        """Test extracting display from coding array."""
        result = _get_display_name(sample_condition)
        assert result == "Type 2 diabetes mellitus"

    def test_falls_back_to_text(self):
        """Test falling back to text field."""
        resource = {"code": {"text": "Hypertension"}}
        result = _get_display_name(resource)
        assert result == "Hypertension"

    def test_returns_none_for_empty(self):
        """Test returning None for empty resource."""
        result = _get_display_name({})
        assert result is None

    def test_custom_code_field(self, sample_medication: dict):
        """Test using custom code field."""
        result = _get_display_name(sample_medication, "medicationCodeableConcept")
        assert result == "Metformin 500 MG"


# =============================================================================
# AgentService Tests
# =============================================================================


class TestAgentServiceInit:
    """Tests for AgentService initialization."""

    def test_init_with_defaults(self):
        """Test initialization with default settings."""
        with patch("app.services.agent.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            with patch("app.services.agent.AsyncOpenAI") as mock_openai:
                service = AgentService()

                assert service._model == DEFAULT_MODEL
                assert service._reasoning_effort == DEFAULT_REASONING_EFFORT
                assert service._max_output_tokens == DEFAULT_MAX_OUTPUT_TOKENS
                mock_openai.assert_called_once()

    def test_init_with_custom_client(self):
        """Test initialization with custom client."""
        mock_client = AsyncMock()
        service = AgentService(client=mock_client)

        assert service._client is mock_client

    def test_init_with_custom_model(self):
        """Test initialization with custom model."""
        mock_client = AsyncMock()
        service = AgentService(client=mock_client, model="gpt-5")

        assert service._model == "gpt-5"

    def test_init_with_custom_reasoning_effort(self):
        """Test initialization with custom reasoning effort."""
        mock_client = AsyncMock()
        service = AgentService(client=mock_client, reasoning_effort="high")

        assert service._reasoning_effort == "high"

    def test_init_without_api_key_raises(self):
        """Test that missing API key raises ValueError."""
        with patch("app.services.agent.settings") as mock_settings:
            mock_settings.openai_api_key = ""

            with pytest.raises(ValueError, match="OPENAI_API_KEY"):
                AgentService()


class TestAgentServiceGenerateResponse:
    """Tests for AgentService.generate_response method."""

    @pytest.mark.asyncio
    async def test_generate_response_basic(self, system_prompt: str, patient_id: str):
        """Test basic response generation."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client)

        response = await service.generate_response(
            system_prompt=system_prompt, patient_id=patient_id,
            message="What medications is this patient taking?",
        )

        assert isinstance(response, AgentResponse)
        assert response.narrative is not None
        assert len(response.narrative) > 0
        mock_client.responses.parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_with_history(self, system_prompt: str, patient_id: str):
        """Test response generation with conversation history."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client)

        history = [
            {"role": "user", "content": "Tell me about this patient"},
            {"role": "assistant", "content": "This is a 65-year-old male..."},
        ]

        response = await service.generate_response(
            system_prompt=system_prompt, patient_id=patient_id,
            message="What about their medications?",
            history=history,
        )

        assert isinstance(response, AgentResponse)

        call_args = mock_client.responses.parse.call_args
        input_messages = call_args.kwargs["input"]
        assert len(input_messages) == 4  # system + 2 history + current

    @pytest.mark.asyncio
    async def test_generate_response_empty_message_raises(self, system_prompt: str, patient_id: str):
        """Test that empty message raises ValueError."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client)

        with pytest.raises(ValueError, match="message cannot be empty"):
            await service.generate_response(system_prompt=system_prompt, patient_id=patient_id, message="")

    @pytest.mark.asyncio
    async def test_generate_response_whitespace_message_raises(self, system_prompt: str, patient_id: str):
        """Test that whitespace-only message raises ValueError."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client)

        with pytest.raises(ValueError, match="message cannot be empty"):
            await service.generate_response(system_prompt=system_prompt, patient_id=patient_id, message="   ")

    @pytest.mark.asyncio
    async def test_generate_response_reasoning_effort_override(self, system_prompt: str, patient_id: str):
        """Test overriding reasoning effort for a single call."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client, reasoning_effort="low")

        await service.generate_response(
            system_prompt=system_prompt, patient_id=patient_id,
            message="Complex question",
            reasoning_effort="high",
        )

        call_args = mock_client.responses.parse.call_args
        reasoning = call_args.kwargs["reasoning"]
        effort = getattr(reasoning, "effort", None) or reasoning.get("effort")
        assert effort == "high"

    @pytest.mark.asyncio
    async def test_generate_response_uses_correct_model(self, system_prompt: str, patient_id: str):
        """Test that correct model is passed to API."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client, model="gpt-5.2-preview")

        await service.generate_response(
            system_prompt=system_prompt, patient_id=patient_id,
            message="Test question",
        )

        call_args = mock_client.responses.parse.call_args
        assert call_args.kwargs["model"] == "gpt-5.2-preview"

    @pytest.mark.asyncio
    async def test_generate_response_uses_text_format(self, system_prompt: str, patient_id: str):
        """Test that AgentResponse is passed as text_format."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client)

        await service.generate_response(
            system_prompt=system_prompt, patient_id=patient_id,
            message="Test question",
        )

        call_args = mock_client.responses.parse.call_args
        assert call_args.kwargs["text_format"] is AgentResponse

    @pytest.mark.asyncio
    async def test_generate_response_includes_max_tokens(self, system_prompt: str, patient_id: str):
        """Test that max_output_tokens is passed to API."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client, max_output_tokens=2048)

        await service.generate_response(
            system_prompt=system_prompt, patient_id=patient_id,
            message="Test question",
        )

        call_args = mock_client.responses.parse.call_args
        assert call_args.kwargs["max_output_tokens"] == 2048

    @pytest.mark.asyncio
    async def test_generate_response_fallback_on_none(self, system_prompt: str, patient_id: str):
        """Test fallback when structured parsing returns None but raw text available."""
        mock_client = AsyncMock()

        expected_response = create_mock_agent_response()
        mock_response = MagicMock()
        mock_response.output_parsed = None
        mock_response.output_text = expected_response.model_dump_json()

        mock_client.responses.parse = AsyncMock(return_value=mock_response)

        service = AgentService(client=mock_client)

        response = await service.generate_response(
            system_prompt=system_prompt, patient_id=patient_id,
            message="Test question",
        )

        assert isinstance(response, AgentResponse)
        assert response.narrative == expected_response.narrative

    @pytest.mark.asyncio
    async def test_generate_response_raises_on_parse_failure(self, system_prompt: str, patient_id: str):
        """Test that RuntimeError is raised when all parsing fails."""
        mock_client = AsyncMock()

        mock_response = MagicMock()
        mock_response.output_parsed = None
        mock_response.output_text = None

        mock_client.responses.parse = AsyncMock(return_value=mock_response)

        service = AgentService(client=mock_client)

        with pytest.raises(RuntimeError, match="LLM response could not be parsed"):
            await service.generate_response(
                system_prompt=system_prompt, patient_id=patient_id,
                message="Test question",
            )

    @pytest.mark.asyncio
    async def test_generate_response_filters_invalid_history(self, system_prompt: str, patient_id: str):
        """Test that invalid history entries are filtered."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client)

        history = [
            {"role": "user", "content": "Valid message"},
            {"role": "system", "content": "Should be ignored"},
            {"role": "assistant", "content": ""},
            {"role": "assistant", "content": "Valid assistant message"},
        ]

        await service.generate_response(
            system_prompt=system_prompt, patient_id=patient_id,
            message="Current question",
            history=history,
        )

        call_args = mock_client.responses.parse.call_args
        input_messages = call_args.kwargs["input"]

        # system + 2 valid history + current = 4
        assert len(input_messages) == 4


def create_mock_stream(response: AgentResponse | None = None):
    """Create a mock stream context manager with reasoning and text delta events."""
    if response is None:
        response = create_mock_agent_response()

    reasoning_event = MagicMock()
    reasoning_event.type = "response.reasoning_summary_text.delta"
    reasoning_event.delta = "thinking about diabetes"

    text_event = MagicMock()
    text_event.type = "response.output_text.delta"
    text_event.delta = "The patient has diabetes."

    # Build the async iterator for events
    async def mock_aiter(self):
        yield reasoning_event
        yield text_event

    mock_final = MagicMock()
    mock_final.output_parsed = response
    mock_final.output_text = response.model_dump_json()

    stream = AsyncMock()
    stream.__aiter__ = mock_aiter
    stream.get_final_response = AsyncMock(return_value=mock_final)

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=stream)
    ctx.__aexit__ = AsyncMock(return_value=False)

    return ctx


class TestAgentServiceGenerateResponseStream:
    """Tests for AgentService.generate_response_stream method."""

    @pytest.mark.asyncio
    async def test_stream_yields_reasoning_and_narrative(self, system_prompt: str, patient_id: str):
        """Test that stream yields reasoning and narrative deltas then done."""
        mock_client = AsyncMock()
        expected = create_mock_agent_response()
        mock_client.responses.stream = MagicMock(return_value=create_mock_stream(expected))

        service = AgentService(client=mock_client)

        events = []
        async for event_type, data in service.generate_response_stream(
            system_prompt=system_prompt, patient_id=patient_id,
            message="What about diabetes?",
        ):
            events.append((event_type, data))

        assert events[0][0] == "reasoning"
        assert json.loads(events[0][1])["delta"] == "thinking about diabetes"

        assert events[1][0] == "narrative"
        assert json.loads(events[1][1])["delta"] == "The patient has diabetes."

        assert events[2][0] == "done"
        done_data = AgentResponse.model_validate_json(events[2][1])
        assert done_data.narrative == expected.narrative

    @pytest.mark.asyncio
    async def test_stream_empty_message_raises(self, system_prompt: str, patient_id: str):
        """Test that empty message raises ValueError."""
        mock_client = AsyncMock()
        service = AgentService(client=mock_client)

        with pytest.raises(ValueError, match="message cannot be empty"):
            async for _ in service.generate_response_stream(
                system_prompt=system_prompt, patient_id=patient_id, message=""
            ):
                pass

    @pytest.mark.asyncio
    async def test_stream_passes_correct_kwargs(self, system_prompt: str, patient_id: str):
        """Test that stream call uses same params as generate_response."""
        mock_client = AsyncMock()
        mock_client.responses.stream = MagicMock(
            return_value=create_mock_stream()
        )

        service = AgentService(client=mock_client, model="gpt-5.2-preview", reasoning_effort="high")

        async for _ in service.generate_response_stream(
            system_prompt=system_prompt, patient_id=patient_id,
            message="Test question",
        ):
            pass

        call_args = mock_client.responses.stream.call_args
        assert call_args.kwargs["model"] == "gpt-5.2-preview"
        assert call_args.kwargs["text_format"] is AgentResponse
        reasoning = call_args.kwargs["reasoning"]
        effort = getattr(reasoning, "effort", None) or reasoning.get("effort")
        assert effort == "high"

    @pytest.mark.asyncio
    async def test_stream_fallback_on_none_parsed(self, system_prompt: str, patient_id: str):
        """Test fallback when structured parsing returns None."""
        mock_client = AsyncMock()
        expected = create_mock_agent_response()

        ctx = create_mock_stream(expected)
        # Make output_parsed None on the final response
        stream_obj = await ctx.__aenter__()
        final = await stream_obj.get_final_response()
        final.output_parsed = None
        final.output_text = expected.model_dump_json()

        mock_client.responses.stream = MagicMock(return_value=ctx)

        service = AgentService(client=mock_client)

        events = []
        async for event_type, data in service.generate_response_stream(
            system_prompt=system_prompt, patient_id=patient_id,
            message="Test",
        ):
            events.append((event_type, data))

        done_events = [e for e in events if e[0] == "done"]
        assert len(done_events) == 1
        parsed = AgentResponse.model_validate_json(done_events[0][1])
        assert parsed.narrative == expected.narrative


class TestAgentServiceClose:
    """Tests for AgentService.close method."""

    @pytest.mark.asyncio
    async def test_close_calls_client_close(self):
        """Test that close calls the underlying client close."""
        mock_client = AsyncMock()
        service = AgentService(client=mock_client)

        await service.close()

        mock_client.close.assert_called_once()


# =============================================================================
# Tool Schema Tests
# =============================================================================


class TestToolSchemas:
    """Tests for TOOL_SCHEMAS definitions."""

    def test_all_tools_defined(self):
        """Test that all 3 tool schemas are defined."""
        assert len(TOOL_SCHEMAS) == 3

    def test_tool_names(self):
        """Test that tool names match the function names."""
        names = {t["name"] for t in TOOL_SCHEMAS}
        assert names == {
            "query_patient_data",
            "explore_connections",
            "get_patient_timeline",
        }

    def test_all_schemas_have_required_fields(self):
        """Test that each schema has type, name, description, parameters."""
        for schema in TOOL_SCHEMAS:
            assert schema["type"] == "function"
            assert "name" in schema
            assert "description" in schema
            assert "parameters" in schema
            assert schema["parameters"]["type"] == "object"


# =============================================================================
# Tool Execution Tests
# =============================================================================


class TestExecuteTool:
    """Tests for execute_tool dispatch function."""

    @pytest.mark.asyncio
    async def test_dispatch_query_patient_data(self):
        """Test that execute_tool dispatches to query_patient_data."""
        mock_graph = AsyncMock()
        mock_db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_db.execute.return_value = mock_result

        result = await execute_tool(
            name="query_patient_data",
            arguments='{"name": "diabetes", "resource_type": null, "status": null, "category": null, "date_from": null, "date_to": null, "include_full_resource": true, "limit": 20}',
            patient_id="patient-123",
            graph=mock_graph,
            db=mock_db,
        )

        parsed = json.loads(result)
        assert parsed["total"] == 0

    @pytest.mark.asyncio
    async def test_dispatch_unknown_tool(self):
        """Test that unknown tool returns error message."""
        result = await execute_tool(
            name="nonexistent_tool",
            arguments="{}",
            patient_id="patient-123",
            graph=AsyncMock(),
            db=AsyncMock(),
        )

        assert "Unknown tool" in result


# =============================================================================
# Tool-Use Loop Tests
# =============================================================================


def _make_function_call_item(name: str, arguments: str, call_id: str = "call_1"):
    """Create a mock function_call output item."""
    item = MagicMock()
    item.type = "function_call"
    item.name = name
    item.arguments = arguments
    item.call_id = call_id
    return item


def _make_text_item():
    """Create a mock text output item."""
    item = MagicMock()
    item.type = "message"
    return item


def create_mock_openai_client_with_tools(
    tool_responses: list[list] | None = None,
    final_response: AgentResponse | None = None,
):
    """Create a mock client that returns tool calls then a final text response.

    Args:
        tool_responses: List of lists of function_call items for each round.
        final_response: The final AgentResponse after tool calls complete.
    """
    if final_response is None:
        final_response = create_mock_agent_response()

    mock_client = AsyncMock()
    responses = []

    # Tool call rounds
    for tool_calls in (tool_responses or []):
        mock_resp = MagicMock()
        mock_resp.output = tool_calls
        mock_resp.output_parsed = None
        responses.append(mock_resp)

    # Final text response
    final_mock = MagicMock()
    final_mock.output = [_make_text_item()]
    final_mock.output_parsed = final_response
    final_mock.output_text = final_response.model_dump_json()
    responses.append(final_mock)

    mock_client.responses.parse = AsyncMock(side_effect=responses)

    return mock_client


class TestToolUseLoop:
    """Tests for the tool-use loop in generate_response."""

    @pytest.mark.asyncio
    async def test_no_tools_when_graph_db_absent(self, system_prompt: str, patient_id: str):
        """Test that tools are not passed when graph/db not provided."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client)

        await service.generate_response(
            system_prompt=system_prompt, patient_id=patient_id,
            message="What medications?",
        )

        call_args = mock_client.responses.parse.call_args
        assert "tools" not in call_args.kwargs

    @pytest.mark.asyncio
    async def test_tools_passed_when_graph_db_provided(self, system_prompt: str, patient_id: str):
        """Test that tools are passed when graph and db are provided."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client)

        await service.generate_response(
            system_prompt=system_prompt, patient_id=patient_id,
            message="What medications?",
            graph=AsyncMock(),
            db=AsyncMock(),
        )

        # First .parse() call (inside _execute_tool_calls) should include tools
        first_call = mock_client.responses.parse.call_args_list[0]
        assert first_call.kwargs["tools"] is TOOL_SCHEMAS

    @pytest.mark.asyncio
    @patch("app.services.agent.execute_tool", new_callable=AsyncMock)
    async def test_single_tool_call_round(
        self, mock_execute, system_prompt: str, patient_id: str
    ):
        """Test that a single tool call is executed and result fed back."""
        mock_execute.return_value = "Search results: diabetes found"

        tool_call = _make_function_call_item(
            "query_patient_data", '{"name": "diabetes", "resource_type": null, "status": null, "category": null, "date_from": null, "date_to": null, "include_full_resource": true, "limit": 20}'
        )
        mock_client = create_mock_openai_client_with_tools(
            tool_responses=[[tool_call]],
        )
        service = AgentService(client=mock_client)

        response = await service.generate_response(
            system_prompt=system_prompt, patient_id=patient_id,
            message="Tell me about diabetes",
            graph=AsyncMock(),
            db=AsyncMock(),
        )

        assert isinstance(response, AgentResponse)
        assert mock_client.responses.parse.call_count == 2
        mock_execute.assert_called_once()

        # Verify function_call_output was fed back
        second_call_input = mock_client.responses.parse.call_args_list[1].kwargs["input"]
        outputs = [m for m in second_call_input if isinstance(m, dict) and m.get("type") == "function_call_output"]
        assert len(outputs) == 1
        assert outputs[0]["output"] == "Search results: diabetes found"
        assert outputs[0]["call_id"] == "call_1"

    @pytest.mark.asyncio
    @patch("app.services.agent.execute_tool", new_callable=AsyncMock)
    async def test_multiple_tool_call_rounds(
        self, mock_execute, system_prompt: str, patient_id: str
    ):
        """Test multi-round tool calling."""
        mock_execute.side_effect = ["Round 1 result", "Round 2 result"]

        round1_call = _make_function_call_item(
            "query_patient_data", '{"name": "diabetes", "resource_type": null, "status": null, "category": null, "date_from": null, "date_to": null, "include_full_resource": true, "limit": 20}', "call_r1"
        )
        round2_call = _make_function_call_item(
            "explore_connections", '{"fhir_id": "cond-1", "resource_type": "Condition", "include_full_resource": true, "max_per_relationship": 10}', "call_r2"
        )
        mock_client = create_mock_openai_client_with_tools(
            tool_responses=[[round1_call], [round2_call]],
        )
        service = AgentService(client=mock_client)

        response = await service.generate_response(
            system_prompt=system_prompt, patient_id=patient_id,
            message="Diabetes labs?",
            graph=AsyncMock(),
            db=AsyncMock(),
        )

        assert isinstance(response, AgentResponse)
        assert mock_client.responses.parse.call_count == 3
        assert mock_execute.call_count == 2

    @pytest.mark.asyncio
    @patch("app.services.agent.execute_tool", new_callable=AsyncMock)
    async def test_parallel_tool_calls_in_one_round(
        self, mock_execute, system_prompt: str, patient_id: str
    ):
        """Test multiple tool calls in a single round."""
        mock_execute.side_effect = ["Result A", "Result B"]

        call_a = _make_function_call_item(
            "query_patient_data", '{"name": "diabetes", "resource_type": null, "status": null, "category": null, "date_from": null, "date_to": null, "include_full_resource": true, "limit": 20}', "call_a"
        )
        call_b = _make_function_call_item(
            "explore_connections", '{"fhir_id": "cond-1", "resource_type": "Condition", "include_full_resource": true, "max_per_relationship": 10}', "call_b"
        )
        mock_client = create_mock_openai_client_with_tools(
            tool_responses=[[call_a, call_b]],
        )
        service = AgentService(client=mock_client)

        response = await service.generate_response(
            system_prompt=system_prompt, patient_id=patient_id,
            message="Diabetes overview",
            graph=AsyncMock(),
            db=AsyncMock(),
        )

        assert isinstance(response, AgentResponse)
        assert mock_execute.call_count == 2
        assert mock_client.responses.parse.call_count == 2


class TestToolUseStreamLoop:
    """Tests for tool-use in generate_response_stream."""

    @pytest.mark.asyncio
    async def test_stream_no_tools_when_graph_db_absent(self, system_prompt: str, patient_id: str):
        """Test that streaming without graph/db skips tools entirely."""
        mock_client = AsyncMock()
        mock_client.responses.stream = MagicMock(return_value=create_mock_stream())

        service = AgentService(client=mock_client)

        events = []
        async for et, data in service.generate_response_stream(
            system_prompt=system_prompt, patient_id=patient_id,
            message="What medications?",
        ):
            events.append((et, data))

        # Should have gone through streaming path
        assert any(e[0] == "done" for e in events)
        # .stream() was called, not .parse()
        mock_client.responses.stream.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.agent.execute_tool", new_callable=AsyncMock)
    async def test_stream_with_tool_calls(
        self, mock_execute, system_prompt: str, patient_id: str
    ):
        """Test streaming with tool calls uses parse for tool rounds then streams final."""
        mock_execute.return_value = "Tool result text"

        tool_call = _make_function_call_item(
            "query_patient_data", '{"name": "diabetes", "resource_type": null, "status": null, "category": null, "date_from": null, "date_to": null, "include_full_resource": true, "limit": 20}'
        )

        # First .parse() returns tool call, second returns no tool calls (text ready)
        tool_round_resp = MagicMock()
        tool_round_resp.output = [tool_call]
        tool_round_resp.output_parsed = None

        # Second .parse() returns no tool calls — _execute_tool_calls stops
        no_tool_resp = MagicMock()
        no_tool_resp.output = [_make_text_item()]
        no_tool_resp.output_parsed = None

        mock_client = AsyncMock()
        mock_client.responses.parse = AsyncMock(side_effect=[tool_round_resp, no_tool_resp])

        # Final streaming call returns the response
        final_response = create_mock_agent_response()
        mock_client.responses.stream = MagicMock(return_value=create_mock_stream(final_response))

        service = AgentService(client=mock_client)

        events = []
        async for et, data in service.generate_response_stream(
            system_prompt=system_prompt, patient_id=patient_id,
            message="Diabetes info",
            graph=AsyncMock(),
            db=AsyncMock(),
        ):
            events.append((et, data))

        # Should get tool_call, tool_result, then reasoning, narrative, done
        tool_call_events = [e for e in events if e[0] == "tool_call"]
        tool_result_events = [e for e in events if e[0] == "tool_result"]
        assert len(tool_call_events) == 1
        assert len(tool_result_events) == 1

        tc_data = json.loads(tool_call_events[0][1])
        assert tc_data["name"] == "query_patient_data"
        assert tc_data["call_id"] == "call_1"

        tr_data = json.loads(tool_result_events[0][1])
        assert tr_data["call_id"] == "call_1"
        assert tr_data["output"] == "Tool result text"

        assert any(e[0] == "reasoning" for e in events)
        assert any(e[0] == "narrative" for e in events)
        done_events = [e for e in events if e[0] == "done"]
        assert len(done_events) == 1
        parsed = AgentResponse.model_validate_json(done_events[0][1])
        assert parsed.narrative == final_response.narrative

        mock_execute.assert_called_once()
        # .parse() called for tool rounds, .stream() for final
        assert mock_client.responses.parse.call_count == 2
        mock_client.responses.stream.assert_called_once()


# =============================================================================
# _prune_fhir_resource Tests
# =============================================================================


def _make_document_reference(note_text: str) -> dict:
    """Build a minimal DocumentReference with base64-encoded note text."""
    return {
        "resourceType": "DocumentReference",
        "id": "docref-test",
        "status": "current",
        "content": [
            {
                "attachment": {
                    "contentType": "text/plain",
                    "data": base64.b64encode(note_text.encode("utf-8")).decode("ascii"),
                }
            }
        ],
    }


class TestPruneFhirResourceDocumentReference:
    """Tests for _prune_fhir_resource handling of DocumentReference resources."""

    def test_short_note_preserved(self):
        """Short clinical notes are fully preserved."""
        note = "Patient presents with mild headache."
        resource = _make_document_reference(note)
        pruned = _prune_fhir_resource(resource)
        assert pruned["clinical_note"] == note

    def test_long_note_not_truncated(self):
        """Long clinical notes are fully preserved without truncation."""
        note = "A" * 3000
        resource = _make_document_reference(note)
        pruned = _prune_fhir_resource(resource)
        assert pruned["clinical_note"] == note
        assert len(pruned["clinical_note"]) == 3000
        assert "truncated" not in pruned["clinical_note"]

    def test_raw_content_replaced_by_clinical_note(self):
        """The raw base64 'content' key is dropped when clinical_note is decoded."""
        note = "Decoded note text"
        resource = _make_document_reference(note)
        pruned = _prune_fhir_resource(resource)
        assert "content" not in pruned
        assert pruned["clinical_note"] == note

    def test_non_text_plain_attachment_ignored(self):
        """Attachments with non-text/plain contentType are not decoded."""
        resource = {
            "resourceType": "DocumentReference",
            "id": "docref-pdf",
            "status": "current",
            "content": [
                {
                    "attachment": {
                        "contentType": "application/pdf",
                        "data": base64.b64encode(b"binary").decode("ascii"),
                    }
                }
            ],
        }
        pruned = _prune_fhir_resource(resource)
        assert "clinical_note" not in pruned

    def test_strip_keys_removed(self):
        """Standard FHIR boilerplate keys are stripped from DocumentReferences."""
        resource = _make_document_reference("note")
        resource["meta"] = {"versionId": "1"}
        resource["text"] = {"div": "<div>html</div>"}
        pruned = _prune_fhir_resource(resource)
        assert "meta" not in pruned
        assert "text" not in pruned

    def test_enrichment_fields_pass_through(self):
        """Enrichment fields (_trend, _recency, _inferred, _duration_days) survive pruning."""
        resource = _make_document_reference("note")
        resource["_trend"] = "improving"
        resource["_recency"] = "recent"
        resource["_inferred"] = True
        resource["_duration_days"] = 30
        pruned = _prune_fhir_resource(resource)
        assert pruned["_trend"] == "improving"
        assert pruned["_recency"] == "recent"
        assert pruned["_inferred"] is True
        assert pruned["_duration_days"] == 30


class TestPruneFhirResourceGeneral:
    """Tests for _prune_fhir_resource on non-DocumentReference resources."""

    def test_enrichment_fields_pass_through_on_observation(self):
        """Enrichment fields survive pruning on Observation resources."""
        resource = {
            "resourceType": "Observation",
            "id": "obs-1",
            "status": "final",
            "_trend": "stable",
            "_recency": "old",
            "_inferred": False,
            "_duration_days": 90,
        }
        pruned = _prune_fhir_resource(resource)
        assert pruned["_trend"] == "stable"
        assert pruned["_recency"] == "old"
        assert pruned["_inferred"] is False
        assert pruned["_duration_days"] == 90

    def test_meta_and_text_stripped(self):
        """Standard FHIR boilerplate is stripped from any resource type."""
        resource = {
            "resourceType": "Condition",
            "id": "cond-1",
            "meta": {"versionId": "1"},
            "text": {"div": "<div>html</div>"},
            "identifier": [{"value": "abc"}],
            "clinicalStatus": {
                "coding": [{"code": "active", "display": "Active"}]
            },
        }
        pruned = _prune_fhir_resource(resource)
        assert "meta" not in pruned
        assert "text" not in pruned
        assert "identifier" not in pruned
        assert pruned["clinicalStatus"] == "Active"


# =============================================================================
# build_system_prompt_v2 Tests
# =============================================================================


@pytest.fixture
def minimal_compiled_summary() -> dict:
    """Minimal compiled summary with just patient orientation."""
    return {
        "patient_orientation": "Jane Doe, Female, DOB 1955-03-20 (age 71)",
        "compilation_date": "2026-02-05",
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


@pytest.fixture
def full_compiled_summary() -> dict:
    """Full compiled summary with all tiers populated."""
    return {
        "patient_orientation": "John Smith, Male, DOB 1960-05-15 (age 65)",
        "compilation_date": "2026-02-05",
        "tier1_active_conditions": [
            {
                "condition": {
                    "resourceType": "Condition",
                    "id": "cond-diabetes",
                    "code": {
                        "coding": [{"code": "44054006", "display": "Type 2 diabetes mellitus"}]
                    },
                    "clinicalStatus": "Active",
                    "onsetDateTime": "2015-03-10",
                },
                "treating_medications": [
                    {
                        "resourceType": "MedicationRequest",
                        "id": "med-metformin",
                        "medicationCodeableConcept": "Metformin 500 MG",
                        "status": "active",
                        "_recency": "established",
                        "_duration_days": 3200,
                        "_dose_history": [
                            {"dose": "250 MG", "authoredOn": "2015-03-10", "status": "completed"},
                        ],
                    },
                ],
                "care_plans": [
                    {
                        "resourceType": "CarePlan",
                        "id": "cp-diabetes",
                        "category": "Diabetes self management plan",
                        "status": "active",
                    },
                ],
                "related_procedures": [],
            },
            {
                "condition": {
                    "resourceType": "Condition",
                    "id": "cond-hypertension",
                    "code": {
                        "coding": [{"code": "38341003", "display": "Essential hypertension"}]
                    },
                    "clinicalStatus": "Active",
                    "onsetDateTime": "2018-06-22",
                },
                "treating_medications": [
                    {
                        "resourceType": "MedicationRequest",
                        "id": "med-lisinopril",
                        "medicationCodeableConcept": "Lisinopril 10 MG",
                        "status": "active",
                        "_recency": "established",
                        "_duration_days": 2800,
                        "_inferred": True,
                    },
                ],
                "care_plans": [],
                "related_procedures": [],
            },
        ],
        "tier1_recently_resolved": [
            {
                "condition": {
                    "resourceType": "Condition",
                    "id": "cond-bronchitis",
                    "code": {
                        "coding": [{"code": "10509002", "display": "Acute bronchitis"}]
                    },
                    "clinicalStatus": "resolved",
                },
                "treating_medications": [],
                "care_plans": [],
                "related_procedures": [],
            },
        ],
        "tier1_unlinked_medications": [
            {
                "resourceType": "MedicationRequest",
                "id": "med-aspirin",
                "medicationCodeableConcept": "Aspirin 81 MG",
                "status": "active",
                "_recency": "established",
            },
        ],
        "tier1_allergies": [
            {
                "resourceType": "AllergyIntolerance",
                "id": "allergy-penicillin",
                "code": "Penicillin",
                "criticality": "high",
                "category": "medication",
            },
        ],
        "tier1_immunizations": [
            {
                "resourceType": "Immunization",
                "id": "imm-flu",
                "vaccineCode": "Influenza vaccine",
                "occurrenceDateTime": "2025-10-15",
            },
        ],
        "tier1_care_plans": [
            {
                "resourceType": "CarePlan",
                "id": "cp-wellness",
                "category": "Routine wellness plan",
                "status": "active",
            },
        ],
        "tier2_recent_encounters": [
            {
                "encounter": {
                    "resourceType": "Encounter",
                    "id": "enc-last",
                    "type": "General examination",
                    "class": {"code": "AMB"},
                    "period": {"start": "2026-01-15"},
                },
                "events": {
                    "DIAGNOSED": [
                        {
                            "resourceType": "Condition",
                            "id": "cond-diabetes",
                            "code": {"coding": [{"display": "Type 2 diabetes mellitus"}]},
                        },
                    ],
                    "RECORDED": [
                        {
                            "resourceType": "Observation",
                            "id": "obs-bp",
                            "code": {"coding": [{"display": "Blood pressure panel"}]},
                        },
                    ],
                },
                "clinical_notes": ["Patient reports good adherence to medication regimen."],
            },
        ],
        "tier3_latest_observations": {
            "laboratory": [
                {
                    "resourceType": "Observation",
                    "id": "obs-hba1c",
                    "code": {"coding": [{"code": "4548-4", "display": "Hemoglobin A1c"}]},
                    "valueQuantity": {"value": 7.2, "unit": "%"},
                    "effectiveDateTime": "2026-01-10",
                    "referenceRange": [
                        {"low": {"value": 4.0}, "high": {"value": 5.6}},
                    ],
                    "_trend": {
                        "direction": "rising",
                        "delta": 0.3,
                        "delta_percent": 4.35,
                        "previous_value": 6.9,
                        "previous_date": "2025-07-15",
                        "timespan_days": 179,
                    },
                },
            ],
            "vital-signs": [
                {
                    "resourceType": "Observation",
                    "id": "obs-sys-bp",
                    "code": {"coding": [{"display": "Systolic blood pressure"}]},
                    "valueQuantity": {"value": 138, "unit": "mmHg"},
                    "effectiveDateTime": "2026-01-15",
                },
            ],
            "survey": [],
            "social-history": [],
        },
        "safety_constraints": {
            "active_allergies": [
                {
                    "resourceType": "AllergyIntolerance",
                    "id": "allergy-penicillin",
                    "code": "Penicillin",
                    "criticality": "high",
                    "category": "medication",
                },
            ],
            "drug_interactions_note": "Review active medications for potential interactions.",
        },
    }


class TestBuildSystemPromptV2:
    """Tests for build_system_prompt_v2 function."""

    def test_minimal_summary_includes_role(self, minimal_compiled_summary: dict):
        """Test that v2 prompt includes role/PCP persona."""
        prompt = build_system_prompt_v2(minimal_compiled_summary)
        assert "clinical reasoning assistant" in prompt
        assert "primary care physician" in prompt

    def test_minimal_summary_includes_patient_orientation(self, minimal_compiled_summary: dict):
        """Test that v2 prompt includes patient orientation."""
        prompt = build_system_prompt_v2(minimal_compiled_summary)
        assert "Jane Doe" in prompt
        assert "age 71" in prompt

    def test_minimal_summary_includes_compilation_date(self, minimal_compiled_summary: dict):
        """Test that v2 prompt includes compilation date."""
        prompt = build_system_prompt_v2(minimal_compiled_summary)
        assert "compiled 2026-02-05" in prompt

    def test_minimal_summary_includes_reasoning_directives(self, minimal_compiled_summary: dict):
        """Test that v2 prompt includes reasoning directives."""
        prompt = build_system_prompt_v2(minimal_compiled_summary)
        assert "Reasoning Directives" in prompt
        assert "Absence reporting" in prompt
        assert "Cross-condition reasoning" in prompt
        assert "Tool-chain self-checking" in prompt
        assert "Temporal awareness" in prompt
        assert "Confidence calibration" in prompt

    def test_minimal_summary_includes_tool_guidance(self, minimal_compiled_summary: dict):
        """Test that v2 prompt includes tool descriptions and usage guidance."""
        prompt = build_system_prompt_v2(minimal_compiled_summary)
        assert "query_patient_data" in prompt
        assert "explore_connections" in prompt
        assert "get_patient_timeline" in prompt

    def test_minimal_summary_includes_trend_guidance(self, minimal_compiled_summary: dict):
        """Test that v2 prompt includes explicit _trend limitation guidance."""
        prompt = build_system_prompt_v2(minimal_compiled_summary)
        assert "_trend" in prompt
        assert "ONE previous value" in prompt
        assert "multi-point trend analysis" in prompt.lower()
        assert "query_patient_data" in prompt

    def test_minimal_summary_includes_dose_history_guidance(self, minimal_compiled_summary: dict):
        """Test that v2 prompt includes explicit _dose_history guidance."""
        prompt = build_system_prompt_v2(minimal_compiled_summary)
        assert "_dose_history" in prompt
        assert "dose changes" in prompt
        assert "complete" in prompt.lower()

    def test_minimal_summary_includes_safety(self, minimal_compiled_summary: dict):
        """Test that v2 prompt includes safety constraints section."""
        prompt = build_system_prompt_v2(minimal_compiled_summary)
        assert "Safety Constraints" in prompt
        assert "drug allergies" in prompt
        assert "Never recommend starting, stopping, or changing medications" in prompt

    def test_minimal_summary_includes_response_format(self, minimal_compiled_summary: dict):
        """Test that v2 prompt includes response format guidance."""
        prompt = build_system_prompt_v2(minimal_compiled_summary)
        assert "Response Format" in prompt
        assert "narrative" in prompt
        assert "follow_ups" in prompt

    def test_full_summary_includes_conditions(self, full_compiled_summary: dict):
        """Test that v2 prompt includes active conditions."""
        prompt = build_system_prompt_v2(full_compiled_summary)
        assert "Type 2 diabetes mellitus" in prompt
        assert "Essential hypertension" in prompt
        assert "cond-diabetes" in prompt
        assert "cond-hypertension" in prompt

    def test_full_summary_includes_treating_medications(self, full_compiled_summary: dict):
        """Test that v2 prompt includes treating medications with enrichments."""
        prompt = build_system_prompt_v2(full_compiled_summary)
        assert "Metformin 500 MG" in prompt
        assert "Lisinopril 10 MG" in prompt
        assert "established" in prompt
        assert "3200d on therapy" in prompt

    def test_full_summary_includes_dose_history_data(self, full_compiled_summary: dict):
        """Test that v2 prompt includes dose history data when present."""
        prompt = build_system_prompt_v2(full_compiled_summary)
        assert "250 MG" in prompt
        assert "2015-03-10" in prompt

    def test_full_summary_includes_inferred_links(self, full_compiled_summary: dict):
        """Test that v2 prompt shows inferred medication-condition links."""
        prompt = build_system_prompt_v2(full_compiled_summary)
        assert "inferred via encounter" in prompt

    def test_full_summary_includes_recently_resolved(self, full_compiled_summary: dict):
        """Test that v2 prompt includes recently resolved conditions."""
        prompt = build_system_prompt_v2(full_compiled_summary)
        assert "Recently Resolved" in prompt
        assert "Acute bronchitis" in prompt

    def test_full_summary_includes_unlinked_medications(self, full_compiled_summary: dict):
        """Test that v2 prompt includes unlinked medications."""
        prompt = build_system_prompt_v2(full_compiled_summary)
        assert "Aspirin 81 MG" in prompt
        assert "not linked to a condition" in prompt

    def test_full_summary_includes_allergies(self, full_compiled_summary: dict):
        """Test that v2 prompt includes allergies in summary and safety."""
        prompt = build_system_prompt_v2(full_compiled_summary)
        assert "Penicillin" in prompt
        assert "high" in prompt

    def test_full_summary_includes_immunizations(self, full_compiled_summary: dict):
        """Test that v2 prompt includes immunizations."""
        prompt = build_system_prompt_v2(full_compiled_summary)
        assert "Influenza vaccine" in prompt
        assert "2025-10-15" in prompt

    def test_full_summary_includes_care_plans(self, full_compiled_summary: dict):
        """Test that v2 prompt includes care plans (inline and standalone)."""
        prompt = build_system_prompt_v2(full_compiled_summary)
        assert "Diabetes self management plan" in prompt
        assert "Routine wellness plan" in prompt

    def test_full_summary_includes_encounters(self, full_compiled_summary: dict):
        """Test that v2 prompt includes recent encounters."""
        prompt = build_system_prompt_v2(full_compiled_summary)
        assert "2026-01-15" in prompt
        assert "General examination" in prompt
        assert "good adherence" in prompt

    def test_full_summary_includes_observations_with_trend(self, full_compiled_summary: dict):
        """Test that v2 prompt includes observations with trend data."""
        prompt = build_system_prompt_v2(full_compiled_summary)
        assert "Hemoglobin A1c" in prompt
        assert "7.2" in prompt
        assert "rising" in prompt
        assert "6.9" in prompt
        assert "ref: 4.0-5.6" in prompt

    def test_full_summary_includes_vital_signs(self, full_compiled_summary: dict):
        """Test that v2 prompt includes vital signs."""
        prompt = build_system_prompt_v2(full_compiled_summary)
        assert "Systolic blood pressure" in prompt
        assert "138" in prompt

    def test_full_summary_safety_includes_allergy(self, full_compiled_summary: dict):
        """Test that safety constraints include the allergy."""
        prompt = build_system_prompt_v2(full_compiled_summary)
        assert "ALLERGY: Penicillin" in prompt

    def test_with_patient_profile(self, minimal_compiled_summary: dict):
        """Test that patient profile is included when provided."""
        profile = "Active retired teacher who enjoys gardening and cooking."
        prompt = build_system_prompt_v2(minimal_compiled_summary, patient_profile=profile)
        assert "Active retired teacher" in prompt
        assert "Profile:" in prompt

    def test_without_patient_profile(self, minimal_compiled_summary: dict):
        """Test that profile section is absent when not provided."""
        prompt = build_system_prompt_v2(minimal_compiled_summary)
        assert "Profile:" not in prompt

    def test_prompt_token_count_reasonable(self, full_compiled_summary: dict):
        """Test that full prompt is within reasonable token range (~22-38k chars ~ 5.5-9.5k tokens)."""
        profile = "Active retired teacher who enjoys gardening and has 3 grandchildren."
        prompt = build_system_prompt_v2(full_compiled_summary, patient_profile=profile)
        # The prompt itself (without a real patient with many conditions) should be
        # well-structured. With a real patient the compiled summary would be much larger.
        # For our test fixture, verify the prompt has reasonable structure.
        char_count = len(prompt)
        # At minimum the template + fixture data should be > 3000 chars
        assert char_count > 3000, f"Prompt too short: {char_count} chars"
        # With our test data it shouldn't exceed 10k chars
        assert char_count < 10000, f"Prompt too long for test fixture: {char_count} chars"


class TestFormatTier1Conditions:
    """Tests for _format_tier1_conditions helper."""

    def test_empty_conditions(self):
        """Test formatting empty conditions list."""
        result = _format_tier1_conditions([])
        assert result == "No active conditions recorded."

    def test_condition_with_all_enrichments(self):
        """Test formatting a condition with all medication enrichments."""
        conditions = [
            {
                "condition": {
                    "resourceType": "Condition",
                    "id": "cond-1",
                    "code": {"coding": [{"display": "Diabetes"}]},
                    "clinicalStatus": "Active",
                    "onsetDateTime": "2020-01-01",
                },
                "treating_medications": [
                    {
                        "resourceType": "MedicationRequest",
                        "id": "med-1",
                        "medicationCodeableConcept": "Metformin 500 MG",
                        "status": "active",
                        "_recency": "established",
                        "_duration_days": 1800,
                        "_inferred": True,
                        "_dose_history": [
                            {"dose": "250 MG", "authoredOn": "2020-01-01", "status": "completed"},
                        ],
                    },
                ],
                "care_plans": [],
                "related_procedures": [],
            },
        ]
        result = _format_tier1_conditions(conditions)
        assert "Diabetes" in result
        assert "cond-1" in result
        assert "Metformin 500 MG" in result
        assert "established" in result
        assert "1800d on therapy" in result
        assert "inferred via encounter" in result
        assert "250 MG" in result

    def test_condition_with_care_plan_and_procedure(self):
        """Test formatting a condition with care plans and procedures."""
        conditions = [
            {
                "condition": {
                    "id": "cond-2",
                    "code": {"coding": [{"display": "Hypertension"}]},
                    "clinicalStatus": "Active",
                },
                "treating_medications": [],
                "care_plans": [
                    {"category": "HTN management", "status": "active"},
                ],
                "related_procedures": [
                    {"code": "Blood pressure monitoring"},
                ],
            },
        ]
        result = _format_tier1_conditions(conditions)
        assert "Hypertension" in result
        assert "CarePlan: HTN management" in result
        assert "Procedure: Blood pressure monitoring" in result


class TestFormatTier2Encounters:
    """Tests for _format_tier2_encounters helper."""

    def test_empty_encounters(self):
        """Test formatting empty encounters list."""
        result = _format_tier2_encounters([])
        assert result == "No recent encounters."

    def test_encounter_with_events_and_notes(self):
        """Test formatting encounters with events and clinical notes."""
        encounters = [
            {
                "encounter": {
                    "id": "enc-1",
                    "type": "Office visit",
                    "class": {"code": "AMB"},
                    "period": {"start": "2026-01-10"},
                },
                "events": {
                    "DIAGNOSED": [
                        {"code": {"coding": [{"display": "Common cold"}]}},
                    ],
                },
                "clinical_notes": ["Patient presents with runny nose and cough."],
            },
        ]
        result = _format_tier2_encounters(encounters)
        assert "2026-01-10" in result
        assert "Office visit" in result
        assert "AMB" in result
        assert "Common cold" in result
        assert "runny nose" in result


class TestFormatTier3Observations:
    """Tests for _format_tier3_observations helper."""

    def test_empty_observations(self):
        """Test formatting empty observations."""
        result = _format_tier3_observations({})
        assert result == "No recent observations."

    def test_observations_with_trend_and_ref_range(self):
        """Test formatting observations with trend data and reference range."""
        obs = {
            "laboratory": [
                {
                    "code": {"coding": [{"display": "Glucose"}]},
                    "valueQuantity": {"value": 120, "unit": "mg/dL"},
                    "effectiveDateTime": "2026-01-05",
                    "referenceRange": [
                        {"low": {"value": 70}, "high": {"value": 100}},
                    ],
                    "_trend": {
                        "direction": "rising",
                        "previous_value": 95,
                        "previous_date": "2025-07-01",
                    },
                },
            ],
        }
        result = _format_tier3_observations(obs)
        assert "Lab Results:" in result
        assert "Glucose" in result
        assert "120" in result
        assert "mg/dL" in result
        assert "ref: 70-100" in result
        assert "rising" in result
        assert "prev=95" in result

    def test_observations_skips_empty_categories(self):
        """Test that empty categories are omitted."""
        obs = {
            "laboratory": [],
            "vital-signs": [
                {
                    "code": {"coding": [{"display": "Heart rate"}]},
                    "valueQuantity": {"value": 72, "unit": "bpm"},
                    "effectiveDateTime": "2026-01-15",
                },
            ],
            "survey": [],
        }
        result = _format_tier3_observations(obs)
        assert "Lab Results" not in result
        assert "Vital Signs:" in result
        assert "Heart rate" in result
        assert "Surveys" not in result


class TestFormatSafetyConstraintsV2:
    """Tests for _format_safety_constraints_v2 helper."""

    def test_no_allergies(self):
        """Test safety constraints with no allergies."""
        safety = {
            "active_allergies": [{"note": "None recorded"}],
            "drug_interactions_note": "Review active medications for potential interactions.",
        }
        result = _format_safety_constraints_v2(safety)
        assert "No known allergies recorded" in result
        assert "Review active medications" in result

    def test_with_allergy(self):
        """Test safety constraints with an allergy."""
        safety = {
            "active_allergies": [
                {"code": "Penicillin", "criticality": "high"},
            ],
            "drug_interactions_note": "Review active medications for potential interactions.",
        }
        result = _format_safety_constraints_v2(safety)
        assert "ALLERGY: Penicillin" in result
        assert "high" in result

    def test_empty_safety(self):
        """Test safety constraints when empty."""
        result = _format_safety_constraints_v2({})
        assert result == "No specific safety constraints."
