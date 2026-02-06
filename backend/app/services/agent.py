"""LLM Agent Service for clinical reasoning with structured output.

This is the brain of the chat system - it takes patient context and user messages,
reasons about them using GPT-5.2, and returns structured responses with insights,
visualizations, and follow-up suggestions.

Uses the OpenAI Responses API with Pydantic structured outputs for type-safe
response parsing.
"""

import base64
import json
import logging
from collections.abc import AsyncGenerator
from typing import Any, Literal

from openai import AsyncOpenAI
from openai.types.shared_params import Reasoning
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.schemas import AgentResponse, PatientContext
from app.services.agent_tools import TOOL_SCHEMAS, execute_tool
from app.services.graph import KnowledgeGraph

logger = logging.getLogger(__name__)

# Default model for agent responses
DEFAULT_MODEL = "gpt-5-mini"

# Default reasoning effort (medium balances quality with speed; summary="concise" enables streaming summaries)
DEFAULT_REASONING_EFFORT: Literal["low", "medium", "high"] = "medium"

# Maximum tokens for response generation
DEFAULT_MAX_OUTPUT_TOKENS = 16384

# Maximum tool-calling rounds before forcing a final response
MAX_TOOL_ROUNDS = 10

# System prompt template for clinical reasoning
SYSTEM_PROMPT_TEMPLATE = """You are a clinical reasoning assistant helping healthcare providers understand patient data.

## Your Role
- Analyze patient medical records and provide clinical insights
- Answer questions about patient history, conditions, medications, and test results
- Highlight important clinical findings and potential concerns
- Suggest relevant follow-up questions to deepen understanding

## Tools
You have access to tools that let you search and retrieve additional patient data on demand.
Use tools when the provided context doesn't contain enough detail to fully answer the question.
You can call multiple tools and make multiple rounds of calls to gather all needed information.
Do NOT guess or fabricate clinical data — if you need it, call a tool.

## Response Guidelines
1. Be accurate and evidence-based - cite specific data from the patient's records
2. Use clear, professional medical language
3. Highlight safety-critical information (allergies, drug interactions, critical values)
4. Provide actionable insights when appropriate
5. Suggest 2-3 relevant follow-up questions to help explore the patient's data

## Patient Context

### Patient Demographics
{patient_info}

{profile_section}

### Verified Clinical Facts (HIGH CONFIDENCE)
These facts are confirmed in the patient's medical record:

**Active Conditions:**
{conditions}

**Current Medications:**
{medications}

**Known Allergies:**
{allergies}

### Retrieved Context (MEDIUM CONFIDENCE)
Additional relevant information from semantic search:
{retrieved_context}

## Safety Constraints
The following constraints MUST be respected in your response:
{constraints}

## Response Format
Provide your response as a structured JSON object with:
- thinking: Your reasoning process (optional, for transparency)
- narrative: Main response in markdown format
- insights: Important clinical insights to highlight (info, warning, critical, positive)
- visualizations: Charts/graphs if data warrants visualization
- tables: Structured data displays if helpful
- actions: Suggested clinical actions if appropriate
- follow_ups: 2-3 SHORT follow-up questions (under 80 chars each) displayed as clickable chips
"""


def _get_display_name(resource: dict[str, Any], code_field: str = "code") -> str | None:
    """Extract display name from a FHIR resource's code field.

    Args:
        resource: FHIR resource dict
        code_field: Name of the code field to extract from

    Returns:
        Display name string or None if not found
    """
    code = resource.get(code_field, {})
    codings = code.get("coding", [])
    if codings:
        return codings[0].get("display")
    return code.get("text")


def _format_patient_info(patient: dict[str, Any]) -> str:
    """Format patient demographics from FHIR Patient resource."""
    parts = []

    names = patient.get("name", [])
    if names:
        name = names[0]
        given = " ".join(name.get("given", []))
        family = name.get("family", "")
        if given or family:
            parts.append(f"Name: {given} {family}".strip())

    if birth_date := patient.get("birthDate"):
        parts.append(f"Date of Birth: {birth_date}")

    if gender := patient.get("gender"):
        parts.append(f"Gender: {gender}")

    if patient_id := patient.get("id"):
        parts.append(f"Patient ID: {patient_id}")

    return "\n".join(parts) if parts else "No demographic information available"


