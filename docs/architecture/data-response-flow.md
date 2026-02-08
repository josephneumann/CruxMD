# End-to-End Data and Response Flow

Technical documentation covering the full data pipeline from FHIR bundle ingestion through LLM generation to frontend rendering.

## Overview

```
FHIR Bundle
    |
    v
[1. fhir_loader.py] ──> PostgreSQL (FhirResource table, JSONB)
    |                 ──> Neo4j (KnowledgeGraph nodes + edges)
    |                 ──> pgvector (embeddings)
    v
[2. compiler.py] ──> compile_patient_summary() ──> 12-step pipeline
    |                 Stored on FhirResource.compiled_summary (JSONB)
    v
[3. chat.py route] ──> classify_query() ──> QueryProfile (Lightning/Quick/Deep)
    |                   build_system_prompt_*() ──> formatted text
    v
[4. agent.py] ──> OpenAI Responses API ──> tool loop ──> structured output
    |               AgentResponse / LightningResponse (Pydantic)
    v
[5. SSE stream] ──> event: reasoning | narrative | tool_call | tool_result | done
    |
    v
[6. Frontend] ──> useChat hook ──> ConversationalCanvas ──> AgentMessage render
```

---

## 1. Data Ingestion: FHIR Bundle to Storage

**File:** `backend/app/services/fhir_loader.py`

### Entry Points

- `load_bundle(db, graph, bundle)` -- primary loader
- `load_bundle_with_profile(db, graph, bundle, profile)` -- loader with optional patient profile FHIR extension

### Pipeline

1. **Extract resources** from `bundle.entry[].resource`. Clean Synthea numeric suffixes from Patient names (`_clean_patient_names`).
2. **Resolve patient identity.** Find the Patient resource, look up existing by `fhir_id`, or generate a new `uuid4()` as the canonical `patient_id`.
3. **Batch upsert to PostgreSQL.** Single query (`_find_existing_resources_batch`) checks for existing `(fhir_id, resource_type)` pairs. Existing rows get their `data` JSONB updated; new rows are inserted as `FhirResource` objects.
4. **Parallel post-processing** via `asyncio.gather`:
   - **Embeddings:** `_generate_embeddings` converts embeddable resources to text via `resource_to_text()`, batch-embeds with `EmbeddingService`, stores vectors in `FhirResource.embedding` (pgvector column).
   - **Knowledge Graph:** `graph.build_from_fhir(patient_id, resources)` creates Neo4j nodes and relationship edges (TREATS, PRESCRIBED, DIAGNOSED, etc.).
5. **Compile patient summary:** `compile_and_store(patient_id, graph, db)` runs the 12-step compilation pipeline and persists the result to `FhirResource.compiled_summary` on the Patient row.

### Patient Profile Extension

Profiles (occupation, living situation, motivation) are embedded as FHIR extensions on the Patient resource under URL `http://cruxmd.ai/fhir/StructureDefinition/patient-narrative-profile`. Extracted at chat time via `get_patient_profile()`.

### Storage Destinations

| Store | What | Purpose |
|-------|------|---------|
| PostgreSQL `fhir_resources` | Raw FHIR JSON (JSONB), embeddings (pgvector), compiled summary (JSONB) | Source of truth, vector search, pre-compiled context |
| Neo4j | Nodes (Patient, Condition, Medication, etc.) + edges (TREATS, PRESCRIBED, DIAGNOSED) | Graph traversal, relationship queries |

---

## 2. Compilation: Patient Summary Assembly

**File:** `backend/app/services/compiler.py`

### Core Function

`compile_patient_summary(patient_id, graph, db, compilation_date)` -- returns a structured dict.

### 12-Step Pipeline

