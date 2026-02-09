"""Two-layer adaptive query classifier for three-tier query routing.

Layer 1 (deterministic, sync): Pattern-matching heuristics classify clear-cut
queries with zero I/O. Ambiguous queries return None and fall through to Layer 2.

Layer 2 (LLM, async): A fast gpt-4o-mini call with structured output classifies
queries that the heuristics can't confidently bucket. Timeout of 2 s with a
DEEP fallback ensures latency stays bounded.

Tiers:
  LIGHTNING — Pure fact extraction from pre-compiled patient summary.
  QUICK     — Focused data retrieval (date filters, trending, history search).
  DEEP      — Full clinical reasoning, interpretation, recommendations.
"""

from __future__ import annotations

import asyncio
import json
import logging
import re
from dataclasses import dataclass
from enum import Enum
from typing import Literal

from openai import AsyncOpenAI

from app.config import settings

logger = logging.getLogger(__name__)


class QueryTier(str, Enum):
    LIGHTNING = "lightning"  # Pure fact extraction, no reasoning
    QUICK = "quick"          # Light reasoning, optional tools
    DEEP = "deep"            # Full clinical reasoning


@dataclass(frozen=True, slots=True)
class QueryProfile:
    tier: QueryTier
    model: str | None
    reasoning: bool
    reasoning_effort: Literal["low", "medium", "high"]
    include_tools: bool
    max_output_tokens: int
    system_prompt_mode: Literal["lightning", "quick", "deep"]
    response_schema: str


LIGHTNING_PROFILE = QueryProfile(
    tier=QueryTier.LIGHTNING,
    model="gpt-4o-mini",
    reasoning=False,
    reasoning_effort="low",
    include_tools=False,
    max_output_tokens=2048,
    system_prompt_mode="lightning",
    response_schema="lightning",
)

QUICK_PROFILE = QueryProfile(
    tier=QueryTier.QUICK,
    model=None,
    reasoning=True,
    reasoning_effort="low",
    include_tools=True,
    max_output_tokens=4096,
    system_prompt_mode="quick",
    response_schema="full",
)

DEEP_PROFILE = QueryProfile(
    tier=QueryTier.DEEP,
    model=None,
    reasoning=True,
    reasoning_effort="medium",
    include_tools=True,
    max_output_tokens=16384,
    system_prompt_mode="deep",
    response_schema="full",
)

# Backward-compatible aliases for downstream consumers not yet updated
FAST_PROFILE = LIGHTNING_PROFILE
STANDARD_PROFILE = DEEP_PROFILE


# ── Keyword / phrase sets ────────────────────────────────────────────────────

_REASONING_KEYWORDS = frozenset({
    "why", "should", "compare", "explain", "interpret",
    "analyze", "assess", "evaluate", "recommend", "suggest",
    "appropriate", "contraindic", "interact",
    "risk", "signific",
    "worsen", "improv",
    "differential", "prognosis", "cause", "correlat",
    "versus", "relationship",
    "quantify", "driving",
})

