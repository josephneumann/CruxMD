---
title: "feat: Trifurcated Query Routing — Lightning / Quick / Deep"
type: feat
date: 2026-02-06
---

# Trifurcated Query Routing: Lightning / Quick / Deep

## Overview

Phase 1 adaptive routing (FAST/STANDARD) reduced simple chart lookups from 72-78s to 24.3s. This Phase 2 plan trifurcates the routing into three tiers to push simple fact queries down to **~3-5s** while preserving full clinical reasoning quality for complex queries.

## Problem Statement

A 24.3s response for "What medications?" is still too slow for a demo-quality experience. The latency breakdown reveals three cost drivers:

| Component | Time | Driver |
|-----------|------|--------|
| TTFT (prefill + reasoning) | 8.2s | Reasoning model overhead — even at `effort=low`, gpt-5-mini performs chain-of-thought |
| Output generation | 16.1s | 972 output tokens @ ~60 tok/s — full AgentResponse schema forces unnecessary fields |
| Input processing | ~2-3s | 7,175 input tokens — system prompt + compiled summary |

The biggest lever is **model routing**: gpt-4o-mini has no reasoning overhead, generates at ~85 tok/s, and can handle simple fact extraction reliably with a simpler output schema.

## Proposed Solution

Three tiers with distinct model, reasoning, schema, and prompt configurations:

```
User message
    │
    ▼
classify_query(message)  ← 0ms heuristic, no LLM call
    │
    ├─ LIGHTNING: gpt-4o-mini, no reasoning, LightningResponse, minimal prompt
    │   → ~3-5s for "What medications?", "allergies", "bp"
    │
    ├─ QUICK: gpt-5-mini, low reasoning, AgentResponse, trimmed prompt, tools available
    │   → ~15-25s for "What were the labs from January?", conversation follow-ups
    │
    └─ DEEP: gpt-5-mini, medium reasoning, AgentResponse, full prompt, full tools
        → ~60-75s for "Walk me through the contraindication landscape"
```

**Client override preserved**: `ChatRequest.reasoning_effort` still trumps the classifier.

## Technical Approach

### 1. QueryProfile Changes (`query_classifier.py`)

Add `model`, `reasoning` (bool), and `response_schema` fields to QueryProfile:

```python
class QueryTier(str, Enum):
    LIGHTNING = "lightning"  # Pure fact extraction, no reasoning
    QUICK = "quick"          # Light reasoning, optional tools
    DEEP = "deep"            # Full clinical reasoning

@dataclass(frozen=True, slots=True)
class QueryProfile:
    tier: QueryTier
    model: str                                          # NEW
    reasoning: bool                                     # NEW — whether to send reasoning kwarg at all
    reasoning_effort: Literal["low", "medium", "high"]
    include_tools: bool
    max_output_tokens: int
    system_prompt_mode: Literal["lightning", "fast", "standard"]  # UPDATED
    response_schema: str                                # NEW — "lightning" or "full"

LIGHTNING_PROFILE = QueryProfile(
    tier=QueryTier.LIGHTNING,
    model="gpt-4o-mini",
    reasoning=False,          # gpt-4o-mini rejects reasoning param
    reasoning_effort="low",   # unused but kept for type consistency
    include_tools=False,
    max_output_tokens=2048,
    system_prompt_mode="lightning",
    response_schema="lightning",
)

QUICK_PROFILE = QueryProfile(
    tier=QueryTier.QUICK,
    model="gpt-5-mini",
    reasoning=True,
    reasoning_effort="low",
    include_tools=True,
    max_output_tokens=4096,
    system_prompt_mode="fast",
    response_schema="full",
)

DEEP_PROFILE = QueryProfile(
    tier=QueryTier.DEEP,
    model="gpt-5-mini",
    reasoning=True,
    reasoning_effort="medium",
    include_tools=True,
    max_output_tokens=16384,
    system_prompt_mode="standard",
    response_schema="full",
)
```

### 2. Classifier Updates (`query_classifier.py`)

Split current FAST paths between LIGHTNING and QUICK. Current STANDARD becomes DEEP.

**LIGHTNING** — pure fact extraction (all data in compiled summary):
- Path A: Chart entity + lookup prefix (e.g., "What medications?", "List conditions")
- Path B: Bare entity shortcut ≤30 chars (e.g., "medications", "labs?", "bp")
- Path C: Specific-item patterns ≤100 chars (e.g., "What's the HbA1c?", "Is the patient on metformin?")
- **Guard**: No conversation history present (if history exists → QUICK)

**QUICK** — light reasoning, might need tools:
- Any query that would be LIGHTNING but has conversation history (follow-up context needed)
- Queries with date-filtering language ("from January", "in the last month", "since last visit")
- Queries with comparison words that don't trigger full reasoning ("same as before", "changed")
- Follow-up shorthand with chart entities ("And the allergies?", "Also show conditions")

**DEEP** — full clinical reasoning (unchanged from current STANDARD):
- Reasoning keywords (why, should, compare, explain, interpret, etc.)
- Analytical phrases (see if, check if, determine if, etc.)
- Conversation references (you mentioned, you said, earlier)
- Search/tool requests (search for, look up, find)
- Summary/overview queries (no chart entity match)
- Messages >200 chars
- Demo scenario queries requiring clinical analysis

