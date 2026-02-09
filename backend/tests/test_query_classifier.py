"""Tests for the two-layer adaptive query classifier.

Tests the hybrid classifier that routes queries to LIGHTNING (pure fact
extraction), QUICK (focused retrieval), or DEEP (full clinical reasoning)
profiles using deterministic heuristics (Layer 1) and an LLM fallback (Layer 2).

Layer 1 tests call _classify_layer1() directly (sync, no mocking needed).
Layer 2 tests call classify_query() with Layer 2 mocked.
Integration tests call classify_query() with the full two-layer flow.
"""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.services.query_classifier import (
    DEEP_PROFILE,
    LIGHTNING_PROFILE,
    QUICK_LOOKUP_PROFILE,
    QUICK_PROFILE,
    QueryProfile,
    QueryTier,
    _classify_layer1,
    classify_query,
)


# =============================================================================
# Layer 1: Category Lookups → QUICK (for structured table rendering)
# =============================================================================


class TestLayer1CategoryLookups:
    """Layer 1 deterministic classification → QUICK_LOOKUP for category data lookups."""

    # Path A: entity + lookup prefix → QUICK_LOOKUP (tables, no reasoning/tools)
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
        "Active meds and conditions",
        "What are the latest labs?",
        "Show me the vitals",
        "What's the blood pressure?",
        "Are there any allergies?",
    ])
    def test_path_a_entity_plus_prefix(self, msg: str):
        assert _classify_layer1(msg) == QUICK_LOOKUP_PROFILE

    # Path B: bare entity shortcut (<=30 chars) → QUICK_LOOKUP (tables, no reasoning/tools)
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
        assert _classify_layer1(msg) == QUICK_LOOKUP_PROFILE


# =============================================================================
# Layer 1: LIGHTNING Path Tests (specific-item lookups, no tables needed)
# =============================================================================


class TestLayer1LightningPath:
    """Layer 1 deterministic classification → LIGHTNING."""

    # Path C: specific-item patterns (<=100 chars) → LIGHTNING (single-value answer)
    # Note: queries with chart entities (e.g., "blood pressure", "allergies") hit
    # Path A first → QUICK. Only queries without chart entities land here.
    @pytest.mark.parametrize("msg", [
        "What's the HbA1c?",
        "What is the latest A1c?",
        "What's the A1c?",
        "When was the last HbA1c?",
        "Is the patient on metformin?",
        "Does the patient have diabetes?",
        "Is the patient taking lisinopril?",
        "Is the patient allergic to penicillin?",
        "What is the patient's BMI?",
    ])
    def test_path_c_specific_item(self, msg: str):
        assert _classify_layer1(msg) == LIGHTNING_PROFILE


# =============================================================================
# Layer 1: QUICK Path Tests
# =============================================================================


class TestLayer1QuickPath:
    """Layer 1 deterministic classification → QUICK."""

    # Temporal modifiers with chart entity
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
        "BP readings this year",
    ])
    def test_temporal_modifier_with_entity(self, msg: str):
        assert _classify_layer1(msg) == QUICK_PROFILE

    # Trending / tracking (retrieval verbs + chart entity)
    @pytest.mark.parametrize("msg", [
        "Trend the A1c results",
        "Track the blood pressure over time",
        "Filter medications by active status",
        "Sort labs by date",
    ])
    def test_retrieval_verb_with_entity(self, msg: str):
        assert _classify_layer1(msg) == QUICK_PROFILE

    # Focused retrieval patterns
    @pytest.mark.parametrize("msg", [
        "Find the latest labs",
        "Find the most recent A1c",
        "Look up the HbA1c history",
        "Pull up the recent vitals",
        "Get the last blood pressure",
        "Find latest labs",
        "Find recent observations",
        "Get the most recent A1c",
    ])
    def test_focused_retrieval_patterns(self, msg: str):
        assert _classify_layer1(msg) == QUICK_PROFILE

    # History of specific item (temporal modifier)
    @pytest.mark.parametrize("msg", [
        "Labs from last month",
    ])
    def test_history_queries(self, msg: str):
        assert _classify_layer1(msg) == QUICK_PROFILE

    def test_temporal_plus_history_still_quick(self):
        """Both temporal modifier and history present — still QUICK."""
        assert _classify_layer1(
            "What were the labs from January?",
        ) == QUICK_PROFILE