_REASONING_SHORTS = frozenset({
    "summary", "summarize", "overview", "assessment",
    "plan", "impression", "brief",
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

_DEEP_SEARCH_PATTERNS = (
    "search for",
)

_FOCUSED_RETRIEVAL_PATTERNS = (
    "find latest", "find recent", "find the latest", "find the most recent",
    "look up the", "look up his", "look up her", "look up their",
    "pull up the", "pull up his", "pull up her",
    "get the latest", "get the most recent", "get the last",
)

_RETRIEVAL_VERBS = frozenset({
    "trend", "track", "graph", "chart", "plot",
    "filter", "sort", "rank",
})

_NON_CLINICAL_SHORTS = frozenset({
    "hello", "hi", "hey", "thanks", "thank",
    "help", "what", "how", "ok", "okay", "yes", "no",
})

# Temporal modifiers that upgrade LIGHTNING → QUICK
_TEMPORAL_MODIFIERS = (
    "from ", "since ", "after ", "before ", "during ",
    "in the last ", "in the past ", "over the last ",
    "last month", "last year", "last week",
    "this month", "this year", "this week",
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
    "2024", "2025", "2026",
)

# Word boundary pattern for matching chart entities
_WORD_BOUNDARY = re.compile(r"\b\w+\b")


# ── Helper predicates ────────────────────────────────────────────────────────

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


def _has_deep_search_pattern(msg: str) -> bool:
    """Check if message contains a deep-search pattern (broad search requests)."""
    for pattern in _DEEP_SEARCH_PATTERNS:
        if pattern in msg:
            return True
    return False


def _has_focused_retrieval_pattern(msg: str) -> bool:
    """Check if message contains a focused retrieval pattern."""
    for pattern in _FOCUSED_RETRIEVAL_PATTERNS:
        if pattern in msg:
            return True
    return False


def _has_temporal_modifier(msg: str) -> bool:
    """Check if message contains date-filtering language."""
    for modifier in _TEMPORAL_MODIFIERS:
        if modifier in msg:
            return True
    return False


def _has_reasoning_short(msg: str, words: set[str]) -> bool:
    """Check if query is short (<=4 words) and contains a reasoning short word."""
    if len(words) > 4:
        return False
    for word in words:
        if word in _REASONING_SHORTS:
            return True
    return False


def _has_retrieval_verb_with_entity(msg: str, words: set[str]) -> bool:
    """Check if query contains both a retrieval verb AND a chart entity."""
    has_verb = bool(words & _RETRIEVAL_VERBS)
    if not has_verb:
        return False
    return _has_chart_entity(msg, words)


def _has_non_clinical_short(words: set[str]) -> bool:
    """Check if query is <=4 words and ALL words are non-clinical."""
    if len(words) > 4 or len(words) == 0:
        return False
    return words <= _NON_CLINICAL_SHORTS


# ── Layer 1: deterministic classification ────────────────────────────────────

def _classify_layer1(message: str) -> QueryProfile | None:
    """Deterministic classification. Returns None for ambiguous queries."""

    # 1. Normalize
    msg = message.strip().lower()

    # 2. DEEP guard rails — empty, >200 chars, conversation refs
    if not msg:
        return DEEP_PROFILE
    if len(msg) > 200:
        return DEEP_PROFILE
    if _has_conversation_ref(msg):
        return DEEP_PROFILE

    # 3. DEEP deny-list
    # 3a. Deep search patterns first
    if _has_deep_search_pattern(msg):
        return DEEP_PROFILE

    # 3b. Reasoning keywords (substring match)
    if _has_reasoning_keyword(msg):
        return DEEP_PROFILE

    # 3c. Analytical phrases
    if _has_analytical_phrase(msg):
        return DEEP_PROFILE

    # Extract words for entity/short-query matching
    words = set(_WORD_BOUNDARY.findall(msg))

    # 3d. Reasoning shorts (<=4 words + reasoning short word)
    if _has_reasoning_short(msg, words):
        return DEEP_PROFILE

    # 4. Non-clinical shorts — <=4 words, all words are non-clinical → DEEP
    if _has_non_clinical_short(words):
        return DEEP_PROFILE

    # 5. QUICK signals
    # 5a. Focused retrieval patterns
    if _has_focused_retrieval_pattern(msg):
        return QUICK_PROFILE

    # 5b. Temporal modifiers + entity
    if _has_temporal_modifier(msg) and _has_chart_entity(msg, words):
        return QUICK_PROFILE

    # 5c. Retrieval verbs + entity
    if _has_retrieval_verb_with_entity(msg, words):
        return QUICK_PROFILE

    # 6. Category data lookups → QUICK (need structured tables)
    # 6a. Chart entity + lookup prefix → QUICK for table rendering
    if _has_chart_entity(msg, words) and _has_lookup_prefix(msg):
        return QUICK_PROFILE

    # 6b. Bare entity shortcut (<=30 chars after stripping punctuation)
    bare = re.sub(r"[^\w\s]", "", msg).strip()
    _follow_up_starts = ("and ", "also ", "how about ", "plus ")
    if len(bare) <= 30 and _has_chart_entity(msg, words) and not any(
        bare.startswith(s) for s in _follow_up_starts
    ):
        return QUICK_PROFILE

    # 6c. Specific-item patterns (<=100 chars) → LIGHTNING (single-value lookups)
    if len(msg) <= 100:
        for starter in _SPECIFIC_ITEM_STARTERS:
            if msg.startswith(starter):
                return LIGHTNING_PROFILE

    # 7. Short-query default — <=4 words with no reasoning signals → ambiguous
    if len(words) <= 4:
        return None

    # 8. Fallback — ambiguous, pass to Layer 2
    return None


# ── Layer 2: LLM-based classification ────────────────────────────────────────

_LAYER2_PROMPT = """Classify this patient chart query into exactly one tier:

LIGHTNING — The answer is a CATEGORY of data always present in a patient summary
  (e.g., "medications", "allergies", "vitals", "labs", "conditions", "immunizations")
QUICK — Requires looking up a SPECIFIC clinical value, filtering by date, trending
  a value, or searching history. Includes specific lab names, measurements, or
  clinical terms not found as standard summary categories
  (e.g., "hemoglobin", "potassium", "ejection fraction", "ferritin", "thyroid",
   "creatinine", "glucose", "weight", "a1c", "trend bp")
DEEP — Requires clinical reasoning, interpretation, comparison, risk assessment,
  recommendations, or combining information across multiple clinical domains

Query: "{message}"

Return: {{"tier": "lightning" | "quick" | "deep"}}"""

_LAYER2_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "tier_classification",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "tier": {
                    "type": "string",
                    "enum": ["lightning", "quick", "deep"],
                },
            },
            "required": ["tier"],
            "additionalProperties": False,
        },
    },
}