def _format_resource_list(
    resources: list[dict[str, Any]],
    empty_message: str,
    code_field: str = "code",
    format_fn: callable = None,
) -> str:
    """Generic formatter for lists of FHIR resources.

    Args:
        resources: List of FHIR resources
        empty_message: Message to return if list is empty
        code_field: Field name containing the code (default: "code")
        format_fn: Optional function to format each resource line

    Returns:
        Formatted string with one line per resource
    """
    if not resources:
        return empty_message

    lines = []
    for resource in resources:
        display = _get_display_name(resource, code_field)
        if not display:
            display = f"Unknown {resource.get('resourceType', 'resource')}"

        if format_fn:
            line = format_fn(resource, display)
        else:
            line = f"- {display}"
        lines.append(line)

    return "\n".join(lines)


def _format_condition(resource: dict[str, Any], display: str) -> str:
    """Format a single condition resource."""
    clinical_status = resource.get("clinicalStatus", {})
    status_codings = clinical_status.get("coding", [])
    status = status_codings[0].get("code") if status_codings else "unknown"
    return f"- {display} (status: {status})"


def _format_medication(resource: dict[str, Any], display: str) -> str:
    """Format a single medication resource."""
    status = resource.get("status", "unknown")
    return f"- {display} (status: {status})"


def _format_allergy(resource: dict[str, Any], display: str) -> str:
    """Format a single allergy resource."""
    criticality = resource.get("criticality", "unknown")
    categories = resource.get("category", [])
    category = categories[0] if categories else "unknown"
    return f"- {display} (criticality: {criticality}, category: {category})"


def _get_observation_category(resource: dict[str, Any]) -> str:
    """Extract the category code from a FHIR Observation resource."""
    categories = resource.get("category", [])
    if categories:
        codings = categories[0].get("coding", [])
        if codings:
            return codings[0].get("code", "unknown")
    return "unknown"


# ── FHIR resource pruning ────────────────────────────────────────────────────
# Instead of maintaining per-type formatters, we recursively simplify the raw
# FHIR JSON so the LLM sees every clinically relevant field without FHIR
# boilerplate (system URIs, meta, profiles, identifiers, narrative HTML).

# Top-level keys to strip (zero clinical value to the LLM)
_STRIP_KEYS = frozenset({
    "meta", "text", "identifier", "implicitRules", "language",
    "contained", "extension", "modifierExtension",
})

# Keys to strip from inner objects (noisy identifiers / serialisation artifacts)
_STRIP_INNER_KEYS = frozenset({
    "system", "use", "assigner", "rank", "postalCode",
})


def _simplify_codeable_concept(cc: dict[str, Any]) -> str | dict[str, Any]:
    """Reduce a CodeableConcept to its display string when possible."""
    codings = cc.get("coding", [])
    display = cc.get("text") or (codings[0].get("display") if codings else None)
    code = codings[0].get("code") if codings else None
    if display and code:
        return display
    if display:
        return display
    return cc  # can't simplify, pass through


def _simplify_reference(ref: dict[str, Any]) -> str | dict[str, Any]:
    """Reduce a Reference to its display string or a short ID."""
    display = ref.get("display")
    raw_ref = ref.get("reference", "")
    # Strip urn:uuid: prefix
    short_ref = raw_ref[9:] if raw_ref.startswith("urn:uuid:") else raw_ref
    if display:
        return display
    if short_ref:
        return short_ref
    return ref


def _is_codeable_concept(val: Any) -> bool:
    """Check if a value looks like a FHIR CodeableConcept."""
    return isinstance(val, dict) and ("coding" in val or ("text" in val and len(val) <= 3))


def _is_reference(val: Any) -> bool:
    """Check if a value looks like a FHIR Reference."""
    return isinstance(val, dict) and "reference" in val and not isinstance(val.get("reference"), dict)


def _simplify_value(val: Any) -> Any:
    """Recursively simplify a FHIR value."""
    if isinstance(val, dict):
        if _is_codeable_concept(val):
            return _simplify_codeable_concept(val)
        if _is_reference(val):
            return _simplify_reference(val)
        return _simplify_dict(val)
    if isinstance(val, list):
        simplified = [_simplify_value(item) for item in val]
        # Unwrap single-element lists of simple values
        if len(simplified) == 1 and isinstance(simplified[0], str):
            return simplified[0]
        return simplified
    return val


