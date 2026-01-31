"""Tests for Quick Action schemas and surfacing logic."""

import pytest

from app.schemas.quick_actions import QuickAction, QuickActionSource, QuickActionType
from app.schemas.task import TaskType
from app.services.quick_actions import (
    MAX_ACTIONS,
    deduplicate_actions,
    get_ai_suggestion_actions,
    get_clinical_rule_actions,
    get_task_defaults,
    surface_quick_actions,
)


# =============================================================================
# Schema Tests
# =============================================================================


class TestQuickActionSchema:
    def test_creates_minimal_action(self):
        action = QuickAction(
            label="Test",
            type=QuickActionType.ORDER,
            source=QuickActionSource.TASK_DEFAULT,
        )
        assert action.label == "Test"
        assert action.priority == 50
        assert action.payload is None

    def test_creates_action_with_payload(self):
        action = QuickAction(
            label="Hold med",
            type=QuickActionType.ORDER,
            priority=5,
            source=QuickActionSource.CLINICAL_RULE,
            payload={"medication": "Spironolactone"},
        )
        assert action.payload == {"medication": "Spironolactone"}

    def test_priority_bounds(self):
        with pytest.raises(Exception):
            QuickAction(
                label="Bad",
                type=QuickActionType.ORDER,
                priority=101,
                source=QuickActionSource.TASK_DEFAULT,
            )


# =============================================================================
# Task Default Tests
# =============================================================================


class TestGetTaskDefaults:
    def test_critical_lab_review_defaults(self):
        actions = get_task_defaults(TaskType.CRITICAL_LAB_REVIEW)
        assert len(actions) == 2
        labels = {a.label for a in actions}
        assert "Repeat stat" in labels
        assert "Call patient" in labels

    def test_unknown_task_type_returns_empty(self):
        actions = get_task_defaults(TaskType.CUSTOM)
        assert actions == []

    def test_returns_copies(self):
        """Ensure returned list is a copy, not a reference to the original."""
        a1 = get_task_defaults(TaskType.CRITICAL_LAB_REVIEW)
        a2 = get_task_defaults(TaskType.CRITICAL_LAB_REVIEW)
        assert a1 is not a2


# =============================================================================
# Clinical Rule Tests
# =============================================================================


class TestGetClinicalRuleActions:
    def test_potassium_with_k_sparing_triggers(self):
        meds = [
            {
                "resourceType": "MedicationRequest",
                "medicationCodeableConcept": {
                    "coding": [{"display": "Spironolactone 25 MG"}]
                },
                "status": "active",
            }
        ]
        focus = {
            "resourceType": "Observation",
            "code": {"coding": [{"display": "Potassium [Moles/volume] in Blood"}]},
        }
        actions = get_clinical_rule_actions(meds, [], [], focus_resource=focus)
        assert len(actions) >= 1
        assert any("Hold" in a.label for a in actions)

    def test_no_trigger_without_focus(self):
        meds = [
            {
                "medicationCodeableConcept": {
                    "coding": [{"display": "Spironolactone 25 MG"}]
                },
                "status": "active",
            }
        ]
        actions = get_clinical_rule_actions(meds, [], [])
        # No K+ focus resource, so K+ rule shouldn't fire
        assert not any("Hold" in a.label for a in actions)

    def test_high_criticality_allergy_triggers(self):
        allergies = [
            {
                "code": {"coding": [{"display": "Penicillin"}]},
                "criticality": "high",
                "category": ["medication"],
            }
        ]
        actions = get_clinical_rule_actions([], [], allergies)
        assert len(actions) >= 1
        assert any("allergy" in a.label.lower() for a in actions)

    def test_no_rules_fire_for_empty_data(self):
        actions = get_clinical_rule_actions([], [], [])
        assert actions == []


# =============================================================================
# AI Suggestion Tests
# =============================================================================


class TestGetAISuggestionActions:
    def test_converts_valid_suggestions(self):
        suggestions = [
            {"label": "Check HbA1c", "type": "order", "priority": 30},
        ]
        actions = get_ai_suggestion_actions(suggestions)
        assert len(actions) == 1
        assert actions[0].source == QuickActionSource.AI_INSIGHT

    def test_skips_invalid_suggestions(self):
        suggestions = [
            {"label": "Bad", "type": "invalid_type"},
            {"missing_label": True, "type": "order"},
        ]
        actions = get_ai_suggestion_actions(suggestions)
        assert actions == []

    def test_returns_empty_for_none(self):
        assert get_ai_suggestion_actions(None) == []


# =============================================================================
# Deduplication Tests
# =============================================================================


class TestDeduplicateActions:
    def test_deduplicates_by_label(self):
        actions = [
            QuickAction(label="Call patient", type=QuickActionType.MESSAGE, priority=20, source=QuickActionSource.TASK_DEFAULT),
            QuickAction(label="Call patient", type=QuickActionType.MESSAGE, priority=30, source=QuickActionSource.AI_INSIGHT),
        ]
        result = deduplicate_actions(actions)
        assert len(result) == 1
        assert result[0].priority == 20  # keeps higher priority (lower number)

    def test_case_insensitive_dedup(self):
        actions = [
            QuickAction(label="Call Patient", type=QuickActionType.MESSAGE, priority=20, source=QuickActionSource.TASK_DEFAULT),
            QuickAction(label="call patient", type=QuickActionType.MESSAGE, priority=30, source=QuickActionSource.AI_INSIGHT),
        ]
        result = deduplicate_actions(actions)
        assert len(result) == 1


# =============================================================================
# Surface Quick Actions (Integration)
# =============================================================================


class TestSurfaceQuickActions:
    def test_returns_max_4_actions(self):
        # Critical lab review has 2 defaults + we add AI suggestions
        ai = [
            {"label": "AI action 1", "type": "order"},
            {"label": "AI action 2", "type": "message"},
            {"label": "AI action 3", "type": "navigate"},
        ]
        actions = surface_quick_actions(
            task_type=TaskType.CRITICAL_LAB_REVIEW,
            medications=[],
            conditions=[],
            allergies=[],
            ai_suggestions=ai,
        )
        assert len(actions) <= MAX_ACTIONS

    def test_sorted_by_priority(self):
        actions = surface_quick_actions(
            task_type=TaskType.CRITICAL_LAB_REVIEW,
            medications=[],
            conditions=[],
            allergies=[],
        )
        priorities = [a.priority for a in actions]
        assert priorities == sorted(priorities)

    def test_clinical_rules_included(self):
        allergies = [
            {
                "code": {"coding": [{"display": "Penicillin"}]},
                "criticality": "high",
            }
        ]
        actions = surface_quick_actions(
            task_type=TaskType.CRITICAL_LAB_REVIEW,
            medications=[],
            conditions=[],
            allergies=allergies,
        )
        sources = {a.source for a in actions}
        assert QuickActionSource.CLINICAL_RULE in sources

    def test_empty_for_custom_task_no_data(self):
        actions = surface_quick_actions(
            task_type=TaskType.CUSTOM,
            medications=[],
            conditions=[],
            allergies=[],
        )
        assert actions == []