| Step | Description | Data Sources |
|------|-------------|--------------|
| 1 | **Patient orientation narrative** -- "John Smith, Male, DOB 1985-03-15 (age 40)" | PostgreSQL Patient resource |
| 2 | **Tier 1 resources** -- active conditions, medications, allergies, immunizations, recently resolved conditions, care plans | Neo4j verified queries (`get_verified_conditions`, `get_verified_medications`, etc.) + PostgreSQL |
| 3 | **Encounter-inferred medication links** -- for meds without a direct TREATS edge, traverse `med -> PRESCRIBED -> encounter -> DIAGNOSED -> condition` | Neo4j graph traversal |
| 4 | **Medication enrichments** -- `_recency`, `_duration_days`, `_dose_history` for all active medications | PostgreSQL queries |
| 5 | **Tier 2 encounters** -- recent encounters (6-month window, or at least the most recent) with events and clinical notes | Neo4j `get_patient_encounters` + `get_encounter_events` + PostgreSQL |
| 6 | **Tier 3 observations** -- latest observation per LOINC code, grouped by category | PostgreSQL window function query |
| 7 | **Observation trends** -- `_trend` metadata (direction, delta, previous value, timespan) | PostgreSQL batch query for previous observations |
| 8 | **Tier 3 vs Tier 2 dedup** -- remove observations already present in Tier 2 encounter events | In-memory fhir_id set comparison |
| 9 | **Tier 2 vs Tier 1 dedup** -- remove PRESCRIBED meds from encounters if already linked at condition level | In-memory fhir_id set comparison |
| 10 | **Safety constraints** -- active allergies + drug interaction note | Extracted from allergies in Tier 1 |
| 11 | **Prune + enrich remaining** -- apply `prune_and_enrich()` to allergies, immunizations, standalone care plans | In-memory transformation |
| 12 | **Assemble final dict** | Combine all tiers |

### Deduplication Helpers

Two functions deduplicate FHIR resources before they enter the compiled summary:

- **`_extract_coding_key(resource, code_field)`** -- extracts a dedup key from a CodeableConcept field. Tries `coding[0].code` first (RxNorm, CVX, SNOMED), falls back to `coding[0].display`.
- **`_dedup_by_code(resources, code_field, sort_key, sort_reverse)`** -- sorts resources by `sort_key` (e.g. `authoredOn`, `occurrenceDateTime`), then keeps only the first resource per coding key. Resources without a coding key are always kept.

Applied to: conditions (by SNOMED code), medications (by RxNorm code), allergies (by code), immunizations (by CVX code), recently resolved conditions.

### Enrichment Fields

Fields prefixed with `_` are synthetic enrichments added by the compiler, not part of the original FHIR data:

| Field | Attached To | Computation |
|-------|-------------|-------------|
| `_trend` | Observations | Compares current value to previous observation of same LOINC code. Contains `direction` (rising/falling/stable at 5% threshold), `delta`, `delta_percent`, `previous_value`, `previous_date`, `timespan_days`. |
| `_recency` | MedicationRequests | Based on `authoredOn` relative to compilation date: `new` (<30 days), `recent` (<180 days), `established` (>=180 days). |
| `_duration_days` | MedicationRequests | Days since `authoredOn`. |
| `_dose_history` | MedicationRequests | Prior MedicationRequests with same medication display but different dosage. Chronological list of `{dose, authoredOn, status}`. Same-dose refills excluded. |
| `_inferred` | MedicationRequests | Boolean. True when medication-condition link was inferred via encounter traversal rather than a direct TREATS graph edge. |

### FHIR Resource Pruning

`_prune_fhir_resource(resource)` in `agent.py` recursively simplifies raw FHIR JSON for LLM consumption:

- Strips boilerplate keys: `meta`, `text`, `identifier`, `contained`, `extension`, `modifierExtension`
- Strips inner noise keys: `system`, `use`, `assigner`, `rank`, `postalCode`
- Simplifies CodeableConcepts to display strings
- Simplifies References to display strings or short IDs
- Truncates ISO datetime strings to date-only (`2024-01-15T10:30:00Z` -> `2024-01-15`)
- Decodes base64 DocumentReference content into `clinical_note` text
- Unwraps single-element lists of simple values

### Compiled Summary JSON Structure

