"""Tests for the Context Engine service.

Tests hybrid retrieval combining Neo4j graph verified facts with
pgvector semantic search, including token budget management and
constraint generation.
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.schemas.context import (
    PatientContext,
    RetrievedLayer,
    RetrievedResource,
    VerifiedLayer,
)
from app.schemas.quick_actions import QuickAction
from app.schemas.task import TaskType
from app.services.context_engine import (
    CLINICALLY_SIGNIFICANT_TERMS,
    ContextEngine,
    DEFAULT_TOKEN_BUDGET,
    DEFAULT_RETRIEVAL_LIMIT,
    DEFAULT_SIMILARITY_THRESHOLD,
    _generate_allergy_constraints,
    _generate_condition_constraints,
    _generate_medication_constraints,
)
from app.services.vector_search import SearchResult, VectorSearchService
from app.utils.fhir_helpers import extract_display_name


# =============================================================================
# Test Fixtures
# =============================================================================


@pytest.fixture
def patient_id() -> str:
    """Generate a unique patient ID for testing."""
    return str(uuid.uuid4())


@pytest.fixture
def sample_condition() -> dict:
    """Sample FHIR Condition resource."""
    return {
        "resourceType": "Condition",
        "id": "condition-test-123",
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
        "id": "med-test-456",
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
    """Sample FHIR AllergyIntolerance resource with high criticality."""
    return {
        "resourceType": "AllergyIntolerance",
        "id": "allergy-test-789",
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
        "id": "obs-test-abc",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "2339-0",
                    "display": "Glucose [Mass/volume] in Blood",
                }
            ]
        },
        "status": "final",
        "valueQuantity": {"value": 120, "unit": "mg/dL"},
    }


@pytest.fixture
def mock_graph():
    """Mock KnowledgeGraph instance."""
    graph = AsyncMock()
    graph.get_verified_conditions = AsyncMock(return_value=[])
    graph.get_verified_medications = AsyncMock(return_value=[])
    graph.get_verified_allergies = AsyncMock(return_value=[])
    return graph


@pytest.fixture
def mock_embedding_service():
    """Mock EmbeddingService instance."""
    service = AsyncMock()
    # Return a mock embedding vector
    service.embed_text = AsyncMock(return_value=[0.1] * 1536)
    return service


@pytest.fixture
def mock_vector_search():
    """Mock VectorSearchService instance."""
    service = MagicMock(spec=VectorSearchService)
    service.search_by_text = AsyncMock(return_value=[])
    return service


@pytest_asyncio.fixture
async def context_engine(mock_graph, mock_embedding_service, mock_vector_search):
    """ContextEngine instance with mocked dependencies."""
    return ContextEngine(
        graph=mock_graph,
        embedding_service=mock_embedding_service,
        vector_search=mock_vector_search,
    )


# =============================================================================
# FHIR Helper Function Tests
# =============================================================================


class TestExtractDisplayName:
    """Tests for extract_display_name helper function from fhir_helpers."""

    def test_extracts_from_coding(self, sample_condition):
        """Test extraction from code.coding[0].display."""
        result = extract_display_name(sample_condition)
        assert result == "Type 2 diabetes mellitus"

    def test_extracts_from_medication_codeable_concept(self, sample_medication):
        """Test extraction from medicationCodeableConcept."""
        result = extract_display_name(sample_medication)
        assert result == "Metformin 500 MG"

    def test_extracts_from_text_fallback(self):
        """Test extraction from code.text when coding is empty."""
        resource = {"code": {"text": "Some condition"}}
        result = extract_display_name(resource)
        assert result == "Some condition"

    def test_returns_none_for_empty_code(self):
        """Test returns None when no code is present."""
        resource = {"resourceType": "Condition"}
        result = extract_display_name(resource)
        assert result is None


# =============================================================================
# Constraint Generation Tests
# =============================================================================


class TestGenerateAllergyConstraints:
    """Tests for _generate_allergy_constraints helper function."""

    def test_generates_high_criticality_constraint(self, sample_allergy):
        """Test constraint generation for high criticality allergy."""
        constraints = _generate_allergy_constraints([sample_allergy])

        assert len(constraints) == 1
        assert "CRITICAL ALLERGY" in constraints[0]
        assert "Penicillin" in constraints[0]
        assert "HIGH criticality" in constraints[0]
        assert "medication" in constraints[0]

    def test_generates_normal_allergy_constraint(self):
        """Test constraint generation for normal criticality allergy."""
        allergy = {
            "code": {"coding": [{"display": "Sulfa drugs"}]},
            "category": ["medication"],
            "criticality": "low",
        }
        constraints = _generate_allergy_constraints([allergy])

        assert len(constraints) == 1
        assert "ALLERGY:" in constraints[0]
        assert "Sulfa drugs" in constraints[0]
        assert "CRITICAL" not in constraints[0]

    def test_handles_multiple_allergies(self, sample_allergy):
        """Test constraint generation for multiple allergies."""
        allergy2 = {
            "code": {"coding": [{"display": "Latex"}]},
            "category": ["environment"],
        }
        constraints = _generate_allergy_constraints([sample_allergy, allergy2])

        assert len(constraints) == 2

    def test_skips_allergy_without_display(self):
        """Test skips allergies without display name."""
        allergy = {"code": {}}
        constraints = _generate_allergy_constraints([allergy])

        assert len(constraints) == 0


class TestGenerateMedicationConstraints:
    """Tests for _generate_medication_constraints helper function."""

    def test_generates_active_medication_constraint(self, sample_medication):
        """Test constraint generation for active medication."""
        constraints = _generate_medication_constraints([sample_medication])

        assert len(constraints) == 1
        assert "ACTIVE MEDICATION" in constraints[0]
        assert "Metformin 500 MG" in constraints[0]

    def test_skips_inactive_medication(self):
        """Test skips medications with non-active status."""
        med = {
            "medicationCodeableConcept": {"coding": [{"display": "Old Med"}]},
            "status": "stopped",
        }
        constraints = _generate_medication_constraints([med])

        assert len(constraints) == 0


class TestGenerateConditionConstraints:
    """Tests for _generate_condition_constraints helper function."""

    def test_generates_diabetes_constraint(self, sample_condition):
        """Test constraint generation for diabetes condition."""
        constraints = _generate_condition_constraints([sample_condition])

        assert len(constraints) == 1
        assert "CONDITION:" in constraints[0]
        assert "Type 2 diabetes mellitus" in constraints[0]
        assert "treatment implications" in constraints[0]

    def test_generates_kidney_constraint(self):
        """Test constraint generation for kidney condition."""
        condition = {
            "code": {"coding": [{"display": "Chronic kidney disease stage 3"}]}
        }
        constraints = _generate_condition_constraints([condition])

        assert len(constraints) == 1
        assert "kidney" in constraints[0].lower()

    def test_skips_generic_condition(self):
        """Test skips conditions without special treatment implications."""
        condition = {"code": {"coding": [{"display": "Common cold"}]}}
        constraints = _generate_condition_constraints([condition])

        assert len(constraints) == 0

    def test_uses_custom_significant_terms(self):
        """Test custom significant terms parameter."""
        condition = {"code": {"coding": [{"display": "Custom condition xyz"}]}}
        custom_terms = frozenset(["xyz"])
        constraints = _generate_condition_constraints([condition], custom_terms)

        assert len(constraints) == 1
        assert "xyz" in constraints[0].lower()

    def test_clinically_significant_terms_is_frozenset(self):
        """Test CLINICALLY_SIGNIFICANT_TERMS is immutable."""
        assert isinstance(CLINICALLY_SIGNIFICANT_TERMS, frozenset)
        assert "diabetes" in CLINICALLY_SIGNIFICANT_TERMS


# =============================================================================
# ContextEngine Tests
# =============================================================================


class TestBuildVerifiedLayer:
    """Tests for ContextEngine._build_verified_layer method."""

    @pytest.mark.asyncio
    async def test_builds_verified_layer_from_graph(
        self,
        context_engine,
        mock_graph,
        patient_id,
        sample_condition,
        sample_medication,
        sample_allergy,
    ):
        """Test verified layer is built from graph queries."""
        mock_graph.get_verified_conditions.return_value = [sample_condition]
        mock_graph.get_verified_medications.return_value = [sample_medication]
        mock_graph.get_verified_allergies.return_value = [sample_allergy]

        layer = await context_engine._build_verified_layer(patient_id)

        assert isinstance(layer, VerifiedLayer)
        assert len(layer.conditions) == 1
        assert len(layer.medications) == 1
        assert len(layer.allergies) == 1
        assert layer.conditions[0]["id"] == "condition-test-123"

    @pytest.mark.asyncio
    async def test_builds_empty_verified_layer(
        self,
        context_engine,
        patient_id,
    ):
        """Test verified layer is empty when graph returns nothing."""
        layer = await context_engine._build_verified_layer(patient_id)

        assert layer.conditions == []
        assert layer.medications == []
        assert layer.allergies == []
        assert layer.total_count() == 0


class TestBuildRetrievedLayer:
    """Tests for ContextEngine._build_retrieved_layer method."""

    @pytest.mark.asyncio
    async def test_builds_retrieved_layer_from_vector_search(
        self,
        context_engine,
        mock_vector_search,
        patient_id,
        sample_observation,
    ):
        """Test retrieved layer is built from vector search results."""
        search_result = SearchResult(
            resource=sample_observation,
            score=0.85,
            resource_type="Observation",
            fhir_id="obs-test-abc",
        )
        mock_vector_search.search_by_text.return_value = [search_result]

        layer = await context_engine._build_retrieved_layer(
            patient_id=patient_id,
            query="blood glucose levels",
        )

        assert isinstance(layer, RetrievedLayer)
        assert len(layer.resources) == 1
        assert layer.resources[0].score == 0.85
        assert layer.resources[0].reason == "semantic_match"

    @pytest.mark.asyncio
    async def test_returns_empty_layer_for_empty_query(
        self,
        context_engine,
        patient_id,
    ):
        """Test returns empty layer when query is empty."""
        layer = await context_engine._build_retrieved_layer(
            patient_id=patient_id,
            query="",
        )

        assert layer.resources == []

    @pytest.mark.asyncio
    async def test_handles_vector_search_error_gracefully(
        self,
        context_engine,
        mock_vector_search,
        patient_id,
    ):
        """Test handles vector search errors without crashing."""
        mock_vector_search.search_by_text.side_effect = Exception("Vector search failed")

        layer = await context_engine._build_retrieved_layer(
            patient_id=patient_id,
            query="some query",
        )

        assert layer.resources == []


class TestBuildContext:
    """Tests for ContextEngine.build_context method."""

    @pytest.mark.asyncio
    async def test_builds_complete_context(
        self,
        context_engine,
        mock_graph,
        patient_id,
        sample_condition,
        sample_medication,
        sample_allergy,
    ):
        """Test builds complete context with all layers."""
        mock_graph.get_verified_conditions.return_value = [sample_condition]
        mock_graph.get_verified_medications.return_value = [sample_medication]
        mock_graph.get_verified_allergies.return_value = [sample_allergy]

        context = await context_engine.build_context(
            patient_id=patient_id,
            query="diabetes management",
        )

        assert isinstance(context, PatientContext)
        assert context.meta.patient_id == patient_id
        assert context.meta.query == "diabetes management"
        assert len(context.verified.conditions) == 1
        assert len(context.verified.medications) == 1
        assert len(context.verified.allergies) == 1

    @pytest.mark.asyncio
    async def test_generates_constraints_from_verified_facts(
        self,
        context_engine,
        mock_graph,
        patient_id,
        sample_condition,
        sample_allergy,
    ):
        """Test generates constraints from verified clinical facts."""
        mock_graph.get_verified_conditions.return_value = [sample_condition]
        mock_graph.get_verified_allergies.return_value = [sample_allergy]

        context = await context_engine.build_context(
            patient_id=patient_id,
            query="treatment options",
        )

        # Should have allergy and condition constraints
        assert len(context.constraints) >= 2
        constraint_text = " ".join(context.constraints)
        assert "Penicillin" in constraint_text
        assert "diabetes" in constraint_text.lower()

    @pytest.mark.asyncio
    async def test_respects_token_budget(
        self,
        context_engine,
        mock_graph,
        patient_id,
    ):
        """Test context respects token budget."""
        context = await context_engine.build_context(
            patient_id=patient_id,
            query="test",
            token_budget=12000,
        )

        assert context.meta.token_budget == 12000
        assert context.within_budget()

    @pytest.mark.asyncio
    async def test_uses_default_token_budget(
        self,
        context_engine,
        patient_id,
    ):
        """Test uses default token budget when not specified."""
        context = await context_engine.build_context(
            patient_id=patient_id,
            query="test",
        )

        assert context.meta.token_budget == DEFAULT_TOKEN_BUDGET

    @pytest.mark.asyncio
    async def test_sets_retrieval_strategy(
        self,
        context_engine,
        patient_id,
    ):
        """Test sets retrieval strategy in metadata."""
        context = await context_engine.build_context(
            patient_id=patient_id,
            query="test",
        )

        assert context.meta.retrieval_strategy == "query_focused"

    @pytest.mark.asyncio
    async def test_tracks_retrieval_stats(
        self,
        context_engine,
        mock_graph,
        mock_vector_search,
        patient_id,
        sample_condition,
        sample_observation,
    ):
        """Test tracks retrieval statistics."""
        mock_graph.get_verified_conditions.return_value = [sample_condition]

        search_result = SearchResult(
            resource=sample_observation,
            score=0.85,
            resource_type="Observation",
            fhir_id="obs-test-abc",
        )
        mock_vector_search.search_by_text.return_value = [search_result]

        context = await context_engine.build_context(
            patient_id=patient_id,
            query="blood glucose",
        )

        assert context.meta.retrieval_stats.verified_count == 1
        assert context.meta.retrieval_stats.retrieved_count == 1
        assert context.meta.retrieval_stats.tokens_used > 0


class TestTrimToBudget:
    """Tests for ContextEngine._trim_to_budget method."""

    @pytest.mark.asyncio
    async def test_trims_retrieved_resources_first(
        self,
        context_engine,
        mock_graph,
        mock_vector_search,
        patient_id,
        sample_observation,
    ):
        """Test trims retrieved resources before verified resources."""
        # Create many search results
        search_results = [
            SearchResult(
                resource=sample_observation,
                score=0.8 - i * 0.01,
                resource_type="Observation",
                fhir_id=f"obs-{i}",
            )
            for i in range(50)
        ]
        mock_vector_search.search_by_text.return_value = search_results

        context = await context_engine.build_context(
            patient_id=patient_id,
            query="test",
            token_budget=1000,  # Very small budget
        )

        # Should have trimmed retrieved resources
        assert context.meta.token_budget == 1000

    @pytest.mark.asyncio
    async def test_preserves_verified_resources(
        self,
        context_engine,
        mock_graph,
        patient_id,
        sample_condition,
        sample_allergy,
    ):
        """Test preserves verified resources during trimming."""
        mock_graph.get_verified_conditions.return_value = [sample_condition]
        mock_graph.get_verified_allergies.return_value = [sample_allergy]

        context = await context_engine.build_context(
            patient_id=patient_id,
            query="test",
            token_budget=10000,
        )

        # Verified resources should be preserved
        assert len(context.verified.conditions) == 1
        assert len(context.verified.allergies) == 1


class TestBuildContextWithPatient:
    """Tests for ContextEngine.build_context_with_patient method."""

    @pytest.mark.asyncio
    async def test_uses_provided_patient_resource(
        self,
        context_engine,
        patient_id,
    ):
        """Test uses the provided patient resource."""
        patient_resource = {
            "resourceType": "Patient",
            "id": patient_id,
            "name": [{"given": ["Jane"], "family": "Doe"}],
            "birthDate": "1990-01-15",
        }

        context = await context_engine.build_context_with_patient(
            patient_id=patient_id,
            patient_resource=patient_resource,
            query="test",
        )

        assert context.patient["name"][0]["given"][0] == "Jane"
        assert context.patient["birthDate"] == "1990-01-15"

    @pytest.mark.asyncio
    async def test_includes_profile_summary(
        self,
        context_engine,
        patient_id,
    ):
        """Test includes profile summary when provided."""
        patient_resource = {"resourceType": "Patient", "id": patient_id}

        context = await context_engine.build_context_with_patient(
            patient_id=patient_id,
            patient_resource=patient_resource,
            query="test",
            profile_summary="Retired teacher who enjoys gardening.",
        )

        assert context.profile_summary == "Retired teacher who enjoys gardening."


class TestContextEngineIntegration:
    """Integration-style tests for the ContextEngine."""

    @pytest.mark.asyncio
    async def test_empty_patient_returns_minimal_context(
        self,
        context_engine,
        patient_id,
    ):
        """Test patient with no data returns minimal but valid context."""
        context = await context_engine.build_context(
            patient_id=patient_id,
            query="any query",
        )

        assert context.meta.patient_id == patient_id
        assert context.patient["resourceType"] == "Patient"
        assert context.verified.total_count() == 0
        assert context.retrieved.total_count() == 0
        assert context.constraints == []
        assert context.within_budget()

    @pytest.mark.asyncio
    async def test_context_token_estimate_is_populated(
        self,
        context_engine,
        mock_graph,
        patient_id,
        sample_condition,
    ):
        """Test token estimate is calculated and populated."""
        mock_graph.get_verified_conditions.return_value = [sample_condition]

        context = await context_engine.build_context(
            patient_id=patient_id,
            query="test",
        )

        assert context.token_estimate() > 0
        assert context.meta.retrieval_stats.tokens_used > 0
        assert context.meta.retrieval_stats.tokens_used == context.token_estimate()


class TestBuildTaskContext:
    """Tests for ContextEngine.build_task_context method."""

    @pytest.mark.asyncio
    async def test_returns_context_and_quick_actions(
        self,
        context_engine,
        patient_id,
    ):
        """Test returns a tuple of context and quick actions."""
        context, actions = await context_engine.build_task_context(
            patient_id=patient_id,
            query="review critical lab",
            task_type=TaskType.CRITICAL_LAB_REVIEW,
        )

        assert isinstance(context, PatientContext)
        assert isinstance(actions, list)
        assert all(isinstance(a, QuickAction) for a in actions)

    @pytest.mark.asyncio
    async def test_surfaces_task_defaults(
        self,
        context_engine,
        patient_id,
    ):
        """Test surfaces default actions for the task type."""
        _, actions = await context_engine.build_task_context(
            patient_id=patient_id,
            query="review critical lab",
            task_type=TaskType.CRITICAL_LAB_REVIEW,
        )

        labels = {a.label for a in actions}
        assert "Repeat stat" in labels

    @pytest.mark.asyncio
    async def test_surfaces_clinical_rule_actions(
        self,
        context_engine,
        mock_graph,
        patient_id,
    ):
        """Test surfaces clinical rule actions from verified data."""
        mock_graph.get_verified_allergies.return_value = [
            {
                "code": {"coding": [{"display": "Penicillin"}]},
                "criticality": "high",
                "category": ["medication"],
            }
        ]

        _, actions = await context_engine.build_task_context(
            patient_id=patient_id,
            query="review",
            task_type=TaskType.CRITICAL_LAB_REVIEW,
        )

        sources = {a.source.value for a in actions}
        assert "clinical_rule" in sources

    @pytest.mark.asyncio
    async def test_uses_patient_resource_when_provided(
        self,
        context_engine,
        patient_id,
    ):
        """Test uses pre-fetched patient resource."""
        patient_resource = {
            "resourceType": "Patient",
            "id": patient_id,
            "name": [{"given": ["Test"], "family": "User"}],
        }

        context, _ = await context_engine.build_task_context(
            patient_id=patient_id,
            query="test",
            task_type=TaskType.PATIENT_MESSAGE,
            patient_resource=patient_resource,
            profile_summary="Test summary",
        )

        assert context.patient["name"][0]["given"][0] == "Test"
        assert context.profile_summary == "Test summary"

    @pytest.mark.asyncio
    async def test_max_4_actions(
        self,
        context_engine,
        patient_id,
    ):
        """Test actions capped at 4."""
        ai_suggestions = [
            {"label": f"AI {i}", "type": "order"} for i in range(5)
        ]

        _, actions = await context_engine.build_task_context(
            patient_id=patient_id,
            query="test",
            task_type=TaskType.CRITICAL_LAB_REVIEW,
            ai_suggestions=ai_suggestions,
        )

        assert len(actions) <= 4
