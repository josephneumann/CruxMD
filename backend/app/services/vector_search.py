"""Vector search service for semantic search over FHIR resource embeddings.

Uses pgvector's cosine distance operator with HNSW index for efficient
similarity search, scoped to individual patients for security.

SECURITY: This service enforces patient-scoped queries but does NOT perform
authentication or authorization. API routes MUST verify that the authenticated
user has permission to access the requested patient_id before calling these methods.
"""

import logging
import math
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FhirResource

logger = logging.getLogger(__name__)

# Default similarity threshold (cosine similarity, 0-1 scale)
# Resources with similarity below this are filtered out
DEFAULT_THRESHOLD = 0.7

# Default maximum results to return
DEFAULT_LIMIT = 10

# Hard maximum limit to prevent resource exhaustion
MAX_LIMIT = 100

# Expected embedding dimensions (text-embedding-3-small)
EMBEDDING_DIMENSION = 1536


@dataclass
class SearchResult:
    """A FHIR resource with its similarity score.

    Attributes:
        resource: The FHIR resource data (raw JSON).
        score: Cosine similarity score (0-1, higher is more similar).
        resource_type: The FHIR resource type (e.g., "Condition", "Observation").
        fhir_id: The FHIR resource ID.
    """

    resource: dict[str, Any]
    score: float
    resource_type: str
    fhir_id: str