#### Conversation history guard

The key new classifier input is `conversation_history`. When a user sends "medications" as a follow-up to a conversation about drug interactions, the model needs conversational context — a non-reasoning model can't handle that well. So:

```python
def classify_query(message: str, has_history: bool = False) -> QueryProfile:
    # ... existing heuristic logic ...
    # At the point where we'd return LIGHTNING_PROFILE:
    if has_history:
        return QUICK_PROFILE
    return LIGHTNING_PROFILE
```

#### Date-filtering detection

New set of temporal modifiers that upgrade LIGHTNING → QUICK:

```python
_TEMPORAL_MODIFIERS = (
    "from ", "since ", "after ", "before ", "during ",
    "in the last ", "in the past ", "over the last ",
    "last month", "last year", "last week",
    "this month", "this year", "this week",
    "january", "february", "march", "april", "may", "june",
    "july", "august", "september", "october", "november", "december",
    "2024", "2025", "2026",
)
```

If any temporal modifier present AND query would otherwise be LIGHTNING → return QUICK.

### 3. LightningResponse Schema (`schemas/agent.py`)

Simpler schema for Lightning tier — only the fields gpt-4o-mini needs to produce:

```python
class LightningResponse(BaseModel):
    """Minimal response for Lightning-tier fact extraction."""

    narrative: str = Field(
        min_length=1,
        description="Direct answer in markdown format",
    )
    follow_ups: list[FollowUp] | None = Field(
        default=None,
        description="2-3 suggested follow-up questions",
    )
```

**Why simpler schema?**
- gpt-4o-mini structured output reliability is ~97-98% for simple schemas, drops with complexity
- Cuts output tokens from ~970 to ~200-400 (no thinking, insights, visualizations, tables, actions)
- At ~85 tok/s, 300 tokens = ~3.5s generation time

### 4. Lightning System Prompt (`agent.py`)

Even more trimmed than current fast prompt:

```python
def build_system_prompt_lightning(compiled_summary: str, patient_profile: str | None = None) -> str:
    role = (
        "You are a clinical chart assistant. Extract and present the requested data "
        "from the patient summary below. Cite specific values and dates. "
        "Never fabricate clinical data. If the data isn't in the summary, say so."
    )
    summary_section = _build_patient_summary_section(compiled_summary, patient_profile)
    safety_section = _build_safety_section(compiled_summary)
    format_section = (
        "## Response Format\n"
        "Respond with a JSON object containing:\n"
        "- narrative: Your answer in concise markdown. Use bullet lists for multiple items.\n"
        "- follow_ups: 2-3 short follow-up questions (under 80 chars each)"
    )
    return "\n\n".join([role, summary_section, safety_section, format_section])
```

**Savings vs fast prompt**: ~300 fewer chars (no insight/viz/table instructions).
**Savings vs standard prompt**: ~3000 fewer chars.

### 5. Agent Changes (`agent.py`)

#### Conditional reasoning parameter

gpt-4o-mini returns a 400 error if `reasoning` kwarg is passed. Must be conditionally omitted:

```python
# In both generate_response() and generate_response_stream():
kwargs: dict[str, Any] = {
    "model": effective_model,
    "input": input_messages,
    "text_format": response_schema_class,
    "max_output_tokens": effective_max_tokens,
}

# Only add reasoning for reasoning-capable models
if use_reasoning:
    kwargs["reasoning"] = Reasoning(effort=effective_effort, summary="concise")

if include_tools:
    kwargs["tools"] = TOOL_SCHEMAS
```

#### Model resolution

```python
effective_model = (query_profile.model if query_profile else None) or self._model
use_reasoning = (query_profile.reasoning if query_profile else True)
response_schema_class = LightningResponse if (query_profile and query_profile.response_schema == "lightning") else AgentResponse
```

#### Response wrapping

For Lightning tier, wrap `LightningResponse` into `AgentResponse` before returning:

```python
if isinstance(parsed_response, LightningResponse):
    agent_response = AgentResponse(
        narrative=parsed_response.narrative,
        follow_ups=parsed_response.follow_ups,
    )
```

This keeps the return type uniform — no changes needed downstream in chat.py or frontend.

#### Streaming behavior