# =============================================================================
# Layer 1: DEEP Path Tests
# =============================================================================


class TestLayer1DeepPath:
    """Layer 1 deterministic classification → DEEP."""

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
        assert _classify_layer1(msg) == DEEP_PROFILE

    # New reasoning keywords: quantify, driving
    @pytest.mark.parametrize("msg", [
        "What's driving the diuretic escalation? Pull her recent trends.",
        "Quantify the TdP risk — I need to know if this is a phone call today or an ER send.",
    ])
    def test_new_reasoning_keywords(self, msg: str):
        assert _classify_layer1(msg) == DEEP_PROFILE

    # Deep search patterns
    def test_deep_search_pattern(self):
        assert _classify_layer1("Search for all diabetes-related observations") == DEEP_PROFILE

    # Conversation references
    @pytest.mark.parametrize("msg", [
        "You mentioned the medications earlier, tell me more",
        "As you said about the labs",
    ])
    def test_conversation_references(self, msg: str):
        assert _classify_layer1(msg) == DEEP_PROFILE

    # Reasoning shorts (<=4 words + reasoning short word)
    @pytest.mark.parametrize("msg", [
        "Summarize the patient record",
        "Patient overview",
        "Give me a summary",
        "Assessment",
    ])
    def test_reasoning_shorts(self, msg: str):
        assert _classify_layer1(msg) == DEEP_PROFILE

    # Analytical phrases (entity present but analytical intent)
    @pytest.mark.parametrize("msg", [
        "Show me his glucose logs and any recent encounters — let's see if he's actually been having hypo episodes.",
        "Show me the labs and check if there's a pattern",
        "Pull up the encounters and determine if he was seen recently",
        "List medications and figure out which one is causing the issue",
        "Check if there's a pattern in the labs",
        "See if the medication is working",
    ])
    def test_analytical_phrases(self, msg: str):
        assert _classify_layer1(msg) == DEEP_PROFILE

    # Demo scenario queries (complex clinical reasoning)
    @pytest.mark.parametrize("msg", [
        "I'm thinking GDMT — walk me through initiation given her current regimen and the contraindication landscape.",
        "Why are you flagging a lower A1c? Walk me through the risk.",
    ])
    def test_demo_scenario_queries(self, msg: str):
        assert _classify_layer1(msg) == DEEP_PROFILE

    # Non-clinical shorts
    @pytest.mark.parametrize("msg", [
        "Hello",
        "hi",
        "hey",
        "ok",
    ])
    def test_non_clinical_shorts(self, msg: str):
        assert _classify_layer1(msg) == DEEP_PROFILE

    # General / multi-word non-clinical
    @pytest.mark.parametrize("msg", [
        "What do you think?",
        "Tell me about this patient",
    ])
    def test_general_queries(self, msg: str):
        """Queries without chart entities or signals → DEEP or ambiguous."""
        result = _classify_layer1(msg)
        # "What do you think?" — "what" is in _NON_CLINICAL_SHORTS, 4 words → DEEP
        # "Tell me about this patient" — 5 words, no entity → None (ambiguous)
        assert result in (DEEP_PROFILE, None)


# =============================================================================
# Layer 1: Ambiguous (returns None → Layer 2)
# =============================================================================


