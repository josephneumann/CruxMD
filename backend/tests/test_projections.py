"""Tests for the FHIR projection system."""

import json
import uuid
from datetime import date, datetime, timezone

import pytest

from app.projections.registry import FieldExtractor, ProjectionConfig, ProjectionRegistry
from app.projections.serializers.task import TaskFhirSerializer
from app.projections.status import get_cruxmd_status, get_fhir_status
from app.projections.extractors.task import (
    extract_status,
    extract_priority,
    extract_category,
    extract_task_type,
    extract_title,
    extract_due_on,
    extract_priority_score,
    extract_provenance,
    extract_context_config,
    extract_session_id,
)


class TestProjectionRegistry:
    """Tests for ProjectionRegistry."""

    def setup_method(self):
        """Clear registry before each test."""
        ProjectionRegistry._clear_for_testing()

    def test_register_and_get(self):
        """Test registering and retrieving a projection config."""
        # Create a mock model class
        class MockModel:
            pass

        class MockSerializer:
            pass

        config = ProjectionConfig(
            resource_type="TestResource",
            table_name="test_projections",
            model_class=MockModel,
            serializer_class=MockSerializer,
            extractors=[
                FieldExtractor("field1", lambda d: d.get("value")),
            ],
        )

        ProjectionRegistry.register(config)

        retrieved = ProjectionRegistry.get("TestResource")
        assert retrieved is not None
        assert retrieved.resource_type == "TestResource"
        assert retrieved.table_name == "test_projections"

    def test_has_projection(self):
        """Test checking if projection exists."""
        class MockModel:
            pass

        class MockSerializer:
            pass

        config = ProjectionConfig(
            resource_type="TestResource",
            table_name="test_projections",
            model_class=MockModel,
            serializer_class=MockSerializer,
        )

        ProjectionRegistry.register(config)

        assert ProjectionRegistry.has_projection("TestResource") is True
        assert ProjectionRegistry.has_projection("NonExistent") is False

    def test_get_nonexistent_returns_none(self):
        """Test that getting non-existent projection returns None."""
        assert ProjectionRegistry.get("NonExistent") is None


class TestProjectionConfig:
    """Tests for ProjectionConfig.extract()."""

    def test_extract_fields(self):
        """Test extracting fields from FHIR data."""
        class MockModel:
            pass

        class MockSerializer:
            pass

        config = ProjectionConfig(
            resource_type="Task",
            table_name="task_projections",
            model_class=MockModel,
            serializer_class=MockSerializer,
            extractors=[
                FieldExtractor("status", lambda d: d.get("status")),
                FieldExtractor("title", lambda d: d.get("description")),
                FieldExtractor("priority", lambda d: d.get("priority")),
            ],
        )

        fhir_data = {
            "resourceType": "Task",
            "status": "requested",
            "description": "Test task",
            "priority": "routine",
        }

        extracted = config.extract(fhir_data)

        assert extracted["status"] == "requested"
        assert extracted["title"] == "Test task"
        assert extracted["priority"] == "routine"