def _simplify_dict(d: dict[str, Any]) -> dict[str, Any]:
    """Recursively simplify a FHIR dict, stripping boilerplate keys."""
    result = {}
    for key, val in d.items():
        if key in _STRIP_INNER_KEYS:
            continue
        simplified = _simplify_value(val)
        # Truncate ISO date strings anywhere in the tree.
        # Only match keys that genuinely contain dates — avoid false
        # positives like "location" matching on the "on" suffix.
        if isinstance(simplified, str) and "T" in simplified and (
            key.lower().endswith(("date", "datetime"))
            or key in ("issued", "recorded", "started", "created", "authoredOn")
        ):
            simplified = _truncate_date(simplified)
        # Truncate dates inside period objects anywhere in the tree
        if isinstance(simplified, dict) and key.lower() in (
            "period", "billableperiod", "performedperiod",
        ):
            for pkey in ("start", "end"):
                if isinstance(simplified.get(pkey), str):
                    simplified[pkey] = _truncate_date(simplified[pkey])
        result[key] = simplified
    return result


def _truncate_date(val: str) -> str:
    """Truncate an ISO datetime to date-only if it includes time."""
    if isinstance(val, str) and "T" in val:
        return val[:10]
    return val


def _prune_fhir_resource(resource: dict[str, Any]) -> dict[str, Any]:
    """Recursively prune a FHIR resource for LLM consumption.

    Removes FHIR boilerplate (meta, system URIs, identifiers, narrative HTML),
    simplifies CodeableConcepts and References to display strings, decodes
    base64 clinical note content, and truncates dates. The result contains
    every clinically relevant field in a compact, readable form.
    """
    # Pre-process: handle DocumentReference base64 content before recursion
    extra: dict[str, Any] = {}
    if resource.get("resourceType") == "DocumentReference":
        for content_item in resource.get("content", []):
            attachment = content_item.get("attachment", {})
            if attachment.get("data") and "text/plain" in attachment.get("contentType", ""):
                try:
                    decoded = base64.b64decode(attachment["data"]).decode("utf-8")
                    extra["clinical_note"] = decoded
                except Exception:
                    pass

    # Build a filtered copy, then let _simplify_dict handle recursive
    # simplification, date truncation, and inner-key stripping.
    filtered = {}
    skip_keys = _STRIP_KEYS | {
        # Device noise
        "udiCarrier", "distinctIdentifier", "lotNumber", "serialNumber",
        # Claim/EOB noise
        "insurance", "priority",
    }
    for key, val in resource.items():
        if key in skip_keys:
            continue
        # Replace raw content with decoded clinical_note
        if key == "content" and "clinical_note" in extra:
            continue
        filtered[key] = val

    pruned = _simplify_dict(filtered)
    pruned.update(extra)
    return pruned


def _format_retrieved_context(retrieved_resources: list[dict[str, Any]]) -> str:
    """Format retrieved resources grouped by type for the prompt.

    Uses pruned JSON to give the LLM complete access to all clinically
    relevant fields without FHIR boilerplate. Resources are grouped by type
    with Observations sub-grouped by category.
    """
    if not retrieved_resources:
        return "No additional context retrieved"

    # Group by resource type
    grouped: dict[str, list[dict[str, Any]]] = {}
    for item in retrieved_resources:
        resource = item.get("resource", item)
        resource_type = resource.get("resourceType", "Unknown")
        grouped.setdefault(resource_type, []).append(resource)

    # Render groups with headers
    sections = []
    # Show Observations first (most commonly queried), then alphabetical
    type_order = sorted(grouped.keys(), key=lambda t: (0 if t == "Observation" else 1, t))
    for rtype in type_order:
        resources = grouped[rtype]
        if rtype == "Observation":
            # Sub-group observations by category for clarity
            by_category: dict[str, list[dict[str, Any]]] = {}
            for r in resources:
                cat = _get_observation_category(r)
                by_category.setdefault(cat, []).append(r)
            cat_order = ["laboratory", "vital-signs", "survey", "procedure", "unknown"]
            cat_labels = {
                "laboratory": "Lab Results",
                "vital-signs": "Vital Signs",
                "survey": "Surveys",
                "procedure": "Procedure Results",
                "unknown": "Other Observations",
            }
            for cat in cat_order:
                if cat not in by_category:
                    continue
                cat_resources = by_category[cat]
                label = cat_labels.get(cat, cat.title())
                pruned = [_prune_fhir_resource(r) for r in cat_resources]
                sections.append(f"**{label} ({len(cat_resources)}):**\n```json\n{json.dumps(pruned, indent=2)}\n```")
            # Any categories not in cat_order
            for cat, cat_resources in by_category.items():
                if cat not in cat_order:
                    pruned = [_prune_fhir_resource(r) for r in cat_resources]
                    sections.append(f"**{cat.title()} Observations ({len(cat_resources)}):**\n```json\n{json.dumps(pruned, indent=2)}\n```")
        else:
            pruned = [_prune_fhir_resource(r) for r in resources]
            sections.append(f"**{rtype}s ({len(resources)}):**\n```json\n{json.dumps(pruned, indent=2)}\n```")

    return "\n\n".join(sections)