For Lightning tier (no reasoning):
- No `response.reasoning_summary_text.delta` events emitted (gpt-4o-mini doesn't reason)
- Frontend already handles missing reasoning events gracefully (no thinking animation)
- `narrative` text deltas stream normally
- `done` event wraps LightningResponse → AgentResponse as above

### 6. Chat Route Changes (`chat.py`)

#### Pass history flag to classifier

```python
has_history = bool(request.conversation_history)
query_profile = classify_query(request.message, has_history=has_history)
```

#### Three-way prompt selection

```python
if query_profile.system_prompt_mode == "lightning":
    system_prompt = build_system_prompt_lightning(compiled_summary, patient_profile=profile_summary)
elif query_profile.system_prompt_mode == "fast":
    system_prompt = build_system_prompt_fast(compiled_summary, patient_profile=profile_summary)
else:
    system_prompt = build_system_prompt_v2(compiled_summary, patient_profile=profile_summary)
```

#### Enhanced logging

```
"Chat context ready: patient=%s, summary=%s, tier=%s, model=%s, prompt=%d chars (~%d tokens), ..."
```

## Gotchas & Mitigations

| Gotcha | Mitigation |
|--------|------------|
| gpt-4o-mini rejects `reasoning` parameter with 400 error | Conditionally omit `reasoning` kwarg when `query_profile.reasoning == False` |
| No reasoning stream events for Lightning | Frontend already handles gracefully — no thinking animation shown |
| LightningResponse must become AgentResponse before SSE | Wrap in agent.py before returning, keep return types uniform |
| gpt-4o-mini structured output ~97-98% reliable | Use simpler LightningResponse schema (2 fields vs 7) to maximize reliability |
| Non-reasoning model may hallucinate on ambiguous queries | Conservative classifier — default is always DEEP, LIGHTNING only for clear chart lookups |
| Conversation follow-ups need context a non-reasoning model can't handle | `has_history` guard upgrades LIGHTNING → QUICK |

## Acceptance Criteria

### Functional Requirements

- [ ] Lightning queries ("What medications?", "allergies", "bp") return in ~3-5s
- [ ] Quick queries (date-filtered lookups, conversation follow-ups with chart entities) return in ~15-25s
- [ ] Deep queries (clinical reasoning, trend analysis, interactions) continue at current quality (~60-75s)
- [ ] Client `reasoning_effort` override still works across all tiers
- [ ] Frontend renders correctly for all three tiers (same AgentResponse schema, same SSE events)
- [ ] No reasoning stream events for Lightning tier (verified in logs)

### Non-Functional Requirements

- [ ] All existing tests pass (no regressions)
- [ ] New tests for Lightning tier classification, prompt, schema, and agent behavior
- [ ] Classifier remains pure function with zero I/O
- [ ] No frontend changes required
- [ ] No new dependencies

### Quality Gates

- [ ] `make test` — all tests pass
- [ ] `make rebuild` — manual testing of all three tiers
- [ ] Log verification: tier, model, effort, token counts for each tier

## Files Changed

| File | Change |
|------|--------|
| `backend/app/services/query_classifier.py` | QueryTier LIGHTNING/QUICK/DEEP, new QueryProfile fields (model, reasoning, response_schema), updated classify_query() with has_history param and temporal modifier detection |
| `backend/app/schemas/agent.py` | Add LightningResponse schema |
| `backend/app/services/agent.py` | Add build_system_prompt_lightning(), conditional reasoning param, model routing, response schema routing, LightningResponse → AgentResponse wrapping |
| `backend/app/routes/chat.py` | Pass has_history to classifier, three-way prompt selection, enhanced logging |
| `backend/tests/test_query_classifier.py` | Update all tests for three tiers, add Lightning/Quick/Deep classification tests, temporal modifier tests, has_history tests |
| `backend/tests/test_agent.py` | Tests for lightning prompt, conditional reasoning, LightningResponse wrapping, model routing |
| `backend/tests/test_chat.py` | Tests for three-way routing, has_history propagation |

No new dependencies. No frontend changes. No schema migrations.

## Implementation Order

1. Update `query_classifier.py` — add LIGHTNING/QUICK/DEEP tiers, new QueryProfile fields, update classify_query() with has_history and temporal modifiers
2. Update `test_query_classifier.py` — new tests for three tiers, temporal modifiers, has_history
3. Add `LightningResponse` to `schemas/agent.py`
4. Add `build_system_prompt_lightning()` to `agent.py`
5. Update agent generate methods — conditional reasoning, model routing, schema routing, response wrapping
6. Update `chat.py` — three-way prompt selection, has_history, enhanced logging
7. Update `test_agent.py` and `test_chat.py`
8. `make test` — all pass
9. `make rebuild` — manual testing of all three tiers

## Verification

1. `make test` — all existing + new tests pass
2. `make rebuild`
3. Send "What medications?" → logs show `tier=lightning, model=gpt-4o-mini`, no reasoning, ~3-5s
4. Send "What were the labs from January?" → logs show `tier=quick, model=gpt-5-mini`, low reasoning
5. Send "Explain the HbA1c trend" → logs show `tier=deep, model=gpt-5-mini`, medium reasoning
6. Send "medications" as first message → LIGHTNING; send "medications" as follow-up → QUICK
7. Verify frontend renders correctly for all three tiers

## Future Considerations

### Phase 3: Semantic classifier

When traffic data is available, upgrade from keyword heuristic to embedding-based routing:
- Embed queries with a medical sentence transformer (PubMedBERT / BioSentVec)
- Cosine-similarity routing against pre-embedded intent exemplars
- Low-confidence queries fall back to LLM classifier or default DEEP

### Model upgrades

As faster reasoning models become available (gpt-5-mini speed improvements, etc.), the Lightning tier could be collapsed back into Quick if the speed gap narrows. The trifurcated architecture makes this trivial — just update the profile constants.
