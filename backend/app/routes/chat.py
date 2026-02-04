"""Chat API routes for clinical reasoning agent."""

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
from app.database import get_db
from app.models import FhirResource
from app.models.session import Session
from app.schemas import AgentResponse
from app.schemas.context import PatientContext
from app.services.agent import AgentService
from app.services.context_engine import ContextEngine
from app.services.embeddings import EmbeddingService
from app.services.fhir_loader import get_patient_profile
from app.services.graph import KnowledgeGraph
from app.services.vector_search import VectorSearchService

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
    context: PatientContext
    history: list[dict[str, str]] | None
    graph: KnowledgeGraph
    embedding_service: EmbeddingService
    agent: AgentService

    async def cleanup(self) -> None:
        """Close all services."""
        await self.graph.close()
        await self.embedding_service.close()
        await self.agent.close()


async def _prepare_chat_context(
    request: ChatRequest,
    db: AsyncSession,
) -> ChatContext:
    """Validate patient, build context, and initialize services.

    Shared setup used by both /chat and /chat/stream endpoints.

    Args:
        request: Chat request with patient_id, message, and optional history.
        db: Database session.

    Returns:
        ChatContext with all prepared services and context.

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

    # Initialize services
    graph = KnowledgeGraph()
    embedding_service = EmbeddingService()
    vector_search = VectorSearchService(db)
    agent = AgentService(model=request.model) if request.model else AgentService()

    context_engine = ContextEngine(
        graph=graph,
        embedding_service=embedding_service,
        vector_search=vector_search,
    )

    # Extract patient profile summary if available
    profile = get_patient_profile(patient_resource.data)
    profile_summary = _format_profile_summary(profile) if profile else None

    # Build patient context with the patient resource
    context = await context_engine.build_context_with_patient(
        patient_id=str(request.patient_id),
        patient_resource=patient_resource.data,
        query=request.message,
        profile_summary=profile_summary,
    )

    # Convert conversation history to the format expected by AgentService
    history = None
    if request.conversation_history:
        history = [
            {"role": msg.role, "content": msg.content}
            for msg in request.conversation_history
        ]

    return ChatContext(
        conversation_id=conversation_id,
        context=context,
        history=history,
        graph=graph,
        embedding_service=embedding_service,
        agent=agent,
    )


async def _persist_messages(
    db: AsyncSession,
    session_id: uuid.UUID,
    user_message: str,
    assistant_content: str,
) -> None:
    """Persist user and assistant messages to a session.

    This enables fire-and-forget message persistence: the backend saves
    messages regardless of whether the client is still connected.

    Args:
        db: Database session.
        session_id: Session UUID to update.
        user_message: The user's message content.
        assistant_content: The assistant's response content.
    """
    try:
        result = await db.execute(select(Session).where(Session.id == session_id))
        session = result.scalar_one_or_none()

        if session is None:
            logger.warning("Session %s not found for message persistence", session_id)
            return

        # Append new messages to the existing array
        messages = list(session.messages)
        messages.append({"role": "user", "content": user_message})
        messages.append({"role": "assistant", "content": assistant_content})

        session.messages = messages
        session.last_active_at = datetime.now(timezone.utc)
        await db.flush()

        logger.debug("Persisted messages to session %s", session_id)
    except Exception:
        logger.exception("Failed to persist messages to session %s", session_id)
        # Don't raise - message persistence failure shouldn't break the chat


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

    try:
        agent_response = await chat_ctx.agent.generate_response(
            context=chat_ctx.context,
            message=request.message,
            history=chat_ctx.history,
            reasoning_effort=request.reasoning_effort,
            graph=chat_ctx.graph,
            db=db,
        )

        # Persist messages to session if session_id provided
        if request.session_id:
            await _persist_messages(
                db=db,
                session_id=request.session_id,
                user_message=request.message,
                assistant_content=agent_response.narrative,
            )

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

    async def event_generator():
        try:
            async for event_type, data_json in chat_ctx.agent.generate_response_stream(
                context=chat_ctx.context,
                message=request.message,
                history=chat_ctx.history,
                reasoning_effort=request.reasoning_effort,
                graph=chat_ctx.graph,
                db=db,
            ):
                if event_type == "done":
                    # Persist messages before yielding (fire-and-forget)
                    # This ensures messages are saved even if client disconnects after
                    if request.session_id:
                        try:
                            response_data = json.loads(data_json)
                            await _persist_messages(
                                db=db,
                                session_id=request.session_id,
                                user_message=request.message,
                                assistant_content=response_data.get("narrative", ""),
                            )
                        except json.JSONDecodeError:
                            logger.warning("Failed to parse done event for persistence")

                    # Wrap with conversation_id — data_json is already valid JSON
                    done_payload = f'{{"conversation_id":"{chat_ctx.conversation_id}","response":{data_json}}}'
                    yield f"event: done\ndata: {done_payload}\n\n"
                else:
                    yield f"event: {event_type}\ndata: {data_json}\n\n"
        except ValueError as e:
            logger.error("ValueError in chat stream: %s", e, exc_info=True)
            error_payload = json.dumps({"detail": "Invalid request parameters."})
            yield f"event: error\ndata: {error_payload}\n\n"
        except RuntimeError:
            logger.error("Agent response parsing failed in stream", exc_info=True)
            error_payload = json.dumps({"detail": "Failed to generate response."})
            yield f"event: error\ndata: {error_payload}\n\n"
        except Exception:
            logger.exception("Unexpected error during chat stream")
            error_payload = json.dumps({"detail": "An error occurred during streaming."})
            yield f"event: error\ndata: {error_payload}\n\n"
        finally:
            await chat_ctx.cleanup()

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