_TIER_TO_PROFILE = {
    "lightning": LIGHTNING_PROFILE,
    "quick": QUICK_PROFILE,
    "deep": DEEP_PROFILE,
}

_layer2_client: AsyncOpenAI | None = None


def _get_layer2_client() -> AsyncOpenAI:
    global _layer2_client
    if _layer2_client is None:
        _layer2_client = AsyncOpenAI(api_key=settings.openai_api_key)
    return _layer2_client


async def _classify_layer2(message: str) -> QueryProfile:
    """LLM-based classification for ambiguous queries."""
    import time

    client = _get_layer2_client()
    start = time.monotonic()

    try:
        response = await asyncio.wait_for(
            client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "user",
                        "content": _LAYER2_PROMPT.format(message=message),
                    },
                ],
                response_format=_LAYER2_SCHEMA,
                temperature=0,
                max_tokens=20,
            ),
            timeout=2.0,
        )
        elapsed_ms = (time.monotonic() - start) * 1000
        raw = response.choices[0].message.content
        result = json.loads(raw)
        tier = result.get("tier", "deep")
        profile = _TIER_TO_PROFILE.get(tier, DEEP_PROFILE)
        logger.info(
            "Layer 2 classified %r → %s (%.0f ms)",
            message[:80],
            profile.tier.value,
            elapsed_ms,
        )
        return profile
    except asyncio.TimeoutError:
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.warning(
            "Layer 2 timed out for %r (%.0f ms), falling back to DEEP",
            message[:80],
            elapsed_ms,
        )
        return DEEP_PROFILE
    except Exception:
        elapsed_ms = (time.monotonic() - start) * 1000
        logger.exception(
            "Layer 2 error for %r (%.0f ms), falling back to DEEP",
            message[:80],
            elapsed_ms,
        )
        return DEEP_PROFILE


# ── Public API ───────────────────────────────────────────────────────────────

async def classify_query(
    message: str,
    *,
    has_history: bool = False,  # kept for API compat, ignored internally
) -> QueryProfile:
    """Classify a user message into LIGHTNING, QUICK, or DEEP query profile.

    Two-layer architecture:
      Layer 1 — Deterministic pattern matching (sync, zero I/O).
      Layer 2 — LLM call via gpt-4o-mini for ambiguous queries (async, ≤2 s).

    Args:
        message: The user's chat message.
        has_history: Retained for API compatibility; ignored internally.

    Returns:
        QueryProfile (LIGHTNING_PROFILE, QUICK_PROFILE, or DEEP_PROFILE).
    """
    result = _classify_layer1(message)
    if result is not None:
        logger.debug(
            "Layer 1 classified %r → %s",
            message[:80],
            result.tier.value,
        )
        return result

    logger.info("Layer 1 ambiguous for %r, invoking Layer 2", message[:80])
    return await _classify_layer2(message)