```json
{
  "patient_orientation": "John Smith, Male, DOB 1985-03-15 (age 40)",
  "compilation_date": "2026-02-07",

  "tier1_active_conditions": [
    {
      "condition": { "resourceType": "Condition", "code": "Diabetes mellitus type 2", "id": "...", "onsetDateTime": "2020-01-15", "clinicalStatus": "active" },
      "treating_medications": [
        { "resourceType": "MedicationRequest", "medicationCodeableConcept": "Metformin 500 MG", "status": "active", "_recency": "established", "_duration_days": 730, "_dose_history": [...], "_inferred": false }
      ],
      "care_plans": [ { "resourceType": "CarePlan", "category": "Diabetes self management plan", "status": "active" } ],
      "related_procedures": [ { "resourceType": "Procedure", "code": "HbA1c measurement" } ]
    }
  ],
  "tier1_recently_resolved": [ /* same structure, conditions resolved in last 6 months */ ],
  "tier1_unlinked_medications": [ /* medications not linked to any condition */ ],
  "tier1_allergies": [ { "code": "Penicillin V", "criticality": "high", "category": "medication" } ],
  "tier1_immunizations": [ { "vaccineCode": "Influenza seasonal", "occurrenceDateTime": "2025-10-01" } ],
  "tier1_care_plans": [ /* standalone care plans not linked to conditions */ ],

  "tier2_recent_encounters": [
    {
      "encounter": { "resourceType": "Encounter", "type": "Encounter for problem", "period": {"start": "2026-01-15"}, "class": {"code": "AMB"} },
      "events": {
        "DIAGNOSED": [ { "code": "Acute bronchitis" } ],
        "PRESCRIBED": [ { "medicationCodeableConcept": "Amoxicillin 500 MG" } ],
        "RECORDED": [ { "code": "Body Weight", "valueQuantity": {"value": 80, "unit": "kg"} } ],
        "DOCUMENTED": [ { "clinical_note": "Patient presents with cough..." } ]
      }
    }
  ],

  "tier3_latest_observations": {
    "vital-signs": [ { "code": "Blood Pressure", "valueQuantity": {"value": 120, "unit": "mmHg"}, "effectiveDateTime": "2026-01-15", "_trend": {"direction": "stable", "delta": -2, "previous_value": 122, "timespan_days": 90} } ],
    "laboratory": [ /* latest lab per LOINC code */ ],
    "survey": [],
    "social-history": []
  },

  "safety_constraints": {
    "active_allergies": [ { "code": "Penicillin V", "criticality": "high" } ],
    "drug_interactions_note": "Review active medications for potential interactions."
  }
}
```

### Storage

`compile_and_store()` persists the summary dict to `FhirResource.compiled_summary` (JSONB column) and sets `FhirResource.compiled_at` (timestamp). The summary is recompiled when a new FHIR bundle is loaded.

---

## 3. Query Classification

**File:** `backend/app/services/query_classifier.py`

### Purpose

Two-layer hybrid classifier that routes user messages into one of three tiers. Layer 1 is a deterministic heuristic (0ms, no I/O). Layer 2 is an LLM fallback (~200ms, gpt-4o-mini) for ambiguous queries that Layer 1 can't resolve.

### `classify_query(message, has_history=False) -> QueryProfile`

Now an **async** function. `has_history` is kept for backward compatibility but ignored internally.

### Layer 1: Deterministic Classification

Returns a definitive tier for clear-cut queries, or `None` for ambiguous cases (passes to Layer 2).

**Decision flow** (applied in order):

1. **DEEP guard rails:** Empty, >200 chars, conversation references ("you mentioned", "earlier"), deep search patterns ("search for") → DEEP
2. **DEEP deny-list:** Reasoning keywords ("why", "should", "compare", "explain", "assess", "risk", "quantify", "driving", etc.), analytical phrases ("see if", "check if", "determine if") → DEEP
3. **DEEP reasoning shorts:** Short queries (≤4 words) with summary/overview/assessment intent → DEEP
4. **Non-clinical shorts:** Short queries (≤4 words) composed entirely of non-clinical words ("hello", "help", "what") → DEEP
5. **QUICK signals:** Focused retrieval patterns ("find latest", "pull up the", "get the last"), temporal modifiers ("from", "since", "last month") with chart entity, retrieval verbs ("trend", "track", "graph", "filter") with chart entity → QUICK
6. **LIGHTNING signals:** Chart entity + lookup prefix ("what medications", "list conditions"), bare entity shortcut (≤30 chars, "medications", "bp"), specific-item patterns ("what's the A1c?", "is the patient on metformin?") → LIGHTNING
7. **Ambiguous:** Short queries (≤4 words) with no clear signals → `None` (pass to Layer 2)
8. **Default:** `None` (pass to Layer 2)

### Layer 2: LLM Fallback

Called only when Layer 1 returns `None`. Uses gpt-4o-mini with structured output to classify into one of the three tiers.

- **Model:** gpt-4o-mini (fast, cheap)
- **Timeout:** 2 seconds (falls back to DEEP on timeout/error)
- **Output:** JSON `{"tier": "lightning" | "quick" | "deep"}`
- **Latency:** ~200ms typical

