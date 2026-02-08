---
title: "feat: Retrieval redesign — pre-compiled context, generic traversal, 3 agent tools"
type: feat
date: 2026-02-04
supersedes: 2026-01-31-feat-agent-data-access-redesign-plan.md
brainstorm: docs/brainstorms/2026-02-04-retrieval-redesign-brainstorm.md
---

# Retrieval Redesign — Pre-compiled Context + Generic Traversal + Agent Tools

## Overview

Replace the per-query retrieval pipeline with a pre-compiled patient summary generated at seed time, three focused agent tools (down from 5), and a generic graph traversal method. The pre-compiled summary gives the agent instant clinical context (~18-20k tokens) covering active conditions, recent encounters, and latest observations — organized by clinical relationships, not flat lists.

## Problem Statement

Every user message currently triggers a full retrieval pipeline: verified layer from Neo4j, graph traversal with synonym expansion, and pgvector semantic search. This is expensive, often guesses wrong about what the agent needs, and presents data as flat lists without clinical relationships. The agent can't see which medication treats which condition without inferring from clinical knowledge.

## Supersedes

This plan supersedes `2026-01-31-feat-agent-data-access-redesign-plan.md`. Phase 1 of that plan (graph-centric context, tasks 1-5) is implemented. Phase 2 (5 agent tools) is partially implemented. This redesign replaces the per-query context engine with pre-compiled summaries and consolidates to 3 tools.

## Architecture Decisions

1. **Pre-compiled at seed time, not per-query** — Demo platform with controlled data loads. Recompile on seed and bundle load. No cache infrastructure.
2. **Condition-centric organization** — Active conditions as the organizing principle. Meds, care plans nested under the conditions they treat. Position encodes relationship.
3. **Pruned FHIR JSON as universal format** — `_prune_fhir_resource()` everywhere. No per-type formatters. ~60% reduction from raw FHIR.
4. **Generic graph traversal** — Single Cypher query returning all edges from any node. No hard-coded per-relationship methods.
5. **Shared compilation logic** — `compile_node_context()` powers both batch (pre-compiled) and live (tool) paths.
6. **Storage: JSONB column on Patient FhirResource** — Store compiled summary as a JSONB column (`compiled_summary`) on the FhirResource row where `resource_type='Patient'`. No new table needed — the Patient resource is the natural anchor. Add `compiled_at` timestamp column.
7. **Fallback: compile on-demand if summary missing** — If chat request finds no pre-compiled summary, compile it synchronously (slow first request) and cache it. No need to keep the old ContextEngine as a fallback.
8. **Clinical note edge type is `DOCUMENTED`** — The brainstorm says `CREATED_DURING` but the codebase uses `DOCUMENTED` for DocumentReference and `CREATED_DURING` for CarePlan. Use `DOCUMENTED`.
9. **Clinical note trimming** — The pruner's 1500-char cap is removed for the pre-compiled summary. The note text is extracted before pruning and included separately (not inside the pruned resource). For live tool calls, same behavior — full note text when DocumentReferences are encountered.

## Design Decisions Resolved from Open Questions

| Question | Decision | Rationale |
|----------|----------|-----------|
| Storage format | JSONB column on Patient FhirResource row + `compiled_at` timestamp | Simplest. No new table. Atomic read with patient data. |
| Missing summary at chat time | Compile on-demand, store result | Self-healing. Slow first request but never broken. |
| Compilation failure | All-or-nothing. Retry on next request if missing. | Partial summaries are worse than no summary. |
| Encounter selection with no AMB | Fall back to most recent encounter of any class | Guarantee Tier 2 is never empty if encounters exist. |
| Clinical note trimming | Extract note before pruning, include full text | Pruner handles resources; note is a separate section. |
| Drug interaction flags | System prompt instructs agent to reason about interactions from med list. No lookup table. | Lookup table is out of scope. Agent can infer from clinical knowledge. |
| Dedup ordering (Tier 2 vs Tier 1) | Tier 2 dedup against Tier 1 runs AFTER Tier 3 dedup against Tier 2. Current order is correct. | Tier 3 dedup uses fhir_id matching against Tier 2's full set. Tier 2 dedup against Tier 1 only removes meds (not observations). |
| Enrichment fields through pruner | Pruner preserves `_trend`, `_recency`, `_inferred`, `_duration_days` — they don't match any strip keys. Add test coverage. | Verified by inspecting `_STRIP_KEYS` and `_STRIP_INNER_KEYS`. |
| Medication node patient_id | Generic traversal uses `fhir_id` only when `patient_id` is null on the node. Medication nodes don't have patient_id. | Handle in the Cypher query with optional patient_id matching. |
| Recompilation sync/async | Synchronous during seed. Synchronous during bundle load (data is small, 5 patients). | Async adds complexity for no benefit at current data volume. |
| Empty sections | Show "None recorded" for allergies, immunizations, care plans. Omit section header for empty recently-resolved conditions, unlinked meds. | Allergies/immunizations absence is clinically meaningful. Empty "unlinked meds" is just clutter. |

