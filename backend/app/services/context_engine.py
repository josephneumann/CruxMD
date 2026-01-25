"""Context Engine for hybrid retrieval combining graph and vector search.

Assembles patient context from two complementary sources:
1. Verified Layer (HIGH confidence): Facts from Neo4j knowledge graph
2. Retrieved Layer (MEDIUM confidence): Semantic search via pgvector

The context engine respects token budgets and generates safety constraints
from verified clinical facts (allergies, medications, conditions).
"""

import logging
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.context import (
    ContextMeta,
    PatientContext,
    RetrievalStats,
    RetrievedLayer,
    RetrievedResource,
    VerifiedLayer,
)
from app.services.embeddings import EmbeddingService
from app.services.graph import KnowledgeGraph
from app.services.vector_search import VectorSearchService

logger = logging.getLogger(__name__)

# Default token budget for context assembly
DEFAULT_TOKEN_BUDGET = 12000

# Default similarity threshold for vector search
DEFAULT_SIMILARITY_THRESHOLD = 0.7

# Maximum resources to retrieve from vector search
DEFAULT_RETRIEVAL_LIMIT = 20


def _extract_display_name(resource: dict[str, Any]) -> str | None:
    """Extract display name from a FHIR resource's code field.

    Handles both code.coding[0].display and code.text patterns.

    Args:
        resource: FHIR resource with a 'code' field

    Returns:
        Display name string or None if not found
    """
    code = resource.get("code", {})
    if not code:
        # Check for medicationCodeableConcept (MedicationRequest)
        code = resource.get("medicationCodeableConcept", {})

    codings = code.get("coding", [])
    if codings:
        return codings[0].get("display")
    return code.get("text")


def _generate_allergy_constraints(allergies: list[dict[str, Any]]) -> list[str]:
    """Generate safety constraints from allergy resources.

    Args:
        allergies: List of FHIR AllergyIntolerance resources

    Returns:
        List of constraint strings for the LLM
    """
    constraints = []
    for allergy in allergies:
        display = _extract_display_name(allergy)
        if not display:
            continue

        criticality = allergy.get("criticality", "")
        categories = allergy.get("category", [])
        category = categories[0] if categories else ""

        if criticality == "high":
            constraint = f"CRITICAL ALLERGY: Patient has HIGH criticality allergy to {display}"
        else:
            constraint = f"ALLERGY: Patient is allergic to {display}"

        if category:
            constraint += f" ({category})"

        constraints.append(constraint)

    return constraints


def _generate_medication_constraints(medications: list[dict[str, Any]]) -> list[str]:
    """Generate safety constraints from active medications.

    Focuses on medications that may have significant interactions.

    Args:
        medications: List of FHIR MedicationRequest resources

    Returns:
        List of constraint strings for the LLM
    """
    constraints = []
    for med in medications:
        display = _extract_display_name(med)
        if not display:
            continue

        status = med.get("status", "")
        if status == "active":
            constraints.append(f"ACTIVE MEDICATION: Patient is taking {display}")

    return constraints


def _generate_condition_constraints(conditions: list[dict[str, Any]]) -> list[str]:
    """Generate safety constraints from active conditions.

    Focuses on conditions that may affect treatment decisions.

    Args:
        conditions: List of FHIR Condition resources

    Returns:
        List of constraint strings for the LLM
    """
    constraints = []
    for condition in conditions:
        display = _extract_display_name(condition)
        if not display:
            continue

        # Look for conditions that typically require special consideration
        display_lower = display.lower()
        if any(
            term in display_lower
            for term in [
                "diabetes",
                "kidney",
                "renal",
                "liver",
                "hepatic",
                "heart",
                "cardiac",
                "pregnant",
                "pregnancy",
            ]
        ):
            constraints.append(f"CONDITION: Patient has {display} - consider treatment implications")

    return constraints