class TestLayer1Ambiguous:
    """Layer 1 returns None for ambiguous queries that need Layer 2."""

    @pytest.mark.parametrize("msg", [
        "hemoglobin",
        "potassium",
        "ejection fraction",
        "ferritin level",
        "thyroid panel",
        "creatinine",
        "weight",
        "a1c",
        "BMI?",
        # Retrieval verb present but no chart entity (weight, glucose not in set)
        "Graph the weight history",
        "Plot the glucose readings",
    ])
    def test_ambiguous_clinical_terms_pass_to_layer2(self, msg: str):
        """Specific clinical terms not in _CHART_ENTITIES → Layer 2."""
        assert _classify_layer1(msg) is None


# =============================================================================
# Layer 1: has_history is ignored
# =============================================================================


class TestLayer1HasHistoryIgnored:
    """has_history parameter no longer affects classification."""

    @pytest.mark.parametrize("msg,expected", [
        # Category lookups → QUICK_LOOKUP (tables, no reasoning)
        ("What medications is the patient on?", QUICK_LOOKUP_PROFILE),
        ("medications", QUICK_LOOKUP_PROFILE),
        ("labs?", QUICK_LOOKUP_PROFILE),
        ("bp", QUICK_LOOKUP_PROFILE),
        ("List all conditions", QUICK_LOOKUP_PROFILE),
        ("allergies", QUICK_LOOKUP_PROFILE),
        # Specific-item lookups → LIGHTNING
        ("What's the HbA1c?", LIGHTNING_PROFILE),
        ("Is the patient on metformin?", LIGHTNING_PROFILE),
    ])
    @pytest.mark.asyncio
    async def test_has_history_no_longer_upgrades(self, msg: str, expected: QueryProfile):
        """Classification is stable regardless of has_history."""
        assert _classify_layer1(msg) == expected
        assert await classify_query(msg, has_history=True) == expected
        assert await classify_query(msg, has_history=False) == expected


# =============================================================================
# Layer 1: Edge Cases
# =============================================================================


class TestLayer1EdgeCases:
    """Edge cases and boundary conditions for Layer 1."""

    def test_empty_string(self):
        assert _classify_layer1("") == DEEP_PROFILE

    def test_whitespace_only(self):
        assert _classify_layer1("   ") == DEEP_PROFILE

    def test_over_200_chars(self):
        msg = "What medications " + "x" * 200
        assert _classify_layer1(msg) == DEEP_PROFILE

    def test_case_insensitivity(self):
        assert _classify_layer1("WHAT MEDICATIONS?") == QUICK_LOOKUP_PROFILE
        assert _classify_layer1("What Medications?") == QUICK_LOOKUP_PROFILE

    def test_reasoning_keyword_overrides_entity(self):
        assert _classify_layer1("Why is the patient on these medications?") == DEEP_PROFILE
        assert _classify_layer1("Explain the lab results") == DEEP_PROFILE

    def test_analytical_phrase_overrides_entity(self):
        assert _classify_layer1("Show me encounters and see if he's getting worse") == DEEP_PROFILE

    def test_contraindication_stem(self):
        assert _classify_layer1("Any contraindications for this drug?") == DEEP_PROFILE

    def test_how_many_is_quick_lookup(self):
        assert _classify_layer1("How many medications?") == QUICK_LOOKUP_PROFILE

    def test_how_should_is_deep(self):
        assert _classify_layer1("How should we manage the diabetes?") == DEEP_PROFILE

    def test_follow_up_shorthand_and_the(self):
        # "And the allergies?" -> no lookup prefix, follow-up excluded
        result = _classify_layer1("And the allergies?")
        # Short query (3 words), has entity but excluded by follow-up start
        # Falls through to ambiguous
        assert result is None or result == DEEP_PROFILE

    def test_what_about_is_quick_lookup(self):
        # "What about the labs?" -> "what" prefix + entity -> QUICK_LOOKUP (tables)
        assert _classify_layer1("What about the labs?") == QUICK_LOOKUP_PROFILE

    def test_clinical_shorthand_bp(self):
        assert _classify_layer1("bp") == QUICK_LOOKUP_PROFILE
        assert _classify_layer1("bp?") == QUICK_LOOKUP_PROFILE

    def test_clinical_shorthand_hr(self):
        assert _classify_layer1("hr") == QUICK_LOOKUP_PROFILE

    def test_whether_analytical_phrase(self):
        assert _classify_layer1("Show labs and whether the A1c improved") == DEEP_PROFILE

    def test_trend_is_quick_not_deep(self):
        """'trend' was moved from _REASONING_KEYWORDS to _RETRIEVAL_VERBS."""
        assert _classify_layer1("Trend the A1c results") == QUICK_PROFILE

    def test_between_removed_from_reasoning(self):
        """'between' was removed from _REASONING_KEYWORDS."""
        # "labs between January and March" has temporal modifier + entity → QUICK
        result = _classify_layer1("labs between January and March")
        # "january" is a temporal modifier, "labs" is a chart entity → QUICK
        assert result == QUICK_PROFILE

    def test_focused_retrieval_not_deep(self):
        """'Look up the HbA1c history' is now QUICK (focused retrieval), not DEEP."""
        assert _classify_layer1("Look up the HbA1c history") == QUICK_PROFILE

    def test_find_latest_is_quick(self):
        """'find latest labs' is now QUICK (focused retrieval), not DEEP."""
        assert _classify_layer1("Find the latest labs") == QUICK_PROFILE


