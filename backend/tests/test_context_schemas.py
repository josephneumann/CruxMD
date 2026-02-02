"""Tests for PatientContext schemas."""

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.schemas.context import (
    ContextMeta,
    PatientContext,
    RetrievalStats,
    RetrievedLayer,
    RetrievedResource,
    VerifiedLayer,
)


# =============================================================================
# Test Data Fixtures
# =============================================================================


@pytest.fixture
def sample_fhir_patient() -> dict:
    """Sample FHIR Patient resource."""
    return {
        "resourceType": "Patient",
        "id": "patient-123",
        "name": [{"given": ["John"], "family": "Doe"}],
        "birthDate": "1965-04-15",
        "gender": "male",
    }


@pytest.fixture
def sample_fhir_condition() -> dict:
    """Sample FHIR Condition resource."""
    return {
        "resourceType": "Condition",
        "id": "condition-456",
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
def sample_fhir_medication() -> dict:
    """Sample FHIR MedicationRequest resource."""
    return {
        "resourceType": "MedicationRequest",
        "id": "medication-789",
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
def sample_fhir_allergy() -> dict:
    """Sample FHIR AllergyIntolerance resource."""
    return {
        "resourceType": "AllergyIntolerance",
        "id": "allergy-abc",
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
        "criticality": "high",
    }


@pytest.fixture
def sample_fhir_observation() -> dict:
    """Sample FHIR Observation resource."""
    return {
        "resourceType": "Observation",
        "id": "observation-xyz",
        "code": {
            "coding": [
                {
                    "system": "http://loinc.org",
                    "code": "4548-4",
                    "display": "Hemoglobin A1c",
                }
            ]
        },
        "status": "final",
        "valueQuantity": {"value": 7.2, "unit": "%"},
    }


# =============================================================================
# RetrievalStats Tests
# =============================================================================


def test_retrieval_stats_defaults():
    """RetrievalStats should have sensible defaults."""
    stats = RetrievalStats()
    assert stats.verified_count == 0
    assert stats.retrieved_count == 0
    assert stats.tokens_used == 0


def test_retrieval_stats_defaults_graph_traversal_count():
    """RetrievalStats should default graph_traversal_count to 0."""
    stats = RetrievalStats()
    assert stats.graph_traversal_count == 0


def test_retrieval_stats_with_values():
    """RetrievalStats should accept custom values."""
    stats = RetrievalStats(verified_count=5, retrieved_count=10, tokens_used=1500)
    assert stats.verified_count == 5
    assert stats.retrieved_count == 10
    assert stats.tokens_used == 1500


def test_retrieval_stats_with_graph_traversal_count():
    """RetrievalStats should accept graph_traversal_count."""
    stats = RetrievalStats(graph_traversal_count=3, verified_count=5)
    assert stats.graph_traversal_count == 3
    assert stats.verified_count == 5


# =============================================================================
# ContextMeta Tests
# =============================================================================


def test_context_meta_required_fields():
    """ContextMeta requires patient_id."""
    with pytest.raises(ValidationError):
        ContextMeta()


def test_context_meta_minimal():
    """ContextMeta can be created with just patient_id."""
    meta = ContextMeta(patient_id="patient-123")
    assert meta.patient_id == "patient-123"
    assert meta.query == ""
    assert meta.retrieval_strategy == "query_focused"
    assert meta.token_budget == 6000
    assert isinstance(meta.timestamp, datetime)


def test_context_meta_full():
    """ContextMeta accepts all fields."""
    ts = datetime(2024, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    meta = ContextMeta(
        patient_id="patient-456",
        query="What medications is the patient taking?",
        timestamp=ts,
        retrieval_strategy="comprehensive",
        token_budget=8000,
        retrieval_stats=RetrievalStats(verified_count=3, retrieved_count=7),
    )
    assert meta.patient_id == "patient-456"
    assert meta.query == "What medications is the patient taking?"
    assert meta.timestamp == ts
    assert meta.retrieval_strategy == "comprehensive"
    assert meta.token_budget == 8000
    assert meta.retrieval_stats.verified_count == 3


def test_context_meta_serialization():
    """ContextMeta should serialize to dict/JSON."""
    meta = ContextMeta(patient_id="patient-123", query="test query")
    data = meta.model_dump()
    assert data["patient_id"] == "patient-123"
    assert data["query"] == "test query"
    assert "timestamp" in data
    assert "retrieval_stats" in data


# =============================================================================
# VerifiedLayer Tests
# =============================================================================


def test_verified_layer_empty():
    """VerifiedLayer should work with empty lists."""
    verified = VerifiedLayer()
    assert verified.conditions == []
    assert verified.medications == []
    assert verified.allergies == []
    assert verified.token_estimate() == 0
    assert verified.total_count() == 0


def test_verified_layer_with_resources(
    sample_fhir_condition, sample_fhir_medication, sample_fhir_allergy
):
    """VerifiedLayer should hold FHIR resources."""
    verified = VerifiedLayer(
        conditions=[sample_fhir_condition],
        medications=[sample_fhir_medication],
        allergies=[sample_fhir_allergy],
    )
    assert len(verified.conditions) == 1
    assert len(verified.medications) == 1
    assert len(verified.allergies) == 1
    assert verified.total_count() == 3
    assert verified.conditions[0]["resourceType"] == "Condition"


def test_verified_layer_token_estimate(sample_fhir_condition):
    """VerifiedLayer should estimate tokens."""
    verified = VerifiedLayer(conditions=[sample_fhir_condition])
    estimate = verified.token_estimate()
    # Should be roughly len(json.dumps(condition)) / 4
    assert estimate > 0
    assert estimate < 500  # Sanity check


def test_verified_layer_serialization(sample_fhir_condition):
    """VerifiedLayer should serialize preserving FHIR structure."""
    verified = VerifiedLayer(conditions=[sample_fhir_condition])
    data = verified.model_dump()
    assert data["conditions"][0]["resourceType"] == "Condition"
    assert data["conditions"][0]["code"]["coding"][0]["display"] == "Type 2 diabetes mellitus"


# =============================================================================
# RetrievedResource Tests
# =============================================================================


def test_retrieved_resource_required_fields(sample_fhir_observation):
    """RetrievedResource requires resource and resource_type."""
    with pytest.raises(ValidationError):
        RetrievedResource()

    # Should work with required fields
    rr = RetrievedResource(resource=sample_fhir_observation, resource_type="Observation")
    assert rr.resource["id"] == "observation-xyz"
    assert rr.resource_type == "Observation"
    assert rr.score == 0.0
    assert rr.reason == "semantic_match"


def test_retrieved_resource_full(sample_fhir_observation):
    """RetrievedResource accepts all fields."""
    rr = RetrievedResource(
        resource=sample_fhir_observation,
        resource_type="Observation",
        score=0.85,
        reason="query_focus",
    )
    assert rr.score == 0.85
    assert rr.reason == "query_focus"


def test_retrieved_resource_graph_traversal_reason(sample_fhir_observation):
    """RetrievedResource accepts graph_traversal as a reason."""
    rr = RetrievedResource(
        resource=sample_fhir_observation,
        resource_type="Observation",
        score=0.95,
        reason="graph_traversal",
    )
    assert rr.reason == "graph_traversal"


def test_retrieved_resource_score_validation(sample_fhir_observation):
    """RetrievedResource score must be 0.0-1.0."""
    with pytest.raises(ValidationError):
        RetrievedResource(
            resource=sample_fhir_observation,
            resource_type="Observation",
            score=1.5,  # Invalid: > 1.0
        )

    with pytest.raises(ValidationError):
        RetrievedResource(
            resource=sample_fhir_observation,
            resource_type="Observation",
            score=-0.1,  # Invalid: < 0.0
        )


def test_retrieved_resource_token_estimate(sample_fhir_observation):
    """RetrievedResource should estimate tokens."""
    rr = RetrievedResource(resource=sample_fhir_observation, resource_type="Observation")
    estimate = rr.token_estimate()
    assert estimate > 0


# =============================================================================
# RetrievedLayer Tests
# =============================================================================


def test_retrieved_layer_empty():
    """RetrievedLayer should work with empty resources."""
    retrieved = RetrievedLayer()
    assert retrieved.resources == []
    assert retrieved.token_estimate() == 0
    assert retrieved.total_count() == 0


def test_retrieved_layer_with_resources(sample_fhir_observation):
    """RetrievedLayer should hold RetrievedResource items."""
    rr = RetrievedResource(
        resource=sample_fhir_observation,
        resource_type="Observation",
        score=0.9,
    )
    retrieved = RetrievedLayer(resources=[rr])
    assert retrieved.total_count() == 1
    assert retrieved.token_estimate() > 0


# =============================================================================
# PatientContext Tests
# =============================================================================


def test_patient_context_required_fields(sample_fhir_patient):
    """PatientContext requires meta and patient."""
    with pytest.raises(ValidationError):
        PatientContext()

    with pytest.raises(ValidationError):
        PatientContext(meta=ContextMeta(patient_id="123"))  # Missing patient

    # Should work with required fields
    ctx = PatientContext(
        meta=ContextMeta(patient_id="123"),
        patient=sample_fhir_patient,
    )
    assert ctx.patient["resourceType"] == "Patient"


def test_patient_context_defaults(sample_fhir_patient):
    """PatientContext should have sensible defaults."""
    ctx = PatientContext(
        meta=ContextMeta(patient_id="123"),
        patient=sample_fhir_patient,
    )
    assert ctx.profile_summary is None
    assert ctx.verified.conditions == []
    assert ctx.retrieved.resources == []
    assert ctx.constraints == []


def test_patient_context_full(
    sample_fhir_patient,
    sample_fhir_condition,
    sample_fhir_medication,
    sample_fhir_allergy,
    sample_fhir_observation,
):
    """PatientContext should accept all fields."""
    ctx = PatientContext(
        meta=ContextMeta(
            patient_id="patient-123",
            query="What is the patient's diabetes management?",
            token_budget=8000,
        ),
        patient=sample_fhir_patient,
        profile_summary="John is a 59-year-old retired teacher who enjoys gardening.",
        verified=VerifiedLayer(
            conditions=[sample_fhir_condition],
            medications=[sample_fhir_medication],
            allergies=[sample_fhir_allergy],
        ),
        retrieved=RetrievedLayer(
            resources=[
                RetrievedResource(
                    resource=sample_fhir_observation,
                    resource_type="Observation",
                    score=0.92,
                    reason="query_focus",
                )
            ]
        ),
        constraints=["ALLERGY: Do not recommend Penicillin or related antibiotics"],
    )
    assert ctx.meta.query == "What is the patient's diabetes management?"
    assert ctx.profile_summary is not None
    assert ctx.verified.total_count() == 3
    assert ctx.retrieved.total_count() == 1
    assert len(ctx.constraints) == 1


def test_patient_context_token_estimate(sample_fhir_patient, sample_fhir_condition):
    """PatientContext should estimate total tokens."""
    ctx = PatientContext(
        meta=ContextMeta(patient_id="123", token_budget=6000),
        patient=sample_fhir_patient,
        profile_summary="A brief profile.",
        verified=VerifiedLayer(conditions=[sample_fhir_condition]),
        constraints=["Some constraint"],
    )
    estimate = ctx.token_estimate()
    assert estimate > 0
    # Should be sum of patient + profile + verified + retrieved + constraints
    assert estimate < 1000  # Sanity check for small test data


def test_patient_context_within_budget(sample_fhir_patient):
    """PatientContext should check if within token budget."""
    ctx = PatientContext(
        meta=ContextMeta(patient_id="123", token_budget=6000),
        patient=sample_fhir_patient,
    )
    assert ctx.within_budget() is True

    # Create a context that exceeds budget
    ctx_over = PatientContext(
        meta=ContextMeta(patient_id="123", token_budget=1),  # Very small budget
        patient=sample_fhir_patient,
    )
    assert ctx_over.within_budget() is False


def test_patient_context_serialization(sample_fhir_patient, sample_fhir_condition):
    """PatientContext should serialize to dict preserving structure."""
    ctx = PatientContext(
        meta=ContextMeta(patient_id="123"),
        patient=sample_fhir_patient,
        verified=VerifiedLayer(conditions=[sample_fhir_condition]),
    )
    data = ctx.model_dump()

    assert data["meta"]["patient_id"] == "123"
    assert data["patient"]["resourceType"] == "Patient"
    assert data["verified"]["conditions"][0]["resourceType"] == "Condition"
    assert "retrieved" in data
    assert "constraints" in data


def test_patient_context_json_round_trip(sample_fhir_patient, sample_fhir_condition):
    """PatientContext should survive JSON serialization round trip."""
    ctx = PatientContext(
        meta=ContextMeta(patient_id="123", query="test"),
        patient=sample_fhir_patient,
        verified=VerifiedLayer(conditions=[sample_fhir_condition]),
        constraints=["No penicillin"],
    )

    # Serialize to JSON string
    json_str = ctx.model_dump_json()

    # Deserialize back
    ctx_restored = PatientContext.model_validate_json(json_str)

    assert ctx_restored.meta.patient_id == ctx.meta.patient_id
    assert ctx_restored.meta.query == ctx.meta.query
    assert ctx_restored.patient["id"] == ctx.patient["id"]
    assert len(ctx_restored.verified.conditions) == 1
    assert ctx_restored.constraints == ["No penicillin"]
