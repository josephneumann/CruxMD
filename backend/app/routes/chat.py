"""Chat API routes for clinical reasoning agent."""

import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_bearer_token
from app.database import async_session_maker, get_db
from app.models import FhirResource
from app.models.session import Session
from app.schemas import AgentResponse
from app.services.agent import AgentService, build_system_prompt_v2
from app.services.compiler import compile_and_store, get_compiled_summary
from app.services.fhir_loader import get_patient_profile
from app.services.graph import KnowledgeGraph

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])

# Validation limits
MAX_MESSAGE_LENGTH = 10000
MAX_CONVERSATION_HISTORY = 50


def _format_profile_summary(profile: dict) -> str | None:
    """Format a brief summary from patient profile fields.

    Args:
        profile: Patient profile dict from FHIR extension.

    Returns:
        Formatted summary string or None if no relevant fields.
    """
    parts = []
    if profile.get("occupation"):
        parts.append(profile["occupation"])
    if profile.get("living_situation"):
        parts.append(profile["living_situation"])
    if profile.get("primary_motivation"):
        parts.append(profile["primary_motivation"])

    return ". ".join(parts) + "." if parts else None


class ChatMessage(BaseModel):
    """A single message in conversation history."""

    role: Literal["user", "assistant"] = Field(
        description="Message role: 'user' or 'assistant'"
    )
    content: str = Field(
        min_length=1,
        max_length=MAX_MESSAGE_LENGTH,
        description="Message content",
    )


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    patient_id: uuid.UUID = Field(description="PostgreSQL UUID of the patient")
    message: str = Field(
        min_length=1,
        max_length=MAX_MESSAGE_LENGTH,
        description="The user's message",
    )
    conversation_id: uuid.UUID | None = Field(
        default=None,
        description="Optional conversation ID. Generated if not provided.",
    )
    session_id: uuid.UUID | None = Field(
        default=None,
        description="Optional session ID. If provided, messages will be persisted to this session.",
    )
    conversation_history: list[ChatMessage] | None = Field(
        default=None,
        max_length=MAX_CONVERSATION_HISTORY,
        description="Optional previous messages in the conversation",
    )
    model: str | None = Field(
        default=None,
        description="Model to use for generation. Defaults to server-side default.",
    )
    reasoning_effort: Literal["low", "medium", "high"] | None = Field(
        default=None,
        description="Reasoning effort level. Defaults to server-side default.",
    )


class ChatResponse(BaseModel):
    """Response wrapper including conversation metadata."""

    conversation_id: uuid.UUID = Field(description="Conversation ID for continuity")
    response: AgentResponse = Field(description="Agent's structured response")


@dataclass
class ChatContext:
    """Prepared context for chat endpoints."""

    conversation_id: uuid.UUID
    system_prompt: str
    patient_id: str
    history: list[dict[str, str]] | None
    graph: KnowledgeGraph
    agent: AgentService

    async def cleanup(self) -> None:
        """Close all services."""
        await self.graph.close()
        await self.agent.close()


async def _prepare_chat_context(
    request: ChatRequest,
    db: AsyncSession,
) -> ChatContext:
    """Validate patient, load compiled summary, and initialize services.

    Shared setup used by both /chat and /chat/stream endpoints.
    Loads the pre-compiled patient summary (or compiles on-demand if missing),
    then builds the v2 system prompt.

    Args:
        request: Chat request with patient_id, message, and optional history.
        db: Database session.

    Returns:
        ChatContext with system prompt, graph, and agent services.

    Raises:
        HTTPException: 404 if patient not found.
    """
    conversation_id = request.conversation_id or uuid.uuid4()

    # Validate patient exists FIRST (before initializing expensive services)
    stmt = select(FhirResource).where(
        FhirResource.id == request.patient_id,
        FhirResource.resource_type == "Patient",
    )
    result = await db.execute(stmt)
    patient_resource = result.scalar_one_or_none()

    if patient_resource is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient not found",
        )

    # Initialize services (graph needed for both compilation fallback and tool execution)
    graph = KnowledgeGraph()
    agent = AgentService(model=request.model) if request.model else AgentService()

    # Load pre-compiled summary, compile on-demand if missing
    compiled_summary = await get_compiled_summary(request.patient_id, db)
    if compiled_summary is None:
        logger.info("No cached summary for patient %s, compiling on-demand", request.patient_id)
        compiled_summary = await compile_and_store(request.patient_id, graph, db)

    # Extract patient profile summary if available
    profile = get_patient_profile(patient_resource.data)
    profile_summary = _format_profile_summary(profile) if profile else None

    # Build v2 system prompt from compiled summary
    system_prompt = build_system_prompt_v2(compiled_summary, patient_profile=profile_summary)

    # Convert conversation history to the format expected by AgentService
    history = None
    if request.conversation_history:
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]

    return ChatContext(
        conversation_id=conversation_id,
        system_prompt=system_prompt,
        patient_id=str(request.patient_id),
        history=history,
        graph=graph,
        agent=agent,
    )


