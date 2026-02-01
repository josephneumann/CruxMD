"""Tests for agent response schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.agent import (
    Action,
    AgentResponse,
    DataQuery,
    DataTable,
    FollowUp,
    Insight,
    TableColumn,
    Visualization,
)


class TestDataQuery:
    """Tests for DataQuery schema."""

    def test_empty_data_query(self):
        """DataQuery with no fields is valid."""
        query = DataQuery()
        assert query.resource_types is None
        assert query.filters is None
        assert query.time_range is None
        assert query.limit is None

    def test_full_data_query(self):
        """DataQuery with all fields populated."""
        query = DataQuery(
            resource_types=["Observation", "Condition"],
            filters='{"code": "HbA1c", "status": "final"}',
            time_range="last_6_months",
            limit=50,
        )
        assert query.resource_types == ["Observation", "Condition"]
        assert "HbA1c" in query.filters
        assert query.time_range == "last_6_months"
        assert query.limit == 50

    def test_limit_validation(self):
        """DataQuery limit must be between 1 and 1000."""
        with pytest.raises(ValidationError) as exc_info:
            DataQuery(limit=0)
        assert "limit" in str(exc_info.value)

        with pytest.raises(ValidationError) as exc_info:
            DataQuery(limit=1001)
        assert "limit" in str(exc_info.value)


class TestInsight:
    """Tests for Insight schema."""

    def test_valid_insight(self):
        """Insight with required fields."""
        insight = Insight(
            type="warning",
            title="Drug Interaction Alert",
            content="Potential interaction between medications.",
        )
        assert insight.type == "warning"
        assert insight.title == "Drug Interaction Alert"
        assert insight.citations is None

    def test_insight_with_citations(self):
        """Insight with FHIR resource citations."""
        insight = Insight(
            type="critical",
            title="Allergy Alert",
            content="Patient has documented penicillin allergy.",
            citations=["AllergyIntolerance/123", "AllergyIntolerance/456"],
        )
        assert len(insight.citations) == 2

    def test_insight_type_validation(self):
        """Insight type must be a valid literal."""
        with pytest.raises(ValidationError) as exc_info:
            Insight(type="invalid", title="Test", content="Test content")
        assert "type" in str(exc_info.value)

    def test_insight_empty_title_rejected(self):
        """Insight title cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            Insight(type="info", title="", content="Test content")
        assert "title" in str(exc_info.value)


class TestVisualization:
    """Tests for Visualization schema."""

    def test_valid_visualization(self):
        """Visualization with required fields."""
        viz = Visualization(
            type="line_chart",
            title="HbA1c Trend",
            data_query=DataQuery(
                resource_types=["Observation"],
                filters='{"code": "HbA1c"}',
            ),
        )
        assert viz.type == "line_chart"
        assert viz.title == "HbA1c Trend"
        assert viz.description is None
        assert viz.config is None

    def test_visualization_with_config(self):
        """Visualization with optional config."""
        viz = Visualization(
            type="bar_chart",
            title="Medication Adherence",
            description="Weekly adherence rates",
            data_query=DataQuery(),
            config='{"color": "blue", "showLegend": true}',
        )
        assert "blue" in viz.config
        assert viz.description == "Weekly adherence rates"

    def test_visualization_type_validation(self):
        """Visualization type must be valid literal."""
        with pytest.raises(ValidationError) as exc_info:
            Visualization(
                type="pie_chart",  # Not a valid type
                title="Test",
                data_query=DataQuery(),
            )
        assert "type" in str(exc_info.value)


class TestDataTable:
    """Tests for DataTable schema."""

    def test_valid_data_table(self):
        """DataTable with columns and data query."""
        table = DataTable(
            title="Recent Lab Results",
            columns=[
                TableColumn(key="date", header="Date", format="date"),
                TableColumn(key="value", header="Value", format="number"),
                TableColumn(key="status", header="Status", format="badge"),
            ],
            data_query=DataQuery(resource_types=["Observation"]),
        )
        assert table.title == "Recent Lab Results"
        assert len(table.columns) == 3
        assert table.columns[0].format == "date"

    def test_data_table_requires_columns(self):
        """DataTable must have at least one column."""
        with pytest.raises(ValidationError) as exc_info:
            DataTable(
                title="Empty Table",
                columns=[],
                data_query=DataQuery(),
            )
        assert "columns" in str(exc_info.value)


