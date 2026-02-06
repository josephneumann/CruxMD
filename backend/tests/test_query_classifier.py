"""Tests for the adaptive three-tier query classifier.

Tests the heuristic classifier that routes queries to LIGHTNING (pure fact
extraction), QUICK (light reasoning), or DEEP (full clinical reasoning) profiles.
"""

import pytest

from app.services.query_classifier import (
    DEEP_PROFILE,
    LIGHTNING_PROFILE,
    QUICK_PROFILE,
    QueryProfile,
    QueryTier,
    classify_query,
)


# =============================================================================
# LIGHTNING Path Tests
# =============================================================================


class TestClassifyQueryLightningPath:
    """All three paths to LIGHTNING classification (no history, no temporal)."""

    # Path A: entity + lookup prefix
    @pytest.mark.parametrize("msg", [
        "What medications is the patient on?",
        "What meds is this patient taking?",
        "List all conditions",
        "Show me the allergies",
        "Any allergies?",
        "Latest labs?",
        "What are the vital signs?",
        "Current medications",
        "Active conditions",
        "Recent lab results",
        "Last visit date",
        "Tell me about the medications",
        "What about the medications?",
        "Give me the medication list",
        "How many medications?",
        "List encounters",
        "Show procedures",
        "Does the patient have any allergies?",
        "What immunizations has the patient had?",
        "What are the latest observations?",
        "What meds did the patient used to take?",
        "What conditions were resolved?",
        "What medications were stopped?",
        "When was the last visit?",
        "When was the last HbA1c?",
        "Active meds and conditions",
    ])
    def test_path_a_entity_plus_prefix(self, msg: str):
        assert classify_query(msg) == LIGHTNING_PROFILE

    # Path B: bare entity shortcut (<=30 chars)
    @pytest.mark.parametrize("msg", [
        "medications",
        "labs?",
        "allergies",
        "blood pressure",
        "vitals",
        "care plans",
        "Previous medications",
        "Former conditions",
        "bp",
        "bp?",
        "hr",
    ])
    def test_path_b_bare_entity(self, msg: str):
        assert classify_query(msg) == LIGHTNING_PROFILE

    # Path C: specific-item patterns (<=100 chars)
    @pytest.mark.parametrize("msg", [
        "What's the HbA1c?",
        "What is the latest A1c?",
        "What's the blood pressure?",
        "Is the patient on metformin?",
        "Does the patient have diabetes?",
        "Is the patient taking lisinopril?",
        "Are there any allergies?",
        "Is the patient allergic to penicillin?",
    ])
    def test_path_c_specific_item(self, msg: str):
        assert classify_query(msg) == LIGHTNING_PROFILE


# =============================================================================
# QUICK Path Tests
# =============================================================================


class TestClassifyQueryQuickPath:
    """Queries upgraded from LIGHTNING to QUICK via temporal modifiers or history."""

    # Temporal modifier upgrades LIGHTNING → QUICK
    @pytest.mark.parametrize("msg", [
        "What were the labs from January?",
        "What medications since 2025?",
        "Latest labs from last month",
        "Show vitals from the last week",
        "What tests were done in the past year?",
        "Labs before the surgery",
        "Medications during 2024",
        "What was the blood pressure this month?",
        "Show encounters over the last year",
        "What labs after March?",
    ])
    def test_temporal_modifier_upgrades_to_quick(self, msg: str):
        assert classify_query(msg) == QUICK_PROFILE

    # has_history upgrades LIGHTNING → QUICK
    @pytest.mark.parametrize("msg", [
        "What medications is the patient on?",
        "medications",
        "labs?",
        "bp",
        "What's the HbA1c?",
        "Is the patient on metformin?",
        "List all conditions",
        "allergies",
    ])
    def test_has_history_upgrades_to_quick(self, msg: str):
        assert classify_query(msg, has_history=True) == QUICK_PROFILE

    def test_temporal_plus_history_still_quick(self):
        """Both temporal modifier and history present — still QUICK, not DEEP."""
        assert classify_query(
            "What were the labs from January?", has_history=True,
        ) == QUICK_PROFILE


# =============================================================================
# DEEP Path Tests
# =============================================================================


