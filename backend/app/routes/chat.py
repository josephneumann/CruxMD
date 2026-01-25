"""Chat API routes for clinical reasoning agent."""

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import verify_api_key
from app.database import get_db
from app.models import FhirResource
from app.schemas import AgentResponse
from app.services.agent import AgentService
from app.services.context_engine import ContextEngine
from app.services.embeddings import EmbeddingService
from app.services.fhir_loader import get_patient_profile
from app.services.graph import KnowledgeGraph
from app.services.vector_search import VectorSearchService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/chat", tags=["chat"])


class ChatMessage(BaseModel):
    """A single message in conversation history."""

    role: str = Field(description="Message role: 'user' or 'assistant'")
    content: str = Field(description="Message content")


class ChatRequest(BaseModel):
    """Request body for chat endpoint."""

    patient_id: uuid.UUID = Field(description="PostgreSQL UUID of the patient")
    message: str = Field(min_length=1, description="The user's message")
    conversation_id: uuid.UUID | None = Field(
        default=None,
        description="Optional conversation ID. Generated if not provided.",
    )
    conversation_history: list[ChatMessage] | None = Field(
        default=None,
        description="Optional previous messages in the conversation",
    )


class ChatResponse(BaseModel):
    """Response wrapper including conversation metadata."""

    conversation_id: uuid.UUID = Field(description="Conversation ID for continuity")
    response: AgentResponse = Field(description="Agent's structured response")


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    _api_key: str = Depends(verify_api_key),
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
        _api_key: Validated API key (injected).

    Returns:
        ChatResponse with conversation_id and agent response.

    Raises:
        HTTPException: 404 if patient not found, 500 on agent errors.
    """
    # Generate conversation_id if not provided
    conversation_id = request.conversation_id or uuid.uuid4()

    # Validate patient exists and get patient resource
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

    context_engine = ContextEngine(
        graph=graph,
        embedding_service=embedding_service,
        vector_search=vector_search,
    )

    agent = AgentService()

    try:
        # Extract patient profile summary if available
        profile_summary = None
        profile = get_patient_profile(patient_resource.data)
        if profile:
            # Format a brief summary from profile fields
            parts = []
            if profile.get("occupation"):
                parts.append(profile["occupation"])
            if profile.get("living_situation"):
                parts.append(profile["living_situation"])
            if profile.get("primary_motivation"):
                parts.append(profile["primary_motivation"])
            if parts:
                profile_summary = ". ".join(parts) + "."

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

        # Generate response
        agent_response = await agent.generate_response(
            context=context,
            message=request.message,
            history=history,
        )

        return ChatResponse(
            conversation_id=conversation_id,
            response=agent_response,
        )

    except ValueError as e:
        # Validation errors from AgentService (e.g., empty message)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except RuntimeError as e:
        # LLM parsing failures
        logger.error(f"Agent response parsing failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate response. Please try again.",
        )
    except Exception as e:
        # Catch-all for unexpected errors
        logger.exception(f"Unexpected error in chat endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred.",
        )
    finally:
        # Clean up services
        await graph.close()
        await embedding_service.close()
        await agent.close()