def _format_constraints(constraints: list[str]) -> str:
    """Format safety constraints for the prompt."""
    if not constraints:
        return "No specific safety constraints"
    return "\n".join(f"- {constraint}" for constraint in constraints)


def build_system_prompt(context: PatientContext) -> str:
    """Build the system prompt from patient context.

    Args:
        context: PatientContext with verified facts and retrieved resources

    Returns:
        Formatted system prompt string
    """
    patient_info = _format_patient_info(context.patient)

    profile_section = ""
    if context.profile_summary:
        profile_section = f"### Patient Profile\n{context.profile_summary}"

    conditions = _format_resource_list(
        context.verified.conditions,
        "No active conditions recorded",
        format_fn=_format_condition,
    )
    medications = _format_resource_list(
        context.verified.medications,
        "No active medications recorded",
        code_field="medicationCodeableConcept",
        format_fn=_format_medication,
    )
    allergies = _format_resource_list(
        context.verified.allergies,
        "No known allergies recorded",
        format_fn=_format_allergy,
    )

    retrieved_dicts = [
        {"resource": r.resource, "score": r.score}
        for r in context.retrieved.resources
    ]
    retrieved_context = _format_retrieved_context(retrieved_dicts)

    constraints = _format_constraints(context.constraints)

    return SYSTEM_PROMPT_TEMPLATE.format(
        patient_info=patient_info,
        profile_section=profile_section,
        conditions=conditions,
        medications=medications,
        allergies=allergies,
        retrieved_context=retrieved_context,
        constraints=constraints,
    )


