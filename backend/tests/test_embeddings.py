"""Tests for embedding service.

Uses mock OpenAI client to avoid real API calls.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.embeddings import (
    EmbeddingService,
    EMBEDDING_DIMENSION,
    EMBEDDABLE_TYPES,
    resource_to_text,
    _template_condition,
    _template_observation,
    _template_medication_request,
    _template_allergy_intolerance,
    _template_procedure,
    _template_encounter,
    _template_diagnostic_report,
    _template_document_reference,
    _template_care_plan,
)


# =============================================================================
# Mock OpenAI Client
# =============================================================================


def create_mock_embedding(dimension: int = EMBEDDING_DIMENSION) -> list[float]:
    """Create a mock embedding vector."""
    return [0.1] * dimension


def create_mock_openai_client(num_embeddings: int = 1) -> AsyncMock:
    """Create a mock AsyncOpenAI client that returns fake embeddings."""
    mock_client = AsyncMock()

    # Create mock response structure
    mock_response = MagicMock()
    mock_response.data = [
        MagicMock(embedding=create_mock_embedding()) for _ in range(num_embeddings)
    ]

    # Set up the embeddings.create method
    mock_client.embeddings.create = AsyncMock(return_value=mock_response)

    return mock_client


# =============================================================================
# Template Function Tests
# =============================================================================


class TestTemplateCondition:
    """Tests for _template_condition."""

    def test_basic_condition(self):
        """Test templating a basic Condition resource."""
        resource = {
            "resourceType": "Condition",
            "code": {
                "coding": [{"display": "Type 2 Diabetes Mellitus"}]
            },
            "clinicalStatus": {"coding": [{"code": "active"}]},
            "onsetDateTime": "2020-01-15",
        }
        result = _template_condition(resource)

        assert "Condition: Type 2 Diabetes Mellitus" in result
        assert "Status: active" in result
        assert "Onset: 2020-01-15" in result

    def test_condition_with_text_fallback(self):
        """Test condition using text field when no coding."""
        resource = {
            "resourceType": "Condition",
            "code": {"text": "High blood pressure"},
        }
        result = _template_condition(resource)

        assert "Condition: High blood pressure" in result

    def test_minimal_condition(self):
        """Test condition with minimal data."""
        resource = {
            "resourceType": "Condition",
            "code": {},
        }
        result = _template_condition(resource)

        assert "Condition:" in result


class TestTemplateObservation:
    """Tests for _template_observation."""

    def test_observation_with_quantity(self):
        """Test observation with valueQuantity."""
        resource = {
            "resourceType": "Observation",
            "code": {"coding": [{"display": "Systolic Blood Pressure"}]},
            "valueQuantity": {"value": 120, "unit": "mmHg"},
            "status": "final",
            "effectiveDateTime": "2024-01-15",
        }
        result = _template_observation(resource)

        assert "Observation: Systolic Blood Pressure" in result
        assert "Value: 120 mmHg" in result
        assert "Status: final" in result
        assert "Date: 2024-01-15" in result

    def test_observation_with_codeable_concept(self):
        """Test observation with valueCodeableConcept."""
        resource = {
            "resourceType": "Observation",
            "code": {"coding": [{"display": "Blood Type"}]},
            "valueCodeableConcept": {"coding": [{"display": "A positive"}]},
        }
        result = _template_observation(resource)

        assert "Value: A positive" in result

    def test_observation_with_string_value(self):
        """Test observation with valueString."""
        resource = {
            "resourceType": "Observation",
            "code": {"coding": [{"display": "Clinical Note"}]},
            "valueString": "Patient reports feeling better",
        }
        result = _template_observation(resource)

        assert "Value: Patient reports feeling better" in result

    def test_observation_with_boolean(self):
        """Test observation with valueBoolean."""
        resource = {
            "resourceType": "Observation",
            "code": {"coding": [{"display": "Pregnancy Test"}]},
            "valueBoolean": True,
        }
        result = _template_observation(resource)

        assert "Value: positive" in result


class TestTemplateMedicationRequest:
    """Tests for _template_medication_request."""

    def test_basic_medication(self):
        """Test templating a basic MedicationRequest."""
        resource = {
            "resourceType": "MedicationRequest",
            "medicationCodeableConcept": {
                "coding": [{"display": "Metformin 500 MG Oral Tablet"}]
            },
            "status": "active",
            "authoredOn": "2024-01-15",
        }
        result = _template_medication_request(resource)

        assert "Medication: Metformin 500 MG Oral Tablet" in result
        assert "Status: active" in result
        assert "Prescribed: 2024-01-15" in result

    def test_medication_with_dosage(self):
        """Test medication with dosage instructions."""
        resource = {
            "resourceType": "MedicationRequest",
            "medicationCodeableConcept": {
                "coding": [{"display": "Lisinopril 10 MG"}]
            },
            "status": "active",
            "dosageInstruction": [{"text": "Take once daily in the morning"}],
        }
        result = _template_medication_request(resource)

        assert "Dosage: Take once daily in the morning" in result


class TestTemplateAllergyIntolerance:
    """Tests for _template_allergy_intolerance."""

    def test_basic_allergy(self):
        """Test templating a basic AllergyIntolerance."""
        resource = {
            "resourceType": "AllergyIntolerance",
            "code": {"coding": [{"display": "Penicillin"}]},
            "clinicalStatus": {"coding": [{"code": "active"}]},
            "criticality": "high",
            "category": ["medication"],
        }
        result = _template_allergy_intolerance(resource)

        assert "Allergy: Penicillin" in result
        assert "Status: active" in result
        assert "Criticality: high" in result
        assert "Category: medication" in result

    def test_allergy_with_reactions(self):
        """Test allergy with reaction manifestations."""
        resource = {
            "resourceType": "AllergyIntolerance",
            "code": {"coding": [{"display": "Peanuts"}]},
            "reaction": [
                {
                    "manifestation": [
                        {"coding": [{"display": "Hives"}]},
                        {"coding": [{"display": "Anaphylaxis"}]},
                    ]
                }
            ],
        }
        result = _template_allergy_intolerance(resource)

        assert "Reactions: Hives, Anaphylaxis" in result


class TestTemplateProcedure:
    """Tests for _template_procedure."""

    def test_basic_procedure(self):
        """Test templating a basic Procedure."""
        resource = {
            "resourceType": "Procedure",
            "code": {"coding": [{"display": "Appendectomy"}]},
            "status": "completed",
            "performedDateTime": "2024-01-15T10:00:00Z",
        }
        result = _template_procedure(resource)

        assert "Procedure: Appendectomy" in result
        assert "Status: completed" in result
        assert "Performed: 2024-01-15T10:00:00Z" in result

    def test_procedure_with_period(self):
        """Test procedure with performedPeriod instead of dateTime."""
        resource = {
            "resourceType": "Procedure",
            "code": {"coding": [{"display": "Physical Therapy"}]},
            "status": "completed",
            "performedPeriod": {"start": "2024-01-15", "end": "2024-02-15"},
        }
        result = _template_procedure(resource)

        assert "Performed: 2024-01-15" in result

    def test_procedure_with_body_site(self):
        """Test procedure with body site."""
        resource = {
            "resourceType": "Procedure",
            "code": {"coding": [{"display": "Knee replacement"}]},
            "status": "completed",
            "bodySite": [{"coding": [{"display": "Left knee"}]}],
        }
        result = _template_procedure(resource)

        assert "Body site: Left knee" in result


class TestTemplateEncounter:
    """Tests for _template_encounter."""

    def test_basic_encounter(self):
        """Test templating a basic Encounter."""
        resource = {
            "resourceType": "Encounter",
            "type": [{"coding": [{"display": "Office visit"}]}],
            "status": "finished",
            "class": {"code": "AMB"},
            "period": {"start": "2024-01-15T09:00:00Z"},
        }
        result = _template_encounter(resource)

        assert "Encounter: Office visit" in result
        assert "Status: finished" in result
        assert "Class: AMB" in result
        assert "Date: 2024-01-15T09:00:00Z" in result

    def test_encounter_with_reason(self):
        """Test encounter with reason code."""
        resource = {
            "resourceType": "Encounter",
            "type": [{"coding": [{"display": "Emergency visit"}]}],
            "status": "finished",
            "reasonCode": [{"coding": [{"display": "Chest pain"}]}],
        }
        result = _template_encounter(resource)

        assert "Reason: Chest pain" in result

    def test_encounter_without_type(self):
        """Test encounter without type defaults to 'Visit'."""
        resource = {
            "resourceType": "Encounter",
            "status": "finished",
        }
        result = _template_encounter(resource)

        assert "Encounter: Visit" in result


class TestTemplateDiagnosticReport:
    """Tests for _template_diagnostic_report."""

    def test_basic_report(self):
        """Test templating a basic DiagnosticReport."""
        resource = {
            "resourceType": "DiagnosticReport",
            "code": {"coding": [{"display": "Complete Blood Count"}]},
            "status": "final",
            "effectiveDateTime": "2024-01-15",
        }
        result = _template_diagnostic_report(resource)

        assert "Diagnostic Report: Complete Blood Count" in result
        assert "Status: final" in result
        assert "Date: 2024-01-15" in result

    def test_report_with_conclusion(self):
        """Test report with conclusion."""
        resource = {
            "resourceType": "DiagnosticReport",
            "code": {"coding": [{"display": "Chest X-Ray"}]},
            "status": "final",
            "conclusion": "No acute findings",
        }
        result = _template_diagnostic_report(resource)

        assert "Conclusion: No acute findings" in result

    def test_report_with_category(self):
        """Test report with category."""
        resource = {
            "resourceType": "DiagnosticReport",
            "code": {"coding": [{"display": "Metabolic Panel"}]},
            "category": [{"coding": [{"display": "Laboratory"}]}],
            "status": "final",
        }
        result = _template_diagnostic_report(resource)

        assert "Category: Laboratory" in result


class TestTemplateDocumentReference:
    """Tests for _template_document_reference."""

    def test_basic_document(self):
        """Test templating a basic DocumentReference."""
        resource = {
            "resourceType": "DocumentReference",
            "type": {"coding": [{"display": "Discharge Summary"}]},
            "status": "current",
            "date": "2024-01-15T10:00:00Z",
        }
        result = _template_document_reference(resource)

        assert "Document: Discharge Summary" in result
        assert "Status: current" in result
        assert "Date: 2024-01-15T10:00:00Z" in result

    def test_document_with_description(self):
        """Test document with description."""
        resource = {
            "resourceType": "DocumentReference",
            "type": {"coding": [{"display": "Clinical Note"}]},
            "status": "current",
            "description": "Follow-up visit notes for diabetes management",
        }
        result = _template_document_reference(resource)

        assert "Description: Follow-up visit notes for diabetes management" in result

    def test_document_without_type(self):
        """Test document without type defaults to 'Clinical Document'."""
        resource = {
            "resourceType": "DocumentReference",
            "status": "current",
        }
        result = _template_document_reference(resource)

        assert "Document: Clinical Document" in result


class TestTemplateCarePlan:
    """Tests for _template_care_plan."""

    def test_basic_care_plan(self):
        """Test templating a basic CarePlan."""
        resource = {
            "resourceType": "CarePlan",
            "title": "Diabetes Management Plan",
            "status": "active",
            "intent": "plan",
            "period": {"start": "2024-01-15"},
        }
        result = _template_care_plan(resource)

        assert "Care Plan: Diabetes Management Plan" in result
        assert "Status: active" in result
        assert "Intent: plan" in result
        assert "Start: 2024-01-15" in result

    def test_care_plan_with_categories(self):
        """Test care plan with categories."""
        resource = {
            "resourceType": "CarePlan",
            "title": "Treatment Plan",
            "status": "active",
            "category": [
                {"coding": [{"display": "Longitudinal care plan"}]},
            ],
        }
        result = _template_care_plan(resource)

        assert "Categories: Longitudinal care plan" in result

    def test_care_plan_with_activities(self):
        """Test care plan with activities."""
        resource = {
            "resourceType": "CarePlan",
            "title": "Weight Loss Plan",
            "status": "active",
            "activity": [
                {"detail": {"description": "Exercise 30 minutes daily"}},
                {"detail": {"code": {"coding": [{"display": "Dietary counseling"}]}}},
            ],
        }
        result = _template_care_plan(resource)

        assert "Activities:" in result
        assert "Exercise 30 minutes daily" in result
        assert "Dietary counseling" in result

    def test_care_plan_without_title(self):
        """Test care plan without title defaults to 'Treatment Plan'."""
        resource = {
            "resourceType": "CarePlan",
            "status": "active",
        }
        result = _template_care_plan(resource)

        assert "Care Plan: Treatment Plan" in result


# =============================================================================
# resource_to_text Tests
# =============================================================================


class TestResourceToText:
    """Tests for resource_to_text function."""

    def test_embeddable_types(self):
        """Test that all embeddable types are handled."""
        expected_types = {
            "Condition",
            "Observation",
            "MedicationRequest",
            "AllergyIntolerance",
            "Procedure",
            "Encounter",
            "DiagnosticReport",
            "DocumentReference",
            "CarePlan",
            "Immunization",
            "ImagingStudy",
            "MedicationAdministration",
            "Medication",
            "Device",
            "CareTeam",
            "Claim",
            "ExplanationOfBenefit",
            "SupplyDelivery",
            "Patient",
        }
        assert EMBEDDABLE_TYPES == expected_types

    def test_returns_none_for_unsupported_type(self):
        """Test that unsupported types return None."""
        resource = {
            "resourceType": "Organization",
            "name": "Hospital",
        }
        result = resource_to_text(resource)
        assert result is None

    def test_returns_none_for_missing_type(self):
        """Test that resources without type return None."""
        resource = {"code": {"coding": [{"display": "Test"}]}}
        result = resource_to_text(resource)
        assert result is None

    def test_converts_condition(self):
        """Test converting a Condition resource."""
        resource = {
            "resourceType": "Condition",
            "code": {"coding": [{"display": "Hypertension"}]},
        }
        result = resource_to_text(resource)
        assert result is not None
        assert "Condition: Hypertension" in result


# =============================================================================
# EmbeddingService Tests
# =============================================================================


class TestEmbeddingService:
    """Tests for EmbeddingService class."""

    @pytest.mark.asyncio
    async def test_embed_text_single(self):
        """Test embedding a single text."""
        mock_client = create_mock_openai_client(num_embeddings=1)
        service = EmbeddingService(client=mock_client)

        result = await service.embed_text("Hello world")

        assert len(result) == EMBEDDING_DIMENSION
        mock_client.embeddings.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_texts_batch(self):
        """Test embedding multiple texts in a batch."""
        texts = ["Hello", "World", "Test"]
        mock_client = create_mock_openai_client(num_embeddings=3)
        service = EmbeddingService(client=mock_client)

        results = await service.embed_texts(texts)

        assert len(results) == 3
        assert all(len(emb) == EMBEDDING_DIMENSION for emb in results)
        mock_client.embeddings.create.assert_called_once()

    @pytest.mark.asyncio
    async def test_embed_texts_empty_raises(self):
        """Test that empty texts list raises ValueError."""
        mock_client = create_mock_openai_client()
        service = EmbeddingService(client=mock_client)

        with pytest.raises(ValueError, match="texts list cannot be empty"):
            await service.embed_texts([])

    @pytest.mark.asyncio
    async def test_embed_texts_batching(self):
        """Test that large text lists are batched correctly."""
        # Create 150 texts, which should be split into 2 batches with batch_size=100
        texts = [f"Text {i}" for i in range(150)]

        # Mock client that returns correct number of embeddings per call
        mock_client = AsyncMock()

        call_count = 0

        async def mock_create(model, input):
            nonlocal call_count
            call_count += 1
            mock_response = MagicMock()
            mock_response.data = [
                MagicMock(embedding=create_mock_embedding()) for _ in input
            ]
            return mock_response

        mock_client.embeddings.create = mock_create

        service = EmbeddingService(client=mock_client, model="text-embedding-3-small")
        results = await service.embed_texts(texts, batch_size=100)

        assert len(results) == 150
        assert call_count == 2  # Should have made 2 API calls

    @pytest.mark.asyncio
    async def test_embed_resource_condition(self):
        """Test embedding a FHIR Condition resource."""
        mock_client = create_mock_openai_client(num_embeddings=1)
        service = EmbeddingService(client=mock_client)

        resource = {
            "resourceType": "Condition",
            "code": {"coding": [{"display": "Type 2 Diabetes"}]},
            "clinicalStatus": {"coding": [{"code": "active"}]},
        }

        result = await service.embed_resource(resource)

        assert result is not None
        assert len(result) == EMBEDDING_DIMENSION

        # Verify the text passed to the API contains expected content
        call_args = mock_client.embeddings.create.call_args
        input_text = call_args.kwargs["input"][0]
        assert "Condition: Type 2 Diabetes" in input_text
        assert "Status: active" in input_text

    @pytest.mark.asyncio
    async def test_embed_resource_unsupported_returns_none(self):
        """Test that unsupported resource types return None."""
        mock_client = create_mock_openai_client()
        service = EmbeddingService(client=mock_client)

        resource = {
            "resourceType": "Organization",
            "name": "Hospital",
        }

        result = await service.embed_resource(resource)

        assert result is None
        mock_client.embeddings.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_embed_resources_batch(self):
        """Test embedding multiple FHIR resources."""
        mock_client = create_mock_openai_client(num_embeddings=2)
        service = EmbeddingService(client=mock_client)

        resources = [
            {
                "resourceType": "Condition",
                "code": {"coding": [{"display": "Hypertension"}]},
            },
            {
                "resourceType": "Observation",
                "code": {"coding": [{"display": "Blood Pressure"}]},
                "valueQuantity": {"value": 120, "unit": "mmHg"},
            },
        ]

        results = await service.embed_resources(resources)

        assert len(results) == 2
        assert results[0][0]["resourceType"] == "Condition"
        assert results[1][0]["resourceType"] == "Observation"
        assert all(len(emb) == EMBEDDING_DIMENSION for _, emb in results)

    @pytest.mark.asyncio
    async def test_embed_resources_filters_unsupported(self):
        """Test that unsupported resources are filtered out."""
        mock_client = create_mock_openai_client(num_embeddings=1)
        service = EmbeddingService(client=mock_client)

        resources = [
            {
                "resourceType": "Provenance",  # Unsupported
                "target": [{"reference": "Patient/pat-1"}],
            },
            {
                "resourceType": "Condition",  # Supported
                "code": {"coding": [{"display": "Diabetes"}]},
            },
            {
                "resourceType": "Organization",  # Unsupported
                "name": "Hospital",
            },
        ]

        results = await service.embed_resources(resources)

        # Only the Condition should be embedded
        assert len(results) == 1
        assert results[0][0]["resourceType"] == "Condition"

    @pytest.mark.asyncio
    async def test_embed_resources_empty_returns_empty(self):
        """Test that empty resource list returns empty list."""
        mock_client = create_mock_openai_client()
        service = EmbeddingService(client=mock_client)

        results = await service.embed_resources([])

        assert results == []
        mock_client.embeddings.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_embed_resources_all_unsupported_returns_empty(self):
        """Test that list of only unsupported resources returns empty."""
        mock_client = create_mock_openai_client()
        service = EmbeddingService(client=mock_client)

        resources = [
            {"resourceType": "Provenance", "target": [{"reference": "Patient/pat-1"}]},
            {"resourceType": "Organization", "name": "Hospital"},
        ]

        results = await service.embed_resources(resources)

        assert results == []
        mock_client.embeddings.create.assert_not_called()

    @pytest.mark.asyncio
    async def test_uses_custom_model(self):
        """Test that custom model parameter is used."""
        mock_client = create_mock_openai_client(num_embeddings=1)
        custom_model = "text-embedding-3-large"
        service = EmbeddingService(client=mock_client, model=custom_model)

        await service.embed_text("Test")

        call_args = mock_client.embeddings.create.call_args
        assert call_args.kwargs["model"] == custom_model