class TestTaskFhirSerializer:
    """Tests for TaskFhirSerializer."""

    def test_to_fhir_basic(self):
        """Test basic task to FHIR conversion."""
        task_data = {
            "type": "critical_lab_review",
            "category": "critical",
            "status": "pending",
            "priority": "urgent",
            "title": "Review critical lab",
            "patient_id": uuid.uuid4(),
        }

        fhir = TaskFhirSerializer.to_fhir(task_data)

        assert fhir["resourceType"] == "Task"
        assert fhir["status"] == "requested"  # pending -> requested
        assert fhir["priority"] == "urgent"
        assert fhir["description"] == "Review critical lab"
        assert fhir["intent"] == "order"
        assert "for" in fhir
        assert fhir["for"]["reference"].startswith("Patient/")

    def test_to_fhir_with_priority_score(self):
        """Test FHIR conversion with priority score extension."""
        task_data = {
            "type": "custom",
            "category": "routine",
            "status": "pending",
            "priority": "routine",
            "title": "Test task",
            "priority_score": 75,
            "patient_id": uuid.uuid4(),
        }

        fhir = TaskFhirSerializer.to_fhir(task_data)

        # Find priority score extension
        extensions = fhir.get("extension", [])
        priority_ext = next(
            (e for e in extensions if e["url"].endswith("/priority-score")),
            None,
        )

        assert priority_ext is not None
        assert priority_ext["valueInteger"] == 75

    def test_to_fhir_with_provenance(self):
        """Test FHIR conversion with provenance extension."""
        task_data = {
            "type": "custom",
            "category": "routine",
            "status": "pending",
            "priority": "routine",
            "title": "Test task",
            "patient_id": uuid.uuid4(),
            "provenance": {
                "trigger": {"type": "care_gap"},
            },
        }

        fhir = TaskFhirSerializer.to_fhir(task_data)

        extensions = fhir.get("extension", [])
        prov_ext = next(
            (e for e in extensions if e["url"].endswith("/task-provenance")),
            None,
        )

        assert prov_ext is not None
        assert "trigger" in json.loads(prov_ext["valueString"])

    def test_to_fhir_with_due_date(self):
        """Test FHIR conversion with due date."""
        task_data = {
            "type": "custom",
            "category": "routine",
            "status": "pending",
            "priority": "routine",
            "title": "Test task",
            "patient_id": uuid.uuid4(),
            "due_on": date(2026, 2, 15),
        }

        fhir = TaskFhirSerializer.to_fhir(task_data)

        assert "restriction" in fhir
        assert fhir["restriction"]["period"]["end"] == "2026-02-15"

    def test_status_mapping(self):
        """Test status mapping from CruxMD to FHIR."""
        assert get_fhir_status("pending") == "requested"
        assert get_fhir_status("in_progress") == "in-progress"
        assert get_fhir_status("paused") == "on-hold"
        assert get_fhir_status("completed") == "completed"
        assert get_fhir_status("cancelled") == "cancelled"
        assert get_fhir_status("deferred") == "on-hold"

    def test_reverse_status_mapping(self):
        """Test status mapping from FHIR to CruxMD."""
        assert get_cruxmd_status("requested") == "pending"
        assert get_cruxmd_status("in-progress") == "in_progress"
        assert get_cruxmd_status("on-hold") == "paused"
        assert get_cruxmd_status("on-hold", is_deferred=True) == "deferred"
        assert get_cruxmd_status("completed") == "completed"
        assert get_cruxmd_status("cancelled") == "cancelled"


