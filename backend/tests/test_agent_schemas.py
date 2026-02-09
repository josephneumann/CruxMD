"""Tests for agent response schemas."""

import pytest
from pydantic import ValidationError

from app.schemas.agent import (
    AgentResponse,
    ClinicalTable,
    ClinicalVisualization,
    FollowUp,
    Insight,
    LightningResponse,
    MedTimelineRow,
    MedTimelineSegment,
    RangeBand,
    ReferenceLine,
    TimelineEvent,
    TrendPoint,
    TrendSeries,
)


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


class TestClinicalTable:
    """Tests for ClinicalTable schema."""

    def test_valid_medications_table(self):
        """ClinicalTable with medications type and JSON-encoded rows."""
        import json
        rows_data = [
            {
                "medication": "Lisinopril 10 MG Oral Tablet",
                "frequency": "1x daily",
                "reason": "Hypertension",
                "status": "active",
                "authoredOn": "2025-01-15",
                "requester": "Dr. Smith",
            },
        ]
        table = ClinicalTable(
            type="medications",
            title="Current Medications",
            rows=json.dumps(rows_data),
        )
        assert table.type == "medications"
        parsed = json.loads(table.rows)
        assert len(parsed) == 1
        assert parsed[0]["medication"] == "Lisinopril 10 MG Oral Tablet"

    def test_valid_lab_results_table(self):
        """ClinicalTable with lab_results type including history and panel."""
        import json
        rows_data = [
            {
                "test": "Hemoglobin A1c",
                "value": 6.8,
                "unit": "%",
                "rangeLow": 4.0,
                "rangeHigh": 5.6,
                "interpretation": "H",
                "date": "2026-01-25",
                "history": [
                    {"value": 7.4, "date": "2025-08-12"},
                    {"value": 6.8, "date": "2026-01-25"},
                ],
                "panel": "Metabolic Panel",
            },
        ]
        table = ClinicalTable(
            type="lab_results",
            title="Recent Lab Results",
            rows=json.dumps(rows_data),
        )
        assert table.type == "lab_results"
        parsed = json.loads(table.rows)
        assert parsed[0]["value"] == 6.8
        assert parsed[0]["interpretation"] == "H"
        assert len(parsed[0]["history"]) == 2

    def test_all_eight_table_types(self):
        """All 8 clinical table types are valid."""
        types = [
            "medications", "lab_results", "vitals", "conditions",
            "allergies", "immunizations", "procedures", "encounters",
        ]
        for t in types:
            table = ClinicalTable(type=t, title=f"Test {t}", rows="[]")
            assert table.type == t

    def test_invalid_table_type(self):
        """ClinicalTable rejects unknown types."""
        with pytest.raises(ValidationError) as exc_info:
            ClinicalTable(type="diagnosis", title="Test", rows="[]")
        assert "type" in str(exc_info.value)

    def test_title_max_length(self):
        """ClinicalTable title respects max_length."""
        with pytest.raises(ValidationError):
            ClinicalTable(type="medications", title="x" * 201, rows="[]")

    def test_empty_rows_allowed(self):
        """ClinicalTable with empty JSON array string is valid."""
        table = ClinicalTable(type="conditions", title="Conditions", rows="[]")
        assert table.rows == "[]"


