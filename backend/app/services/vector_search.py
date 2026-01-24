"""Vector search service for semantic search over FHIR resource embeddings.

Uses pgvector's cosine distance operator with HNSW index for efficient
similarity search, scoped to individual patients for security.
"""

import logging
import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FhirResource

logger = logging.getLogger(__name__)

# Default similarity threshold (cosine similarity, 0-1 scale)
# Resources with similarity below this are filtered out
DEFAULT_THRESHOLD = 0.7

# Default maximum results to return
DEFAULT_LIMIT = 10


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
            limit: Maximum number of results to return. Defaults to 10.
            threshold: Minimum similarity score (0-1). Resources with lower
                      similarity are filtered out. Defaults to 0.7.

        Returns:
            List of SearchResult objects, ordered by similarity (highest first).
            Each result contains the FHIR resource data and similarity score.

        Raises:
            ValueError: If query_embedding is empty or has wrong dimensions.
        """
        if not query_embedding:
            raise ValueError("query_embedding cannot be empty")

        # Convert string patient_id to UUID if needed
        if isinstance(patient_id, str):
            patient_id = uuid.UUID(patient_id)

        # pgvector's <=> operator returns cosine distance (0 = identical, 2 = opposite)
        # We convert to similarity: similarity = 1 - distance
        # Since we're using cosine_ops, distance is in [0, 2] range
        # Threshold on distance: distance <= 1 - threshold
        # (because similarity >= threshold means 1 - distance >= threshold)
        max_distance = 1 - threshold

        # Build the query using pgvector's <=> operator
        # The HNSW index (idx_fhir_embedding_hnsw) will be used automatically
        query = (
            select(
                FhirResource.data,
                FhirResource.resource_type,
                FhirResource.fhir_id,
                # Calculate cosine distance using <=> operator
                # Convert embedding list to PostgreSQL vector format
                (FhirResource.embedding.cosine_distance(query_embedding)).label("distance"),
            )
            .where(
                FhirResource.patient_id == patient_id,
                FhirResource.embedding.isnot(None),
            )
            # Filter by distance threshold
            .where(
                FhirResource.embedding.cosine_distance(query_embedding) <= max_distance
            )
            # Order by distance (ascending = most similar first)
            .order_by(text("distance"))
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
            limit: Maximum number of results to return. Defaults to 10.
            threshold: Minimum similarity score (0-1). Defaults to 0.7.

        Returns:
            List of SearchResult objects, ordered by similarity (highest first).
            The source resource is excluded from results.

        Raises:
            ValueError: If the source resource has no embedding.
        """
        # Convert string IDs to UUIDs if needed
        if isinstance(patient_id, str):
            patient_id = uuid.UUID(patient_id)
        if isinstance(resource_id, str):
            resource_id = uuid.UUID(resource_id)

        # First, get the embedding of the source resource
        source_query = select(FhirResource.embedding).where(
            FhirResource.id == resource_id,
            FhirResource.patient_id == patient_id,  # Security: verify ownership
        )
        result = await self._session.execute(source_query)
        row = result.first()

        if not row or row.embedding is None:
            raise ValueError(f"Resource {resource_id} has no embedding")

        # Convert pgvector vector to list
        source_embedding = list(row.embedding)

        # Calculate max distance from threshold
        max_distance = 1 - threshold

        # Search for similar resources, excluding the source
        query = (
            select(
                FhirResource.data,
                FhirResource.resource_type,
                FhirResource.fhir_id,
                (FhirResource.embedding.cosine_distance(source_embedding)).label("distance"),
            )
            .where(
                FhirResource.patient_id == patient_id,
                FhirResource.embedding.isnot(None),
                FhirResource.id != resource_id,  # Exclude source resource
            )
            .where(
                FhirResource.embedding.cosine_distance(source_embedding) <= max_distance
            )
            .order_by(text("distance"))
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