class AgentService:
    """LLM agent service for clinical reasoning with structured output.

    Uses OpenAI's Responses API with Pydantic structured outputs to generate
    type-safe responses with clinical insights, visualizations, and follow-ups.

    Example:
        agent = AgentService()

        response = await agent.generate_response(
            context=patient_context,
            message="What medications is this patient taking for diabetes?",
            history=[
                {"role": "user", "content": "Tell me about this patient"},
                {"role": "assistant", "content": "This is a 65-year-old..."},
            ],
        )

        print(response.narrative)
        for insight in response.insights or []:
            print(f"[{insight.type}] {insight.title}")
    """

    def __init__(
        self,
        client: AsyncOpenAI | None = None,
        model: str = DEFAULT_MODEL,
        reasoning_effort: Literal["low", "medium", "high"] = DEFAULT_REASONING_EFFORT,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
    ):
        """Initialize AgentService.

        Args:
            client: Optional pre-configured AsyncOpenAI client (for testing).
                   If not provided, creates one from settings.
            model: Model to use for generation. Defaults to gpt-5.2.
            reasoning_effort: Reasoning effort level. Defaults to "low" for speed.
            max_output_tokens: Maximum tokens in response. Defaults to 4096.

        Raises:
            ValueError: If no client provided and OPENAI_API_KEY is not configured.
        """
        if client is not None:
            self._client = client
        else:
            if not settings.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY environment variable is required. "
                    "Set it in your .env file or environment."
                )
            self._client = AsyncOpenAI(api_key=settings.openai_api_key)

        self._model = model
        self._reasoning_effort = reasoning_effort
        self._max_output_tokens = max_output_tokens

    async def close(self) -> None:
        """Close the OpenAI client connection."""
        await self._client.close()

    @staticmethod
    def _append_response_output(kwargs: dict[str, Any], response: Any) -> None:
        """Append response output items to kwargs["input"], serializing SDK objects.

        SDK objects from .parse() carry extra fields (e.g. parsed_arguments)
        that the API rejects on re-send. This method serializes function_call
        items to plain dicts with only the required fields.
        """
        for item in response.output:
            if item.type == "function_call":
                kwargs["input"].append({
                    "type": "function_call",
                    "id": item.id,
                    "call_id": item.call_id,
                    "name": item.name,
                    "arguments": item.arguments,
                })
            else:
                kwargs["input"].append(item)

    async def _execute_tool_calls(
        self,
        kwargs: dict[str, Any],
        patient_id: str,
        graph: KnowledgeGraph,
        db: AsyncSession,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """Execute tool-calling rounds, yielding SSE events for each tool interaction.

        After this returns, kwargs["input"] contains the full conversation
        including all tool calls and results, ready for a final call.

        Yields (event_type, data_json) tuples:
          - ("tool_call", json) when the LLM invokes a tool
          - ("tool_result", json) when a tool returns its result

        Args:
            kwargs: API call kwargs (mutated in place).
            patient_id: Current patient ID for tool execution.
            graph: KnowledgeGraph instance.
            db: AsyncSession instance.
        """
        for _round in range(MAX_TOOL_ROUNDS):
            response = await self._client.responses.parse(**kwargs)

            tool_calls = [
                item for item in response.output
                if item.type == "function_call"
            ]
            if not tool_calls:
                kwargs.pop("tools", None)
                kwargs["_last_response"] = response
                return

            logger.debug(f"Tool round {_round + 1}: {len(tool_calls)} tool call(s)")

            self._append_response_output(kwargs, response)

            for tool_call in tool_calls:
                yield ("tool_call", json.dumps({
                    "name": tool_call.name,
                    "call_id": tool_call.call_id,
                    "arguments": tool_call.arguments,
                }))

                result = await execute_tool(
                    name=tool_call.name,
                    arguments=tool_call.arguments,
                    patient_id=patient_id,
                    graph=graph,
                    db=db,
                )
                kwargs["input"].append({
                    "type": "function_call_output",
                    "call_id": tool_call.call_id,
                    "output": result,
                })

                yield ("tool_result", json.dumps({
                    "call_id": tool_call.call_id,
                    "name": tool_call.name,
                    "output": result,
                }))

        # Max rounds reached — remove tools to force text generation
        kwargs.pop("tools", None)
        kwargs["_last_response"] = None

    def _build_input_messages(
        self,
        context: PatientContext,
        message: str,
        history: list[dict[str, str]] | None = None,
    ) -> list[dict[str, str]]:
        """Build input messages for the API call.

        Args:
            context: Patient context for system prompt
            message: Current user message
            history: Optional conversation history

        Returns:
            List of message dicts for the API
        """
        messages = [
            {"role": "system", "content": build_system_prompt(context)},
        ]

        if history:
            for msg in history:
                role = msg.get("role", "user")
                content = msg.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append({"role": role, "content": content})

        messages.append({"role": "user", "content": message})

        return messages

    async def generate_response(
        self,
        context: PatientContext,
        message: str,
        history: list[dict[str, str]] | None = None,
        reasoning_effort: Literal["low", "medium", "high"] | None = None,
        graph: KnowledgeGraph | None = None,
        db: AsyncSession | None = None,
    ) -> AgentResponse:
        """Generate a structured response for a clinical question.

        Args:
            context: PatientContext with verified facts and retrieved resources
            message: The user's question or message
            history: Optional list of previous messages in the conversation.
                    Each message should have 'role' and 'content' keys.
            reasoning_effort: Override default reasoning effort for this call
            graph: KnowledgeGraph instance for tool execution
            db: AsyncSession for tool execution

        Returns:
            AgentResponse with narrative, insights, visualizations, and follow-ups

        Raises:
            ValueError: If message is empty
            openai.APIError: If API call fails
        """
        if not message or not message.strip():
            raise ValueError("message cannot be empty")

        input_messages = self._build_input_messages(context, message, history)
        effort = reasoning_effort or self._reasoning_effort
        tools_available = graph is not None and db is not None

        logger.debug(
            f"Generating response with model={self._model}, "
            f"{len(input_messages)} messages, reasoning_effort={effort}, "
            f"tools={'enabled' if tools_available else 'disabled'}"
        )

        kwargs: dict[str, Any] = {
            "model": self._model,
            "input": input_messages,
            "text_format": AgentResponse,
            "max_output_tokens": self._max_output_tokens,
            "reasoning": Reasoning(effort=effort, summary="concise"),
        }
        if tools_available:
            kwargs["tools"] = TOOL_SCHEMAS

            # Run tool rounds (discard SSE events — non-streaming path).
            # _execute_tool_calls stores the final non-tool response in kwargs.
            async for _ in self._execute_tool_calls(
                kwargs, context.meta.patient_id, graph, db
            ):
                pass

        # Reuse the response from _execute_tool_calls if available,
        # otherwise make a fresh call (no tools path, or max rounds hit).
        response = kwargs.pop("_last_response", None)
        if response is None:
            response = await self._client.responses.parse(**kwargs)

        agent_response = response.output_parsed

        if agent_response is None:
            # Fallback: try to parse from raw output if structured parsing failed
            logger.warning("Structured parsing returned None, attempting fallback")
            raw_output = getattr(response, "output_text", None)
            if raw_output:
                agent_response = AgentResponse.model_validate_json(raw_output)
            else:
                raise RuntimeError(
                    "LLM response could not be parsed. "
                    "Neither structured output nor raw text was available."
                )

        logger.debug(
            f"Generated response with {len(agent_response.insights or [])} insights, "
            f"{len(agent_response.follow_ups or [])} follow-ups"
        )

        return agent_response

    async def generate_response_stream(
        self,
        context: PatientContext,
        message: str,
        history: list[dict[str, str]] | None = None,
        reasoning_effort: Literal["low", "medium", "high"] | None = None,
        graph: KnowledgeGraph | None = None,
        db: AsyncSession | None = None,
    ) -> AsyncGenerator[tuple[str, str], None]:
        """Stream a structured response, yielding deltas as they arrive.

        Yields (event_type, data_json) tuples:
          - ("reasoning", json) for reasoning summary text deltas
          - ("narrative", json) for output text deltas

        After all deltas, yields ("done", json) with the final parsed AgentResponse.

        Tool execution rounds happen silently (no events emitted) between
        streaming rounds. Only the final text response is streamed.

        Args:
            context: PatientContext with verified facts and retrieved resources
            message: The user's question or message
            history: Optional conversation history
            reasoning_effort: Override default reasoning effort for this call
            graph: KnowledgeGraph instance for tool execution
            db: AsyncSession for tool execution

        Raises:
            ValueError: If message is empty
        """
        if not message or not message.strip():
            raise ValueError("message cannot be empty")

        input_messages = self._build_input_messages(context, message, history)
        effort = reasoning_effort or self._reasoning_effort
        tools_available = graph is not None and db is not None

        logger.debug(
            f"Streaming response with model={self._model}, "
            f"{len(input_messages)} messages, reasoning_effort={effort}, "
            f"tools={'enabled' if tools_available else 'disabled'}"
        )

        kwargs: dict[str, Any] = {
            "model": self._model,
            "input": input_messages,
            "text_format": AgentResponse,
            "max_output_tokens": self._max_output_tokens,
            "reasoning": Reasoning(effort=effort, summary="concise"),
        }
        if tools_available:
            kwargs["tools"] = TOOL_SCHEMAS

        # Execute tool rounds, yielding tool_call/tool_result events as they happen.
        # _execute_tool_calls leaves kwargs ready for the final streaming call.
        if tools_available:
            async for event in self._execute_tool_calls(
                kwargs, context.meta.patient_id, graph, db
            ):
                yield event

        # Remove internal-only key before calling the API
        kwargs.pop("_last_response", None)

        # Stream the final response (reasoning summaries + narrative deltas)
        async with self._client.responses.stream(**kwargs) as stream:
            async for event in stream:
                if event.type == "response.reasoning_summary_text.delta":
                    yield ("reasoning", json.dumps({"delta": event.delta}))
                elif event.type == "response.output_text.delta":
                    yield ("narrative", json.dumps({"delta": event.delta}))

            final = await stream.get_final_response()

        agent_response = final.output_parsed
        if agent_response is None:
            raw_output = getattr(final, "output_text", None)
            if raw_output:
                agent_response = AgentResponse.model_validate_json(raw_output)
            else:
                raise RuntimeError(
                    "LLM response could not be parsed. "
                    "Neither structured output nor raw text was available."
                )

        yield ("done", agent_response.model_dump_json())
