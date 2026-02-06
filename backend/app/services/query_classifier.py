"""Adaptive query classifier for fast chart lookups vs standard clinical reasoning.

Classifies user messages into FAST (chart lookup) or STANDARD (clinical reasoning)
tiers using a pure heuristic approach — no LLM call, zero I/O.

FAST queries (meds, allergies, labs, conditions, vitals) are answerable directly
from the pre-compiled patient summary with lower reasoning effort and no tools.

STANDARD queries (interactions, trends, interpretations) require full clinical
reasoning with tools and higher token limits.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Literal


class QueryTier(str, Enum):
    FAST = "fast"         # Chart lookup answerable from compiled summary
    STANDARD = "standard" # Clinical reasoning, tool use, complex analysis


@dataclass(frozen=True, slots=True)
class QueryProfile:
    tier: QueryTier
    reasoning_effort: Literal["low", "medium", "high"]
    include_tools: bool
    max_output_tokens: int
    system_prompt_mode: Literal["fast", "standard"]


FAST_PROFILE = QueryProfile(
    tier=QueryTier.FAST,
    reasoning_effort="low",
    include_tools=False,
    max_output_tokens=4096,
    system_prompt_mode="fast",
)

STANDARD_PROFILE = QueryProfile(
    tier=QueryTier.STANDARD,
    reasoning_effort="medium",
    include_tools=True,
    max_output_tokens=16384,
    system_prompt_mode="standard",
)


# ── Keyword / phrase sets ────────────────────────────────────────────────────

_REASONING_KEYWORDS = frozenset({
    "why", "should", "compare", "explain", "interpret",
    "analyze", "assess", "evaluate", "recommend", "suggest",
    "appropriate", "contraindic", "interact",
    "risk", "signific",
    "trend", "worsen", "improv",
    "differential", "prognosis", "cause", "correlat",
    "between", "versus", "relationship",
})

_ANALYTICAL_PHRASES = (
    "see if", "check if", "determine if", "figure out",
    "find out", "whether",
)

_CHART_ENTITIES = frozenset({
    # Medications
    "medication", "medications", "meds", "medicine", "medicines",
    "drug", "drugs", "prescription", "prescriptions",
    # Allergies
    "allergy", "allergies", "allergic",
    # Conditions
    "condition", "conditions", "diagnosis", "diagnoses", "problem", "problems",
    # Labs
    "lab", "labs", "laboratory", "test", "tests", "result", "results",
    "observation", "observations",
    # Vitals
    "vital", "vitals", "bp", "hr",
    # Immunizations
    "immunization", "immunizations", "vaccine", "vaccines", "vaccination", "vaccinations",
    # Encounters
    "visit", "visits", "encounter", "encounters", "appointment", "appointments",
    # Procedures
    "procedure", "procedures", "surgery", "surgeries",
    # Care plans
    "careplan",
})

# Multi-word entities checked as substrings
_BIGRAM_ENTITIES = frozenset({
    "blood pressure", "heart rate", "blood work", "care plan", "care plans",
    "vital signs", "lab results", "test results",
})

_LOOKUP_PREFIXES = (
    "what", "which", "when", "list", "show", "tell me", "give me",
    "any", "does", "is there", "are there", "how many",
    "current", "active", "latest", "recent", "last",
)

_SPECIFIC_ITEM_STARTERS = (
    "what's the ", "what is the ", "what are the ",
    "what's their ", "what is their ", "what's his ", "what's her ",
    "when was the last ", "when was the ",
    "is the patient on ", "is the patient taking ",
    "is the patient allergic to ",
    "is this patient on ", "is this patient taking ",
    "does the patient have ", "does this patient have ",
    "is there a ", "is there an ", "are there any ",
)

# Conversation reference patterns
_CONVERSATION_REFS = (
    "you mentioned", "you said", "earlier", "above",
    "as you said", "like you said",
)

# Search/tool request patterns
_SEARCH_PATTERNS = (
    "search for", "search ", "look up", "look for", "find ",
)

# Word boundary pattern for matching chart entities
_WORD_BOUNDARY = re.compile(r"\b\w+\b")


def _has_chart_entity(msg: str, words: set[str]) -> bool:
    """Check if message contains a chart entity (word-boundary or bigram)."""
    if words & _CHART_ENTITIES:
        return True
    for bigram in _BIGRAM_ENTITIES:
        if bigram in msg:
            return True
    return False


def _has_reasoning_keyword(msg: str) -> bool:
    """Check if message contains a reasoning keyword (substring match for stems)."""
    for kw in _REASONING_KEYWORDS:
        if kw in msg:
            return True
    return False


def _has_analytical_phrase(msg: str) -> bool:
    """Check if message contains an analytical phrase."""
    for phrase in _ANALYTICAL_PHRASES:
        if phrase in msg:
            return True
    return False


def _has_lookup_prefix(msg: str) -> bool:
    """Check if message starts with a lookup prefix."""
    for prefix in _LOOKUP_PREFIXES:
        if msg.startswith(prefix):
            return True
    return False


def _has_conversation_ref(msg: str) -> bool:
    """Check if message references previous conversation."""
    for ref in _CONVERSATION_REFS:
        if ref in msg:
            return True
    return False


def _has_search_pattern(msg: str) -> bool:
    """Check if message requests a search/tool action."""
    for pattern in _SEARCH_PATTERNS:
        if pattern in msg:
            return True
    return False


def classify_query(message: str) -> QueryProfile:
    """Classify a user message into FAST or STANDARD query profile.

    Pure function, zero I/O. Three independent paths to FAST;
    default is always STANDARD.

    Args:
        message: The user's chat message.

    Returns:
        QueryProfile (FAST_PROFILE or STANDARD_PROFILE).
    """
    # 1. Normalize
    msg = message.strip().lower()

    # 2. STANDARD if empty, >200 chars, conversation refs, search requests
    if not msg:
        return STANDARD_PROFILE
    if len(msg) > 200:
        return STANDARD_PROFILE
    if _has_conversation_ref(msg):
        return STANDARD_PROFILE
    if _has_search_pattern(msg):
        return STANDARD_PROFILE

    # 3. STANDARD if reasoning keyword present
    if _has_reasoning_keyword(msg):
        return STANDARD_PROFILE

    # 3b. STANDARD if analytical phrase present
    if _has_analytical_phrase(msg):
        return STANDARD_PROFILE

    # Extract words for entity matching
    words = set(_WORD_BOUNDARY.findall(msg))

    # 4A. Chart entity + lookup prefix → FAST
    if _has_chart_entity(msg, words) and _has_lookup_prefix(msg):
        return FAST_PROFILE

    # 4B. Bare entity shortcut (≤30 chars after stripping punctuation)
    # Excludes follow-up shorthand ("and the ...", "also ...", "how about ...")
    bare = re.sub(r"[^\w\s]", "", msg).strip()
    _follow_up_starts = ("and ", "also ", "how about ", "plus ")
    if len(bare) <= 30 and _has_chart_entity(msg, words) and not any(
        bare.startswith(s) for s in _follow_up_starts
    ):
        return FAST_PROFILE

    # 4C. Specific-item patterns (≤100 chars)
    if len(msg) <= 100:
        for starter in _SPECIFIC_ITEM_STARTERS:
            if msg.startswith(starter):
                return FAST_PROFILE

    # 5. Default → STANDARD
    return STANDARD_PROFILE