class TestClinicalVisualization:
    """Tests for ClinicalVisualization schema."""

    def test_valid_trend_chart(self):
        """ClinicalVisualization with trend_chart type and series."""
        viz = ClinicalVisualization(
            type="trend_chart",
            title="HbA1c Trend",
            subtitle="12-month glycemic control",
            current_value="7.2%",
            trend_summary="↓ 21% · Above Target",
            trend_status="warning",
            series=[
                TrendSeries(
                    name="HbA1c",
                    unit="%",
                    data_points=[
                        TrendPoint(date="Jan 24", value=9.1),
                        TrendPoint(date="Jan 25", value=7.2),
                    ],
                )
            ],
            reference_lines=[ReferenceLine(value=7.0, label="Target <7%")],
            range_bands=[
                RangeBand(y1=4.0, y2=5.7, severity="normal", label="Normal"),
                RangeBand(y1=5.7, y2=6.5, severity="warning", label="Pre-diabetes"),
                RangeBand(y1=6.5, y2=14.0, severity="critical", label="Diabetes"),
            ],
        )
        assert viz.type == "trend_chart"
        assert len(viz.series) == 1
        assert len(viz.reference_lines) == 1
        assert len(viz.range_bands) == 3
        assert viz.trend_status == "warning"

    def test_trend_chart_with_medications(self):
        """Trend chart with medication timeline aligned below."""
        viz = ClinicalVisualization(
            type="trend_chart",
            title="Blood Pressure",
            series=[
                TrendSeries(name="Systolic", unit="mmHg", data_points=[
                    TrendPoint(date="Sep", value=152),
                    TrendPoint(date="Jan", value=122),
                ]),
            ],
            medications=[
                MedTimelineRow(drug="Lisinopril", segments=[
                    MedTimelineSegment(label="10mg", flex=3, active=True),
                    MedTimelineSegment(label="20mg", flex=4, active=True),
                ]),
            ],
        )
        assert len(viz.medications) == 1
        assert viz.medications[0].drug == "Lisinopril"

    def test_valid_encounter_timeline(self):
        """ClinicalVisualization with encounter_timeline type."""
        viz = ClinicalVisualization(
            type="encounter_timeline",
            title="Encounter History",
            events=[
                TimelineEvent(
                    date="2026-01-25",
                    title="General examination",
                    detail="Routine visit",
                    category="AMB",
                ),
                TimelineEvent(
                    date="2025-07-14",
                    title="Emergency room admission",
                    category="EMER",
                ),
            ],
        )
        assert viz.type == "encounter_timeline"
        assert len(viz.events) == 2
        assert viz.events[0].category == "AMB"

    def test_invalid_visualization_type(self):
        """ClinicalVisualization rejects unknown types."""
        with pytest.raises(ValidationError) as exc_info:
            ClinicalVisualization(type="pie_chart", title="Test")
        assert "type" in str(exc_info.value)

    def test_trend_status_validation(self):
        """Trend status must be a valid literal."""
        with pytest.raises(ValidationError):
            ClinicalVisualization(
                type="trend_chart",
                title="Test",
                trend_status="invalid",
            )

    def test_range_band_severity_validation(self):
        """RangeBand severity must be normal/warning/critical."""
        with pytest.raises(ValidationError):
            RangeBand(y1=0, y2=10, severity="mild")

    def test_minimal_trend_chart(self):
        """Trend chart with only required fields."""
        viz = ClinicalVisualization(type="trend_chart", title="Weight Trend")
        assert viz.subtitle is None
        assert viz.series is None
        assert viz.range_bands is None

    def test_trend_point_with_label(self):
        """TrendPoint with optional annotation label."""
        point = TrendPoint(date="Sep 15", value=148, label="Started Lisinopril 10mg")
        assert point.label == "Started Lisinopril 10mg"


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