## Task Decomposition

### Layer 0: Foundation (no dependencies)

#### Task 1: Database migration — add compiled_summary and compiled_at columns

Add `compiled_summary` (JSONB, nullable) and `compiled_at` (DateTime with timezone, nullable) columns to the `fhir_resources` table. These columns are only populated for Patient-type resources.

**Files**: New Alembic migration, `backend/app/models/fhir.py`
**Acceptance criteria**:
- Migration applies cleanly, rollback works
- FhirResource model has `compiled_summary` and `compiled_at` fields
- Existing data unaffected (columns are nullable)

#### Task 2: Generic graph traversal — `get_all_connections()`

Add `get_all_connections(fhir_id, patient_id=None)` to `KnowledgeGraph`. Single Cypher query returning all edges from a node, excluding Patient nodes. Groups results by relationship type with direction.

Handle Medication nodes (no `patient_id`) by making the patient_id match optional:
```cypher
MATCH (n {fhir_id: $fhir_id})-[r]-(m)
WHERE NOT m:Patient
  AND (n.patient_id = $patient_id OR n.patient_id IS NULL)
RETURN type(r) as relationship,
       CASE WHEN startNode(r) = n THEN 'outgoing' ELSE 'incoming' END as direction,
       m.fhir_id as fhir_id,
       m.resource_type as resource_type,
       m.name as name,
       m.fhir_resource as fhir_resource
ORDER BY relationship, resource_type
```

**Files**: `backend/app/services/graph.py`, `backend/tests/test_graph.py`
**Acceptance criteria**:
- Returns all edges from a Condition node (TREATS, ADDRESSES, DIAGNOSED, etc.)
- Returns all edges from an Encounter node (DIAGNOSED, PRESCRIBED, RECORDED, etc.)
- Returns empty list for node with no edges
- Returns empty list for nonexistent node
- Works for Medication nodes (no patient_id)
- Filters out Patient nodes (no HAS_* results)
- Integration test with real Neo4j

#### Task 3: Fix `get_verified_conditions()` active status filter

Change the Cypher query from `clinical_status = 'active'` to `clinical_status IN ['active', 'recurrence', 'relapse']`. Known bug documented in the brainstorm.

**Files**: `backend/app/services/graph.py`, `backend/tests/test_graph.py`
**Acceptance criteria**:
- Conditions with `recurrence` and `relapse` clinical status are returned
- Existing `active` conditions still returned
- Test covers all three statuses

#### Task 4: Remove clinical note 1500-char truncation from pruner

Modify `_prune_fhir_resource()` to not truncate DocumentReference base64 content. The note is decoded fully. The `clinical_note` field carries the complete text.

**Files**: `backend/app/services/agent.py`, `backend/tests/test_agent.py`
**Acceptance criteria**:
- DocumentReference with >1500 char note produces full `clinical_note` field
- Existing short notes still work
- Test with a long note verifies no truncation

### Layer 1: Compilation Building Blocks (depends on Layer 0)

#### Task 5: Shared compilation core — `compile_node_context()`

Create `backend/app/services/compiler.py` with the shared building block:

```python
async def compile_node_context(
    fhir_id: str,
    patient_id: str,
    graph: KnowledgeGraph,
    db: AsyncSession,
) -> dict[str, list[dict]]:
    """Get all connections from a node, fetch full resources, prune.
    Returns {relationship_type: [pruned_resource_dicts]}."""
```

Logic:
1. Call `graph.get_all_connections(fhir_id, patient_id)` to get connected node metadata
2. Batch-fetch full FHIR resources from Postgres by `fhir_id` (not from Neo4j — Postgres is canonical)
3. Prune each resource with `_prune_fhir_resource()`
4. For DocumentReference resources, decode note text and include as separate field
5. Group by relationship type

Also add helpers:
- `fetch_resources_by_fhir_ids(db, fhir_ids, patient_id)` — batch Postgres lookup
- `prune_and_enrich(resource_data, enrichments=None)` — prune + attach synthetic fields