async def _persist_message(
    session_id: uuid.UUID,
    role: Literal["user", "assistant"],
    content: str,
) -> None:
    """Persist a message to a session.

    Uses an independent database session to ensure the message is saved
    even if the request's db session is closed (fire-and-forget pattern).

    Args:
        session_id: Session UUID to update.
        role: Message role ('user' or 'assistant').
        content: The message content.
    """
    try:
        async with async_session_maker() as db:
            result = await db.execute(select(Session).where(Session.id == session_id))
            session = result.scalar_one_or_none()

            if session is None:
                logger.warning("Session %s not found for %s message persistence", session_id, role)
                return

            messages = list(session.messages)
            messages.append({"role": role, "content": content})
            session.messages = messages
            session.last_active_at = datetime.now(timezone.utc)
            await db.commit()
    except Exception:
        logger.exception("Failed to persist %s message to session %s", role, session_id)


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    _user_id: str = Depends(verify_bearer_token),
) -> ChatResponse:
    """Process a chat message and return agent response.

    This endpoint:
    1. Validates the patient exists
    2. Builds patient context using hybrid retrieval (graph + vector)
    3. Generates a structured response using the LLM agent
    4. Returns the response with conversation metadata

    Args:
        request: Chat request with patient_id, message, and optional history.
        db: Database session (injected).
        _user_id: Authenticated user ID (injected).

    Returns:
        ChatResponse with conversation_id and agent response.

    Raises:
        HTTPException: 404 if patient not found, 500 on agent errors.
    """
    chat_ctx = await _prepare_chat_context(request, db)

    # Persist user message immediately
    if request.session_id:
        await _persist_message(request.session_id, "user", request.message)

    try:
        agent_response = await chat_ctx.agent.generate_response(
            system_prompt=chat_ctx.system_prompt,
            patient_id=chat_ctx.patient_id,
            message=request.message,
            history=chat_ctx.history,
            reasoning_effort=request.reasoning_effort,
            graph=chat_ctx.graph,
            db=db,
        )

        # Persist assistant message when done
        if request.session_id:
            await _persist_message(request.session_id, "assistant", agent_response.narrative)

        return ChatResponse(
            conversation_id=chat_ctx.conversation_id,
            response=agent_response,
        )

    except ValueError as e:
        logger.error("ValueError in chat endpoint: %s", e, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid request parameters",
        )
    except RuntimeError:
        logger.error("Agent response parsing failed", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate response. Please try again.",
        )
    except Exception:
        logger.exception("Unexpected error in chat endpoint")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )
    finally:
        await chat_ctx.cleanup()


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    _user_id: str = Depends(verify_bearer_token),
) -> StreamingResponse:
    """Stream a chat response as Server-Sent Events.

    SSE event types:
    - event: reasoning — reasoning summary text deltas
    - event: narrative — output text deltas
    - event: done — final AgentResponse with conversation_id
    - event: error — error details

    The response is generated in a background task that continues even if the
    client disconnects. This ensures messages are persisted regardless of
    client connection state.

    Args:
        request: Chat request with patient_id, message, and optional history.
        db: Database session (injected).
        _user_id: Authenticated user ID (injected).

    Returns:
        StreamingResponse with SSE events.

    Raises:
        HTTPException: 404 if patient not found.
    """
    chat_ctx = await _prepare_chat_context(request, db)

    # Persist user message immediately (fire-and-forget)
    if request.session_id:
        await _persist_message(request.session_id, "user", request.message)

    # Queue for passing events from background task to SSE stream
    event_queue: asyncio.Queue[tuple[str, str] | None] = asyncio.Queue()

    async def generate_and_persist():
        """Generate response in background, persist when done.

        This task runs independently of the SSE stream, so it continues
        even if the client disconnects mid-stream.
        """
        final_response_json: str | None = None

        try:
            async for event_type, data_json in chat_ctx.agent.generate_response_stream(
                system_prompt=chat_ctx.system_prompt,
                patient_id=chat_ctx.patient_id,
                message=request.message,
                history=chat_ctx.history,
                reasoning_effort=request.reasoning_effort,
                graph=chat_ctx.graph,
                db=db,
            ):
                await event_queue.put((event_type, data_json))
                if event_type == "done":
                    final_response_json = data_json

        except ValueError as e:
            logger.error("ValueError in chat stream: %s", e, exc_info=True)
            await event_queue.put(("error", json.dumps({"detail": "Invalid request parameters."})))
        except RuntimeError:
            logger.error("Agent response parsing failed in stream", exc_info=True)
            await event_queue.put(("error", json.dumps({"detail": "Failed to generate response."})))
        except Exception:
            logger.exception("Unexpected error during chat stream")
            await event_queue.put(("error", json.dumps({"detail": "An error occurred during streaming."})))
        finally:
            # Signal end of stream
            await event_queue.put(None)

            # Persist assistant message after generation completes (fire-and-forget)
            # This happens regardless of whether client is still connected
            if request.session_id and final_response_json:
                try:
                    response_data = json.loads(final_response_json)
                    await _persist_message(
                        request.session_id,
                        "assistant",
                        response_data.get("narrative", ""),
                    )
                except Exception:
                    logger.exception("Failed to persist assistant message after stream")

            await chat_ctx.cleanup()

    async def generate_with_timeout():
        """Wrap generation with a 10-minute timeout."""
        try:
            await asyncio.wait_for(generate_and_persist(), timeout=600.0)
        except asyncio.TimeoutError:
            logger.error("Background generation task timed out after 10 minutes")
            await event_queue.put(("error", json.dumps({"detail": "Request timed out."})))
            await event_queue.put(None)
            await chat_ctx.cleanup()

    # Start generation in background task (continues even if client disconnects)
    asyncio.create_task(generate_with_timeout())

    async def event_generator():
        """Yield SSE events from the queue."""
        while True:
            try:
                event = await event_queue.get()
                if event is None:
                    break

                event_type, data_json = event
                if event_type == "done":
                    done_payload = f'{{"conversation_id":"{chat_ctx.conversation_id}","response":{data_json}}}'
                    yield f"event: done\ndata: {done_payload}\n\n"
                else:
                    yield f"event: {event_type}\ndata: {data_json}\n\n"
            except asyncio.CancelledError:
                # Client disconnected - task continues in background
                break

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
