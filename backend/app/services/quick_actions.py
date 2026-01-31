"""Quick Action surfacing logic.

Assembles contextual quick actions from three sources:
1. Task-type defaults — static actions appropriate for the task type
2. AI-driven suggestions — extracted from the last agent response
3. Clinical rule triggers — derived from verified clinical facts

Actions are deduplicated by label and capped at MAX_ACTIONS.
"""

import logging
from typing import Any

from app.schemas.quick_actions import QuickAction, QuickActionSource, QuickActionType
from app.schemas.task import TaskType
from app.utils.fhir_helpers import extract_display_name

logger = logging.getLogger(__name__)

MAX_ACTIONS = 4

# === Task-Type Default Actions ===

TASK_TYPE_DEFAULTS: dict[TaskType, list[QuickAction]] = {
    TaskType.CRITICAL_LAB_REVIEW: [
        QuickAction(
            label="Repeat stat",
            type=QuickActionType.ORDER,
            priority=10,
            source=QuickActionSource.TASK_DEFAULT,
        ),
        QuickAction(
            label="Call patient",
            type=QuickActionType.MESSAGE,
            priority=20,
            source=QuickActionSource.TASK_DEFAULT,
        ),
    ],
    TaskType.ABNORMAL_RESULT: [
        QuickAction(
            label="Order follow-up",
            type=QuickActionType.ORDER,
            priority=20,
            source=QuickActionSource.TASK_DEFAULT,
        ),
        QuickAction(
            label="Message patient",
            type=QuickActionType.MESSAGE,
            priority=30,
            source=QuickActionSource.TASK_DEFAULT,
        ),
    ],
    TaskType.PATIENT_MESSAGE: [
        QuickAction(
            label="Reply to patient",
            type=QuickActionType.MESSAGE,
            priority=10,
            source=QuickActionSource.TASK_DEFAULT,
        ),
    ],
    TaskType.PRE_VISIT_PREP: [
        QuickAction(
            label="Review care gaps",
            type=QuickActionType.NAVIGATE,
            priority=20,
            source=QuickActionSource.TASK_DEFAULT,
        ),
        QuickAction(
            label="Order pre-visit labs",
            type=QuickActionType.ORDER,
            priority=30,
            source=QuickActionSource.TASK_DEFAULT,
        ),
    ],
    TaskType.ORDER_SIGNATURE: [
        QuickAction(
            label="Sign order",
            type=QuickActionType.ORDER,
            priority=10,
            source=QuickActionSource.TASK_DEFAULT,
        ),
    ],
    TaskType.HOSPITALIZATION_ALERT: [
        QuickAction(
            label="Review discharge summary",
            type=QuickActionType.NAVIGATE,
            priority=10,
            source=QuickActionSource.TASK_DEFAULT,
        ),
        QuickAction(
            label="Schedule follow-up",
            type=QuickActionType.ORDER,
            priority=20,
            source=QuickActionSource.TASK_DEFAULT,
        ),
    ],
    TaskType.FOLLOW_UP: [
        QuickAction(
            label="Document note",
            type=QuickActionType.DOCUMENT,
            priority=20,
            source=QuickActionSource.TASK_DEFAULT,
        ),
    ],
}

# === Clinical Rule Definitions ===
# Each rule: (condition_check_fn, action_to_surface)
# condition_check_fn receives (medications, conditions, allergies) as FHIR dicts


def _check_critical_potassium_with_k_sparing(
    medications: list[dict[str, Any]],
    conditions: list[dict[str, Any]],
    allergies: list[dict[str, Any]],
    focus_resource: dict[str, Any] | None,
) -> QuickAction | None:
    """If focus resource is a critical K+ result and patient is on a K+-sparing med, suggest hold."""
    if not focus_resource:
        return None

    # Check if focus resource is a potassium observation
    display = extract_display_name(focus_resource) or ""
    if "potassium" not in display.lower() and "k+" not in display.lower():
        return None

    k_sparing_keywords = frozenset(["spironolactone", "amiloride", "triamterene", "eplerenone"])
    for med in medications:
        med_display = (extract_display_name(med) or "").lower()
        if any(kw in med_display for kw in k_sparing_keywords):
            return QuickAction(
                label=f"Hold {extract_display_name(med)}",
                type=QuickActionType.ORDER,
                priority=5,
                source=QuickActionSource.CLINICAL_RULE,
                payload={"rule": "critical_k_plus_k_sparing", "medication": extract_display_name(med)},
            )
    return None


