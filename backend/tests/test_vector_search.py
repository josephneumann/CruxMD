"""Tests for vector search service.

Tests semantic search over FHIR resource embeddings, with focus on:
- Patient-scoped security (CRITICAL)
- Similarity threshold filtering
- Limit parameter handling
- Edge cases and error handling
"""

import uuid
from unittest.mock import AsyncMock

import pytest
import pytest_asyncio
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import FhirResource
from app.services.vector_search import (
    VectorSearchService,
    SearchResult,
    DEFAULT_THRESHOLD,
    DEFAULT_LIMIT,
)


# =============================================================================
# Test Fixtures
# =============================================================================


def create_mock_embedding(value: float = 0.1, dimension: int = 1536) -> list[float]:
    """Create a mock embedding vector with uniform values."""
    return [value] * dimension


def create_normalized_embedding(values: list[float], dimension: int = 1536) -> list[float]:
    """Create an embedding with specific first values, padded with zeros."""
    result = values + [0.0] * (dimension - len(values))
    # Normalize to unit length for proper cosine similarity
    magnitude = sum(v * v for v in result) ** 0.5
    if magnitude > 0:
        result = [v / magnitude for v in result]
    return result


@pytest_asyncio.fixture
async def patient_a_id() -> uuid.UUID:
    """UUID for test patient A."""
    return uuid.uuid4()


@pytest_asyncio.fixture
async def patient_b_id() -> uuid.UUID:
    """UUID for test patient B (for isolation tests)."""
    return uuid.uuid4()


@pytest_asyncio.fixture
async def populated_db(
    db_session: AsyncSession,
    patient_a_id: uuid.UUID,
    patient_b_id: uuid.UUID,
) -> dict:
    """Populate database with test FHIR resources with embeddings.

    Creates resources for two patients to test patient scoping.
    Returns dict with resource IDs for test assertions.
    """
    # Create embeddings with known similarity patterns
    # Using normalized vectors for predictable cosine similarity
    base_embedding = create_normalized_embedding([1.0, 0.0, 0.0])
    similar_embedding = create_normalized_embedding([0.95, 0.31, 0.0])  # ~0.95 similarity
    less_similar_embedding = create_normalized_embedding([0.7, 0.7, 0.0])  # ~0.7 similarity
    dissimilar_embedding = create_normalized_embedding([0.0, 1.0, 0.0])  # ~0.0 similarity

    resources = {}

    # Patient A resources
    condition_a = FhirResource(
        fhir_id="condition-a-001",
        resource_type="Condition",
        patient_id=patient_a_id,
        data={
            "resourceType": "Condition",
            "id": "condition-a-001",
            "code": {"coding": [{"display": "Type 2 Diabetes"}]},
            "clinicalStatus": {"coding": [{"code": "active"}]},
        },
        embedding=base_embedding,
        embedding_text="Condition: Type 2 Diabetes. Status: active",
    )
    db_session.add(condition_a)

    observation_a = FhirResource(
        fhir_id="observation-a-001",
        resource_type="Observation",
        patient_id=patient_a_id,
        data={
            "resourceType": "Observation",
            "id": "observation-a-001",
            "code": {"coding": [{"display": "Blood Glucose"}]},
            "valueQuantity": {"value": 120, "unit": "mg/dL"},
        },
        embedding=similar_embedding,
        embedding_text="Observation: Blood Glucose. Value: 120 mg/dL",
    )
    db_session.add(observation_a)

    medication_a = FhirResource(
        fhir_id="medication-a-001",
        resource_type="MedicationRequest",
        patient_id=patient_a_id,
        data={
            "resourceType": "MedicationRequest",
            "id": "medication-a-001",
            "medicationCodeableConcept": {"coding": [{"display": "Metformin"}]},
            "status": "active",
        },
        embedding=less_similar_embedding,
        embedding_text="Medication: Metformin. Status: active",
    )
    db_session.add(medication_a)

    # Resource without embedding (should be excluded from search)
    allergy_a = FhirResource(
        fhir_id="allergy-a-001",
        resource_type="AllergyIntolerance",
        patient_id=patient_a_id,
        data={
            "resourceType": "AllergyIntolerance",
            "id": "allergy-a-001",
            "code": {"coding": [{"display": "Penicillin"}]},
        },
        embedding=None,
        embedding_text=None,
    )
    db_session.add(allergy_a)

    # Dissimilar resource (should be filtered by threshold)
    procedure_a = FhirResource(
        fhir_id="procedure-a-001",
        resource_type="Procedure",
        patient_id=patient_a_id,
        data={
            "resourceType": "Procedure",
            "id": "procedure-a-001",
            "code": {"coding": [{"display": "Appendectomy"}]},
        },
        embedding=dissimilar_embedding,
        embedding_text="Procedure: Appendectomy",
    )
    db_session.add(procedure_a)

    # Patient B resources (should NEVER appear in Patient A searches)
    condition_b = FhirResource(
        fhir_id="condition-b-001",
        resource_type="Condition",
        patient_id=patient_b_id,
        data={
            "resourceType": "Condition",
            "id": "condition-b-001",
            "code": {"coding": [{"display": "Hypertension"}]},
        },
        embedding=base_embedding,  # Same embedding as Patient A's condition
        embedding_text="Condition: Hypertension. Status: active",
    )
    db_session.add(condition_b)

    await db_session.commit()

    # Refresh to get generated IDs
    await db_session.refresh(condition_a)
    await db_session.refresh(observation_a)
    await db_session.refresh(medication_a)
    await db_session.refresh(allergy_a)
    await db_session.refresh(procedure_a)
    await db_session.refresh(condition_b)

    resources["condition_a"] = condition_a
    resources["observation_a"] = observation_a
    resources["medication_a"] = medication_a
    resources["allergy_a"] = allergy_a
    resources["procedure_a"] = procedure_a
    resources["condition_b"] = condition_b
    resources["base_embedding"] = base_embedding
    resources["similar_embedding"] = similar_embedding
    resources["less_similar_embedding"] = less_similar_embedding
    resources["dissimilar_embedding"] = dissimilar_embedding

    return resources


