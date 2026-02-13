"""Tests for agent_tools module.

Uses mocked KnowledgeGraph, AsyncSession, and services to test the three
new tools without requiring Neo4j or Postgres.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.agent_tools import (
    execute_tool,
    query_patient_data,
    explore_connections,
    get_patient_timeline,
    TOOL_SCHEMAS,
)


# =============================================================================
# Schema tests
# =============================================================================


class TestToolSchemas:
    def test_four_schemas_defined(self):
        assert len(TOOL_SCHEMAS) == 4

    def test_tool_names(self):
        names = {t["name"] for t in TOOL_SCHEMAS}
        assert names == {"query_patient_data", "explore_connections", "get_patient_timeline", "show_clinical_table"}

    def test_all_schemas_have_required_fields(self):
        for schema in TOOL_SCHEMAS:
            assert schema["type"] == "function"
            assert "name" in schema
            assert "description" in schema
            assert "parameters" in schema
            assert schema["parameters"]["type"] == "object"
            assert schema["strict"] is True

    def test_query_patient_data_parameters(self):
        schema = next(s for s in TOOL_SCHEMAS if s["name"] == "query_patient_data")
        props = schema["parameters"]["properties"]
        assert "name" in props
        assert "resource_type" in props
        assert "status" in props
        assert "category" in props
        assert "date_from" in props
        assert "date_to" in props
        assert "include_full_resource" in props
        assert "limit" in props

    def test_explore_connections_parameters(self):
        schema = next(s for s in TOOL_SCHEMAS if s["name"] == "explore_connections")
        props = schema["parameters"]["properties"]
        assert "fhir_id" in props
        assert "resource_type" in props
        assert "include_full_resource" in props
        assert "max_per_relationship" in props

    def test_get_patient_timeline_parameters(self):
        schema = next(s for s in TOOL_SCHEMAS if s["name"] == "get_patient_timeline")
        props = schema["parameters"]["properties"]
        assert "start_date" in props
        assert "end_date" in props
        assert "include_notes" in props


# =============================================================================
# execute_tool dispatch tests
# =============================================================================


class TestExecuteTool:
    @pytest.mark.asyncio
    async def test_unknown_tool(self):
        result = await execute_tool(
            name="nonexistent",
            arguments="{}",
            patient_id="p-1",
            graph=AsyncMock(),
            db=AsyncMock(),
        )
        parsed = json.loads(result)
        assert "error" in parsed
        assert "Unknown tool" in parsed["error"]

    @pytest.mark.asyncio
    async def test_dispatches_query_patient_data(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        result = await execute_tool(
            name="query_patient_data",
            arguments=json.dumps({
                "name": "diabetes",
                "resource_type": None,
                "status": None,
                "category": None,
                "date_from": None,
                "date_to": None,
                "include_full_resource": True,
                "limit": 20,
            }),
            patient_id="p-1",
            graph=AsyncMock(),
            db=db,
        )
        parsed = json.loads(result)
        assert parsed["total"] == 0

    @pytest.mark.asyncio
    @patch("app.services.compiler.compile_node_context", new_callable=AsyncMock)
    async def test_dispatches_explore_connections(self, mock_compile):
        mock_compile.return_value = {}

        result = await execute_tool(
            name="explore_connections",
            arguments=json.dumps({
                "fhir_id": "cond-1",
                "resource_type": "Condition",
                "include_full_resource": True,
                "max_per_relationship": 10,
            }),
            patient_id="p-1",
            graph=AsyncMock(),
            db=AsyncMock(),
        )
        parsed = json.loads(result)
        assert parsed["total"] == 0
        assert "No connections found" in parsed["message"]

    @pytest.mark.asyncio
    async def test_dispatches_get_patient_timeline(self):
        graph = AsyncMock()
        graph.get_patient_encounters.return_value = []

        result = await execute_tool(
            name="get_patient_timeline",
            arguments=json.dumps({
                "start_date": None,
                "end_date": None,
                "include_notes": False,
            }),
            patient_id="p-1",
            graph=graph,
            db=AsyncMock(),
        )
        parsed = json.loads(result)
        assert parsed["total"] == 0
        assert "No encounters found" in parsed["message"]


# =============================================================================
# query_patient_data tests
# =============================================================================


def _make_fhir_row(fhir_id: str, resource_type: str, data: dict) -> MagicMock:
    """Create a mock FhirResource row."""
    row = MagicMock()
    row.fhir_id = fhir_id
    row.resource_type = resource_type
    row.data = data
    return row


class TestQueryPatientData:
    @pytest.mark.asyncio
    async def test_returns_exact_results(self):
        db = AsyncMock()
        row = _make_fhir_row("cond-1", "Condition", {
            "resourceType": "Condition",
            "id": "cond-1",
            "code": {"coding": [{"display": "Diabetes", "code": "44054006"}]},
            "clinicalStatus": {"coding": [{"code": "active"}]},
        })
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [row]
        db.execute.return_value = mock_result

        result = await query_patient_data(
            patient_id="p-1",
            db=db,
            graph=AsyncMock(),
            name="diabetes",
        )
        parsed = json.loads(result)
        assert parsed["total"] == 1
        assert parsed["exact_count"] == 1
        assert parsed["results"][0]["source"] == "exact"
        assert parsed["results"][0]["fhir_id"] == "cond-1"
        assert parsed["results"][0]["resource"]["id"] == "cond-1"

    @pytest.mark.asyncio
    async def test_no_results_returns_message(self):
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        result = await query_patient_data(
            patient_id="p-1",
            db=db,
            graph=AsyncMock(),
            name="nonexistent",
        )
        parsed = json.loads(result)
        assert parsed["total"] == 0
        assert "No results found" in parsed["message"]

    @pytest.mark.asyncio
    @patch("app.services.agent_tools._query_semantic", new_callable=AsyncMock)
    async def test_triggers_semantic_fallback_when_few_exact(self, mock_semantic):
        """When <3 exact results and name is provided, triggers pgvector fallback."""
        db = AsyncMock()
        # Return 1 exact result (below threshold of 3)
        row = _make_fhir_row("cond-1", "Condition", {
            "resourceType": "Condition",
            "id": "cond-1",
            "code": {"coding": [{"display": "Type 2 diabetes"}]},
        })
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [row]
        db.execute.return_value = mock_result

        # Semantic search returns additional results
        mock_semantic.return_value = [
            {
                "source": "semantic",
                "fhir_id": "obs-1",
                "resource_type": "Observation",
                "similarity_score": 0.75,
                "resource": {"resourceType": "Observation", "id": "obs-1"},
            }
        ]

        result = await query_patient_data(
            patient_id="p-1",
            db=db,
            graph=AsyncMock(),
            name="diabetes",
        )
        parsed = json.loads(result)
        assert parsed["total"] == 2
        assert parsed["exact_count"] == 1
        assert parsed["semantic_count"] == 1
        assert parsed["results"][1]["source"] == "semantic"
        mock_semantic.assert_called_once()

    @pytest.mark.asyncio
    @patch("app.services.agent_tools._query_semantic", new_callable=AsyncMock)
    async def test_no_semantic_fallback_when_enough_exact(self, mock_semantic):
        """When >=3 exact results, no semantic fallback."""
        db = AsyncMock()
        rows = [
            _make_fhir_row(f"r-{i}", "Condition", {
                "resourceType": "Condition", "id": f"r-{i}",
                "code": {"coding": [{"display": f"Condition {i}"}]},
            })
            for i in range(3)
        ]
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = rows
        db.execute.return_value = mock_result

        result = await query_patient_data(
            patient_id="p-1",
            db=db,
            graph=AsyncMock(),
            name="condition",
        )
        parsed = json.loads(result)
        assert parsed["total"] == 3
        assert parsed["exact_count"] == 3
        mock_semantic.assert_not_called()

    @pytest.mark.asyncio
    @patch("app.services.agent_tools._query_semantic", new_callable=AsyncMock)
    async def test_no_semantic_fallback_when_no_name(self, mock_semantic):
        """When no name provided, no semantic fallback even with 0 results."""
        db = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        db.execute.return_value = mock_result

        result = await query_patient_data(
            patient_id="p-1",
            db=db,
            graph=AsyncMock(),
            resource_type="Condition",
        )
        parsed = json.loads(result)
        assert parsed["total"] == 0
        mock_semantic.assert_not_called()

    @pytest.mark.asyncio
    async def test_include_full_resource_false(self):
        db = AsyncMock()
        row = _make_fhir_row("cond-1", "Condition", {
            "resourceType": "Condition",
            "id": "cond-1",
            "code": {"coding": [{"display": "Hypertension"}]},
        })
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = [row]
        db.execute.return_value = mock_result

        result = await query_patient_data(
            patient_id="p-1",
            db=db,
            graph=AsyncMock(),
            name="hypertension",
            include_full_resource=False,
        )
        parsed = json.loads(result)
        assert "resource" not in parsed["results"][0]

    @pytest.mark.asyncio
    async def test_error_handling(self):
        db = AsyncMock()
        db.execute.side_effect = Exception("db error")

        result = await query_patient_data(
            patient_id="p-1",
            db=db,
            graph=AsyncMock(),
            name="test",
        )
        parsed = json.loads(result)
        assert "error" in parsed


# =============================================================================
# explore_connections tests
# =============================================================================


class TestExploreConnections:
    @pytest.mark.asyncio
    @patch("app.services.compiler.compile_node_context", new_callable=AsyncMock)
    async def test_returns_grouped_connections(self, mock_compile):
        mock_compile.return_value = {
            "TREATS": [
                {
                    "resourceType": "MedicationRequest",
                    "id": "med-1",
                    "medicationCodeableConcept": "Metformin",
                    "status": "active",
                }
            ],
            "DIAGNOSED": [
                {
                    "resourceType": "Condition",
                    "id": "cond-1",
                    "code": "Diabetes",
                }
            ],
        }

        result = await explore_connections(
            fhir_id="cond-1",
            patient_id="p-1",
            graph=AsyncMock(),
            db=AsyncMock(),
            resource_type="Condition",
        )
        parsed = json.loads(result)
        assert parsed["total"] == 2
        assert "TREATS" in parsed["connections"]
        assert "DIAGNOSED" in parsed["connections"]
        assert len(parsed["connections"]["TREATS"]) == 1

    @pytest.mark.asyncio
    @patch("app.services.compiler.compile_node_context", new_callable=AsyncMock)
    async def test_empty_connections(self, mock_compile):
        mock_compile.return_value = {}

        result = await explore_connections(
            fhir_id="cond-1",
            patient_id="p-1",
            graph=AsyncMock(),
            db=AsyncMock(),
            resource_type="Condition",
        )
        parsed = json.loads(result)
        assert parsed["total"] == 0
        assert "No connections found" in parsed["message"]

    @pytest.mark.asyncio
    @patch("app.services.compiler.compile_node_context", new_callable=AsyncMock)
    async def test_max_per_relationship(self, mock_compile):
        """Test that max_per_relationship limits results per edge type."""
        mock_compile.return_value = {
            "RECORDED": [
                {"resourceType": "Observation", "id": f"obs-{i}"}
                for i in range(20)
            ],
        }

        result = await explore_connections(
            fhir_id="enc-1",
            patient_id="p-1",
            graph=AsyncMock(),
            db=AsyncMock(),
            resource_type="Encounter",
            max_per_relationship=5,
        )
        parsed = json.loads(result)
        assert len(parsed["connections"]["RECORDED"]) == 5
        assert parsed["total"] == 5

    @pytest.mark.asyncio
    @patch("app.services.compiler.compile_node_context", new_callable=AsyncMock)
    async def test_include_full_resource_false(self, mock_compile):
        mock_compile.return_value = {
            "TREATS": [
                {
                    "resourceType": "MedicationRequest",
                    "id": "med-1",
                    "status": "active",
                }
            ],
        }

        result = await explore_connections(
            fhir_id="cond-1",
            patient_id="p-1",
            graph=AsyncMock(),
            db=AsyncMock(),
            include_full_resource=False,
        )
        parsed = json.loads(result)
        connection = parsed["connections"]["TREATS"][0]
        assert "fhir_id" in connection
        assert "resource_type" in connection
        assert "status" not in connection

    @pytest.mark.asyncio
    @patch("app.services.compiler.compile_node_context", new_callable=AsyncMock)
    async def test_document_reference_notes_included(self, mock_compile):
        """Test that DocumentReferences with decoded notes are returned."""
        mock_compile.return_value = {
            "DOCUMENTED": [
                {
                    "resourceType": "DocumentReference",
                    "id": "doc-1",
                    "clinical_note": "Patient presents with chest pain.",
                }
            ],
        }

        result = await explore_connections(
            fhir_id="enc-1",
            patient_id="p-1",
            graph=AsyncMock(),
            db=AsyncMock(),
            resource_type="Encounter",
        )
        parsed = json.loads(result)
        doc = parsed["connections"]["DOCUMENTED"][0]
        assert "clinical_note" in doc

    @pytest.mark.asyncio
    @patch("app.services.compiler.compile_node_context", new_callable=AsyncMock)
    async def test_error_handling(self, mock_compile):
        mock_compile.side_effect = Exception("graph error")

        result = await explore_connections(
            fhir_id="cond-1",
            patient_id="p-1",
            graph=AsyncMock(),
            db=AsyncMock(),
        )
        parsed = json.loads(result)
        assert "error" in parsed


# =============================================================================
# get_patient_timeline tests
# =============================================================================


class TestGetPatientTimeline:
    @pytest.mark.asyncio
    async def test_returns_timeline(self):
        graph = AsyncMock()
        graph.get_patient_encounters.return_value = [
            {
                "fhir_id": "enc-1",
                "type_display": "Outpatient visit",
                "period_start": "2024-01-15T09:00:00Z",
                "period_end": "2024-01-15T09:30:00Z",
            },
        ]
        graph.get_encounter_events.return_value = {
            "conditions": [
                {
                    "resourceType": "Condition",
                    "id": "cond-1",
                    "code": {"coding": [{"display": "Hypertension"}]},
                    "clinicalStatus": {"coding": [{"code": "active"}]},
                }
            ],
            "medications": [],
            "observations": [],
            "procedures": [],
            "diagnostic_reports": [],
            "immunizations": [],
            "care_plans": [],
            "document_references": [],
            "imaging_studies": [],
            "care_teams": [],
            "medication_administrations": [],
        }

        # Mock db for batch fetch of encounter and event resources
        db = AsyncMock()
        enc_result = MagicMock()
        enc_result.all.return_value = [
            MagicMock(fhir_id="enc-1", data={
                "resourceType": "Encounter",
                "id": "enc-1",
                "type": [{"coding": [{"display": "Outpatient visit"}]}],
                "period": {"start": "2024-01-15T09:00:00Z"},
            }),
        ]

        event_result = MagicMock()
        event_result.all.return_value = [
            MagicMock(fhir_id="cond-1", data={
                "resourceType": "Condition",
                "id": "cond-1",
                "code": {"coding": [{"display": "Hypertension"}]},
                "clinicalStatus": {"coding": [{"code": "active"}]},
            }),
        ]

        db.execute.side_effect = [enc_result, event_result]

        result = await get_patient_timeline("p-1", graph, db)
        parsed = json.loads(result)
        assert parsed["total"] == 1
        enc = parsed["encounters"][0]
        assert enc["fhir_id"] == "enc-1"
        assert enc["type"] == "Outpatient visit"
        assert enc["date"] == "2024-01-15"
        assert "conditions" in enc["events"]

    @pytest.mark.asyncio
    async def test_no_encounters(self):
        graph = AsyncMock()
        graph.get_patient_encounters.return_value = []

        result = await get_patient_timeline("p-1", graph, AsyncMock())
        parsed = json.loads(result)
        assert parsed["total"] == 0
        assert "No encounters found" in parsed["message"]

    @pytest.mark.asyncio
    async def test_with_date_range(self):
        graph = AsyncMock()
        graph.get_patient_encounters.return_value = []

        result = await get_patient_timeline(
            "p-1", graph, AsyncMock(),
            start_date="2024-01-01",
            end_date="2024-12-31",
        )
        parsed = json.loads(result)
        assert "2024-01-01" in parsed["message"]
        assert "2024-12-31" in parsed["message"]

    @pytest.mark.asyncio
    async def test_include_notes_false_excludes_documents(self):
        graph = AsyncMock()
        graph.get_patient_encounters.return_value = [
            {
                "fhir_id": "enc-1",
                "type_display": "Visit",
                "period_start": "2024-01-15T09:00:00Z",
                "period_end": "2024-01-15T10:00:00Z",
            },
        ]
        graph.get_encounter_events.return_value = {
            "conditions": [],
            "medications": [],
            "observations": [],
            "procedures": [],
            "diagnostic_reports": [],
            "immunizations": [],
            "care_plans": [],
            "document_references": [
                {
                    "resourceType": "DocumentReference",
                    "id": "doc-1",
                    "type": {"coding": [{"display": "Clinical Note"}]},
                }
            ],
            "imaging_studies": [],
            "care_teams": [],
            "medication_administrations": [],
        }

        db = AsyncMock()
        enc_result = MagicMock()
        enc_result.all.return_value = []
        event_result = MagicMock()
        event_result.all.return_value = []
        db.execute.side_effect = [enc_result, event_result]

        result = await get_patient_timeline(
            "p-1", graph, db, include_notes=False,
        )
        parsed = json.loads(result)
        enc = parsed["encounters"][0]
        assert "document_references" not in enc["events"]

    @pytest.mark.asyncio
    async def test_include_notes_true_includes_documents(self):
        graph = AsyncMock()
        graph.get_patient_encounters.return_value = [
            {
                "fhir_id": "enc-1",
                "type_display": "Visit",
                "period_start": "2024-01-15T09:00:00Z",
                "period_end": "2024-01-15T10:00:00Z",
            },
        ]
        graph.get_encounter_events.return_value = {
            "conditions": [],
            "medications": [],
            "observations": [],
            "procedures": [],
            "diagnostic_reports": [],
            "immunizations": [],
            "care_plans": [],
            "document_references": [
                {
                    "resourceType": "DocumentReference",
                    "id": "doc-1",
                    "type": {"coding": [{"display": "Clinical Note"}]},
                }
            ],
            "imaging_studies": [],
            "care_teams": [],
            "medication_administrations": [],
        }

        db = AsyncMock()
        enc_result = MagicMock()
        enc_result.all.return_value = []
        event_result = MagicMock()
        event_result.all.return_value = [
            MagicMock(fhir_id="doc-1", data={
                "resourceType": "DocumentReference",
                "id": "doc-1",
                "type": {"coding": [{"display": "Clinical Note"}]},
            }),
        ]
        db.execute.side_effect = [enc_result, event_result]

        result = await get_patient_timeline(
            "p-1", graph, db, include_notes=True,
        )
        parsed = json.loads(result)
        enc = parsed["encounters"][0]
        assert "document_references" in enc["events"]
        assert len(enc["events"]["document_references"]) == 1

    @pytest.mark.asyncio
    async def test_error_handling(self):
        graph = AsyncMock()
        graph.get_patient_encounters.side_effect = Exception("neo4j down")
        result = await get_patient_timeline("p-1", graph, AsyncMock())
        parsed = json.loads(result)
        assert "error" in parsed
