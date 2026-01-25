"""Tests for the Agent Service.

Tests LLM agent service with mocked OpenAI client to avoid real API calls.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.schemas import AgentResponse, FollowUp, Insight
from app.schemas.context import (
    ContextMeta,
    PatientContext,
    RetrievedLayer,
    RetrievedResource,
    VerifiedLayer,
)
from app.services.agent import (
    AgentService,
    DEFAULT_MODEL,
    DEFAULT_REASONING_EFFORT,
    DEFAULT_MAX_OUTPUT_TOKENS,
    build_system_prompt,
    _format_patient_info,
    _format_resource_list,
    _format_condition,
    _format_medication,
    _format_allergy,
    _format_retrieved_context,
    _format_constraints,
    _get_display_name,
)


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
def minimal_context(patient_id: str, sample_patient: dict) -> PatientContext:
    """Minimal patient context for testing."""
    return PatientContext(
        meta=ContextMeta(patient_id=patient_id, query="test query"),
        patient=sample_patient,
        verified=VerifiedLayer(),
        retrieved=RetrievedLayer(),
        constraints=[],
    )


@pytest.fixture
def full_context(
    patient_id: str,
    sample_patient: dict,
    sample_condition: dict,
    sample_medication: dict,
    sample_allergy: dict,
    sample_observation: dict,
) -> PatientContext:
    """Full patient context with all layers populated."""
    return PatientContext(
        meta=ContextMeta(patient_id=patient_id, query="diabetes management"),
        patient=sample_patient,
        profile_summary="Active retired teacher who enjoys gardening.",
        verified=VerifiedLayer(
            conditions=[sample_condition],
            medications=[sample_medication],
            allergies=[sample_allergy],
        ),
        retrieved=RetrievedLayer(
            resources=[
                RetrievedResource(
                    resource=sample_observation,
                    resource_type="Observation",
                    score=0.92,
                    reason="semantic_match",
                )
            ]
        ),
        constraints=[
            "CRITICAL ALLERGY: Patient has HIGH criticality allergy to Penicillin (medication)",
            "ACTIVE MEDICATION: Patient is taking Metformin 500 MG",
            "CONDITION: Patient has Type 2 diabetes mellitus - consider treatment implications",
        ],
    )


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


class TestFormatPatientInfo:
    """Tests for _format_patient_info helper."""

    def test_format_full_patient(self, sample_patient: dict):
        """Test formatting patient with all fields."""
        result = _format_patient_info(sample_patient)

        assert "John Michael Doe" in result
        assert "1960-05-15" in result
        assert "male" in result
        assert "patient-123" in result

    def test_format_patient_no_name(self):
        """Test formatting patient without name."""
        patient = {"resourceType": "Patient", "id": "test", "gender": "female"}
        result = _format_patient_info(patient)

        assert "female" in result
        assert "test" in result

    def test_format_empty_patient(self):
        """Test formatting empty patient resource."""
        result = _format_patient_info({})
        assert result == "No demographic information available"


class TestFormatResourceList:
    """Tests for _format_resource_list helper."""

    def test_format_conditions_list(self, sample_condition: dict):
        """Test formatting list of conditions."""
        result = _format_resource_list(
            [sample_condition],
            "No conditions",
            format_fn=_format_condition,
        )

        assert "Type 2 diabetes mellitus" in result
        assert "active" in result

    def test_format_empty_list(self):
        """Test formatting empty list."""
        result = _format_resource_list([], "No items recorded")
        assert result == "No items recorded"

    def test_format_with_text_fallback(self):
        """Test formatting resource using text fallback."""
        resource = {
            "resourceType": "Condition",
            "code": {"text": "Hypertension"},
            "clinicalStatus": {"coding": [{"code": "active"}]},
        }
        result = _format_resource_list(
            [resource],
            "No conditions",
            format_fn=_format_condition,
        )
        assert "Hypertension" in result

    def test_format_medications(self, sample_medication: dict):
        """Test formatting medications with custom code field."""
        result = _format_resource_list(
            [sample_medication],
            "No medications",
            code_field="medicationCodeableConcept",
            format_fn=_format_medication,
        )

        assert "Metformin 500 MG" in result
        assert "active" in result

    def test_format_allergies(self, sample_allergy: dict):
        """Test formatting allergies."""
        result = _format_resource_list(
            [sample_allergy],
            "No allergies",
            format_fn=_format_allergy,
        )

        assert "Penicillin" in result
        assert "high" in result
        assert "medication" in result


class TestFormatRetrievedContext:
    """Tests for _format_retrieved_context helper."""

    def test_format_observation_with_value(self, sample_observation: dict):
        """Test formatting observation with quantity value."""
        items = [{"resource": sample_observation, "score": 0.95}]
        result = _format_retrieved_context(items)

        assert "Hemoglobin A1c" in result
        assert "7.2" in result
        assert "0.95" in result

    def test_format_empty_retrieved(self):
        """Test formatting empty retrieved context."""
        result = _format_retrieved_context([])
        assert result == "No additional context retrieved"

    def test_format_non_observation_resource(self, sample_condition: dict):
        """Test formatting non-observation resource."""
        items = [{"resource": sample_condition, "score": 0.88}]
        result = _format_retrieved_context(items)

        assert "[Condition]" in result
        assert "0.88" in result


class TestFormatConstraints:
    """Tests for _format_constraints helper."""

    def test_format_constraints_list(self):
        """Test formatting list of constraints."""
        constraints = [
            "ALLERGY: Patient is allergic to Penicillin",
            "MEDICATION: Patient is taking Warfarin",
        ]
        result = _format_constraints(constraints)

        assert "- ALLERGY: Patient is allergic to Penicillin" in result
        assert "- MEDICATION: Patient is taking Warfarin" in result

    def test_format_empty_constraints(self):
        """Test formatting empty constraints list."""
        result = _format_constraints([])
        assert result == "No specific safety constraints"


# =============================================================================
# System Prompt Tests
# =============================================================================


class TestBuildSystemPrompt:
    """Tests for build_system_prompt function."""

    def test_build_prompt_minimal_context(self, minimal_context: PatientContext):
        """Test building prompt with minimal context."""
        prompt = build_system_prompt(minimal_context)

        assert "clinical reasoning assistant" in prompt
        assert "John Michael Doe" in prompt
        assert "No active conditions recorded" in prompt
        assert "No specific safety constraints" in prompt

    def test_build_prompt_full_context(self, full_context: PatientContext):
        """Test building prompt with full context."""
        prompt = build_system_prompt(full_context)

        assert "John Michael Doe" in prompt
        assert "Active retired teacher" in prompt
        assert "Type 2 diabetes mellitus" in prompt
        assert "Metformin 500 MG" in prompt
        assert "Penicillin" in prompt
        assert "Hemoglobin A1c" in prompt
        assert "7.2" in prompt
        assert "CRITICAL ALLERGY" in prompt

    def test_prompt_includes_guidelines(self, minimal_context: PatientContext):
        """Test that prompt includes response guidelines."""
        prompt = build_system_prompt(minimal_context)

        assert "Response Guidelines" in prompt
        assert "Safety Constraints" in prompt
        assert "Response Format" in prompt


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
    async def test_generate_response_basic(self, full_context: PatientContext):
        """Test basic response generation."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client)

        response = await service.generate_response(
            context=full_context,
            message="What medications is this patient taking?",
        )

        assert isinstance(response, AgentResponse)
        assert response.narrative is not None
        assert len(response.narrative) > 0
        mock_client.responses.parse.assert_called_once()

    @pytest.mark.asyncio
    async def test_generate_response_with_history(self, full_context: PatientContext):
        """Test response generation with conversation history."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client)

        history = [
            {"role": "user", "content": "Tell me about this patient"},
            {"role": "assistant", "content": "This is a 65-year-old male..."},
        ]

        response = await service.generate_response(
            context=full_context,
            message="What about their medications?",
            history=history,
        )

        assert isinstance(response, AgentResponse)

        call_args = mock_client.responses.parse.call_args
        input_messages = call_args.kwargs["input"]
        assert len(input_messages) == 4  # system + 2 history + current

    @pytest.mark.asyncio
    async def test_generate_response_empty_message_raises(self, minimal_context: PatientContext):
        """Test that empty message raises ValueError."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client)

        with pytest.raises(ValueError, match="message cannot be empty"):
            await service.generate_response(context=minimal_context, message="")

    @pytest.mark.asyncio
    async def test_generate_response_whitespace_message_raises(self, minimal_context: PatientContext):
        """Test that whitespace-only message raises ValueError."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client)

        with pytest.raises(ValueError, match="message cannot be empty"):
            await service.generate_response(context=minimal_context, message="   ")

    @pytest.mark.asyncio
    async def test_generate_response_reasoning_effort_override(self, full_context: PatientContext):
        """Test overriding reasoning effort for a single call."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client, reasoning_effort="low")

        await service.generate_response(
            context=full_context,
            message="Complex question",
            reasoning_effort="high",
        )

        call_args = mock_client.responses.parse.call_args
        reasoning = call_args.kwargs["reasoning"]
        effort = getattr(reasoning, "effort", None) or reasoning.get("effort")
        assert effort == "high"

    @pytest.mark.asyncio
    async def test_generate_response_uses_correct_model(self, minimal_context: PatientContext):
        """Test that correct model is passed to API."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client, model="gpt-5.2-preview")

        await service.generate_response(
            context=minimal_context,
            message="Test question",
        )

        call_args = mock_client.responses.parse.call_args
        assert call_args.kwargs["model"] == "gpt-5.2-preview"

    @pytest.mark.asyncio
    async def test_generate_response_uses_text_format(self, minimal_context: PatientContext):
        """Test that AgentResponse is passed as text_format."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client)

        await service.generate_response(
            context=minimal_context,
            message="Test question",
        )

        call_args = mock_client.responses.parse.call_args
        assert call_args.kwargs["text_format"] is AgentResponse

    @pytest.mark.asyncio
    async def test_generate_response_includes_max_tokens(self, minimal_context: PatientContext):
        """Test that max_output_tokens is passed to API."""
        mock_client = create_mock_openai_client()
        service = AgentService(client=mock_client, max_output_tokens=2048)

        await service.generate_response(
            context=minimal_context,
            message="Test question",
        )

        call_args = mock_client.responses.parse.call_args
        assert call_args.kwargs["max_output_tokens"] == 2048

    @pytest.mark.asyncio
    async def test_generate_response_fallback_on_none(self, minimal_context: PatientContext):
        """Test fallback when structured parsing returns None but raw text available."""
        mock_client = AsyncMock()

        expected_response = create_mock_agent_response()
        mock_response = MagicMock()
        mock_response.output_parsed = None
        mock_response.output_text = expected_response.model_dump_json()

        mock_client.responses.parse = AsyncMock(return_value=mock_response)

        service = AgentService(client=mock_client)

        response = await service.generate_response(
            context=minimal_context,
            message="Test question",
        )

        assert isinstance(response, AgentResponse)
        assert response.narrative == expected_response.narrative

    @pytest.mark.asyncio
    async def test_generate_response_raises_on_parse_failure(self, minimal_context: PatientContext):
        """Test that RuntimeError is raised when all parsing fails."""
        mock_client = AsyncMock()

        mock_response = MagicMock()
        mock_response.output_parsed = None
        mock_response.output_text = None

        mock_client.responses.parse = AsyncMock(return_value=mock_response)

        service = AgentService(client=mock_client)

        with pytest.raises(RuntimeError, match="LLM response could not be parsed"):
            await service.generate_response(
                context=minimal_context,
                message="Test question",
            )

    @pytest.mark.asyncio
    async def test_generate_response_filters_invalid_history(self, minimal_context: PatientContext):
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
            context=minimal_context,
            message="Current question",
            history=history,
        )

        call_args = mock_client.responses.parse.call_args
        input_messages = call_args.kwargs["input"]

        # system + 2 valid history + current = 4
        assert len(input_messages) == 4


class TestAgentServiceClose:
    """Tests for AgentService.close method."""

    @pytest.mark.asyncio
    async def test_close_calls_client_close(self):
        """Test that close calls the underlying client close."""
        mock_client = AsyncMock()
        service = AgentService(client=mock_client)

        await service.close()

        mock_client.close.assert_called_once()
