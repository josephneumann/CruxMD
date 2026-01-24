"""Patient context schemas for the Context Engine.

These schemas define the structure of context sent to the LLM, with explicit
trust differentiation between verified facts (from Neo4j) and retrieved
resources (from pgvector semantic search).

Design principles:
- FHIR-native: All clinical data remains as raw FHIR resources (dict)
- Trust differentiation: Verified (HIGH) vs Retrieved (MEDIUM) confidence
- Token-aware: Includes estimation methods for budget management
- Debuggable: Metadata tracks retrieval strategy and provenance
"""

import json
from datetime import datetime, timezone
from typing import Any, Literal

from pydantic import BaseModel, Field


def _utc_now() -> datetime:
    """Return current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class RetrievalStats(BaseModel):
    """Statistics about the retrieval process."""

    verified_count: int = Field(default=0, description="Number of verified resources from graph")
    retrieved_count: int = Field(default=0, description="Number of retrieved resources from search")
    tokens_used: int = Field(default=0, description="Actual tokens used in context")


class ContextMeta(BaseModel):
    """Metadata about context retrieval - enables debugging and audit."""

    patient_id: str = Field(..., description="The canonical patient UUID")
    query: str = Field(default="", description="The clinical question being asked")
    timestamp: datetime = Field(default_factory=_utc_now, description="When context was built")
    retrieval_strategy: Literal["query_focused", "comprehensive", "recent"] = Field(
        default="query_focused",
        description="Strategy used for retrieval",
    )
    token_budget: int = Field(default=6000, description="Maximum tokens allowed for context")
    retrieval_stats: RetrievalStats = Field(
        default_factory=RetrievalStats,
        description="Statistics about retrieval",
    )


class VerifiedLayer(BaseModel):
    """Facts verified via knowledge graph relationships.

    Contains raw FHIR resources - NO custom schemas.
    These have explicit typed relationships confirmed in Neo4j.

    Source: Neo4j graph traversal
    Trust: HIGH CONFIDENCE - use as ground truth for clinical assertions
    """

    conditions: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Active FHIR Condition resources (clinical_status='active')",
    )
    medications: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Active FHIR MedicationRequest resources (status in ['active', 'on-hold'])",
    )
    allergies: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Active FHIR AllergyIntolerance resources (clinical_status='active')",
    )

    def token_estimate(self) -> int:
        """Estimate token count for verified layer.

        Uses rough approximation of 4 characters per token.
        """
        total_chars = 0
        for condition in self.conditions:
            total_chars += len(json.dumps(condition))
        for medication in self.medications:
            total_chars += len(json.dumps(medication))
        for allergy in self.allergies:
            total_chars += len(json.dumps(allergy))
        return total_chars // 4

    def total_count(self) -> int:
        """Return total number of verified resources."""
        return len(self.conditions) + len(self.medications) + len(self.allergies)


class RetrievedResource(BaseModel):
    """A single resource retrieved via semantic or structured search.

    Wraps a raw FHIR resource with retrieval metadata.
    """

    resource: dict[str, Any] = Field(..., description="The raw FHIR resource")
    resource_type: str = Field(..., description="FHIR resource type (e.g., 'Observation')")
    score: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Similarity score (0.0-1.0)",
    )
    reason: Literal["semantic_match", "recent", "query_focus"] = Field(
        default="semantic_match",
        description="Why this resource was retrieved",
    )

    def token_estimate(self) -> int:
        """Estimate token count for this resource."""
        return len(json.dumps(self.resource)) // 4


class RetrievedLayer(BaseModel):
    """Resources from semantic search or structured queries.

    Contains raw FHIR resources with retrieval metadata.
    Query-relevant but relationships not graph-verified.

    Source: pgvector similarity search
    Trust: MEDIUM CONFIDENCE - relevant but verify against verified layer
    """

    resources: list[RetrievedResource] = Field(
        default_factory=list,
        description="Retrieved resources with metadata",
    )

    def token_estimate(self) -> int:
        """Estimate token count for retrieved layer."""
        return sum(r.token_estimate() for r in self.resources)

    def total_count(self) -> int:
        """Return total number of retrieved resources."""
        return len(self.resources)


class PatientContext(BaseModel):
    """FHIR-native context with explicit trust layers.

    This is the main context object sent to the LLM. It structures patient
    data into trust-differentiated layers to help the LLM calibrate confidence.

    Design principles:
    - All clinical data is raw FHIR (no custom dataclasses for conditions, meds, etc.)
    - Trust layers help LLM know what's verified vs. potentially relevant
    - Token-aware: stay within budget
    - Constraints derived from verified facts
    """

    # Metadata about this context retrieval
    meta: ContextMeta = Field(..., description="Metadata about context retrieval")

    # The patient resource (always included, from graph)
    patient: dict[str, Any] = Field(..., description="FHIR Patient resource")

    # Patient profile summary (from generated profiles, for personalization)
    profile_summary: str | None = Field(
        default=None,
        description="Non-clinical narrative about the patient (from PatientProfile)",
    )

    # HIGH CONFIDENCE: Facts verified via knowledge graph traversal
    verified: VerifiedLayer = Field(
        default_factory=VerifiedLayer,
        description="Verified facts from Neo4j (HIGH confidence)",
    )

    # MEDIUM CONFIDENCE: Resources from semantic/structured retrieval
    retrieved: RetrievedLayer = Field(
        default_factory=RetrievedLayer,
        description="Retrieved resources from search (MEDIUM confidence)",
    )

    # Query-specific reasoning constraints (derived from verified facts)
    constraints: list[str] = Field(
        default_factory=list,
        description="Safety constraints derived from verified facts (e.g., drug allergies)",
    )

    def token_estimate(self) -> int:
        """Estimate total token count for this context.

        Uses rough approximation of 4 characters per token.
        """
        patient_tokens = len(json.dumps(self.patient)) // 4
        profile_tokens = len(self.profile_summary or "") // 4
        constraints_tokens = sum(len(c) for c in self.constraints) // 4
        return (
            patient_tokens
            + profile_tokens
            + self.verified.token_estimate()
            + self.retrieved.token_estimate()
            + constraints_tokens
        )

    def within_budget(self) -> bool:
        """Check if context is within token budget."""
        return self.token_estimate() <= self.meta.token_budget