# =============================================================================
# SearchResult Tests
# =============================================================================


class TestSearchResult:
    """Tests for SearchResult dataclass."""

    def test_search_result_creation(self):
        """Test creating a SearchResult instance."""
        result = SearchResult(
            resource={"resourceType": "Condition", "id": "test-123"},
            score=0.95,
            resource_type="Condition",
            fhir_id="test-123",
        )

        assert result.resource["resourceType"] == "Condition"
        assert result.score == 0.95
        assert result.resource_type == "Condition"
        assert result.fhir_id == "test-123"

    def test_search_result_with_complex_resource(self):
        """Test SearchResult with a full FHIR resource."""
        resource = {
            "resourceType": "Observation",
            "id": "obs-001",
            "code": {"coding": [{"display": "Blood Pressure"}]},
            "valueQuantity": {"value": 120, "unit": "mmHg"},
            "status": "final",
        }
        result = SearchResult(
            resource=resource,
            score=0.87,
            resource_type="Observation",
            fhir_id="obs-001",
        )

        assert result.resource["valueQuantity"]["value"] == 120
        assert result.score == 0.87


# =============================================================================
# VectorSearchService.search_similar Tests
# =============================================================================


class TestSearchSimilar:
    """Tests for VectorSearchService.search_similar method."""

    @pytest.mark.asyncio
    async def test_basic_search(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test basic vector search returns results."""
        service = VectorSearchService(db_session)
        query_embedding = populated_db["base_embedding"]

        results = await service.search_similar(
            patient_id=patient_a_id,
            query_embedding=query_embedding,
            limit=10,
            threshold=0.5,  # Low threshold to get all results
        )

        assert len(results) > 0
        assert all(isinstance(r, SearchResult) for r in results)

    @pytest.mark.asyncio
    async def test_results_ordered_by_similarity(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test results are ordered by similarity (highest first)."""
        service = VectorSearchService(db_session)
        query_embedding = populated_db["base_embedding"]

        results = await service.search_similar(
            patient_id=patient_a_id,
            query_embedding=query_embedding,
            limit=10,
            threshold=0.5,
        )

        # Verify descending order of similarity scores
        scores = [r.score for r in results]
        assert scores == sorted(scores, reverse=True)

    @pytest.mark.asyncio
    async def test_similarity_scores_in_valid_range(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test similarity scores are between 0 and 1."""
        service = VectorSearchService(db_session)
        query_embedding = populated_db["base_embedding"]

        results = await service.search_similar(
            patient_id=patient_a_id,
            query_embedding=query_embedding,
            limit=10,
            threshold=0.0,  # Get all results
        )

        for result in results:
            assert 0.0 <= result.score <= 1.0, f"Score {result.score} out of range"

    @pytest.mark.asyncio
    async def test_threshold_filters_results(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test threshold parameter filters low-similarity results."""
        service = VectorSearchService(db_session)
        query_embedding = populated_db["base_embedding"]

        # High threshold should filter out less similar results
        high_threshold_results = await service.search_similar(
            patient_id=patient_a_id,
            query_embedding=query_embedding,
            limit=10,
            threshold=0.9,
        )

        # Low threshold should return more results
        low_threshold_results = await service.search_similar(
            patient_id=patient_a_id,
            query_embedding=query_embedding,
            limit=10,
            threshold=0.5,
        )

        assert len(high_threshold_results) <= len(low_threshold_results)

        # Verify all high-threshold results meet the threshold
        for result in high_threshold_results:
            assert result.score >= 0.9

    @pytest.mark.asyncio
    async def test_limit_parameter(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test limit parameter restricts number of results."""
        service = VectorSearchService(db_session)
        query_embedding = populated_db["base_embedding"]

        results = await service.search_similar(
            patient_id=patient_a_id,
            query_embedding=query_embedding,
            limit=2,
            threshold=0.0,
        )

        assert len(results) <= 2

    @pytest.mark.asyncio
    async def test_excludes_resources_without_embedding(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test resources without embeddings are excluded."""
        service = VectorSearchService(db_session)
        query_embedding = populated_db["base_embedding"]

        results = await service.search_similar(
            patient_id=patient_a_id,
            query_embedding=query_embedding,
            limit=100,
            threshold=0.0,
        )

        # allergy_a has no embedding, should not appear
        fhir_ids = [r.fhir_id for r in results]
        assert "allergy-a-001" not in fhir_ids

    @pytest.mark.asyncio
    async def test_empty_results_for_high_threshold(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test empty results when threshold is too high."""
        service = VectorSearchService(db_session)
        # Use an orthogonal embedding
        query_embedding = create_normalized_embedding([0.0, 0.0, 1.0])

        results = await service.search_similar(
            patient_id=patient_a_id,
            query_embedding=query_embedding,
            limit=10,
            threshold=0.99,  # Very high threshold
        )

        assert len(results) == 0

    @pytest.mark.asyncio
    async def test_empty_embedding_raises_error(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
    ):
        """Test empty query embedding raises ValueError."""
        service = VectorSearchService(db_session)

        with pytest.raises(ValueError, match="query_embedding cannot be empty"):
            await service.search_similar(
                patient_id=patient_a_id,
                query_embedding=[],
                limit=10,
                threshold=0.7,
            )

    @pytest.mark.asyncio
    async def test_string_patient_id_conversion(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test string patient_id is correctly converted to UUID."""
        service = VectorSearchService(db_session)
        query_embedding = populated_db["base_embedding"]

        # Pass patient_id as string
        results = await service.search_similar(
            patient_id=str(patient_a_id),
            query_embedding=query_embedding,
            limit=10,
            threshold=0.5,
        )

        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_default_parameters(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test default limit and threshold parameters."""
        service = VectorSearchService(db_session)
        query_embedding = populated_db["base_embedding"]

        # Should use DEFAULT_LIMIT and DEFAULT_THRESHOLD
        results = await service.search_similar(
            patient_id=patient_a_id,
            query_embedding=query_embedding,
        )

        # Verify defaults were applied
        assert len(results) <= DEFAULT_LIMIT
        for result in results:
            assert result.score >= DEFAULT_THRESHOLD


# =============================================================================
# Patient Scoping Security Tests (CRITICAL)
# =============================================================================


class TestPatientScoping:
    """Tests for patient-scoped search security.

    CRITICAL: These tests verify that vector search is properly scoped
    to the requested patient and does not leak data from other patients.
    """

    @pytest.mark.asyncio
    async def test_only_returns_patient_resources(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        patient_b_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test search only returns resources for specified patient."""
        service = VectorSearchService(db_session)
        query_embedding = populated_db["base_embedding"]

        results = await service.search_similar(
            patient_id=patient_a_id,
            query_embedding=query_embedding,
            limit=100,
            threshold=0.0,  # Get all matches
        )

        # Verify no Patient B resources appear
        fhir_ids = [r.fhir_id for r in results]
        assert "condition-b-001" not in fhir_ids

        # Verify Patient A resources do appear
        assert any(fhir_id.startswith("condition-a") for fhir_id in fhir_ids)

    @pytest.mark.asyncio
    async def test_identical_embedding_different_patients(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        patient_b_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test that identical embeddings in different patients are isolated.

        Patient A and Patient B both have resources with the same base_embedding.
        Searching for Patient A should only return Patient A's resource.
        """
        service = VectorSearchService(db_session)
        query_embedding = populated_db["base_embedding"]

        # Search as Patient A
        results_a = await service.search_similar(
            patient_id=patient_a_id,
            query_embedding=query_embedding,
            limit=100,
            threshold=0.99,  # Only exact matches
        )

        # Search as Patient B
        results_b = await service.search_similar(
            patient_id=patient_b_id,
            query_embedding=query_embedding,
            limit=100,
            threshold=0.99,
        )

        # Patient A should only see their condition
        a_ids = {r.fhir_id for r in results_a}
        b_ids = {r.fhir_id for r in results_b}

        assert "condition-a-001" in a_ids
        assert "condition-b-001" not in a_ids

        assert "condition-b-001" in b_ids
        assert "condition-a-001" not in b_ids

    @pytest.mark.asyncio
    async def test_nonexistent_patient_returns_empty(
        self,
        db_session: AsyncSession,
        populated_db: dict,
    ):
        """Test search for non-existent patient returns empty results."""
        service = VectorSearchService(db_session)
        query_embedding = populated_db["base_embedding"]
        nonexistent_patient = uuid.uuid4()

        results = await service.search_similar(
            patient_id=nonexistent_patient,
            query_embedding=query_embedding,
            limit=100,
            threshold=0.0,
        )

        assert len(results) == 0


# =============================================================================
# VectorSearchService.search_by_text Tests
# =============================================================================


class TestSearchByText:
    """Tests for VectorSearchService.search_by_text method."""

    @pytest.mark.asyncio
    async def test_search_by_text_calls_embed_fn(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test search_by_text calls the embedding function."""
        service = VectorSearchService(db_session)

        # Mock embedding function
        mock_embed_fn = AsyncMock(return_value=populated_db["base_embedding"])

        results = await service.search_by_text(
            patient_id=patient_a_id,
            query_text="diabetes blood sugar",
            embed_fn=mock_embed_fn,
            limit=10,
            threshold=0.5,
        )

        mock_embed_fn.assert_called_once_with("diabetes blood sugar")
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_search_by_text_empty_query_raises_error(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
    ):
        """Test empty query text raises ValueError."""
        service = VectorSearchService(db_session)
        mock_embed_fn = AsyncMock()

        with pytest.raises(ValueError, match="query_text cannot be empty"):
            await service.search_by_text(
                patient_id=patient_a_id,
                query_text="",
                embed_fn=mock_embed_fn,
            )

        # Whitespace-only should also raise
        with pytest.raises(ValueError, match="query_text cannot be empty"):
            await service.search_by_text(
                patient_id=patient_a_id,
                query_text="   ",
                embed_fn=mock_embed_fn,
            )


# =============================================================================
# VectorSearchService.search_similar_to_resource Tests
# =============================================================================


class TestSearchSimilarToResource:
    """Tests for VectorSearchService.search_similar_to_resource method."""

    @pytest.mark.asyncio
    async def test_search_similar_to_resource(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test finding resources similar to an existing resource."""
        service = VectorSearchService(db_session)
        source_resource = populated_db["condition_a"]

        results = await service.search_similar_to_resource(
            patient_id=patient_a_id,
            resource_id=source_resource.id,
            limit=10,
            threshold=0.5,
        )

        # Should find similar resources but not the source
        fhir_ids = [r.fhir_id for r in results]
        assert source_resource.fhir_id not in fhir_ids
        assert len(results) > 0

    @pytest.mark.asyncio
    async def test_excludes_source_resource(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test source resource is excluded from results."""
        service = VectorSearchService(db_session)
        source_resource = populated_db["condition_a"]

        results = await service.search_similar_to_resource(
            patient_id=patient_a_id,
            resource_id=source_resource.id,
            limit=100,
            threshold=0.0,  # Get all results
        )

        # Source should never appear in results
        for result in results:
            assert result.fhir_id != source_resource.fhir_id

    @pytest.mark.asyncio
    async def test_resource_without_embedding_raises_error(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test searching from resource without embedding raises ValueError."""
        service = VectorSearchService(db_session)
        allergy_a = populated_db["allergy_a"]  # Has no embedding

        with pytest.raises(ValueError, match="has no embedding"):
            await service.search_similar_to_resource(
                patient_id=patient_a_id,
                resource_id=allergy_a.id,
                limit=10,
                threshold=0.5,
            )

    @pytest.mark.asyncio
    async def test_patient_scoping_for_source_resource(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        patient_b_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test patient must own the source resource."""
        service = VectorSearchService(db_session)
        # Try to use Patient B's resource ID with Patient A's ID
        condition_b = populated_db["condition_b"]

        with pytest.raises(ValueError, match="has no embedding"):
            await service.search_similar_to_resource(
                patient_id=patient_a_id,  # Wrong patient
                resource_id=condition_b.id,
                limit=10,
                threshold=0.5,
            )

    @pytest.mark.asyncio
    async def test_string_ids_conversion(
        self,
        db_session: AsyncSession,
        patient_a_id: uuid.UUID,
        populated_db: dict,
    ):
        """Test string IDs are correctly converted to UUIDs."""
        service = VectorSearchService(db_session)
        source_resource = populated_db["condition_a"]

        results = await service.search_similar_to_resource(
            patient_id=str(patient_a_id),
            resource_id=str(source_resource.id),
            limit=10,
            threshold=0.5,
        )

        assert isinstance(results, list)
