"""Pydantic schemas for Quick Actions.

Quick actions are contextual action suggestions surfaced to the clinician
based on the current task type, AI insights, and clinical rule triggers.
"""

from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class QuickActionType(str, Enum):
    """Types of quick actions available to clinicians."""

    ORDER = "order"
    MESSAGE = "message"
    REFER = "refer"
    DOCUMENT = "document"
    NAVIGATE = "navigate"


class QuickActionSource(str, Enum):
    """Where the quick action originated."""

    TASK_DEFAULT = "task_default"
    AI_INSIGHT = "ai_insight"
    CLINICAL_RULE = "clinical_rule"


class QuickAction(BaseModel):
    """A dynamically surfaced action suggestion for the clinician.

    Quick actions appear as pills/buttons in the UI, giving clinicians
    one-click access to the most relevant next steps for the current task.
    Unlike schemas.task.ContextAction (static sidebar config per task type),
    QuickActions are assembled at runtime from clinical rules, AI insights,
    and task-type defaults, with priority-based deduplication.
    """

    label: str = Field(..., description="Display text (e.g., 'Repeat K+ stat')")
    type: QuickActionType = Field(..., description="Action category")
    priority: int = Field(
        default=50,
        ge=0,
        le=100,
        description="Priority score (0=highest, 100=lowest)",
    )
    source: QuickActionSource = Field(..., description="Where this action originated")
    payload: dict[str, Any] | None = Field(
        default=None,
        description="Action-specific data (e.g., order details, navigation target)",
    )