### Query Profiles

| Profile | Model | Reasoning | Tools | Max Tokens | Prompt Mode | Response Schema |
|---------|-------|-----------|-------|------------|-------------|----------------|
| `LIGHTNING` | gpt-4o-mini | Off | Off | 2048 | lightning | LightningResponse |
| `QUICK` | gpt-5-mini | On (low) | On | 4096 | fast | AgentResponse |
| `DEEP` | gpt-5-mini | On (medium) | On | 16384 | standard | AgentResponse |

### Tier Definitions

| Tier | When to use | Example |
|------|-------------|---------|
| **Lightning** | Answer exists in pre-compiled patient summary. No retrieval, no reasoning. | "BMI?", "medications", "allergies", "what's the A1c?" |
| **Quick** | Focused data retrieval: filter by date, trend a value, search history. Tools needed but minimal reasoning. | "trend a1c results", "labs from last month", "find latest bp readings" |
| **Deep** | Clinical interpretation, reasoning across entities, recommendations. | "why was lisinopril prescribed?", "assess cardiovascular risk" |

### QueryProfile Dataclass

```python
@dataclass(frozen=True, slots=True)
class QueryProfile:
    tier: QueryTier           # LIGHTNING | QUICK | DEEP
    model: str                # e.g. "gpt-4o-mini" or "gpt-5-mini"
    reasoning: bool           # whether to enable reasoning
    reasoning_effort: str     # "low" | "medium" | "high"
    include_tools: bool       # whether tools are available
    max_output_tokens: int    # response token budget
    system_prompt_mode: str   # "lightning" | "fast" | "standard"
    response_schema: str      # "lightning" | "full"
```

---

## 4. Prompt Formatting

**File:** `backend/app/services/agent.py` (prompt builder functions)

### Three System Prompt Builders

The `system_prompt_mode` field on QueryProfile selects which builder to use:

#### `build_system_prompt_lightning(compiled_summary, patient_profile)`

Minimal prompt for fact extraction with gpt-4o-mini (non-reasoning model):
- **Role:** Concise clinical chart assistant directive
- **Patient summary:** `_build_patient_summary_lightning()` -- includes only: patient orientation, active conditions (name + onset + treating meds table), allergies table, immunizations table, observations (vital signs + labs tables). **Skips:** Tier 2 encounters, care plans, procedures, recently resolved conditions, unlinked medications, FHIR IDs. Saves ~800-1200 tokens.
- **Safety:** `_build_safety_section_lightning()` -- allergy alerts + single fabrication guard line
- **Format:** Minimal -- just narrative + follow_ups

#### `build_system_prompt_fast(compiled_summary, patient_profile)`

Trimmed prompt for QUICK-tier queries with light reasoning:
- **Role:** Concise clinical chart assistant
- **Patient summary:** `_build_patient_summary_section(tier=TIER_FAST)` -- full Tier 1/2/3 data, but omits FHIR IDs
- **Safety:** Full safety section
- **Format:** Narrative + insights + follow_ups (no thinking, no tool descriptions)

#### `build_system_prompt_v2(compiled_summary, patient_profile)`

Full prompt for DEEP-tier clinical reasoning:
- **Section 1: Role + PCP Context Persona** -- detailed clinical reasoning assistant identity
- **Section 2: Patient Summary** -- `_build_patient_summary_section(tier=TIER_DEEP)` -- full data with FHIR IDs
- **Section 3: Reasoning Directives** -- absence reporting, cross-condition reasoning, tool-chain self-checking, temporal awareness, confidence calibration
- **Section 4: Tool Descriptions** -- query_patient_data, explore_connections, get_patient_timeline + enrichment field explanations
- **Section 5: Safety Constraints** -- allergy alerts + drug interaction rules
- **Section 6: Response Format** -- thinking, narrative, insights, visualizations, tables, actions, follow_ups

### Compiled Summary to Prompt Mapping

How each compiled summary field maps to prompt sections:

| Compiled Summary Field | Prompt Section | Formatting Function |
|----------------------|----------------|---------------------|
| `patient_orientation` | `**Patient:** ...` header | Direct string |
| `compilation_date` | `## Patient Summary (compiled ...)` | Direct string |
| `tier1_active_conditions` | `### Active Conditions & Treatments` | `_format_tier1_conditions()` -- condition bullet + nested medication markdown table |
| `tier1_recently_resolved` | `### Recently Resolved Conditions` | `_format_tier1_conditions()` |
| `tier1_allergies` | `Allergies:` table | `_format_tier1_section()` with `_allergy_row()` -> markdown table [Allergen, Criticality, Category] |
| `tier1_unlinked_medications` | `Medications (not linked to a condition):` table | `_format_tier1_section()` with `_unlinked_med_row()` -> markdown table [Medication, Status, Recency] |
| `tier1_immunizations` | `Immunizations:` table | `_format_tier1_section()` with `_immunization_row()` -> markdown table [Vaccine, Date] |
| `tier1_care_plans` | `Standalone Care Plans:` list | `_format_tier1_section()` with `_care_plan_display()` |
| `tier2_recent_encounters` | `### Recent Encounters` | `_format_tier2_encounters()` -- date-tagged entries with Diagnoses/Medications/Observations/Notes |
| `tier3_latest_observations` | `### Latest Observations` | `_format_tier3_observations()` -- category-grouped markdown tables [Observation, Value, Date, Ref Range, Trend] |
| `safety_constraints` | `## Safety Constraints` | `_format_safety_constraints_v2()` -- ALLERGY alerts + drug interaction note |

### Shared Formatting Helper

`_format_as_table(headers, rows)` renders markdown tables used throughout the prompt:

```
| Header1 | Header2 | Header3 |
| --- | --- | --- |
| cell1 | cell2 | cell3 |
```

### Tier-Aware Rendering

The `tier` parameter controls verbosity in formatting functions:
- **TIER_DEEP:** Includes FHIR IDs on conditions and encounters (e.g. `id: abc-123`). Full enrichments including `_dose_history` details.
- **TIER_FAST:** Same structure but omits FHIR IDs.
- **TIER_LIGHTNING:** Uses `_format_tier1_conditions_lightning()` which only shows condition name + onset + treating meds table (3 columns instead of 4, no dose history). Skips care plans, procedures, unlinked meds, recently resolved conditions, and encounters entirely.

---

## 5. LLM Generation

**File:** `backend/app/services/agent.py` (AgentService class)

### AgentService

Wraps the OpenAI Responses API with Pydantic structured outputs.

### Response Schemas

**File:** `backend/app/schemas/agent.py`

Two Pydantic models control structured output:

#### `LightningResponse` (for LIGHTNING tier)

```python
class LightningResponse(BaseModel):
    narrative: str          # Direct answer in markdown
    follow_ups: list[FollowUp] | None  # 2-3 follow-up questions
```

#### `AgentResponse` (for QUICK and DEEP tiers)

```python
class AgentResponse(BaseModel):
    thinking: str | None              # Optional reasoning process
    narrative: str                    # Main response in markdown
    insights: list[Insight] | None    # Clinical callout cards (info/warning/critical/positive)
    visualizations: list[Visualization] | None  # Chart/graph specs with DataQuery
    tables: list[DataTable] | None    # Structured data tables with DataQuery
    actions: list[Action] | None      # Suggested clinical actions
    follow_ups: list[FollowUp] | None # Clickable follow-up questions
```

### Generation Flow

#### `generate_response()` (non-streaming)

1. Build input messages: `[system, ...history, user]`
2. Resolve effective parameters from `QueryProfile` (model, reasoning effort, max tokens, tools)
3. If tools enabled, enter tool-calling loop (`_execute_tool_calls`):
   - Call `responses.parse(**kwargs)` with tool schemas
   - If response contains `function_call` items, execute each tool via `execute_tool()` in `agent_tools.py`
   - Append tool call + result to conversation, loop (up to `MAX_TOOL_ROUNDS=10`)
   - When no tool calls returned, exit loop
4. Parse final response as `AgentResponse` or `LightningResponse` via Pydantic structured output
5. If `LightningResponse`, wrap into `AgentResponse` for uniform return type

#### `generate_response_stream()` (streaming)

Same logic but uses `responses.stream()` instead of `responses.parse()`:

1. For each API round, open a streaming context:
   - Yield `("reasoning", {"delta": text})` for `response.reasoning_summary_text.delta` events
   - Yield `("narrative", {"delta": text})` for `response.output_text.delta` events