def _check_allergy_medication_conflict(
    medications: list[dict[str, Any]],
    conditions: list[dict[str, Any]],
    allergies: list[dict[str, Any]],
    focus_resource: dict[str, Any] | None,
) -> QuickAction | None:
    """If patient has high-criticality allergy, suggest reviewing med list."""
    high_crit = [a for a in allergies if a.get("criticality") == "high"]
    if not high_crit:
        return None

    display = extract_display_name(high_crit[0]) or "allergen"
    return QuickAction(
        label="Review allergy alerts",
        type=QuickActionType.NAVIGATE,
        priority=10,
        source=QuickActionSource.CLINICAL_RULE,
        payload={"rule": "high_criticality_allergy", "allergen": display},
    )


CLINICAL_RULES = [
    _check_critical_potassium_with_k_sparing,
    _check_allergy_medication_conflict,
]


def get_task_defaults(task_type: TaskType) -> list[QuickAction]:
    """Get default quick actions for a task type."""
    return list(TASK_TYPE_DEFAULTS.get(task_type, []))


def get_clinical_rule_actions(
    medications: list[dict[str, Any]],
    conditions: list[dict[str, Any]],
    allergies: list[dict[str, Any]],
    focus_resource: dict[str, Any] | None = None,
) -> list[QuickAction]:
    """Evaluate clinical rules and return triggered actions."""
    actions: list[QuickAction] = []
    for rule_fn in CLINICAL_RULES:
        action = rule_fn(medications, conditions, allergies, focus_resource)
        if action is not None:
            actions.append(action)
    return actions


def get_ai_suggestion_actions(ai_suggestions: list[dict[str, Any]] | None) -> list[QuickAction]:
    """Convert AI-driven suggestions into quick actions.

    ai_suggestions should be a list of dicts with at minimum:
      - label: str
      - type: str (one of QuickActionType values)
    Optionally:
      - priority: int
      - payload: dict
    """
    if not ai_suggestions:
        return []

    actions: list[QuickAction] = []
    for suggestion in ai_suggestions:
        try:
            actions.append(
                QuickAction(
                    label=suggestion["label"],
                    type=QuickActionType(suggestion["type"]),
                    priority=suggestion.get("priority", 40),
                    source=QuickActionSource.AI_INSIGHT,
                    payload=suggestion.get("payload"),
                )
            )
        except (KeyError, ValueError):
            logger.warning(f"Skipping invalid AI suggestion: {suggestion}")
    return actions


def deduplicate_actions(actions: list[QuickAction]) -> list[QuickAction]:
    """Deduplicate actions by label, keeping the highest-priority (lowest number) version."""
    seen: dict[str, QuickAction] = {}
    for action in actions:
        key = action.label.lower()
        if key not in seen or action.priority < seen[key].priority:
            seen[key] = action
    return list(seen.values())


def surface_quick_actions(
    task_type: TaskType,
    medications: list[dict[str, Any]],
    conditions: list[dict[str, Any]],
    allergies: list[dict[str, Any]],
    focus_resource: dict[str, Any] | None = None,
    ai_suggestions: list[dict[str, Any]] | None = None,
) -> list[QuickAction]:
    """Assemble, deduplicate, and return top quick actions.

    Sources (in priority order):
    1. Clinical rule triggers (highest priority actions)
    2. Task-type defaults
    3. AI-driven suggestions

    Returns at most MAX_ACTIONS actions, sorted by priority (lowest number first).
    """
    actions: list[QuickAction] = []

    # 1. Clinical rules
    actions.extend(get_clinical_rule_actions(medications, conditions, allergies, focus_resource))

    # 2. Task-type defaults
    actions.extend(get_task_defaults(task_type))

    # 3. AI suggestions
    actions.extend(get_ai_suggestion_actions(ai_suggestions))

    # Deduplicate and sort by priority
    actions = deduplicate_actions(actions)
    actions.sort(key=lambda a: a.priority)

    return actions[:MAX_ACTIONS]
