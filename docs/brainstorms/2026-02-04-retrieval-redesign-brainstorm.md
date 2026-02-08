# Brainstorm: Retrieval Redesign — Pre-compiled Context + Agent Tools + Generic Graph Traversal

**Date**: 2026-02-04
**Status**: Ready for planning
**Supersedes**: `2026-02-01-base-context-agent-driven-search-brainstorm.md`

## Problem Statement

Today, every user message triggers a full retrieval pipeline: verified layer from Neo4j, graph traversal with synonym expansion, and pgvector semantic search. This is expensive, slow, and the pre-retrieval often guesses wrong about what the agent needs.

Additionally:
- The pre-compiled context presents conditions, medications, and allergies as **flat, independent lists** — the agent doesn't know which medication treats which condition without guessing from clinical knowledge.
- Graph relationship data is used for **retrieval** but thrown away before the agent sees it — the agent can't reason about clinical connections.
- Tool results use custom per-type formatters that are lossy and brittle — adding a new resource type or relationship means updating formatting code.
- Graph query methods are hard-coded per relationship type — adding a new edge type requires new code.

## Solution Overview

Three interconnected changes:

1. **Pre-compiled Patient Summary** — Generated at seed time. Condition-centric organization using graph relationships. Pruned FHIR JSON as the universal resource format. Loads instantly on every query with zero retrieval cost.

2. **Redesigned Agent Tools (3 tools)** — Replace the current 5 tools with 3 that cover all query patterns. Shared compilation logic between batch and live paths. Semantic search as automatic fallback inside the query tool.

3. **Generic Graph Traversal** — One Cypher query that returns all edges from any node. No hard-coded per-relationship methods. The graph schema is the single source of truth.

## Key Decisions

### Pre-compiled Context

- **Condition-centric organization**: Active conditions are the organizing principle. Each condition lists its treating medications (TREATS), care plans (ADDRESSES), and other connected resources underneath. Medications not linked to any condition appear in a separate "unlinked" section.
- **Encounter-centric organization for recent visits**: Last AMB encounter + 6-month window encounters. Resources grouped under encounters with edge-type labels (DIAGNOSED, PRESCRIBED, RECORDED, PERFORMED, REPORTED).
- **Pruned FHIR JSON everywhere**: The existing `_prune_fhir_resource()` function is the universal resource format. ~60% reduction from raw FHIR. No custom per-type formatters. Every clinically relevant field preserved.
- **Graph provides organization, pruner provides format**: The graph's job is to determine which resources appear under which headings (compilation time). The pruner's job is to make each resource compact and LLM-readable (leaf-level). These are orthogonal concerns.
- **Position encodes relationship**: Resources are physically nested under the encounter or condition they belong to. The agent understands grouping from spatial structure, not from parsing UUID reference fields.
- **Pruned JSON reference fields carry partial relationship info**: The pruner simplifies FHIR references to display strings. A MedicationRequest's `reasonReference` becomes `"Diabetes mellitus type 2 (disorder)"` — the agent can read this directly. These reference fields are where the graph edges were derived from in the first place. For references with display names (reasonReference, addresses), the relationship is self-documenting. For references that are just UUIDs (encounter), the positional grouping handles it.
- **Pre-compile at seed time, recompile on data changes**: Demo platform with controlled data loads. Recompilation triggered by seed script and bundle loads. No cache infrastructure needed.

### Encounter Selection

- **Always include the most recent AMB encounter** regardless of age — guarantees a substantive clinical visit.
- **Include all other encounters within 6 months of compilation date** — catches recent ER visits, inpatient stays, other ambulatory visits.
- **Anchored to compilation timestamp**, not to the last encounter date.

### "Active" Resource Definitions

| Resource Type | Status Field | Active Filter |
|---|---|---|
| Condition | `clinicalStatus` (CodeableConcept) | `IN (active, recurrence, relapse)` |
| Condition (recently resolved) | `clinicalStatus` + `abatementDateTime` | `IN (resolved, remission, inactive)` AND abatement within 6 months |
| MedicationRequest | `status` (code) | `IN (active, on-hold)` |
| AllergyIntolerance | `clinicalStatus` (CodeableConcept) | `= active` |
| CarePlan | `status` (code) | `IN (active, on-hold)` |
| Immunization | `status` (code) | `= completed` (all completed immunizations included) |