**Files**: `backend/app/services/compiler.py`, `backend/tests/test_compiler.py`
**Depends on**: Task 2 (generic traversal), Task 4 (no note truncation)
**Acceptance criteria**:
- Given a Condition fhir_id, returns grouped connections (TREATS -> meds, ADDRESSES -> care plans, etc.)
- Given an Encounter fhir_id, returns grouped events (DIAGNOSED -> conditions, PRESCRIBED -> meds, etc.)
- DocumentReferences have decoded note text
- All resources are pruned
- Batch Postgres fetch (not N+1)
- Unit tests with mocked graph + db

#### Task 6: Latest observations query + observation trends

Add to `compiler.py`:

```python
async def get_latest_observations_by_category(
    db: AsyncSession, patient_id: str
) -> dict[str, list[dict]]:
    """Latest observation per LOINC code per category."""

async def compute_observation_trends(
    db: AsyncSession, patient_id: str, observations: list[dict]
) -> list[dict]:
    """For each observation, fetch previous value and compute _trend."""
```

Postgres query for latest-per-LOINC:
- Group by `data->'code'->'coding'->0->>'code'` (LOINC) and `data->'category'->0->'coding'->0->>'code'` (category)
- Take max `effectiveDateTime` per group
- Categories: `vital-signs`, `laboratory`, `survey`, `social-history`

Trend computation:
- For each observation, find the second-most-recent with same LOINC code
- Compute `direction` (rising/falling/stable at 5% threshold), `delta`, `delta_percent`, `previous_value`, `previous_date`, `timespan_days`
- Only for numeric `valueQuantity` observations
- Omit `_trend` when no previous value exists
- Handle zero previous value: any non-zero current = "rising", both zero = "stable"

**Files**: `backend/app/services/compiler.py`, `backend/tests/test_compiler.py`
**Depends on**: Nothing (pure Postgres queries, no graph dependency)
**Acceptance criteria**:
- Returns latest observation per LOINC per category
- Categories are correctly separated
- Trend computed for observations with 2+ historical values
- Trend omitted for single-value observations
- Non-numeric observations included but without _trend
- Zero-value edge case handled
- Unit tests with mocked db session

#### Task 7: Medication recency + encounter-inferred medication links

Add to `compiler.py`:

```python
def compute_medication_recency(
    med_data: dict, compilation_date: date
) -> dict:
    """Add _recency and _duration_days from authoredOn."""

async def infer_medication_condition_links(
    unlinked_meds: list[dict],
    graph: KnowledgeGraph,
    patient_id: str,
) -> dict[str, list[dict]]:
    """For meds without TREATS edge, traverse: med -> PRESCRIBED -> encounter -> DIAGNOSED -> condition."""
```

Recency categories:
- `new`: <30 days since `authoredOn`
- `recent`: 30-180 days
- `established`: >180 days

Dose history enrichment:
For each active medication, query Postgres for prior MedicationRequests with the same medication concept (`medicationCodeableConcept` display) but different dosage or status (`completed`/`stopped`). Attach `_dose_history` as a compact list of prior doses:
```python
"_dose_history": [
    {"dose": "20 MG", "authoredOn": "2025-06-01", "status": "stopped"},
    {"dose": "30 MG", "authoredOn": "2025-08-15", "status": "completed"}
]
```
Ordered chronologically. Only include entries where dosage differs from current. Omit `_dose_history` if no prior records exist. This surfaces clinically critical titration patterns (e.g., escalating diuretics, dose adjustments) that are invisible from the current active medication alone.

Inference logic:
1. For each medication, check its connections for TREATS edges (from `compile_node_context` results)
2. If no TREATS edge, find PRESCRIBED edge to an Encounter
3. From that Encounter, find DIAGNOSED edges to Conditions
4. Return mapping: `{condition_fhir_id: [medication_dicts_with_inferred_flag]}`

**Files**: `backend/app/services/compiler.py`, `backend/tests/test_compiler.py`
**Depends on**: Task 5 (compile_node_context for TREATS edge detection)
**Acceptance criteria**:
- Recency computed correctly for all three categories
- Meds without `authoredOn` handled gracefully (skip recency)
- `_dose_history` populated when prior dose records exist
- `_dose_history` omitted when no prior records
- Same-dose refills excluded from `_dose_history` (only different dosages)
- Inferred links flagged with `_inferred: true`
- Meds with no encounter link fall into "unlinked"
- Unit tests