2. After stream completes, check for tool calls:
   - If tool calls found: execute tools, yield `("tool_call", ...)` and `("tool_result", ...)`, then loop
   - If no tool calls: parse final response, yield `("done", agent_response_json)`
3. Max rounds exhausted: strip tools, force one final streaming call

### Tool Execution

**File:** `backend/app/services/agent_tools.py`

Three tools available to the LLM during QUICK and DEEP tiers:

| Tool | Purpose | Backend |
|------|---------|---------|
| `query_patient_data` | Search by name/type/filters with pgvector semantic fallback | PostgreSQL JSONB queries + pgvector similarity |
| `explore_connections` | Graph traversal from a specific FHIR resource ID | Neo4j `get_all_connections` + PostgreSQL batch fetch + prune |
| `get_patient_timeline` | Chronological encounter listing with events | Neo4j + PostgreSQL |

Tools return pruned FHIR JSON strings. The agent appends results as `function_call_output` messages and continues reasoning.

---

## 6. SSE Streaming

**File:** `backend/app/routes/chat.py`

### Chat Context Preparation

`_prepare_chat_context(request, db)` is shared by both `/chat` and `/chat/stream`:

1. Validate patient exists in PostgreSQL
2. Initialize `KnowledgeGraph` and `AgentService`
3. Load or compile patient summary (`get_compiled_summary` -> `compile_and_store` fallback)
4. Extract patient profile from FHIR extension
5. Classify query: `classify_query(message, has_history=bool(conversation_history))`
6. Select prompt builder based on `query_profile.system_prompt_mode`:
   - `"lightning"` -> `build_system_prompt_lightning()`
   - `"fast"` -> `build_system_prompt_fast()`
   - `"standard"` -> `build_system_prompt_v2()`

### POST `/api/chat/stream` Endpoint

Returns a `StreamingResponse` with `text/event-stream` media type.

Architecture: background task + asyncio.Queue pattern for disconnect resilience.

1. **Background task** (`generate_and_persist`): calls `agent.generate_response_stream()`, pushes `(event_type, data_json)` tuples into an `asyncio.Queue`. Wrapped in `generate_with_timeout()` (10-minute limit).
2. **SSE generator** (`event_generator`): reads from the queue, formats as SSE:
   ```
   event: <event_type>
   data: <json_payload>

   ```
3. Special handling for `done` event: wraps response with `conversation_id` before emitting.
4. **Message persistence:** User message persisted immediately via `_persist_message()`. Assistant message persisted in the `finally` block of the background task (fire-and-forget pattern using an independent DB session).

### SSE Event Types

| Event | Payload | When |
|-------|---------|------|
| `reasoning` | `{"delta": "..."}` | Reasoning summary text deltas from LLM |
| `narrative` | `{"delta": "..."}` | Output text deltas (the markdown response) |
| `tool_call` | `{"name": "...", "call_id": "...", "arguments": "..."}` | LLM invokes a tool |
| `tool_result` | `{"call_id": "...", "name": "...", "output": "..."}` | Tool returns result |
| `done` | `{"conversation_id": "...", "response": AgentResponse}` | Final parsed response |
| `error` | `{"detail": "..."}` | Error during generation |

### Frontend Proxy

**File:** `frontend/app/api/chat/stream/route.ts`

Next.js API route that authenticates the request server-side (adding auth headers from `getAuthHeaders()`), then pipes the backend SSE stream through unchanged to the browser. The API key never reaches the client.

---

## 7. Frontend Rendering

### SSE Consumption

**File:** `frontend/hooks/useChat.ts`

The `useChat(patientId, sessionId)` hook manages the full lifecycle:

1. **Send flow:** `sendMessage(content)` creates optimistic user + placeholder assistant `DisplayMessage` objects, then calls `sendStreaming()` with fallback to `sendNonStreaming()`.

2. **SSE parsing:** `parseSSEChunk(buffer, chunk)` handles buffered partial lines from the `ReadableStream`. Each complete SSE event is dispatched through `applyStreamEvent()`:

   | SSE Event | StreamAction | State Change |
   |-----------|-------------|--------------|
   | `tool_call` | `{type: "tool_call"}` | Appends to `toolCalls[]`, sets phase to `"tool_calling"` |
   | `tool_result` | `{type: "tool_result"}` | Updates matching tool call with `result` |
   | `reasoning` | `{type: "reasoning"}` | Appends delta to `reasoningText`, sets phase to `"reasoning"` |
   | `narrative` | `{type: "narrative"}` | Appends delta to `narrativeText`, sets phase to `"narrative"`, updates `content` |
   | `done` | `{type: "done"}` | Sets final `content`, `agentResponse`, phase to `"done"`, clears `pending` |
   | `error` | `{type: "error"}` | Clears streaming state |