class TestTaskExtractors:
    """Tests for Task field extractors."""

    def test_extract_status_from_fhir(self):
        """Test extracting status from FHIR Task."""
        fhir_data = {"status": "in-progress"}
        assert extract_status(fhir_data) == "in_progress"

        fhir_data = {"status": "requested"}
        assert extract_status(fhir_data) == "pending"

    def test_extract_status_deferred(self):
        """Test extracting deferred status from extension."""
        fhir_data = {
            "status": "on-hold",
            "extension": [
                {
                    "url": "https://cruxmd.com/fhir/extensions/is-deferred",
                    "valueBoolean": True,
                }
            ],
        }
        assert extract_status(fhir_data) == "deferred"

    def test_extract_priority(self):
        """Test extracting priority."""
        fhir_data = {"priority": "stat"}
        assert extract_priority(fhir_data) == "stat"

        fhir_data = {}
        assert extract_priority(fhir_data) == "routine"

    def test_extract_category(self):
        """Test extracting category from code.coding."""
        fhir_data = {
            "code": {
                "coding": [
                    {
                        "system": "https://cruxmd.com/fhir/task-category",
                        "code": "critical",
                    }
                ]
            }
        }
        assert extract_category(fhir_data) == "critical"

    def test_extract_type(self):
        """Test extracting task type from code.coding."""
        fhir_data = {
            "code": {
                "coding": [
                    {
                        "system": "https://cruxmd.com/fhir/task-type",
                        "code": "critical_lab_review",
                    }
                ]
            }
        }
        assert extract_task_type(fhir_data) == "critical_lab_review"

    def test_extract_title(self):
        """Test extracting title from description."""
        fhir_data = {"description": "Review patient labs"}
        assert extract_title(fhir_data) == "Review patient labs"

    def test_extract_due_on(self):
        """Test extracting due date."""
        fhir_data = {
            "restriction": {
                "period": {"end": "2026-02-15"}
            }
        }
        assert extract_due_on(fhir_data) == date(2026, 2, 15)

        fhir_data = {}
        assert extract_due_on(fhir_data) is None

    def test_extract_priority_score(self):
        """Test extracting priority score from extension."""
        fhir_data = {
            "extension": [
                {
                    "url": "https://cruxmd.com/fhir/extensions/priority-score",
                    "valueInteger": 85,
                }
            ]
        }
        assert extract_priority_score(fhir_data) == 85

    def test_extract_provenance(self):
        """Test extracting provenance from extension."""
        provenance = {"trigger": {"type": "care_gap"}}
        fhir_data = {
            "extension": [
                {
                    "url": "https://cruxmd.com/fhir/extensions/task-provenance",
                    "valueString": json.dumps(provenance),
                }
            ]
        }
        result = extract_provenance(fhir_data)
        assert result["trigger"]["type"] == "care_gap"

    def test_extract_context_config(self):
        """Test extracting context config from extension."""
        config = {"panels": [{"id": "panel1"}]}
        fhir_data = {
            "extension": [
                {
                    "url": "https://cruxmd.com/fhir/extensions/task-context-config",
                    "valueString": json.dumps(config),
                }
            ]
        }
        result = extract_context_config(fhir_data)
        assert result["panels"][0]["id"] == "panel1"

    def test_extract_session_id(self):
        """Test extracting session ID from extension."""
        session_id = str(uuid.uuid4())
        fhir_data = {
            "extension": [
                {
                    "url": "https://cruxmd.com/fhir/extensions/session-id",
                    "valueString": session_id,
                }
            ]
        }
        assert extract_session_id(fhir_data) == session_id


class TestRoundTrip:
    """Test serialization and extraction round-trip."""

    def test_round_trip_basic(self):
        """Test that data survives serialization -> extraction."""
        original_data = {
            "type": "critical_lab_review",
            "category": "critical",
            "status": "in_progress",
            "priority": "urgent",
            "title": "Review critical potassium",
            "priority_score": 90,
            "patient_id": uuid.uuid4(),
        }

        # Serialize to FHIR
        fhir = TaskFhirSerializer.to_fhir(original_data)

        # Extract back
        assert extract_status(fhir) == "in_progress"
        assert extract_priority(fhir) == "urgent"
        assert extract_category(fhir) == "critical"
        assert extract_task_type(fhir) == "critical_lab_review"
        assert extract_title(fhir) == "Review critical potassium"
        assert extract_priority_score(fhir) == 90

    def test_round_trip_with_extensions(self):
        """Test round-trip with complex extensions."""
        provenance = {
            "trigger": {"type": "clinical_rule", "rule_id": "K001"},
            "reasoning": {"model": "gpt-4o"},
        }
        context_config = {
            "panels": [{"id": "lab", "component": "LabPanel"}],
        }

        original_data = {
            "type": "custom",
            "category": "routine",
            "status": "pending",
            "priority": "routine",
            "title": "Test",
            "patient_id": uuid.uuid4(),
            "provenance": provenance,
            "context_config": context_config,
            "session_id": uuid.uuid4(),
        }

        fhir = TaskFhirSerializer.to_fhir(original_data)

        extracted_prov = extract_provenance(fhir)
        assert extracted_prov["trigger"]["type"] == "clinical_rule"
        assert extracted_prov["trigger"]["rule_id"] == "K001"

        extracted_config = extract_context_config(fhir)
        assert extracted_config["panels"][0]["component"] == "LabPanel"

        assert extract_session_id(fhir) == str(original_data["session_id"])