### Resource Type Categories

Not all FHIR resource types have an active/inactive lifecycle. This distinction drives which resources go into Tier 1 vs Tier 2/3:

- **Lifecycle-based** (have active/inactive status): Condition, MedicationRequest, AllergyIntolerance, CarePlan → Tier 1 (patient state)
- **Event-based** (point-in-time, no "active" concept): Observation, Procedure, DiagnosticReport, Encounter, Immunization → Tier 2 (encounters) or Tier 3 (latest observations)

Immunization is a special case: `completed` means "was administered" and all are clinically relevant (safety concern — don't re-vaccinate), so all completed immunizations go in Tier 1.

### Latest Observations (Tier 3)

- **Most recent observation per distinct LOINC code** within each category.
- **Categories**: `vital-signs`, `laboratory`, `survey`, `social-history`.
- **Deduplicated against encounter resources** by `fhir_id` — only include observations NOT already present in the encounter tiers.

### Token Budget

Based on actual measured pruned resource sizes (59.9% reduction from raw FHIR):

| Resource Type | Pruned Tokens (avg) |
|---|---|
| Condition | ~177 |
| MedicationRequest | ~128 |
| Observation (vital-signs) | ~104 |
| Observation (laboratory) | ~113 |
| Procedure | ~99 |
| Encounter | ~185 |
| DiagnosticReport | ~168 |
| CarePlan | ~311 |
| Immunization | ~99 |

**Estimated pre-compiled context size** (including enrichment features):

| Component | Estimated Tokens |
|---|---|
| Patient orientation narrative | ~100 |
| Tier 1: Patient state (lifecycle resources) | ~5,300 |
| Medication recency fields | ~50 (negligible per-resource overhead) |
| Encounter-inferred med links | ~200 (a few extra meds) |
| Tier 2: Recent encounters | ~6,300 |
| Clinical note (full, untrimmed) | ~2,000-5,000 (varies widely) |
| Tier 3: Latest observations | ~2,700 |
| Observation trend fields | ~300 (per-observation overhead) |
| Safety constraints | ~200 |

- Typical: **~18,000-20,000 tokens** (~15% of 128k)
- Worst case (long clinical note): **~30,000 tokens** (~23% of 128k)
- Comfortable budget for conversation history and tool results.

The clinical note is the largest variable. If a note is exceptionally long (>5,000 tokens), it's still worth including — notes are the single most valuable piece of context for clinical questions.

**Comparison**: Compact text summaries (one-liners) would be ~3,000-4,000 tokens — roughly 5-7x smaller. The trade-off: pruned JSON gives the agent every clinically relevant field (dosage instructions, reference ranges, body sites, reason references) while text summaries are lossy and require per-type formatters to maintain. At 15% of context window, the token cost is acceptable for the completeness and zero-maintenance benefit.

## Agent Reasoning Principles

Informed by Li et al., "Scaling medical AI across clinical contexts" (Nature Medicine, 2025). These are behavioral directives encoded in the system prompt, not structural changes to the data pipeline.

### User Context

All users are **primary care physicians (PCPs)**. The agent's tone, vocabulary, and clinical reasoning should match PCP-level discourse — no patient-facing simplification, no subspecialist jargon without explanation. The system prompt encodes this as a fixed persona constraint.

### Absence as a Clinical Fact

When the agent searches for data and finds nothing, it must **explicitly report the absence** rather than silently omitting it. The absence of an expected finding is itself a clinically useful fact — a PCP needs to know "no allergies recorded" vs not knowing whether allergies were checked, or "no A1c in the last 2 years" vs just not mentioning it.

**Rules**:
- Tool results that return zero matches must say so explicitly: `"No observations matching 'Hemoglobin A1c' found for this patient."`
- The agent must surface these absences in its response, not swallow them: "I looked for recent A1c results but none are on file."
- The pre-compiled context should include explicit "None recorded" markers for empty categories (allergies, immunizations, care plans) rather than omitting empty sections.
- This is a **system prompt instruction**, not a tool implementation change — tools already return "no results" messages, but the agent needs to be told that absence is worth reporting.

### Cross-Condition Reasoning

PCPs manage the whole patient, not one organ system. The agent must reason about **interactions between conditions** — comorbidity effects, polypharmacy risks, shared pathophysiology, contraindications that span conditions.

**System prompt guidance** (approximate):
- "When answering questions about a specific condition, consider how the patient's other active conditions may affect treatment options, drug choices, and clinical priorities."
- "Flag potential drug-drug interactions when the patient is on medications for multiple conditions."
- "When a patient has multiple conditions sharing pathophysiology (e.g., diabetes and cardiovascular disease), note the connections and their treatment implications."

**Why this matters**: The condition-centric organization already makes all conditions visible in the base context. But without explicit reasoning guidance, the agent may answer questions about diabetes without considering the patient's concurrent hypertension or kidney disease. The pre-compiled context provides the data; the system prompt provides the reasoning directive.

### Tool-Chain Self-Checking

When the agent uses tools across multiple rounds, it must **cross-check tool results against the base context** and against each other. If a tool returns something that contradicts the pre-compiled summary — e.g., a medication listed as active in the summary but returned as stopped by a tool — the agent must flag the discrepancy rather than silently using whichever it saw last.

**System prompt guidance** (approximate):
- "If a tool result contradicts information in the patient summary, note the discrepancy and explain which source is likely more current."
- "When combining results from multiple tool calls, check for consistency before synthesizing a response."

**Rationale**: Li et al. identify "compounding error" as a key failure mode of agentic systems — errors accumulate silently across steps. By instructing the agent to cross-check, we add a lightweight self-correction loop without architectural changes.

## Clinical Enrichment Features

Five compilation-time enrichments that elevate the context from a data dump to an opinionated clinical summary:

### 1. Patient Orientation Narrative

A 2-3 sentence template-based summary at the very top of the pre-compiled context. Gives the agent immediate clinical orientation before seeing any data.

**Contents**:
- Patient demographics (name, age, gender)
- Patient profile (occupation, living situation, motivation — from generated profiles stored at seed time)
- Condition burden (count of active conditions, key diagnoses)
- Recent care summary (last encounter type and date)

**Example**:
```
Aaron697 is a 54-year-old male. He works as a warehouse supervisor, lives alone in a
single-family home, and is motivated by wanting to stay active for his grandchildren.
He has 6 active conditions including Type 2 Diabetes and Essential Hypertension.
His last ambulatory visit was on 2025-10-14.
```

**Implementation**: Template string populated from Patient resource + patient profile + compiled Tier 1 counts. No LLM call needed.

### 2. Latest Clinical Note

Include the full clinical note from the most recent encounter's DocumentReference in the pre-compiled context.

**Rules**:
- Fetch the DocumentReference associated with the last encounter (via CREATED_DURING edge or encounter reference).
- Decode base64 `content[].attachment.data` to plain text.
- **Do NOT arbitrarily trim** — include the full note content. Clinical notes are the richest source of context and trimming loses critical nuance.
- If no DocumentReference exists for the last encounter, skip this section.

**Rationale**: Clinical notes contain narrative context that structured FHIR data cannot capture — the physician's reasoning, patient-reported symptoms, clinical impressions, and follow-up plans. This is often exactly what the user is asking about.

### 3. Observation Trends

At compilation time, for each latest observation (Tier 3), fetch the previous value of the same LOINC code and compute directional trend data.

**Computed fields** (added as synthetic `_trend` object on each observation):
- `direction`: `"rising"`, `"falling"`, `"stable"` (stable = <5% change)
- `delta`: Absolute change from previous value
- `delta_percent`: Percentage change
- `previous_value`: The prior value for reference
- `previous_date`: When the prior value was recorded
- `timespan_days`: Days between the two measurements

**Example** (added to pruned observation JSON):
```json
{
  "code": "Hemoglobin A1c",
  "valueQuantity": {"value": 7.2, "unit": "%"},
  "effectiveDateTime": "2025-10-14",
  "_trend": {
    "direction": "rising",
    "delta": 0.4,
    "delta_percent": 5.9,
    "previous_value": 6.8,
    "previous_date": "2025-04-20",
    "timespan_days": 177
  }
}
```

**Implementation**: For each Tier 3 observation, query Postgres for the second-most-recent Observation with the same LOINC code and patient. Compute delta. Only applies to numeric `valueQuantity` observations.

### 4. Medication Recency Signals

For each active medication, compute how long the patient has been on it from the `authoredOn` date relative to the compilation date.

**Computed fields** (added as synthetic fields on each MedicationRequest):
- `_recency`: `"new"` (<1 month), `"recent"` (1-6 months), `"established"` (>6 months)
- `_duration_days`: Days since `authoredOn`

**Example** (added to pruned MedicationRequest JSON):
```json
{
  "medication": "Metformin 500 MG",
  "status": "active",
  "authoredOn": "2020-03-15",
  "_recency": "established",
  "_duration_days": 2040
}
```

**Rationale**: A newly prescribed medication is far more clinically relevant than one the patient has been on for years. The agent can prioritize questions about new medications and flag them in summaries.

### 5. Encounter-Inferred Medication Links

For active medications without an explicit `reasonReference` (graph shows ~33% of active meds lack one), infer the clinical connection by traversing: Medication → prescribing Encounter → Conditions diagnosed at that encounter.

**Logic**:
1. For each active medication with no TREATS edge:
2. Follow the PRESCRIBED edge to find the prescribing Encounter.
3. Follow the DIAGNOSED edge from that Encounter to find Conditions.
4. If conditions are found, create an inferred grouping: the medication appears under those conditions in the condition-centric organization, with an `_inferred: true` flag.

**Example**:
```
### Essential Hypertension (active, onset 2018-06-01) [def-456]
Treating medications:
  {pruned MedicationRequest — Lisinopril}
Inferred medications (prescribed at same encounter):
  {pruned MedicationRequest — Hydrochlorothiazide, _inferred: true}
```

**Rationale**: Fills gaps in structured data linkage. Synthea and many real-world EHRs don't consistently populate `reasonReference`. The encounter-based inference is clinically sound — if a medication was prescribed during the same visit where a condition was diagnosed, the link is strongly implied.

## Assembly Order

The compilation pipeline executes in this order:

1. **Build patient orientation** — Fetch Patient resource + patient profile. Template the orientation narrative.
2. **Build Tier 1** — Fetch active conditions, recently resolved conditions, active meds, active allergies, active care plans, all immunizations. For each condition, run generic graph traversal to find connected resources (treating meds, care plans, etc.).
3. **Run encounter-inferred medication links** — For active meds without TREATS edges, traverse to prescribing encounter → diagnosed conditions. Add inferred groupings to Tier 1.
4. **Compute medication recency** — For each active medication, compute `_recency` and `_duration_days` from `authoredOn`.
5. **Build Tier 2** — Fetch last AMB encounter + all encounters within 6 months of compilation date. For each encounter, run generic graph traversal to find linked resources (observations, procedures, conditions, meds, reports).
6. **Fetch latest clinical note** — Find DocumentReference for the last encounter via CREATED_DURING edge. Decode base64 content. Include full text without trimming.
7. **Build Tier 3** — Fetch latest observation per LOINC code per category (vital-signs, laboratory, survey, social-history).
8. **Compute observation trends** — For each Tier 3 observation, fetch previous value of same LOINC code. Compute direction/delta/timespan. Attach `_trend` object.
9. **Deduplicate Tier 3 against Tier 2** by `fhir_id` — only keep observations NOT already present in encounter resources.
10. **Deduplicate Tier 2 against Tier 1** — if a medication appears under a condition (via TREATS) AND under an encounter (via PRESCRIBED), keep it under the condition, skip in the encounter. (Condition-level grouping takes precedence for readability.)
11. **Derive safety constraints** from Tier 1 — allergy alerts, drug interaction flags, clinically significant condition warnings.
12. **Prune all resources** using `_prune_fhir_resource()`.
13. **Serialize** to storage format.

## What the Agent Uses Tools For

Everything NOT in the pre-compiled summary:
- Historical conditions (resolved more than 6 months ago)
- Past medications (completed, stopped, cancelled)
- Full lab trends over time (the summary has latest values with one-step trends; deeper history requires `query_patient_data`)
- Encounters older than the 6-month window
- Procedure history beyond recent encounters
- Diagnostic report deep-dives (full report details, component observations)
- Clinical relationship discovery ("what treats this condition?" for conditions not in the summary)
- Cross-type concept search ("find anything related to kidney function")
- Timeline browsing ("what happened in 2020?")
- Older clinical notes — retrievable via `get_patient_timeline` (with `include_notes: true`), `explore_connections` on an Encounter node, or `query_patient_data` with `resource_type: DocumentReference`. The pre-compiled summary includes only the last encounter's note; all others are accessible on demand.

## Pre-compiled Context Format

```
## Patient Orientation
Aaron697 is a 54-year-old male. He works as a warehouse supervisor, lives alone in a
single-family home, and is motivated by wanting to stay active for his grandchildren.
He has 6 active conditions including Type 2 Diabetes and Essential Hypertension.
His last ambulatory visit was on 2025-10-14.

## Patient Demographics
{pruned Patient resource}

## Active Conditions

### Type 2 Diabetes (active, onset 2020-01-15) [abc-123]
Treating medications:
  {pruned MedicationRequest — Metformin, _recency: "established", _duration_days: 2040}
  {pruned MedicationRequest — Insulin Glargine, _recency: "recent", _duration_days: 90}
Care plans:
  {pruned CarePlan — Diabetes self-management}

### Essential Hypertension (active, onset 2018-06-01) [def-456]
Treating medications:
  {pruned MedicationRequest — Lisinopril, _recency: "established", _duration_days: 1800}
Inferred medications (prescribed at same encounter):
  {pruned MedicationRequest — Hydrochlorothiazide, _inferred: true, _recency: "new", _duration_days: 14}

## Recently Resolved Conditions (last 6 months)
### Acute Bronchitis (resolved 2025-09-14) [ghi-789]
Treating medications:
  {pruned MedicationRequest — Amoxicillin [completed]}

## Medications Not Linked to a Condition
  {pruned MedicationRequest — Aspirin 81mg, _recency: "established", _duration_days: 730}

## Allergies
  None recorded.

## Immunizations
  [{pruned Immunization resources}]

## Last Encounter: 2025-10-14 (AMB) [enc-001]
PRESCRIBED:
  {pruned MedicationRequest}
RECORDED:
  {pruned Observation — Body Weight}
  {pruned Observation — Blood Pressure}
  {pruned Observation — Hemoglobin A1c}
PERFORMED:
  {pruned Procedure — Depression screening}
REPORTED:
  {pruned DiagnosticReport — CBC panel}

### Clinical Note
{full decoded DocumentReference text from this encounter — no trimming}

## Additional Encounters (6-month window)
### 2025-09-30 (AMB) [enc-002]
RECORDED:
  {pruned observations}
...

## Latest Observations (not in encounters above)
Vital Signs:
  {pruned Observation — Body Weight = 85.2 kg (2025-10-14),
    _trend: {direction: "rising", delta: 1.3, previous_value: 83.9, previous_date: "2025-04-20"}}
  {pruned Observation — Blood Pressure systolic = 138 mmHg (2025-10-14),
    _trend: {direction: "stable", delta: -2, previous_value: 140, previous_date: "2025-04-20"}}
Laboratory:
  {pruned Observation — Hemoglobin A1c = 7.2% (2025-10-14),
    _trend: {direction: "rising", delta: 0.4, previous_value: 6.8, previous_date: "2025-04-20"}}
  {pruned observations per LOINC with _trend}
Survey:
  {pruned observations per LOINC}
Social History:
  {pruned observations per LOINC}

## Safety Constraints
- CRITICAL ALLERGY: ...
- ACTIVE MEDICATION: ...
- CONDITION: Patient has Type 2 Diabetes — consider treatment implications
```

## Agent Tools (3 tools)

### 1. `query_patient_data`

**Purpose**: Search for FHIR resources by type and attributes. The "filing cabinet" search.

**Parameters**:
- `resource_type`: `Condition | MedicationRequest | Observation | Procedure | Encounter | DiagnosticReport | CarePlan | Immunization | AllergyIntolerance | DocumentReference` (optional — omit to search all types)
- `name`: Display name search (optional)
- `status`: Status filter, type-appropriate (optional)
- `category`: Observation category filter (optional, Observation-only)
- `date_from`: ISO date range start (optional)
- `date_to`: ISO date range end (optional)
- `include_full_resource`: Return full pruned JSON vs compact summary (default: true)
- `limit`: Max results (default: 20)

**Search strategy**:
1. Primary: Postgres ILIKE matching on display name + attribute filters.
2. Fallback: If < 3 results and `name` was provided, run pgvector semantic search to catch terminology mismatches (e.g., "kidney function" → Creatinine, GFR, BUN).
3. Results labeled by source (exact match vs semantic match) so agent knows confidence level.

**Replaces**: `search_patient_data`, `get_lab_history`

### 2. `explore_connections`

**Purpose**: Given a specific resource, discover what's clinically connected via graph relationships. The "follow the threads" tool.

**Parameters**:
- `fhir_id`: FHIR ID of the resource to explore from
- `resource_type`: Resource type (for node lookup)
- `include_full_resource`: Return full pruned JSON vs compact summary (default: true)
- `max_per_relationship`: Cap results per edge type (default: 10)

**Implementation**: Generic Cypher query that returns ALL edges from the node, filtering out HAS_* ownership edges. Groups results by relationship type. No hard-coded per-relationship branching. When the source node is an Encounter, connected DocumentReferences are included with decoded clinical note text (via CREATED_DURING edge).

**Output format**:
```
Connections for Condition "Type 2 Diabetes" (abc-123):

TREATS (2):
  {pruned MedicationRequest — Metformin}
  {pruned MedicationRequest — Insulin Glargine}
ADDRESSES (1):
  {pruned CarePlan — Diabetes self-management}
DIAGNOSED (1):
  {pruned Encounter — 2020-01-15 Wellness visit}
```

**Replaces**: `find_related_resources`, `get_encounter_details`

### 3. `get_patient_timeline`

**Purpose**: Browse the patient's encounters in a date range with summary of events. The "calendar view" tool.

**Parameters**:
- `start_date`: ISO date range start (optional)
- `end_date`: ISO date range end (optional)
- `include_notes`: Include clinical note text for each encounter (default: false)

**Implementation**: Neo4j encounter query + generic traversal per encounter. When `include_notes` is true, also fetch DocumentReference resources linked to each encounter via CREATED_DURING edge and include decoded note text.

**Replaces**: `get_patient_timeline` (same name, updated implementation)

## Generic Graph Traversal

### New method: `get_all_connections(fhir_id, patient_id)`

Single Cypher query:

```cypher
MATCH (n {fhir_id: $fhir_id, patient_id: $patient_id})-[r]-(m)
WHERE NOT m:Patient
RETURN type(r) as relationship,
       CASE WHEN startNode(r) = n THEN 'outgoing' ELSE 'incoming' END as direction,
       m.fhir_id as fhir_id,
       m.resource_type as resource_type,
       m.name as name
ORDER BY relationship, resource_type
```

- Returns ALL edges regardless of type — no hard-coding.
- Filters out Patient ownership edges (HAS_*).
- Adding a new edge type to the graph schema automatically surfaces it.
- Replaces: `get_medications_treating_condition`, `get_procedures_for_condition`, `get_care_plans_for_condition`, `get_diagnostic_report_results`.

### Shared Compilation Layer

The same core logic powers both batch (pre-compiled) and live (tool) paths:

```python
# Shared building block
async def compile_node_context(fhir_id, patient_id, graph, db):
    """Get all connections from a node, fetch full resources, prune."""
    connections = await graph.get_all_connections(fhir_id, patient_id)
    # Group by edge type
    # Fetch FHIR resources from Postgres by fhir_id
    # Prune each resource
    return grouped_pruned_connections

# Live: tool calls this once
async def explore_connections(fhir_id, ...):
    return await compile_node_context(fhir_id, ...)

# Batch: compiler calls this in a loop
async def compile_patient_summary(patient_id, ...):
    for condition in active_conditions:
        condition.connections = await compile_node_context(condition.fhir_id, ...)
    for encounter in recent_encounters:
        encounter.events = await compile_node_context(encounter.fhir_id, ...)
    # + Tier 3 latest observations, dedup, safety constraints, assemble
```

## Semantic Search Role

Semantic search (pgvector) has a narrow but important role:

- **NOT used in pre-compiled context compilation** — structured queries only.
- **NOT used in `explore_connections`** — pure graph traversal.
- **NOT used in `get_patient_timeline`** — date-range encounter queries.
- **Used inside `query_patient_data`** as automatic fallback when exact matching returns sparse results. Bridges terminology mismatches (user says "kidney function", data has "Creatinine").

## What Exists vs What's Missing

### Exists (reusable)
- FHIR pruner (`_prune_fhir_resource`) — resource-level formatting ✅
- Verified layer queries (active conditions/meds/allergies/immunizations) ✅
- Encounter event traversal (`get_encounter_events`) ✅
- Patient encounters query (`get_patient_encounters`) ✅
- Embedding generation + pgvector search ✅
- Tool-use integration in AgentService (tool rounds, streaming) ✅

### Missing (must build)
- Generic `get_all_connections()` graph method ❌
- Latest-per-LOINC-per-category Postgres query ❌
- Compilation pipeline (orchestrates tiers, deduplicates, assembles) ❌
- Condition-centric organization logic (graph → structure) ❌
- Patient orientation narrative template ❌
- Clinical note fetching + full-text inclusion (no trimming) ❌
- Observation trend computation (previous value lookup + delta calculation) ❌
- Medication recency computation (duration from authoredOn) ❌
- Encounter-inferred medication links (traverse prescribing encounter → diagnosed conditions) ❌
- Storage mechanism for pre-compiled artifact ❌
- System prompt builder for new structured format ❌
- System prompt: absence reporting instructions ❌
- System prompt: cross-condition reasoning guidance ❌
- System prompt: tool-chain self-checking instructions ❌
- System prompt: PCP user context ❌
- Recompilation trigger from seed script ❌
- New tool implementations (query_patient_data, explore_connections) ❌
- Updated get_patient_timeline implementation (with `include_notes` parameter) ❌
- Clinical note retrieval in explore_connections (DocumentReference decoding) ❌
- DocumentReference as searchable type in query_patient_data ❌

## Scope

### In Scope
- Pre-compiled patient summary artifact (generated at seed time, stored persistently)
- Recompilation trigger on data changes (bundle load, seed)
- Remove per-query graph traversal and vector search from context engine
- Generic graph traversal method replacing per-relationship methods
- 3 redesigned agent tools with shared compilation logic
- System prompt restructured for condition-centric + encounter-centric organization
- Semantic search as fallback inside query_patient_data
- Patient orientation narrative (template-based, includes patient profile)
- Full clinical note inclusion from last encounter DocumentReference (no trimming)
- Observation trend computation (direction, delta, timespan)
- Medication recency signals (new/recent/established from authoredOn)
- Encounter-inferred medication links for meds without reasonReference
- Agent reasoning principles: absence reporting, cross-condition reasoning, tool-chain self-checking (system prompt)
- Clinical note retrieval via all three tools (not just pre-compiled context)

### Out of Scope
- Real-time data ingestion pipeline (data changes are batch/seed events)
- Conversation-level context caching (messages, prior tool results)
- Multi-patient context (agent always works with one patient)
- Changes to the frontend or streaming architecture
- SSE streaming events for tool-use (CruxMD-ij0 — separate task)
- Reference range annotations (separate brainstorm — requires LOINC lookup table)

## Open Questions

- **Storage format for pre-compiled summary**: JSON column on patient record? Separate table? File artifact? (Deferred to planning phase)
- **System prompt wording**: Exact instructions for the agent about what it has (summary) vs what it can get (tools). (Deferred to implementation)
- **Clinical note token budget**: Notes vary widely in length. Need to measure actual Synthea DocumentReference sizes to validate the 2,000-5,000 token estimate. If outliers exist, consider a generous but defined cap (not 1,500 chars — something clinically appropriate).

## Related Brainstorms

- **Reference Range Annotations**: Enriching observations with normal/abnormal ranges via LOINC lookup table. Tracked separately — requires sourcing a reference range dataset and defining the lookup mechanism. Would add `_reference_range` synthetic fields to observations alongside the `_trend` fields.

## Risks

- **Agent may over-rely on base context**: Mitigation — system prompt explicitly states the summary is a starting point and guides tool use.
- **Stale summaries**: Mitigation — recompile on every known data mutation path; log warnings if summary age exceeds threshold.
- **Tool round-trip latency**: Mitigation — base context covers the most common needs; tools are for specific drill-downs.
- **Pruned JSON token cost (~20k with enrichments)**: Higher than compact text summaries (~4k) but well within budget (15% of 128k) and gives the agent complete clinical detail.
- **Clinical note size variance**: Some notes may be very long. Mitigation — measure actual sizes in seed data; set a generous clinical cap if needed (not a hard 1,500 char trim).
- **Encounter-inferred medication links may be wrong**: A medication prescribed during the same encounter as a diagnosis isn't guaranteed to treat that diagnosis. Mitigation — flag inferred links explicitly (`_inferred: true`) so the agent treats them as probable, not certain.
- **Trend computation for sparse data**: Some LOINC codes may have only one historical value, making trend computation impossible. Mitigation — omit `_trend` when no previous value exists.

## Data Volume Context

Based on actual queries against the 5 Synthea patients in the current seed data:

| Metric | Value |
|--------|-------|
| Total patients | 5 |
| Total FHIR resources | 3,850 across 19 types |
| Resources per patient | 559 to 1,065 (avg ~770) |
| Active conditions | 39 total (~8/patient) |
| Resolved conditions | 127 total (~25/patient) |
| Active medications | 18 total (~4/patient) |
| Active care plans | 7 total (~1-2/patient) |
| Completed immunizations | 73 total (~15/patient) |
| AllergyIntolerance resources | 0 (absent from Synthea seed data) |
| Encounters per patient | 27-80 (overwhelmingly AMB) |
| Encounters in 6-month window | 1-3 per patient |
| Resources per encounter | 2-41 (median ~17) |
| Encounter classes | AMB: 200, EMER: 8, IMP: 2 |
| Distinct vital-sign LOINC codes | 9 |
| Distinct laboratory LOINC codes | 17 |
| Observation categories | vital-signs: 381, survey: 199, laboratory: 181, social-history: 60 |

**Key finding**: Latest labs for patient 518322f1 span 2017-2023, while the last encounter is Oct 2025. Without Tier 3 (latest observations independent of encounters), the agent would have zero lab data. This validates pulling latest labs/vitals separately from encounter resources.

### Known Bug in Current Code

`graph.py:get_verified_conditions()` filters `clinical_status = 'active'` but misses `recurrence` and `relapse` — both are clinically active states in the FHIR hierarchy. The active filter table in this document specifies the correct values: `IN (active, recurrence, relapse)`.

## Constraints

- Must work with existing OpenAI Responses API (structured output + tool calling)
- Base context must fit comfortably within model context window alongside conversation history
- Recompilation must be fast enough to run in the seed script without significant overhead
- Agent tools must return pruned FHIR JSON the LLM can reason about
- Generic graph traversal must not hard-code relationship types
- All users are primary care physicians — agent tone and reasoning calibrated accordingly

## References

- Li, M.M., Reis, B.Y., Rodman, A. et al. "Scaling medical AI across clinical contexts." *Nature Medicine* (2025). https://doi.org/10.1038/s41591-025-04184-7 — Informed the Agent Reasoning Principles section (absence reporting, cross-condition reasoning, tool-chain self-checking) and validated the agent-driven tool architecture, knowledge graph approach, and pre-compiled context strategy.