class VectorSearchService:
    """
    Vector search service for semantic similarity search over FHIR resources.

    Uses pgvector's HNSW index with cosine distance for efficient similarity
    search. All queries are scoped to a specific patient for security.

    Example:
        async with async_session_maker() as session:
            service = VectorSearchService(session)
            results = await service.search_similar(
                patient_id=patient_uuid,
                query_embedding=embedding_vector,
                limit=5,
                threshold=0.8,
            )
            for result in results:
                print(f"{result.resource_type}: {result.score:.3f}")
    """

    def __init__(self, session: AsyncSession):
        """
        Initialize VectorSearchService.

        Args:
            session: Async SQLAlchemy session for database queries.
        """
        self._session = session

    async def search_similar(
        self,
        patient_id: uuid.UUID | str,
        query_embedding: list[float],
        limit: int = DEFAULT_LIMIT,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> list[SearchResult]:
        """
        Search for FHIR resources semantically similar to the query embedding.

        SECURITY: All queries are scoped to the specified patient_id.
        Resources belonging to other patients are never returned.

        Args:
            patient_id: The patient UUID to scope the search to.
                       Can be a UUID object or string representation.
            query_embedding: The query embedding vector (1536 dimensions).
            limit: Maximum number of results to return. Defaults to 10, max 100.
            threshold: Minimum similarity score (0-1). Resources with lower
                      similarity are filtered out. Defaults to 0.7.

        Returns:
            List of SearchResult objects, ordered by similarity (highest first).
            Each result contains the FHIR resource data and similarity score.

        Raises:
            ValueError: If parameters are invalid (wrong dimensions, out of range, etc.)
        """
        # Validate embedding
        if not query_embedding:
            raise ValueError("query_embedding cannot be empty")
        if len(query_embedding) != EMBEDDING_DIMENSION:
            raise ValueError(
                f"query_embedding must have exactly {EMBEDDING_DIMENSION} dimensions, "
                f"got {len(query_embedding)}"
            )
        if not all(
            isinstance(v, (int, float)) and not math.isnan(v) and not math.isinf(v)
            for v in query_embedding
        ):
            raise ValueError("query_embedding contains invalid values (NaN or Inf)")

        # Validate limit
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if limit > MAX_LIMIT:
            raise ValueError(f"limit cannot exceed {MAX_LIMIT}")

        # Validate threshold
        if not (0.0 <= threshold <= 1.0):
            raise ValueError("threshold must be between 0.0 and 1.0")

        # Convert string patient_id to UUID if needed
        if isinstance(patient_id, str):
            try:
                patient_id = uuid.UUID(patient_id)
            except ValueError:
                logger.warning("Invalid patient_id format attempted")
                raise ValueError("Invalid patient_id format") from None

        # pgvector's <=> operator returns cosine distance (0 = identical, 2 = opposite)
        # We convert to similarity: similarity = 1 - distance
        # Threshold on distance: distance <= 1 - threshold
        max_distance = 1 - threshold

        # Build subquery to compute distance once (avoids duplicate calculation)
        # The HNSW index (idx_fhir_embedding_hnsw) will be used automatically
        distance_subquery = (
            select(
                FhirResource.data,
                FhirResource.resource_type,
                FhirResource.fhir_id,
                FhirResource.embedding.cosine_distance(query_embedding).label("distance"),
            )
            .where(
                FhirResource.patient_id == patient_id,
                FhirResource.embedding.isnot(None),
            )
            .subquery()
        )

        # Filter and order on the computed distance column
        query = (
            select(
                distance_subquery.c.data,
                distance_subquery.c.resource_type,
                distance_subquery.c.fhir_id,
                distance_subquery.c.distance,
            )
            .where(distance_subquery.c.distance <= max_distance)
            .order_by(distance_subquery.c.distance)
            .limit(limit)
        )

        result = await self._session.execute(query)
        rows = result.all()

        # Convert to SearchResult objects
        search_results = []
        for row in rows:
            # Convert distance to similarity score
            similarity = 1 - row.distance
            search_results.append(
                SearchResult(
                    resource=row.data,
                    score=similarity,
                    resource_type=row.resource_type,
                    fhir_id=row.fhir_id,
                )
            )

        return search_results

    async def search_by_text(
        self,
        patient_id: uuid.UUID | str,
        query_text: str,
        embed_fn,
        limit: int = DEFAULT_LIMIT,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> list[SearchResult]:
        """
        Search for FHIR resources similar to a text query.

        Convenience method that embeds the query text and performs vector search.

        Args:
            patient_id: The patient UUID to scope the search to.
            query_text: The text query to search for.
            embed_fn: Async function that takes text and returns embedding vector.
                     Typically EmbeddingService.embed_text.
            limit: Maximum number of results to return. Defaults to 10.
            threshold: Minimum similarity score (0-1). Defaults to 0.7.

        Returns:
            List of SearchResult objects, ordered by similarity (highest first).

        Raises:
            ValueError: If query_text is empty.
        """
        if not query_text or not query_text.strip():
            raise ValueError("query_text cannot be empty")

        # Generate embedding for the query text
        query_embedding = await embed_fn(query_text)

        return await self.search_similar(
            patient_id=patient_id,
            query_embedding=query_embedding,
            limit=limit,
            threshold=threshold,
        )

    async def search_similar_to_resource(
        self,
        patient_id: uuid.UUID | str,
        resource_id: uuid.UUID | str,
        limit: int = DEFAULT_LIMIT,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> list[SearchResult]:
        """
        Search for FHIR resources similar to an existing resource.

        Finds resources that are semantically similar to a resource that
        already has an embedding stored in the database.

        Args:
            patient_id: The patient UUID to scope the search to.
            resource_id: The database ID of the source resource.
            limit: Maximum number of results to return. Defaults to 10, max 100.
            threshold: Minimum similarity score (0-1). Defaults to 0.7.

        Returns:
            List of SearchResult objects, ordered by similarity (highest first).
            The source resource is excluded from results.

        Raises:
            ValueError: If parameters are invalid or source resource has no embedding.
        """
        # Validate limit
        if limit < 1:
            raise ValueError("limit must be at least 1")
        if limit > MAX_LIMIT:
            raise ValueError(f"limit cannot exceed {MAX_LIMIT}")

        # Validate threshold
        if not (0.0 <= threshold <= 1.0):
            raise ValueError("threshold must be between 0.0 and 1.0")

        # Convert string IDs to UUIDs if needed
        if isinstance(patient_id, str):
            try:
                patient_id = uuid.UUID(patient_id)
            except ValueError:
                logger.warning("Invalid patient_id format attempted")
                raise ValueError("Invalid patient_id format") from None
        if isinstance(resource_id, str):
            try:
                resource_id = uuid.UUID(resource_id)
            except ValueError:
                logger.warning("Invalid resource_id format attempted")
                raise ValueError("Invalid resource_id format") from None

        # First, get the embedding of the source resource
        source_query = select(FhirResource.embedding).where(
            FhirResource.id == resource_id,
            FhirResource.patient_id == patient_id,  # Security: verify ownership
        )
        result = await self._session.execute(source_query)
        row = result.first()

        if not row or row.embedding is None:
            raise ValueError(f"Resource {resource_id} has no embedding")

        # pgvector returns the embedding directly usable
        source_embedding = row.embedding

        # Calculate max distance from threshold
        max_distance = 1 - threshold

        # Build subquery to compute distance once (avoids duplicate calculation)
        distance_subquery = (
            select(
                FhirResource.data,
                FhirResource.resource_type,
                FhirResource.fhir_id,
                FhirResource.embedding.cosine_distance(source_embedding).label("distance"),
            )
            .where(
                FhirResource.patient_id == patient_id,
                FhirResource.embedding.isnot(None),
                FhirResource.id != resource_id,  # Exclude source resource
            )
            .subquery()
        )

        # Filter and order on the computed distance column
        query = (
            select(
                distance_subquery.c.data,
                distance_subquery.c.resource_type,
                distance_subquery.c.fhir_id,
                distance_subquery.c.distance,
            )
            .where(distance_subquery.c.distance <= max_distance)
            .order_by(distance_subquery.c.distance)
            .limit(limit)
        )

        result = await self._session.execute(query)
        rows = result.all()

        # Convert to SearchResult objects
        search_results = []
        for row in rows:
            similarity = 1 - row.distance
            search_results.append(
                SearchResult(
                    resource=row.data,
                    score=similarity,
                    resource_type=row.resource_type,
                    fhir_id=row.fhir_id,
                )
            )

        return search_results
