"""Pydantic schemas for Task API.

These schemas define request/response formats for the Task API,
including the AI provenance and context configuration structures.
"""

from datetime import date, datetime
from enum import Enum
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


# === Enums (match SQLAlchemy enums) ===


class TaskType(str, Enum):
    """Types of clinical tasks."""

    CRITICAL_LAB_REVIEW = "critical_lab_review"
    ABNORMAL_RESULT = "abnormal_result"
    HOSPITALIZATION_ALERT = "hospitalization_alert"
    PATIENT_MESSAGE = "patient_message"
    EXTERNAL_RESULT = "external_result"
    PRE_VISIT_PREP = "pre_visit_prep"
    FOLLOW_UP = "follow_up"
    APPOINTMENT = "appointment"
    RESEARCH_REVIEW = "research_review"
    ORDER_SIGNATURE = "order_signature"
    CUSTOM = "custom"


class TaskCategory(str, Enum):
    """Task categories for queue organization."""

    CRITICAL = "critical"
    ROUTINE = "routine"
    SCHEDULE = "schedule"
    RESEARCH = "research"


class TaskStatus(str, Enum):
    """Task lifecycle states."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    PAUSED = "paused"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    DEFERRED = "deferred"


class TaskPriority(str, Enum):
    """FHIR-aligned priority levels."""

    ROUTINE = "routine"
    URGENT = "urgent"
    ASAP = "asap"
    STAT = "stat"


# === AI Provenance Schemas ===


class TaskTrigger(BaseModel):
    """What triggered this task to be created."""

    type: Literal["care_gap", "clinical_rule", "user_query", "scheduled", "agent_observation"]
    source_data: list[str] | None = Field(
        default=None,
        description="FHIR resource IDs that triggered this task",
    )
    query: str | None = Field(
        default=None,
        description="User question if triggered by query",
    )
    rule_id: str | None = Field(
        default=None,
        description="Clinical rule identifier if triggered by rule",
    )


class Citation(BaseModel):
    """Reference to supporting evidence."""

    resource_id: str = Field(description="FHIR resource ID")
    resource_type: str = Field(description="FHIR resource type")
    display: str | None = Field(default=None, description="Human-readable reference")


class AIReasoning(BaseModel):
    """AI reasoning process for task creation or update."""

    model: str = Field(description="Model used (e.g., 'gpt-4o')")
    timestamp: datetime
    confidence: float | None = Field(default=None, ge=0, le=1)
    chain_of_thought: str | None = Field(default=None, description="Reasoning if shown")
    citations: list[Citation] | None = None


class ExternalReference(BaseModel):
    """Reference to external clinical guidelines or resources."""

    url: str | None = None
    title: str
    source: str | None = None


class Evidence(BaseModel):
    """Supporting evidence for the task."""

    supporting_facts: list[str] | None = Field(
        default=None,
        description="FHIR resource IDs of supporting Conditions, Observations, etc.",
    )
    guidelines: list[ExternalReference] | None = None


class Disposition(BaseModel):
    """User disposition on AI-generated task."""

    status: Literal["pending", "accepted", "modified", "rejected", "deferred"]
    modified_at: datetime | None = None
    modified_by: str | None = Field(default=None, description="User/provider ID")
    rejection_reason: str | None = None
    feedback: str | None = None


class AITaskProvenance(BaseModel):
    """Complete AI provenance for a task.

    Tracks how the task was created, the AI's reasoning,
    supporting evidence, and user disposition.
    """

    trigger: TaskTrigger
    reasoning: AIReasoning | None = None
    evidence: Evidence | None = None
    disposition: Disposition | None = None


# === Context Configuration Schemas ===


class ContextPanel(BaseModel):
    """Configuration for a sidebar panel."""

    id: str
    component: Literal[
        "PatientHeader",
        "MedList",
        "LabPanel",
        "Allergies",
        "ProblemList",
        "RecentNotes",
        "MessageThread",
        "CareGaps",
        "VisitContext",
        "AIContextSummary",
    ]
    props: dict | None = None
    filter: str | None = Field(default=None, description="Filter to apply to data")
    priority: int = Field(description="Display order (lower = higher)")
    collapsible: bool = True
    default_expanded: bool = True


class ContextAction(BaseModel):
    """Action button in the sidebar."""

    label: str
    type: Literal["order", "message", "refer", "document", "navigate"]
    requires_approval: bool = False


class TaskContextConfig(BaseModel):
    """Complete sidebar configuration for a task type."""

    panels: list[ContextPanel]
    actions: list[ContextAction] | None = None


# === API Request/Response Schemas ===


class TaskCreate(BaseModel):
    """Schema for creating a new task."""

    type: TaskType
    category: TaskCategory
    priority: TaskPriority = TaskPriority.ROUTINE
    priority_score: int | None = Field(default=None, ge=0, le=100)
    title: str = Field(min_length=1, max_length=140)
    description: str | None = None
    patient_id: UUID
    session_id: UUID | None = None
    focus_resource_id: UUID | None = None
    provenance: AITaskProvenance | None = None
    context_config: TaskContextConfig | None = None
    due_on: date | None = None


class TaskUpdate(BaseModel):
    """Schema for updating a task."""

    status: TaskStatus | None = None
    priority: TaskPriority | None = None
    priority_score: int | None = Field(default=None, ge=0, le=100)
    title: str | None = Field(default=None, min_length=1, max_length=140)
    description: str | None = None
    session_id: UUID | None = None
    provenance: AITaskProvenance | None = None
    context_config: TaskContextConfig | None = None
    due_on: date | None = None


class TaskResponse(BaseModel):
    """Schema for task in API responses."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: TaskType
    category: TaskCategory
    status: TaskStatus
    priority: TaskPriority
    priority_score: int | None
    title: str
    description: str | None
    patient_id: UUID
    session_id: UUID | None
    focus_resource_id: UUID | None
    provenance: dict | None
    context_config: dict | None
    due_on: date | None
    created_at: datetime
    modified_at: datetime


class TaskListResponse(BaseModel):
    """Paginated list of tasks."""

    items: list[TaskResponse]
    total: int
    skip: int
    limit: int


class TaskQueueResponse(BaseModel):
    """Task queue organized by category."""

    critical: list[TaskResponse]
    routine: list[TaskResponse]
    schedule: list[TaskResponse]
    research: list[TaskResponse]
    total: int