# =============================================================================
# Layer 2: LLM Fallback Tests
# =============================================================================


class TestLayer2LLMFallback:
    """Tests for the LLM-based Layer 2 classification."""

    @pytest.mark.asyncio
    async def test_layer2_classifies_lightning(self):
        """Layer 2 returns LIGHTNING for a fact-lookup query."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"tier": "lightning"})

        with patch(
            "app.services.query_classifier._get_layer2_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await classify_query("hemoglobin")
            assert result == LIGHTNING_PROFILE

    @pytest.mark.asyncio
    async def test_layer2_classifies_quick(self):
        """Layer 2 returns QUICK for a retrieval query."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"tier": "quick"})

        with patch(
            "app.services.query_classifier._get_layer2_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await classify_query("ferritin level")
            assert result == QUICK_PROFILE

    @pytest.mark.asyncio
    async def test_layer2_classifies_deep(self):
        """Layer 2 returns DEEP for a reasoning query."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = json.dumps({"tier": "deep"})

        with patch(
            "app.services.query_classifier._get_layer2_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await classify_query("ejection fraction")
            assert result == DEEP_PROFILE

    @pytest.mark.asyncio
    async def test_layer2_timeout_falls_back_to_deep(self):
        """Layer 2 timeout → DEEP fallback."""
        import asyncio

        with patch(
            "app.services.query_classifier._get_layer2_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=asyncio.TimeoutError()
            )
            mock_get_client.return_value = mock_client

            result = await classify_query("potassium")
            assert result == DEEP_PROFILE

    @pytest.mark.asyncio
    async def test_layer2_error_falls_back_to_deep(self):
        """Layer 2 API error → DEEP fallback."""
        with patch(
            "app.services.query_classifier._get_layer2_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(
                side_effect=RuntimeError("API error")
            )
            mock_get_client.return_value = mock_client

            result = await classify_query("thyroid panel")
            assert result == DEEP_PROFILE

    @pytest.mark.asyncio
    async def test_layer2_invalid_json_falls_back_to_deep(self):
        """Layer 2 returns invalid JSON → DEEP fallback."""
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "not json"

        with patch(
            "app.services.query_classifier._get_layer2_client"
        ) as mock_get_client:
            mock_client = AsyncMock()
            mock_client.chat.completions.create = AsyncMock(return_value=mock_response)
            mock_get_client.return_value = mock_client

            result = await classify_query("potassium")
            assert result == DEEP_PROFILE

    @pytest.mark.asyncio
    async def test_layer1_resolved_does_not_invoke_layer2(self):
        """When Layer 1 resolves, Layer 2 is never called."""
        with patch(
            "app.services.query_classifier._classify_layer2"
        ) as mock_layer2:
            result = await classify_query("medications")
            assert result == QUICK_LOOKUP_PROFILE
            mock_layer2.assert_not_called()

    @pytest.mark.asyncio
    async def test_layer2_invoked_for_ambiguous(self):
        """When Layer 1 returns None, Layer 2 is called."""
        with patch(
            "app.services.query_classifier._classify_layer2",
            new_callable=AsyncMock,
            return_value=LIGHTNING_PROFILE,
        ) as mock_layer2:
            result = await classify_query("hemoglobin")
            assert result == LIGHTNING_PROFILE
            mock_layer2.assert_called_once_with("hemoglobin")


# =============================================================================
# Full Integration: classify_query() async tests
# =============================================================================


class TestClassifyQueryAsync:
    """Integration tests calling the full async classify_query()."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize("msg,expected", [
        # Category lookups → Quick Lookup (structured tables, no reasoning)
        ("medications", QUICK_LOOKUP_PROFILE),
        ("bp", QUICK_LOOKUP_PROFILE),
        ("What medications is the patient on?", QUICK_LOOKUP_PROFILE),
        # Specific-item lookups → Lightning (narrative only)
        ("What's the A1c?", LIGHTNING_PROFILE),
        ("Is the patient allergic to penicillin?", LIGHTNING_PROFILE),
        # Quick — Layer 1 resolves
        ("Trend the A1c results", QUICK_PROFILE),
        ("Labs from last month", QUICK_PROFILE),
        ("Find the latest labs", QUICK_PROFILE),
        ("Look up the HbA1c history", QUICK_PROFILE),
        # Deep — Layer 1 resolves
        ("Why was lisinopril prescribed?", DEEP_PROFILE),
        ("Assess cardiovascular risk", DEEP_PROFILE),
        ("Hello", DEEP_PROFILE),
        ("Search for all diabetes-related observations", DEEP_PROFILE),
        ("Summarize the patient record", DEEP_PROFILE),
    ])
    async def test_layer1_resolved_queries(self, msg: str, expected: QueryProfile):
        """Queries that Layer 1 resolves deterministically."""
        result = await classify_query(msg)
        assert result == expected

    @pytest.mark.asyncio
    async def test_has_history_does_not_upgrade_deep(self):
        """DEEP queries stay DEEP even with has_history=True."""
        assert await classify_query("Explain the lab results", has_history=True) == DEEP_PROFILE
        assert await classify_query("Why was lisinopril prescribed?", has_history=True) == DEEP_PROFILE


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
        assert QUICK_PROFILE.model is None  # defers to user-selected model
        assert QUICK_PROFILE.reasoning is True
        assert QUICK_PROFILE.reasoning_effort == "low"
        assert QUICK_PROFILE.include_tools is True
        assert QUICK_PROFILE.max_output_tokens == 4096
        assert QUICK_PROFILE.system_prompt_mode == "quick"
        assert QUICK_PROFILE.response_schema == "full"

    def test_quick_lookup_profile_values(self):
        assert QUICK_LOOKUP_PROFILE.tier == QueryTier.QUICK
        assert QUICK_LOOKUP_PROFILE.model is None
        assert QUICK_LOOKUP_PROFILE.reasoning is False
        assert QUICK_LOOKUP_PROFILE.include_tools is False
        assert QUICK_LOOKUP_PROFILE.max_output_tokens == 4096
        assert QUICK_LOOKUP_PROFILE.system_prompt_mode == "quick"
        assert QUICK_LOOKUP_PROFILE.response_schema == "full"

    def test_deep_profile_values(self):
        assert DEEP_PROFILE.tier == QueryTier.DEEP
        assert DEEP_PROFILE.model is None  # defers to user-selected model
        assert DEEP_PROFILE.reasoning is True
        assert DEEP_PROFILE.reasoning_effort == "medium"
        assert DEEP_PROFILE.include_tools is True
        assert DEEP_PROFILE.max_output_tokens == 16384
        assert DEEP_PROFILE.system_prompt_mode == "deep"
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
