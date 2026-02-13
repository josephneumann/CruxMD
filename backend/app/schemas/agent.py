"""Agent response schemas for structured LLM output.

These schemas define the structured format for agent responses, enabling
rich conversational experiences with clinical insights, visualizations,
and suggested follow-ups. The LLM outputs JSON conforming to AgentResponse
(narrative, insights, visualizations, follow-ups). Tables are generated
deterministically by backend code and attached to the API response separately.
"""

from typing import Any, Literal

from pydantic import BaseModel, Field


class Insight(BaseModel):
    """Clinical insight highlighted for the user.

    Insights are callout boxes that draw attention to important
    clinical information, warnings, or positive findings.
    """

    type: Literal["info", "warning", "critical", "positive"] = Field(
        description="Severity/category of the insight"
    )
    title: str = Field(
        min_length=1,
        max_length=200,
        description="Short title for the insight",
    )
    content: str = Field(
        min_length=1,
        description="Detailed content of the insight (markdown supported)",
    )
    citations: list[str] | None = Field(
        default=None,
        description="FHIR resource IDs that support this insight",
    )


class ClinicalTable(BaseModel):
    """Resource-typed clinical data table with inline data.

    Tables are generated deterministically by backend code (table_builder.py),
    not by the LLM. The frontend uses the type discriminator to select
    per-resource-type renderers with clinical styling.
    """

    type: Literal[
        "medications", "lab_results", "vitals", "conditions",
        "allergies", "immunizations", "procedures", "encounters",
    ] = Field(description="Clinical resource type determining column layout")
    title: str = Field(
        max_length=200,
        description="Table title displayed in the card header",
    )
    rows: list[dict[str, Any]] = Field(
        description="Array of row objects with keys matching the type's column spec",
    )


class TrendPoint(BaseModel):
    """Single data point on a trend chart."""

    date: str
    value: float
    label: str | None = None


class TrendSeries(BaseModel):
    """One line/area on a trend chart."""

    name: str
    unit: str | None = None
    data_points: list[TrendPoint]


class ReferenceLine(BaseModel):
    """Horizontal threshold line (e.g., 'Target <7%')."""

    value: float
    label: str


class RangeBand(BaseModel):
    """Background color zone for clinical ranges."""

    y1: float
    y2: float
    severity: Literal["normal", "warning", "critical"]
    label: str | None = None


class MedTimelineSegment(BaseModel):
    """One segment in a medication timeline bar."""

    label: str
    flex: int
    active: bool


class MedTimelineRow(BaseModel):
    """One drug row in the medication timeline."""

    drug: str
    segments: list[MedTimelineSegment]


class TimelineEvent(BaseModel):
    """Single event on an encounter timeline."""

    date: str
    title: str
    detail: str | None = None
    category: str | None = None


class ClinicalVisualization(BaseModel):
    """Clinical chart or timeline with inline data.

    The type field determines rendering variant:
    - trend_chart: auto-selects area/line/multi-series based on data
    - encounter_timeline: vertical CSS timeline with category dots
    """

    type: Literal["trend_chart", "encounter_timeline"] = Field(
        description="Visualization type determining render variant"
    )
    title: str = Field(
        max_length=200,
        description="Chart title displayed in the card header",
    )
    subtitle: str | None = None
    # Card header metrics
    current_value: str | None = None
    trend_summary: str | None = None
    trend_status: Literal["positive", "warning", "critical", "neutral"] | None = None
    # trend_chart fields
    series: list[TrendSeries] | None = None
    reference_lines: list[ReferenceLine] | None = None
    range_bands: list[RangeBand] | None = None
    medications: list[MedTimelineRow] | None = None
    # encounter_timeline fields
    events: list[TimelineEvent] | None = None


class FollowUp(BaseModel):
    """Suggested follow-up question for emergent navigation."""

    question: str = Field(
        min_length=1,
        max_length=80,
        description="Short follow-up question (max 80 chars) displayed as a clickable chip",
    )
    intent: str | None = Field(
        default=None,
        description="The intent or category of the question",
    )


class LightningResponse(BaseModel):
    """Minimal response for Lightning-tier fact extraction.

    Simpler schema for gpt-4o-mini structured output reliability.
    Includes narrative and follow-ups only. No thinking, insights,
    tables, or visualizations — those require Quick/Deep tier.
    """

    narrative: str = Field(
        min_length=1,
        description="Direct answer in markdown format",
    )
    follow_ups: list[FollowUp] | None = Field(
        default=None,
        description="2-3 suggested follow-up questions",
    )
    needs_deeper_search: bool = Field(
        default=False,
        description="True if the requested data was not found in the patient summary",
    )


class AgentResponse(BaseModel):
    """Structured response from the clinical reasoning agent (LLM output schema).

    This is the schema passed to OpenAI structured output. It contains
    a required narrative response along with optional structured
    elements like insights, visualizations, and follow-up suggestions.
    Tables are NOT included here — they are generated deterministically
    by backend code and attached via ChatAgentResponse.
    """

    thinking: str | None = Field(
        default=None,
        description="Optional reasoning process (can be shown/hidden in UI)",
    )
    narrative: str = Field(
        min_length=1,
        description="Main response text in markdown format",
    )
    insights: list[Insight] | None = Field(
        default=None,
        description="Clinical insights to highlight",
    )
    visualizations: list[ClinicalVisualization] | None = Field(
        default=None,
        description="Clinical charts and timelines",
    )
    follow_ups: list[FollowUp] | None = Field(
        default=None,
        description="Suggested follow-up questions",
    )
    needs_deeper_search: bool = Field(
        default=False,
        description="Internal flag: True if Lightning couldn't answer from summary",
    )


class ChatAgentResponse(AgentResponse):
    """API response model — extends LLM output with deterministic tables.

    Tables are generated by backend code (table_builder.py), not by the LLM.
    This model is used for the API response only, never as the OpenAI schema.
    """

    tables: list[ClinicalTable] | None = Field(
        default=None,
        description="Clinical data tables (deterministically generated by backend)",
    )