### Layer 2: Compilation Pipeline (depends on Layer 1)

#### Task 8: Patient summary compilation pipeline

The main orchestrator in `compiler.py`:

```python
async def compile_patient_summary(
    patient_id: str,
    graph: KnowledgeGraph,
    db: AsyncSession,
    compilation_date: date | None = None,
) -> dict:
    """Execute the 12-step assembly pipeline. Returns the full pre-compiled summary as a dict."""
```

Assembly steps (updated from brainstorm with demo scenario gap fixes):
1. Build patient orientation narrative (template from Patient resource + profile)
2. Build Tier 1: fetch active/recently-resolved conditions, active meds, allergies, care plans, immunizations. For each condition, `compile_node_context()` to find treating meds, care plans.
3. Run encounter-inferred medication links for unlinked meds
4. Compute medication recency + dose history for all active meds
5. Build Tier 2: fetch last AMB encounter (fall back to any class) + 6-month window encounters. For each, `compile_node_context()` for events. Fetch and decode clinical notes for ALL Tier 2 encounters via `DOCUMENTED` edge (not just the last encounter).
6. Build Tier 3: latest observations per LOINC per category
7. Compute observation trends
8. Deduplicate Tier 3 against Tier 2 by `fhir_id`
9. Deduplicate Tier 2 against Tier 1 (meds only — condition-level takes precedence)
10. Derive safety constraints from Tier 1
11. Prune all resources + attach enrichment fields
12. Assemble into final dict structure

Active resource filters (from brainstorm):
- Condition active: `clinical_status IN (active, recurrence, relapse)`
- Condition recently resolved: `clinical_status IN (resolved, remission, inactive)` AND `abatementDateTime` within 6 months
- MedicationRequest: `status IN (active, on-hold)`
- AllergyIntolerance: `clinical_status = active`
- CarePlan: `status IN (active, on-hold)`
- Immunization: `status = completed`