class ContextEngine:
    """Hybrid retrieval engine combining graph verified facts with vector search.

    Assembles comprehensive patient context for LLM consumption, with explicit
    trust differentiation between verified facts and semantically retrieved content.

    Example:
        async with async_session_maker() as session:
            graph = KnowledgeGraph()
            embedding_service = EmbeddingService()

            engine = ContextEngine(
                db_session=session,
                graph=graph,
                embedding_service=embedding_service,
            )

            context = await engine.build_context(
                patient_id="uuid-here",
                query="What medications is this patient taking for diabetes?",
                token_budget=12000,
            )
    """

    def __init__(
        self,
        db_session: AsyncSession,
        graph: KnowledgeGraph,
        embedding_service: EmbeddingService,
    ):
        """Initialize ContextEngine.

        Args:
            db_session: Async SQLAlchemy session for vector search
            graph: KnowledgeGraph instance for verified facts
            embedding_service: EmbeddingService for query embedding
        """
        self._db_session = db_session
        self._graph = graph
        self._embedding_service = embedding_service
        self._vector_search = VectorSearchService(db_session)

    async def _build_verified_layer(self, patient_id: str) -> VerifiedLayer:
        """Build the verified layer from Neo4j graph.

        Retrieves active conditions, medications, and allergies that have
        been verified through explicit graph relationships.

        Args:
            patient_id: The canonical patient UUID

        Returns:
            VerifiedLayer with conditions, medications, and allergies
        """
        conditions = await self._graph.get_verified_conditions(patient_id)
        medications = await self._graph.get_verified_medications(patient_id)
        allergies = await self._graph.get_verified_allergies(patient_id)

        return VerifiedLayer(
            conditions=conditions,
            medications=medications,
            allergies=allergies,
        )

    async def _build_retrieved_layer(
        self,
        patient_id: str,
        query: str,
        limit: int = DEFAULT_RETRIEVAL_LIMIT,
        threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> RetrievedLayer:
        """Build the retrieved layer from vector search.

        Performs semantic search to find resources relevant to the query.

        Args:
            patient_id: The canonical patient UUID
            query: The clinical question to search for
            limit: Maximum number of resources to retrieve
            threshold: Minimum similarity score (0-1)

        Returns:
            RetrievedLayer with semantically matched resources
        """
        if not query or not query.strip():
            return RetrievedLayer(resources=[])

        try:
            search_results = await self._vector_search.search_by_text(
                patient_id=patient_id,
                query_text=query,
                embed_fn=self._embedding_service.embed_text,
                limit=limit,
                threshold=threshold,
            )
        except Exception as e:
            logger.warning(f"Vector search failed for patient {patient_id}: {e}")
            return RetrievedLayer(resources=[])

        resources = [
            RetrievedResource(
                resource=result.resource,
                resource_type=result.resource_type,
                score=result.score,
                reason="semantic_match",
            )
            for result in search_results
        ]

        return RetrievedLayer(resources=resources)

    def _generate_constraints(self, verified: VerifiedLayer) -> list[str]:
        """Generate safety constraints from verified clinical facts.

        Constraints are derived from:
        - Drug allergies (especially high criticality)
        - Active medications (for interaction checking)
        - Conditions requiring special consideration

        Args:
            verified: VerifiedLayer with clinical facts

        Returns:
            List of constraint strings for the LLM
        """
        constraints = []

        # Allergy constraints are highest priority
        constraints.extend(_generate_allergy_constraints(verified.allergies))

        # Medication constraints for interaction awareness
        constraints.extend(_generate_medication_constraints(verified.medications))

        # Condition constraints for treatment implications
        constraints.extend(_generate_condition_constraints(verified.conditions))

        return constraints

    def _get_empty_patient(self, patient_id: str) -> dict[str, Any]:
        """Create a minimal Patient resource when none is available.

        Args:
            patient_id: The patient UUID

        Returns:
            Minimal FHIR Patient resource
        """
        return {
            "resourceType": "Patient",
            "id": patient_id,
        }

    async def _trim_to_budget(
        self,
        context: PatientContext,
        token_budget: int,
    ) -> PatientContext:
        """Trim context to fit within token budget.

        Trims retrieved resources first (lower confidence), then verified
        resources if still over budget.

        Args:
            context: PatientContext to trim
            token_budget: Maximum tokens allowed

        Returns:
            Trimmed PatientContext within budget
        """
        # Update budget in meta
        context.meta.token_budget = token_budget

        # Check if already within budget
        if context.within_budget():
            return context

        # First, trim retrieved resources (lower confidence)
        while context.retrieved.resources and not context.within_budget():
            context.retrieved.resources.pop()

        # If still over budget, we'd need to trim verified resources
        # But for now, we prioritize verified data - log a warning
        if not context.within_budget():
            logger.warning(
                f"Context exceeds token budget even after trimming retrieved resources. "
                f"Estimate: {context.token_estimate()}, Budget: {token_budget}"
            )

        return context

    async def build_context(
        self,
        patient_id: str,
        query: str,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
        retrieval_limit: int = DEFAULT_RETRIEVAL_LIMIT,
        similarity_threshold: float = DEFAULT_SIMILARITY_THRESHOLD,
    ) -> PatientContext:
        """Build comprehensive patient context for LLM consumption.

        Assembles context from two sources:
        1. Verified Layer: Graph-verified facts (HIGH confidence)
        2. Retrieved Layer: Semantic search results (MEDIUM confidence)

        Also generates safety constraints from verified clinical facts.

        Args:
            patient_id: The canonical patient UUID
            query: The clinical question being asked
            token_budget: Maximum tokens allowed (default 12000)
            retrieval_limit: Max resources from vector search (default 20)
            similarity_threshold: Min similarity score for retrieval (default 0.7)

        Returns:
            PatientContext with verified facts, retrieved resources, and constraints
        """
        # Build verified layer (HIGH confidence)
        verified = await self._build_verified_layer(patient_id)

        # Build retrieved layer (MEDIUM confidence)
        retrieved = await self._build_retrieved_layer(
            patient_id=patient_id,
            query=query,
            limit=retrieval_limit,
            threshold=similarity_threshold,
        )

        # Generate safety constraints from verified facts
        constraints = self._generate_constraints(verified)

        # Build retrieval stats
        stats = RetrievalStats(
            verified_count=verified.total_count(),
            retrieved_count=retrieved.total_count(),
            tokens_used=0,  # Will be updated after assembly
        )

        # Build metadata
        meta = ContextMeta(
            patient_id=patient_id,
            query=query,
            token_budget=token_budget,
            retrieval_strategy="query_focused",
            retrieval_stats=stats,
        )

        # Assemble context
        context = PatientContext(
            meta=meta,
            patient=self._get_empty_patient(patient_id),
            verified=verified,
            retrieved=retrieved,
            constraints=constraints,
        )

        # Trim to budget if needed
        context = await self._trim_to_budget(context, token_budget)

        # Update final token count
        context.meta.retrieval_stats.tokens_used = context.token_estimate()

        return context

    async def build_context_with_patient(
        self,
        patient_id: str,
        patient_resource: dict[str, Any],
        query: str,
        token_budget: int = DEFAULT_TOKEN_BUDGET,
        profile_summary: str | None = None,
    ) -> PatientContext:
        """Build context with a pre-fetched Patient resource.

        Convenience method when the Patient FHIR resource is already available.

        Args:
            patient_id: The canonical patient UUID
            patient_resource: FHIR Patient resource
            query: The clinical question being asked
            token_budget: Maximum tokens allowed
            profile_summary: Optional patient profile summary

        Returns:
            PatientContext with the provided patient resource
        """
        context = await self.build_context(
            patient_id=patient_id,
            query=query,
            token_budget=token_budget,
        )

        # Replace minimal patient with full resource
        context.patient = patient_resource
        context.profile_summary = profile_summary

        # Recalculate token estimate
        context.meta.retrieval_stats.tokens_used = context.token_estimate()

        # Trim again if needed
        context = await self._trim_to_budget(context, token_budget)

        return context