3. **Stream cancellation:** `AbortController` on the fetch request; `cancelStream()` aborts and finalizes any in-flight message.

4. **Non-streaming fallback:** If streaming fails or `response.body` is unavailable, falls back to `POST /api/chat` which returns a complete `ChatResponse` JSON.

### Streaming State Model

```typescript
interface StreamingState {
  phase: "tool_calling" | "reasoning" | "narrative" | "done";
  reasoningText: string;      // accumulated reasoning summary deltas
  narrativeText: string;      // accumulated output text deltas
  toolCalls: ToolCallState[]; // tool calls with optional results
  reasoningDurationMs?: number; // client-measured reasoning time
}
```

### Component Rendering

**File:** `frontend/components/canvas/ConversationalCanvas.tsx`

Top-level layout: error banner + `MessageHistory` + `ChatInput`. Passes `useChat` state down.

**File:** `frontend/components/canvas/AgentMessage.tsx`

Renders a completed assistant message (returns `null` while streaming -- `ThinkingIndicator` handles that phase):

1. **Thinking section:** Expandable "Thought for Xs" button showing reasoning text (rendered as markdown via `ReactMarkdown` with `remarkGfm`) and `ToolActivity` component for tool call details.
2. **Narrative:** Main response rendered as markdown with `ReactMarkdown` + `remarkGfm`. Typewriter animation (`useTypewriter`) for just-finished messages. Styled with Tailwind prose classes for headings, lists, tables, code blocks.
3. **Insights:** `InsightCard` components rendered with staggered animation. Sorted by severity: critical > warning > info > positive.
4. **Message actions:** Copy, thumbs up/down feedback, retry buttons.
5. **Follow-up suggestions:** `FollowUpSuggestions` component renders clickable chips. Appears after all insights have animated in.

### Rendering Sequence for a Streaming Response

```
1. User sends message
   -> Optimistic user message + placeholder assistant message added to state
   -> Assistant message has streaming.phase = "reasoning", pending = true

2. SSE events arrive
   -> ThinkingIndicator renders (AgentMessage returns null while streaming)
   -> reasoning deltas accumulate in streaming.reasoningText
   -> tool_call/tool_result events update streaming.toolCalls
   -> narrative deltas accumulate in streaming.narrativeText
      (displayed as live typing in ThinkingIndicator)

3. "done" event arrives
   -> streaming.phase = "done", pending = false
   -> agentResponse populated with full parsed response
   -> ThinkingIndicator unmounts, AgentMessage renders

4. AgentMessage renders final state
   -> Typewriter animation on narrative text
   -> After typewriter completes: insight cards stagger in (150ms each)
   -> After insights: message actions + follow-up chips appear
```

---

## Appendix: Key File Reference

| File | Role |
|------|------|
| `backend/app/services/fhir_loader.py` | FHIR bundle ingestion, PostgreSQL + Neo4j + embeddings |
| `backend/app/services/compiler.py` | 12-step patient summary compilation pipeline |
| `backend/app/services/agent.py` | Prompt builders, FHIR pruning, AgentService (LLM generation) |
| `backend/app/services/agent_tools.py` | Tool schemas and execution (query, explore, timeline) |
| `backend/app/services/query_classifier.py` | Heuristic query routing (Lightning/Quick/Deep) |
| `backend/app/services/graph.py` | Neo4j KnowledgeGraph operations |
| `backend/app/schemas/agent.py` | AgentResponse, LightningResponse, Insight, Visualization, etc. |
| `backend/app/routes/chat.py` | Chat API endpoints (POST /chat, POST /chat/stream) |
| `frontend/hooks/useChat.ts` | SSE consumption, streaming state machine, message management |
| `frontend/app/api/chat/stream/route.ts` | Next.js SSE proxy (auth passthrough) |
| `frontend/components/canvas/AgentMessage.tsx` | Response rendering (markdown, insights, follow-ups) |
| `frontend/components/canvas/ConversationalCanvas.tsx` | Top-level chat layout |