**Files**: `backend/app/services/compiler.py`, `backend/tests/test_compiler.py`
**Depends on**: Tasks 5, 6, 7 (all compilation building blocks)
**Acceptance criteria**:
- Compiles summary for a patient with all tiers populated
- Handles patient with no recent encounters (Tier 2 has only the "last encounter" which may be old)
- Handles patient with zero active conditions (Tier 1 conditions section is empty)
- Handles patient with no DocumentReference for an encounter (clinical note omitted for that encounter)
- Clinical notes included for ALL Tier 2 encounters (not just the last one)
- Medication dose history (`_dose_history`) populated for meds with prior dose changes
- Deduplication works correctly (same medication doesn't appear in both Tier 1 and Tier 2)
- Empty sections handled correctly (allergies show "None recorded", empty recently-resolved omitted)
- Patient orientation narrative generated correctly
- Output structure matches the format spec in the brainstorm
- Unit tests with mocked graph + db covering all edge cases

#### Task 9: Compilation storage + triggers

Wire compilation into the data pipeline:

1. After `compile_patient_summary()`, serialize to the `compiled_summary` JSONB column and set `compiled_at` on the Patient FhirResource row.
2. Add `compile_and_store(patient_id, graph, db)` wrapper that calls the pipeline and persists.
3. Hook into `fhir_loader.load_bundle()` — after embeddings + graph build, call `compile_and_store()`.
4. Hook into the seed script (if separate from `load_bundle`).
5. Add `get_compiled_summary(db, patient_id)` helper for the chat route.
6. On-demand fallback: if `get_compiled_summary()` returns None, compile synchronously, store, and return.

**Files**: `backend/app/services/compiler.py`, `backend/app/services/fhir_loader.py`, `backend/app/models/fhir.py`
**Depends on**: Task 1 (migration), Task 8 (compilation pipeline)
**Acceptance criteria**:
- After `make seed`, all patients have `compiled_summary` populated
- `compiled_at` reflects compilation time
- `get_compiled_summary()` returns the stored dict
- On-demand compilation works when summary is missing
- Bundle load triggers recompilation

### Layer 3: Agent Integration (depends on Layer 2 for pre-compiled context, Layer 0 for generic traversal)

#### Task 10: System prompt redesign

Rewrite the system prompt template and `build_system_prompt()` to consume the pre-compiled summary instead of `PatientContext`.

New system prompt structure:
1. Role + PCP context persona
2. Pre-compiled patient summary (the entire artifact, formatted as structured text)
3. Agent reasoning directives:
   - Absence reporting: "When you search for data and find nothing, explicitly report the absence."
   - Cross-condition reasoning: "Consider how the patient's other active conditions may affect treatment options."
   - Tool-chain self-checking: "If a tool result contradicts information in the patient summary, note the discrepancy."
4. Tool descriptions + usage guidance:
   - "The summary above covers the patient's current state. Use tools for historical data, deeper exploration, and timeline browsing."
   - Trend field guidance: "The `_trend` fields show direction and one previous value. For multi-point trend analysis (3+ data points, full trajectory), use `query_patient_data` to retrieve the complete observation history."
   - Dose history guidance: "The `_dose_history` field shows recent dose changes. For complete medication history including discontinued medications, use `query_patient_data` with the medication name."
5. Safety constraints (from compiled summary)

New function:
```python
def build_system_prompt_v2(compiled_summary: dict, patient_profile: str | None = None) -> str:
```

**Files**: `backend/app/services/agent.py`, `backend/tests/test_agent.py`
**Depends on**: Task 8 (compilation pipeline output format — needs to know the dict structure)
**Acceptance criteria**:
- System prompt includes full pre-compiled summary
- PCP context, absence reporting, cross-condition reasoning, self-checking directives present
- Tool descriptions guide the agent on when to use tools vs rely on summary
- Safety constraints section included
- Token count within expected range (~22-38k total system prompt — increased from original estimate due to Tier 2 notes for all encounters and dose history enrichment)
- Tests verify prompt construction from a sample compiled summary

#### Task 11: Three new agent tools

Replace the 5 tools in `agent_tools.py` with 3:

**`query_patient_data`**:
- Parameters: `resource_type` (optional), `name` (optional), `status` (optional), `category` (optional), `date_from`/`date_to` (optional), `include_full_resource` (default true), `limit` (default 20)
- Primary: Postgres ILIKE on display name + attribute filters
- Fallback: If <3 results and `name` provided, run pgvector semantic search (threshold 0.4)
- Results labeled by source (exact vs semantic)
- Returns pruned FHIR JSON

**`explore_connections`**:
- Parameters: `fhir_id`, `resource_type`, `include_full_resource` (default true), `max_per_relationship` (default 10)
- Calls `compile_node_context()` (shared with compilation pipeline)
- Groups by relationship type
- When source is Encounter, DocumentReferences include decoded note text
- Returns pruned FHIR JSON grouped by edge type

**`get_patient_timeline`**:
- Parameters: `start_date` (optional), `end_date` (optional), `include_notes` (default false)
- Neo4j encounter query + generic traversal per encounter
- When `include_notes=true`, fetches DocumentReference via DOCUMENTED edge, decodes note
- Returns chronological encounter listing with events

**Files**: `backend/app/services/agent_tools.py`, `backend/tests/test_agent_tools.py`
**Depends on**: Task 2 (generic traversal), Task 5 (compile_node_context)
**Acceptance criteria**:
- `query_patient_data` returns results for exact name match
- `query_patient_data` triggers pgvector fallback when <3 exact results
- `query_patient_data` with no results returns explicit "no results found" message
- `explore_connections` returns grouped connections from a Condition
- `explore_connections` returns DocumentReference notes from an Encounter
- `get_patient_timeline` returns encounters in date range
- `get_patient_timeline` with `include_notes=true` includes clinical note text
- All tools return pruned FHIR JSON
- Old 5 tools removed
- TOOL_SCHEMAS updated
- Unit tests with mocked graph + db

#### Task 12: Chat route integration — wire pre-compiled context into chat flow

Modify the chat route to load the pre-compiled summary and pass it to the new system prompt builder. Remove the per-query ContextEngine call.

Changes to `chat.py`:
1. `_prepare_chat_context()` → load pre-compiled summary via `get_compiled_summary()`
2. If no summary, compile on-demand (from Task 9)
3. Pass summary to `build_system_prompt_v2()`
4. Remove `context_engine.build_context()` call
5. Keep graph + db injection for tool execution (tools still need live access)

Changes to `agent.py`:
1. `AgentService` accepts the compiled summary dict instead of `PatientContext`
2. Tool execution still uses graph + db directly

**Files**: `backend/app/routes/chat.py`, `backend/app/services/agent.py`, `backend/tests/test_chat.py`
**Depends on**: Task 9 (compilation storage), Task 10 (system prompt), Task 11 (new tools)
**Acceptance criteria**:
- Chat endpoint loads pre-compiled summary for the patient
- System prompt uses new format
- Agent tools work in the tool-calling loop
- On-demand compilation fires if summary is missing
- Streaming and non-streaming paths both work
- Integration test: send a chat message, verify response uses pre-compiled context
- Old ContextEngine dependency removed from chat route

### Layer 4: Cleanup (depends on Layer 3)

#### Task 13: Remove deprecated code + final tests

1. Remove or deprecate `ContextEngine` class (or mark as unused)
2. Remove old per-relationship graph methods that are no longer called:
   - `get_medications_treating_condition()`
   - `get_procedures_for_condition()`
   - `get_care_plans_for_condition()`
   - `get_diagnostic_report_results()`
   - `get_encounter_events()` (replaced by generic traversal — BUT check if anything else calls it)
3. Remove `query_parser.py` if no longer used (check if `query_patient_data` reuses any of it)
4. Remove unused formatting helpers from `agent.py` (`_format_condition`, `_format_medication`, `_format_allergy`, `_format_resource_list`, `_format_retrieved_context`)
5. Update `PatientContext` schema or remove if unused
6. Run full test suite, fix any breakage
7. Verify `make seed` works end-to-end (seed → compile → chat)

**Files**: Multiple files across services, schemas, tests
**Depends on**: Task 12 (everything wired up and working)
**Acceptance criteria**:
- No dead code in services/
- All tests pass
- `make seed` followed by chat works correctly
- `make test` passes

## Dependency Graph

```
Layer 0 (Foundation — all parallel):
  Task 1 (migration)
  Task 2 (generic traversal)
  Task 3 (fix verified conditions)
  Task 4 (remove note truncation)

Layer 1 (Building Blocks):
  Task 5 (compile_node_context)     ← depends on Task 2, Task 4
  Task 6 (latest obs + trends)      ← no dependencies (pure Postgres)
  Task 7 (med recency + inferred)   ← depends on Task 5

Layer 2 (Pipeline):
  Task 8 (compilation pipeline)     ← depends on Tasks 5, 6, 7
  Task 9 (storage + triggers)       ← depends on Tasks 1, 8

Layer 3 (Agent Integration):
  Task 10 (system prompt)           ← depends on Task 8 (output format)
  Task 11 (3 agent tools)           ← depends on Tasks 2, 5
  Task 12 (chat route wiring)       ← depends on Tasks 9, 10, 11

Layer 4 (Cleanup):
  Task 13 (remove deprecated code)  ← depends on Task 12
```

### Parallelism Opportunities

- **Layer 0**: All 4 tasks are fully parallel
- **Layer 1**: Tasks 5 and 6 can run in parallel (Task 7 waits for Task 5)
- **Layer 2**: Task 8 waits for all Layer 1. Task 9 waits for Task 1 + Task 8.
- **Layer 3**: Tasks 10 and 11 can run in parallel (both wait for Layer 2 output format but not storage). Task 12 waits for 9, 10, 11.
- **Layer 4**: Sequential after Layer 3

**Maximum parallelism**: 4 workers at Layer 0, 2 at Layer 1, 2 at Layer 3.

## Risks

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| Pre-compiled summary exceeds token budget for heavy patients | Medium | Medium | Including notes for all Tier 2 encounters (1-3 encounters × 2-5k tokens each) raises typical to ~22-28k and worst case to ~38k (~30% of 128k). Measure after Task 8. Trimming strategy if needed: drop oldest Tier 2 encounter notes first, then Tier 3 survey/social-history. |
| Compilation too slow during seed | Low | Low | 5 patients, ~770 resources each. N graph traversals per patient but Neo4j is fast for small graphs. Sequential patient processing. |
| Pruner mangles enrichment fields | Low | High | Task 4 adds explicit test coverage. Enrichment fields don't match strip key patterns. |
| DocumentReference edge type confusion | Resolved | — | Confirmed: `DOCUMENTED` is correct (not `CREATED_DURING`). |
| Stale summary after bundle load | Low | Medium | Synchronous recompilation in Task 9. |

## References

- Brainstorm: `docs/brainstorms/2026-02-04-retrieval-redesign-brainstorm.md`
- Prior plan (superseded): `docs/plans/2026-01-31-feat-agent-data-access-redesign-plan.md`
- Encounter hub traversal learning: `docs/solutions/integration/encounter-hub-traversal-context-engine-20260201.md`
- Key files: `graph.py`, `agent.py`, `agent_tools.py`, `context_engine.py`, `fhir_loader.py`, `models/fhir.py`
- Li et al., "Scaling medical AI across clinical contexts" (Nature Medicine, 2025) — agent reasoning principles
