"""Tests for agent_tools module.

Uses mocked KnowledgeGraph and AsyncSession to test tool formatting
and logic without requiring Neo4j or Postgres.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class AsyncIterator:
    """Helper to create an async iterator from a list."""

    def __init__(self, items):
        self._items = iter(items)

    def __aiter__(self):
        return self

    async def __anext__(self):
        try:
            return next(self._items)
        except StopIteration:
            raise StopAsyncIteration

from app.services.agent_tools import (
    _format_resource_summary,
    search_patient_data,
    get_encounter_details,
    get_lab_history,
    find_related_resources,
    get_patient_timeline,
)


# =============================================================================
# _format_resource_summary tests
# =============================================================================


class TestFormatResourceSummary:
    def test_condition(self):
        resource = {
            "resourceType": "Condition",
            "code": {"coding": [{"display": "Hypertension"}]},
            "clinicalStatus": {"coding": [{"code": "active"}]},
            "onsetDateTime": "2024-01-15T09:00:00Z",
        }
        result = _format_resource_summary(resource)
        assert "Condition: Hypertension" in result
        assert "[active]" in result
        assert "2024-01-15" in result

    def test_observation(self):
        resource = {
            "resourceType": "Observation",
            "code": {"coding": [{"display": "Systolic blood pressure"}]},
            "valueQuantity": {"value": 140, "unit": "mmHg"},
            "effectiveDateTime": "2024-01-15T09:00:00Z",
        }
        result = _format_resource_summary(resource)
        assert "Observation: Systolic blood pressure" in result
        assert "140 mmHg" in result

    def test_medication(self):
        resource = {
            "resourceType": "MedicationRequest",
            "medicationCodeableConcept": {"coding": [{"display": "Lisinopril 10 MG"}]},
            "status": "active",
            "authoredOn": "2024-01-15",
        }
        result = _format_resource_summary(resource)
        assert "Medication: Lisinopril 10 MG" in result
        assert "[active]" in result

    def test_encounter(self):
        resource = {
            "resourceType": "Encounter",
            "type": [{"coding": [{"display": "Outpatient visit"}]}],
            "period": {"start": "2024-01-15T09:00:00Z"},
        }
        result = _format_resource_summary(resource)
        assert "Encounter: Outpatient visit" in result
        assert "2024-01-15" in result

    def test_procedure(self):
        resource = {
            "resourceType": "Procedure",
            "code": {"coding": [{"display": "Blood pressure monitoring"}]},
            "performedDateTime": "2024-01-15T10:00:00Z",
        }
        result = _format_resource_summary(resource)
        assert "Procedure: Blood pressure monitoring" in result

    def test_diagnostic_report(self):
        resource = {
            "resourceType": "DiagnosticReport",
            "code": {"coding": [{"display": "Comprehensive metabolic panel"}]},
            "effectiveDateTime": "2024-01-15T09:00:00Z",
        }
        result = _format_resource_summary(resource)
        assert "Diagnostic Report: Comprehensive metabolic panel" in result

    def test_allergy(self):
        resource = {
            "resourceType": "AllergyIntolerance",
            "code": {"coding": [{"display": "Penicillin"}]},
            "criticality": "high",
        }
        result = _format_resource_summary(resource)
        assert "Allergy: Penicillin" in result
        assert "high criticality" in result

    def test_unknown_type(self):
        resource = {"resourceType": "Coverage", "id": "cov-1"}
        result = _format_resource_summary(resource)
        assert "Coverage" in result


# =============================================================================
# search_patient_data tests
# =============================================================================


class TestSearchPatientData:
    @pytest.mark.asyncio
    async def test_returns_formatted_results(self):
        graph = AsyncMock()
        graph.search_nodes_by_name.return_value = [
            {"fhir_id": "cond-1", "resource_type": "Condition"},
        ]

        mock_row = MagicMock()
        mock_row.fhir_id = "cond-1"
        mock_row.data = {
            "resourceType": "Condition",
            "code": {"coding": [{"display": "Diabetes"}]},
            "clinicalStatus": {"coding": [{"code": "active"}]},
        }

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [mock_row]
        db = AsyncMock()
        db.execute.return_value = mock_result

        result = await search_patient_data("patient-1", "diabetes", graph, db)
        assert "diabetes" in result.lower()
        assert "Diabetes" in result
        assert "1 found" in result

    @pytest.mark.asyncio
    async def test_empty_query(self):
        graph = AsyncMock()
        db = AsyncMock()
        result = await search_patient_data("patient-1", "   ", graph, db)
        assert "No search terms" in result

    @pytest.mark.asyncio
    async def test_no_matches(self):
        graph = AsyncMock()
        graph.search_nodes_by_name.return_value = []
        db = AsyncMock()
        result = await search_patient_data("patient-1", "nonexistent", graph, db)
        assert "No resources found" in result


# =============================================================================
# get_encounter_details tests
# =============================================================================


class TestGetEncounterDetails:
    @pytest.mark.asyncio
    async def test_returns_formatted_events(self):
        graph = AsyncMock()
        graph.get_encounter_events.return_value = {
            "conditions": [
                {
                    "resourceType": "Condition",
                    "code": {"coding": [{"display": "Hypertension"}]},
                    "clinicalStatus": {"coding": [{"code": "active"}]},
                }
            ],
            "medications": [],
            "observations": [
                {
                    "resourceType": "Observation",
                    "code": {"coding": [{"display": "BP"}]},
                    "valueQuantity": {"value": 140, "unit": "mmHg"},
                    "effectiveDateTime": "2024-01-15",
                }
            ],
            "procedures": [],
            "diagnostic_reports": [],
        }

        result = await get_encounter_details("enc-1", graph)
        assert "Encounter enc-1" in result
        assert "Hypertension" in result
        assert "BP" in result

    @pytest.mark.asyncio
    async def test_no_encounter(self):
        graph = AsyncMock()
        graph.get_encounter_events.return_value = {
            "conditions": [],
            "medications": [],
            "observations": [],
            "procedures": [],
            "diagnostic_reports": [],
        }
        result = await get_encounter_details("missing", graph)
        assert "No encounter found" in result


# =============================================================================
# get_lab_history tests
# =============================================================================


class TestGetLabHistory:
    @pytest.mark.asyncio
    async def test_returns_sorted_results(self):
        rows = []
        for i, date in enumerate(["2024-01-10", "2024-03-15", "2024-02-20"]):
            row = MagicMock()
            row.data = {
                "resourceType": "Observation",
                "code": {"coding": [{"display": "Hemoglobin A1c"}]},
                "effectiveDateTime": f"{date}T09:00:00Z",
                "valueQuantity": {"value": 6.5 + i * 0.1, "unit": "%"},
            }
            rows.append(row)

        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rows
        db = AsyncMock()
        db.execute.return_value = mock_result

        result = await get_lab_history("patient-1", "hemoglobin", db)
        assert "3 results" in result
        # Should be sorted descending by date
        lines = result.split("\n")
        dates = [l.strip().split(":")[0] for l in lines if l.strip().startswith("- 2024")]
        assert dates == sorted(dates, reverse=True)

    @pytest.mark.asyncio
    async def test_no_results(self):
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db = AsyncMock()
        db.execute.return_value = mock_result

        result = await get_lab_history("patient-1", "nonexistent", db)
        assert "No lab results found" in result


# =============================================================================
# find_related_resources tests
# =============================================================================


class TestFindRelatedResources:
    @pytest.mark.asyncio
    async def test_condition_shows_meds_and_procs(self):
        graph = AsyncMock()
        graph.get_medications_treating_condition.return_value = [
            {
                "resourceType": "MedicationRequest",
                "medicationCodeableConcept": {"coding": [{"display": "Metformin"}]},
                "status": "active",
            }
        ]
        graph.get_procedures_for_condition.return_value = []

        result = await find_related_resources("cond-1", "Condition", graph)
        assert "Metformin" in result
        assert "Medications treating" in result

    @pytest.mark.asyncio
    async def test_diagnostic_report_shows_observations(self):
        graph = AsyncMock()
        graph.get_diagnostic_report_results.return_value = [
            {
                "resourceType": "Observation",
                "code": {"coding": [{"display": "Glucose"}]},
                "valueQuantity": {"value": 95, "unit": "mg/dL"},
                "effectiveDateTime": "2024-01-15",
            }
        ]

        result = await find_related_resources("dr-1", "DiagnosticReport", graph)
        assert "Glucose" in result

    @pytest.mark.asyncio
    async def test_no_related(self):
        graph = AsyncMock()
        graph.get_medications_treating_condition.return_value = []
        graph.get_procedures_for_condition.return_value = []

        result = await find_related_resources("cond-1", "Condition", graph)
        assert "No related resources found" in result

    @pytest.mark.asyncio
    async def test_unsupported_type(self):
        graph = AsyncMock()
        result = await find_related_resources("obs-1", "Observation", graph)
        assert "No related resources found" in result


# =============================================================================
# get_patient_timeline tests
# =============================================================================


def _make_graph_with_session(mock_session):
    """Create a mock graph whose _driver.session() returns an async context manager."""
    graph = AsyncMock()
    cm = AsyncMock()
    cm.__aenter__ = AsyncMock(return_value=mock_session)
    cm.__aexit__ = AsyncMock(return_value=False)
    # _driver must be a regular MagicMock so .session() doesn't return a coroutine
    mock_driver = MagicMock()
    mock_driver.session.return_value = cm
    graph._driver = mock_driver
    return graph


class TestGetPatientTimeline:
    @pytest.mark.asyncio
    async def test_returns_timeline(self):
        mock_record_1 = MagicMock()
        mock_record_1.data.return_value = {
            "fhir_id": "enc-1",
            "type_display": "Outpatient visit",
            "period_start": "2024-01-15T09:00:00Z",
            "period_end": "2024-01-15T09:30:00Z",
        }

        mock_run_result = AsyncMock()
        mock_run_result.__aiter__ = lambda self: AsyncIterator([mock_record_1])

        mock_session = AsyncMock()
        mock_session.run.return_value = mock_run_result

        graph = _make_graph_with_session(mock_session)
        graph.get_encounter_events.return_value = {
            "conditions": [
                {
                    "resourceType": "Condition",
                    "code": {"coding": [{"display": "Hypertension"}]},
                    "clinicalStatus": {"coding": [{"code": "active"}]},
                }
            ],
            "medications": [],
            "observations": [],
            "procedures": [],
            "diagnostic_reports": [],
        }

        result = await get_patient_timeline("patient-1", graph)
        assert "1 encounters" in result
        assert "Outpatient visit" in result
        assert "Hypertension" in result

    @pytest.mark.asyncio
    async def test_no_encounters(self):
        mock_run_result = AsyncMock()
        mock_run_result.__aiter__ = lambda self: AsyncIterator([])

        mock_session = AsyncMock()
        mock_session.run.return_value = mock_run_result

        graph = _make_graph_with_session(mock_session)

        result = await get_patient_timeline("patient-1", graph)
        assert "No encounters found" in result

    @pytest.mark.asyncio
    async def test_with_date_range(self):
        mock_run_result = AsyncMock()
        mock_run_result.__aiter__ = lambda self: AsyncIterator([])

        mock_session = AsyncMock()
        mock_session.run.return_value = mock_run_result

        graph = _make_graph_with_session(mock_session)

        result = await get_patient_timeline(
            "patient-1", graph, start_date="2024-01-01", end_date="2024-12-31"
        )
        assert "2024-01-01" in result
        assert "2024-12-31" in result