class TestClassifyQueryDeepPath:
    """All paths to DEEP classification."""

    # Reasoning keywords
    @pytest.mark.parametrize("msg", [
        "Is metformin appropriate for this patient?",
        "Explain the HbA1c trend over the last year",
        "What drug interactions exist between the current medications?",
        "Compare the last two visits",
        "Why was lisinopril prescribed?",
        "How should we manage the diabetes going forward?",
        "What is the significance of the rising HbA1c?",
        "Assess the cardiovascular risk for this patient",
        "Should we consider changing the diabetes medication?",
        "Recommend next steps for managing hypertension",
        "Interpret the latest lab results in context of the diabetes",
        "Analyze the relationship between kidney function and BP meds",
    ])
    def test_reasoning_keywords(self, msg: str):
        assert classify_query(msg) == DEEP_PROFILE

    # Search/tool requests
    @pytest.mark.parametrize("msg", [
        "Search for all diabetes-related observations",
        "Look up the HbA1c history",
    ])
    def test_search_requests(self, msg: str):
        assert classify_query(msg) == DEEP_PROFILE

    # Conversation references
    @pytest.mark.parametrize("msg", [
        "You mentioned the medications earlier, tell me more",
    ])
    def test_conversation_references(self, msg: str):
        assert classify_query(msg) == DEEP_PROFILE

    # Summary/overview queries (no chart entity -> DEEP)
    @pytest.mark.parametrize("msg", [
        "Summarize the patient record",
        "Give me a summary",
        "Patient overview",
        "What do I need to know about this patient?",
        "Tell me about this patient",
        "Brief me on this patient",
    ])
    def test_summary_overview_queries(self, msg: str):
        assert classify_query(msg) == DEEP_PROFILE

    # Analytical phrases (entity present but analytical intent)
    @pytest.mark.parametrize("msg", [
        "Show me his glucose logs and any recent encounters — let's see if he's actually been having hypo episodes.",
        "Show me the labs and check if there's a pattern",
        "Pull up the encounters and determine if he was seen recently",
        "List medications and figure out which one is causing the issue",
    ])
    def test_analytical_phrases(self, msg: str):
        assert classify_query(msg) == DEEP_PROFILE

    # Demo scenario queries (complex clinical reasoning)
    @pytest.mark.parametrize("msg", [
        "What's driving the diuretic escalation? Pull her recent trends.",
        "Quantify the TdP risk — I need to know if this is a phone call today or an ER send.",
        "I'm thinking GDMT — walk me through initiation given her current regimen and the contraindication landscape.",
        "Why are you flagging a lower A1c? Walk me through the risk.",
    ])
    def test_demo_scenario_queries(self, msg: str):
        assert classify_query(msg) == DEEP_PROFILE

    # No chart entity
    @pytest.mark.parametrize("msg", [
        "Hello",
        "What do you think?",
    ])
    def test_no_chart_entity(self, msg: str):
        assert classify_query(msg) == DEEP_PROFILE

    def test_has_history_does_not_upgrade_deep(self):
        """DEEP queries stay DEEP even with has_history=True."""
        assert classify_query("Explain the lab results", has_history=True) == DEEP_PROFILE
        assert classify_query("Why was lisinopril prescribed?", has_history=True) == DEEP_PROFILE


# =============================================================================
# Edge Cases
# =============================================================================


