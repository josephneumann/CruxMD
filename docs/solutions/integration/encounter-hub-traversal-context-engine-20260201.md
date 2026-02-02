---
scope: cruxmd
module: context-engine
date: 2026-02-01
problem_type: integration
symptoms:
  - Vector-only retrieval returns isolated resources without visit context
  - Query for "blood pressure" returns observation but not the encounter or related conditions
  - No structured relationship traversal in context assembly
root_cause: incorrect-assumption
severity: medium
tags:
  - fhir-graph
  - encounter-hub
  - hybrid-retrieval
  - knowledge-graph
  - context-engine
  - neo4j
---

# Encounter Hub Traversal Pattern for Context Assembly

## Symptom

The ContextEngine used vector search (pgvector) as the sole retrieval path. Queries returned semantically similar FHIR resources but without visit context — asking about "blood pressure" returned the Observation but not the Encounter it happened in, the Conditions diagnosed during that visit, or the Medications prescribed.

## Investigation

Considered several approaches:

1. **Use `extract_concepts()` from query_parser** to match query terms against known graph node names, then pass results to `search_nodes_by_name()`. Rejected: `search_nodes_by_name` already does case-insensitive substring matching in Cypher, making `extract_concepts` redundant. Would also need an extra graph query to fetch node display names.

2. **Full reverse traversal from every matched node** (e.g., Observation → DiagnosticReport, MedicationRequest → Condition it treats). Rejected: too many paths, risk of pulling large portions of the graph. Deferred for later if gaps appear.

3. **Encounter as hub node** — traverse matched nodes to their parent Encounter, then load all sibling resources. Chosen: Encounter is the natural clinical grouping in FHIR. Most resources link via `encounter.reference`. One hop up to Encounter + one hop out to siblings gives full visit context in 2 hops.

## Root Cause

The original design treated retrieval as purely semantic similarity. FHIR data has explicit structural relationships (Encounter → Condition, Encounter → Observation, etc.) that provide clinically meaningful context groupings. Vector search can't leverage these relationships.

## Solution

**Pattern: Matched Node → Parent Encounter → Encounter Events**

Flow in `_build_graph_traversal_layer()`:

1. Tokenize query with `tokenize()` + `remove_stop_words()` from `query_parser`
2. Pass terms to `graph.search_nodes_by_name(patient_id, terms)` — searches all 7 resource types via Cypher substring matching
3. Collect unique `encounter_fhir_id` values from matched nodes (added to `search_nodes_by_name` return to avoid extra queries)
4. For each encounter, call `graph.get_encounter_events(enc_fhir_id)` — returns conditions, medications, observations, procedures, diagnostic reports
5. Deduplicate by `fhir_id` across encounters
6. Return as `RetrievedResource` list with `reason="graph_traversal"`

`build_context()` orchestration:

1. Verified layer (unchanged — active conditions/meds/allergies)
2. Graph traversal (primary retrieval)
3. Vector search (supplemental discovery)
4. Deduplicate: graph wins over vector for same `fhir_id`
5. Merge into `RetrievedLayer`, graph resources first

Key code: `context_engine.py:_build_graph_traversal_layer()`, `graph.py:search_nodes_by_name()`

## Prevention

- **When adding new resource types to the graph**: update the `searchable` list in `search_nodes_by_name` and the event mapping in `_build_graph_traversal_layer`
- **Avoid unbounded traversal**: always scope to patient, use encounter as the boundary. Don't traverse more than 2 hops without explicit justification.
- **N+1 awareness**: current implementation makes one `get_encounter_events()` call per encounter (sequential). Acceptable for typical result sets (<20 encounters). If latency becomes an issue, batch into a single Cypher query with `WHERE e.fhir_id IN $ids`.
- **Parallelization opportunity**: `_build_graph_traversal_layer` and `_build_retrieved_layer` have no data dependencies and could run with `asyncio.gather()`.
- **Orphan resources**: nodes without `encounter_fhir_id` are silently skipped. If this matters, add a graph method to hydrate FHIR resources by `fhir_id`.

## Related

- Plan: `docs/plans/2026-01-31-feat-agent-data-access-redesign-plan.md` (Task 4)
- Plan: `docs/plans/2026-02-01-feat-expand-knowledge-graph-plan.md` (encounter bug fix, new node types)
- Downstream: `CruxMD-4gh` — lower vector threshold + dedup helper