class TestAction:
    """Tests for Action schema."""

    def test_valid_action(self):
        """Action with required fields."""
        action = Action(
            label="Order Lab",
            type="order",
        )
        assert action.label == "Order Lab"
        assert action.type == "order"
        assert action.description is None
        assert action.payload is None

    def test_action_with_payload(self):
        """Action with optional payload."""
        action = Action(
            label="Schedule Follow-up",
            type="refer",
            description="Schedule with endocrinology",
            payload='{"specialty": "endocrinology", "urgency": "routine"}',
        )
        assert "endocrinology" in action.payload

    def test_action_type_validation(self):
        """Action type must be valid literal."""
        with pytest.raises(ValidationError) as exc_info:
            Action(label="Test", type="invalid_type")
        assert "type" in str(exc_info.value)


class TestFollowUp:
    """Tests for FollowUp schema."""

    def test_valid_follow_up(self):
        """FollowUp with question."""
        follow_up = FollowUp(question="What medications is the patient taking?")
        assert follow_up.question == "What medications is the patient taking?"
        assert follow_up.intent is None

    def test_follow_up_with_intent(self):
        """FollowUp with intent classification."""
        follow_up = FollowUp(
            question="Show me the latest vital signs",
            intent="vitals_review",
        )
        assert follow_up.intent == "vitals_review"

    def test_follow_up_empty_question_rejected(self):
        """FollowUp question cannot be empty."""
        with pytest.raises(ValidationError) as exc_info:
            FollowUp(question="")
        assert "question" in str(exc_info.value)


class TestAgentResponse:
    """Tests for AgentResponse schema."""

    def test_minimal_response(self):
        """AgentResponse with only required narrative."""
        response = AgentResponse(narrative="Here is the patient summary.")
        assert response.narrative == "Here is the patient summary."
        assert response.thinking is None
        assert response.insights is None
        assert response.visualizations is None
        assert response.tables is None
        assert response.actions is None
        assert response.follow_ups is None

    def test_full_response(self):
        """AgentResponse with all optional fields."""
        response = AgentResponse(
            thinking="Let me analyze the patient's data...",
            narrative="## Summary\n\nThe patient has well-controlled diabetes.",
            insights=[
                Insight(
                    type="positive",
                    title="Good Control",
                    content="HbA1c has improved.",
                )
            ],
            visualizations=[
                Visualization(
                    type="line_chart",
                    title="HbA1c Trend",
                    data_query=DataQuery(resource_types=["Observation"]),
                )
            ],
            tables=[
                DataTable(
                    title="Recent Labs",
                    columns=[TableColumn(key="test", header="Test")],
                    data_query=DataQuery(),
                )
            ],
            actions=[Action(label="Order Follow-up", type="order")],
            follow_ups=[FollowUp(question="What about blood pressure?")],
        )
        assert response.thinking is not None
        assert len(response.insights) == 1
        assert len(response.visualizations) == 1
        assert len(response.tables) == 1
        assert len(response.actions) == 1
        assert len(response.follow_ups) == 1

    def test_empty_narrative_rejected(self):
        """AgentResponse requires non-empty narrative."""
        with pytest.raises(ValidationError) as exc_info:
            AgentResponse(narrative="")
        assert "narrative" in str(exc_info.value)

    def test_response_json_serialization(self):
        """AgentResponse can be serialized to JSON."""
        response = AgentResponse(
            narrative="Test response",
            insights=[
                Insight(type="info", title="Note", content="Important information")
            ],
        )
        json_str = response.model_dump_json()
        assert "Test response" in json_str
        assert "Important information" in json_str

    def test_response_from_json(self):
        """AgentResponse can be parsed from JSON."""
        json_data = {
            "narrative": "Parsed response",
            "insights": [
                {"type": "warning", "title": "Alert", "content": "Check this"}
            ],
        }
        response = AgentResponse.model_validate(json_data)
        assert response.narrative == "Parsed response"
        assert response.insights[0].type == "warning"