class TestClassifyQueryEdgeCases:
    """Edge cases and boundary conditions."""

    def test_empty_string(self):
        assert classify_query("") == DEEP_PROFILE

    def test_whitespace_only(self):
        assert classify_query("   ") == DEEP_PROFILE

    def test_over_200_chars(self):
        msg = "What medications " + "x" * 200
        assert classify_query(msg) == DEEP_PROFILE

    def test_case_insensitivity(self):
        assert classify_query("WHAT MEDICATIONS?") == LIGHTNING_PROFILE
        assert classify_query("What Medications?") == LIGHTNING_PROFILE

    def test_reasoning_keyword_overrides_entity(self):
        assert classify_query("Why is the patient on these medications?") == DEEP_PROFILE
        assert classify_query("Explain the lab results") == DEEP_PROFILE

    def test_analytical_phrase_overrides_entity(self):
        assert classify_query("Show me encounters and see if he's getting worse") == DEEP_PROFILE

    def test_contraindication_stem(self):
        assert classify_query("Any contraindications for this drug?") == DEEP_PROFILE

    def test_no_chart_entity_various(self):
        assert classify_query("Tell me about this patient") == DEEP_PROFILE
        assert classify_query("Hello") == DEEP_PROFILE
        assert classify_query("What do you think?") == DEEP_PROFILE

    def test_how_many_is_lightning(self):
        assert classify_query("How many medications?") == LIGHTNING_PROFILE

    def test_how_should_is_deep(self):
        assert classify_query("How should we manage the diabetes?") == DEEP_PROFILE

    def test_follow_up_shorthand_and_the(self):
        # "And the allergies?" -> no lookup prefix, follow-up excluded -> DEEP
        assert classify_query("And the allergies?") == DEEP_PROFILE

    def test_what_about_is_lightning(self):
        # "What about the labs?" -> "what" prefix + entity -> LIGHTNING
        assert classify_query("What about the labs?") == LIGHTNING_PROFILE

    def test_clinical_shorthand_bp(self):
        assert classify_query("bp") == LIGHTNING_PROFILE
        assert classify_query("bp?") == LIGHTNING_PROFILE

    def test_clinical_shorthand_hr(self):
        assert classify_query("hr") == LIGHTNING_PROFILE

    def test_whether_analytical_phrase(self):
        assert classify_query("Show labs and whether the A1c improved") == DEEP_PROFILE

    def test_has_history_keyword_only(self):
        """has_history=True with keyword-only arg syntax."""
        assert classify_query("medications", has_history=True) == QUICK_PROFILE
        assert classify_query("medications", has_history=False) == LIGHTNING_PROFILE


# =============================================================================
# Profile Values Tests
# =============================================================================


class TestQueryProfileValues:
    """Test that profile constants have correct field values."""

    def test_lightning_profile_values(self):
        assert LIGHTNING_PROFILE.tier == QueryTier.LIGHTNING
        assert LIGHTNING_PROFILE.model == "gpt-4o-mini"
        assert LIGHTNING_PROFILE.reasoning is False
        assert LIGHTNING_PROFILE.reasoning_effort == "low"
        assert LIGHTNING_PROFILE.include_tools is False
        assert LIGHTNING_PROFILE.max_output_tokens == 2048
        assert LIGHTNING_PROFILE.system_prompt_mode == "lightning"
        assert LIGHTNING_PROFILE.response_schema == "lightning"

    def test_quick_profile_values(self):
        assert QUICK_PROFILE.tier == QueryTier.QUICK
        assert QUICK_PROFILE.model == "gpt-5-mini"
        assert QUICK_PROFILE.reasoning is True
        assert QUICK_PROFILE.reasoning_effort == "low"
        assert QUICK_PROFILE.include_tools is True
        assert QUICK_PROFILE.max_output_tokens == 4096
        assert QUICK_PROFILE.system_prompt_mode == "fast"
        assert QUICK_PROFILE.response_schema == "full"

    def test_deep_profile_values(self):
        assert DEEP_PROFILE.tier == QueryTier.DEEP
        assert DEEP_PROFILE.model == "gpt-5-mini"
        assert DEEP_PROFILE.reasoning is True
        assert DEEP_PROFILE.reasoning_effort == "medium"
        assert DEEP_PROFILE.include_tools is True
        assert DEEP_PROFILE.max_output_tokens == 16384
        assert DEEP_PROFILE.system_prompt_mode == "standard"
        assert DEEP_PROFILE.response_schema == "full"

    def test_profiles_are_frozen(self):
        with pytest.raises(AttributeError):
            LIGHTNING_PROFILE.tier = QueryTier.DEEP  # type: ignore[misc]
        with pytest.raises(AttributeError):
            DEEP_PROFILE.tier = QueryTier.LIGHTNING  # type: ignore[misc]


# =============================================================================
# Backward Compatibility Tests
# =============================================================================


class TestBackwardCompatibility:
    """Verify backward-compatible aliases still work."""

    def test_fast_profile_is_lightning(self):
        from app.services.query_classifier import FAST_PROFILE
        assert FAST_PROFILE is LIGHTNING_PROFILE

    def test_standard_profile_is_deep(self):
        from app.services.query_classifier import STANDARD_PROFILE
        assert STANDARD_PROFILE is DEEP_PROFILE
