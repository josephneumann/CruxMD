"""Agent response schemas for structured LLM output.

These schemas define the structured format for agent responses, enabling
rich conversational experiences with clinical insights, visualizations,
and suggested follow-ups. The LLM outputs JSON conforming to AgentResponse,
which is validated by Pydantic before being sent to the frontend.
"""

from typing import Literal

from pydantic import BaseModel, Field


class DataQuery(BaseModel):
    """Query specification for resolving data at runtime.

    The LLM specifies what data it needs, and the backend resolves
    the query against the patient's FHIR resources before sending
    the response to the frontend.
    """

    resource_types: list[str] | None = Field(
        default=None,
        description="FHIR resource types to query (e.g., ['Observation', 'Condition'])",
    )
    filters: str | None = Field(
        default=None,
        description="JSON-encoded key-value filters (e.g., '{\"code\": \"HbA1c\"}')",
    )
    time_range: str | None = Field(
        default=None,
        description="Time range for the query (e.g., 'last_6_months', 'last_year')",
    )
    limit: int | None = Field(
        default=None,
        ge=1,
        le=1000,
        description="Maximum number of results to return",
    )


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


class TableColumn(BaseModel):
    """Column definition for a data table."""

    key: str = Field(
        min_length=1,
        description="Key to extract from data rows",
    )
    header: str = Field(
        min_length=1,
        description="Display header for the column",
    )
    format: Literal["text", "date", "number", "badge"] | None = Field(
        default=None,
        description="How to format values in this column",
    )


class Visualization(BaseModel):
    """Visualization specification for charts and graphs."""

    type: Literal["line_chart", "bar_chart", "timeline", "vitals_grid"] = Field(
        description="Type of visualization to render"
    )
    title: str = Field(
        min_length=1,
        max_length=200,
        description="Title for the visualization",
    )
    description: str | None = Field(
        default=None,
        description="Optional description or subtitle",
    )
    data_query: DataQuery = Field(
        description="Query to resolve the visualization data"
    )
    config: str | None = Field(
        default=None,
        description="JSON-encoded configuration for the visualization",
    )


class DataTable(BaseModel):
    """Table specification for displaying structured data."""

    title: str = Field(
        min_length=1,
        max_length=200,
        description="Title for the table",
    )
    columns: list[TableColumn] = Field(
        min_length=1,
        description="Column definitions for the table",
    )
    data_query: DataQuery = Field(
        description="Query to resolve the table data"
    )


class Action(BaseModel):
    """Suggested action for the user to take."""

    label: str = Field(
        min_length=1,
        max_length=100,
        description="Button label for the action",
    )
    type: Literal["order", "refer", "document", "alert", "link"] = Field(
        description="Category of action"
    )
    description: str | None = Field(
        default=None,
        description="Explanation of what the action does",
    )
    payload: str | None = Field(
        default=None,
        description="JSON-encoded data payload for the action",
    )


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


class AgentResponse(BaseModel):
    """Structured response from the clinical reasoning agent.

    This is the primary output format for the LLM. It contains
    a required narrative response along with optional structured
    elements like insights, visualizations, and follow-up suggestions.
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
    visualizations: list[Visualization] | None = Field(
        default=None,
        description="Visualizations to render",
    )
    tables: list[DataTable] | None = Field(
        default=None,
        description="Data tables to display",
    )
    actions: list[Action] | None = Field(
        default=None,
        description="Suggested actions for the user",
    )
    follow_ups: list[FollowUp] | None = Field(
        default=None,
        description="Suggested follow-up questions",
    )