class TestLightningResponse:
    """Tests for LightningResponse schema."""

    def test_minimal_lightning_response(self):
        """LightningResponse with only required narrative."""
        response = LightningResponse(narrative="The patient is on metformin 500mg.")
        assert response.narrative == "The patient is on metformin 500mg."
        assert response.follow_ups is None

    def test_lightning_response_with_follow_ups(self):
        """LightningResponse with follow-up questions."""
        response = LightningResponse(
            narrative="## Medications\n\n- Metformin 500mg\n- Lisinopril 10mg",
            follow_ups=[
                FollowUp(question="What are the allergies?"),
                FollowUp(question="Show me recent lab results"),
            ],
        )
        assert len(response.follow_ups) == 2
        assert response.follow_ups[0].question == "What are the allergies?"

    def test_lightning_response_empty_narrative_rejected(self):
        """LightningResponse requires non-empty narrative."""
        with pytest.raises(ValidationError) as exc_info:
            LightningResponse(narrative="")
        assert "narrative" in str(exc_info.value)

    def test_lightning_response_missing_narrative_rejected(self):
        """LightningResponse requires narrative field."""
        with pytest.raises(ValidationError) as exc_info:
            LightningResponse()
        assert "narrative" in str(exc_info.value)

    def test_lightning_response_json_serialization(self):
        """LightningResponse can be serialized to JSON."""
        response = LightningResponse(
            narrative="Patient has no known allergies.",
            follow_ups=[FollowUp(question="What medications?")],
        )
        json_str = response.model_dump_json()
        assert "no known allergies" in json_str
        assert "What medications?" in json_str

    def test_lightning_response_from_json(self):
        """LightningResponse can be parsed from JSON."""
        json_data = {
            "narrative": "BP is 120/80 mmHg.",
            "follow_ups": [{"question": "Show vitals trend"}],
        }
        response = LightningResponse.model_validate(json_data)
        assert response.narrative == "BP is 120/80 mmHg."
        assert len(response.follow_ups) == 1

    def test_lightning_response_has_no_extra_fields(self):
        """LightningResponse has narrative, tables, follow_ups, and needs_deeper_search -- no thinking, insights, etc."""
        fields = set(LightningResponse.model_fields.keys())
        assert fields == {"narrative", "tables", "follow_ups", "needs_deeper_search"}

    def test_needs_deeper_search_defaults_false(self):
        """needs_deeper_search defaults to False."""
        response = LightningResponse(narrative="Patient is on metformin.")
        assert response.needs_deeper_search is False

    def test_needs_deeper_search_true(self):
        """needs_deeper_search can be set to True."""
        response = LightningResponse(
            narrative="Searching the full patient record for A1c...",
            needs_deeper_search=True,
        )
        assert response.needs_deeper_search is True


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
        assert response.follow_ups is None
        assert response.needs_deeper_search is False

    def test_needs_deeper_search_defaults_false(self):
        """AgentResponse.needs_deeper_search defaults to False."""
        response = AgentResponse(narrative="Test.")
        assert response.needs_deeper_search is False

    def test_needs_deeper_search_propagated(self):
        """AgentResponse.needs_deeper_search can be set to True."""
        response = AgentResponse(narrative="Searching...", needs_deeper_search=True)
        assert response.needs_deeper_search is True

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
            tables=[
                ClinicalTable(
                    type="medications",
                    title="Medications",
                    rows='[{"medication": "Metformin", "status": "active"}]',
                )
            ],
            visualizations=[
                ClinicalVisualization(
                    type="trend_chart",
                    title="HbA1c Trend",
                    series=[TrendSeries(
                        name="HbA1c",
                        unit="%",
                        data_points=[TrendPoint(date="Jan", value=7.2)],
                    )],
                )
            ],
            follow_ups=[FollowUp(question="What about blood pressure?")],
        )
        assert response.thinking is not None
        assert len(response.insights) == 1
        assert len(response.tables) == 1
        assert response.tables[0].type == "medications"
        assert len(response.visualizations) == 1
        assert response.visualizations[0].type == "trend_chart"
        assert len(response.follow_ups) == 1

    def test_no_actions_field(self):
        """AgentResponse does not have an actions field."""
        assert "actions" not in AgentResponse.model_fields

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

    def test_response_with_clinical_table_from_json(self):
        """AgentResponse with clinical table can be parsed from JSON."""
        import json
        json_data = {
            "narrative": "Here are the medications.",
            "tables": [
                {
                    "type": "medications",
                    "title": "Current Medications",
                    "rows": json.dumps([
                        {
                            "medication": "Lisinopril 10 MG",
                            "status": "active",
                            "frequency": "1x daily",
                        }
                    ]),
                }
            ],
        }
        response = AgentResponse.model_validate(json_data)
        assert len(response.tables) == 1
        assert response.tables[0].type == "medications"
        parsed = json.loads(response.tables[0].rows)
        assert parsed[0]["medication"] == "Lisinopril 10 MG"

    def test_response_with_visualization_from_json(self):
        """AgentResponse with visualization can be parsed from JSON."""
        json_data = {
            "narrative": "Here is the trend.",
            "visualizations": [
                {
                    "type": "trend_chart",
                    "title": "HbA1c Trend",
                    "current_value": "7.2%",
                    "trend_summary": "↓ 21%",
                    "trend_status": "warning",
                    "series": [
                        {
                            "name": "HbA1c",
                            "unit": "%",
                            "data_points": [
                                {"date": "Jan", "value": 9.1},
                                {"date": "Jul", "value": 7.2},
                            ],
                        }
                    ],
                }
            ],
        }
        response = AgentResponse.model_validate(json_data)
        assert len(response.visualizations) == 1
        assert response.visualizations[0].current_value == "7.2%"
        assert len(response.visualizations[0].series[0].data_points) == 2
