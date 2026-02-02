---
title: "feat: Expand knowledge graph — properties, bug fix, new node types"
type: feat
date: 2026-02-01
---

# Expand Knowledge Graph

## Overview

Audit of the FHIR fixtures against the Neo4j knowledge graph revealed missing node properties, a bug (Encounter nodes don't store `fhir_resource`), and two clinically relevant resource types not yet represented as graph nodes. This epic closes those gaps to improve agent query quality.

## Problem Statement

1. **Encounter `fhir_resource` bug**: Every node type stores `fhir_resource = json.dumps(resource)` except Encounter. Traversal methods calling `json.loads(node['fhir_resource'])` return None for Encounters, breaking the "matched node → parent Encounter → events" retrieval pattern being built in CruxMD-md2.

2. **Missing node properties**: The graph extracts a subset of FHIR fields onto node properties, but key clinical fields are absent:
   - `Observation.category` (vital-signs, laboratory, survey, etc.) — needed for filtering
   - `Encounter.reasonCode` (why the visit happened) — currently only `type_display` is stored
   - `Condition.abatementDateTime` (when a condition resolved) — only `onset_date` exists

3. **Missing node types**: 73 Immunization and 13 CarePlan resources in fixtures are not represented in the graph, making vaccine history and treatment plan queries impossible.

## Architecture Decisions

1. **Encounter `fhir_resource` is a bug fix, not a feature** — add `e.fhir_resource = $fhir_resource` to `_upsert_encounter`. One-line change.

2. **Property additions are backward-compatible** — Neo4j is schemaless. New properties default to NULL on existing nodes. Re-seeding rebuilds the graph from FHIR bundles, populating all properties.

3. **Migration strategy: re-seed** — No incremental migration. Run `seed_database` which calls `clear_patient_graph()` + `build_from_fhir()` per patient. This is how the demo dataset works.

4. **Immunization is a verified fact** — like AllergyIntolerance, immunizations are factual clinical records. Add to VerifiedLayer with a `get_verified_immunizations()` method.

5. **CarePlan is retrieved context** — too verbose for default verified layer. Included via graph traversal (RetrievedLayer) when relevant to the query.

6. **Store first value for multi-valued fields** — `Observation.category` stores first category code (matches `AllergyIntolerance.category` pattern). `Encounter.reasonCode` stores first display text.

7. **search_nodes_by_name includes Immunization** — searchable by `display` (vaccine name). CarePlan excluded (no good display property for substring search).

8. **REASON_FOR_VISIT edge deferred** — the `reason_display` property on Encounter is sufficient for now. Edge requires code-matching logic that's fragile with Synthea data. Can add later if traversal from Encounter → reason Condition is needed.

## Tasks

### Task 1: Fix Encounter fhir_resource bug (P1)

Add `fhir_resource` storage to `_upsert_encounter` in `graph.py`. This is a one-line SET clause addition plus passing `fhir_resource=json.dumps(resource)` as a parameter.

**Files**: `backend/app/services/graph.py`, `backend/tests/test_graph.py`
**Depends on**: Nothing
**Acceptance**:
- Encounter node has `fhir_resource` property after upsert
- `json.loads(encounter_node['fhir_resource'])` returns valid FHIR Encounter
- Existing traversal methods work with Encounter nodes

### Task 2: Add missing properties to existing node types (P1)

Add properties to three existing node types:

**Observation**: Add `category` property (first category code, e.g., "vital-signs", "laboratory")
**Encounter**: Add `reason_display` and `reason_code` properties from `reasonCode[0]`
**Condition**: Add `abatement_date` property from `abatementDateTime`

**Files**: `backend/app/services/graph.py`, `backend/tests/test_graph.py`
**Depends on**: Nothing
**Acceptance**:
- Observation nodes have `category` property populated from FHIR `category[0].coding[0].code`
- Encounter nodes have `reason_display` from `reasonCode[0].coding[0].display` and `reason_code` from `reasonCode[0].coding[0].code`
- Condition nodes have `abatement_date` from `abatementDateTime`
- Properties are NULL when source data is absent (no errors)
- Tests verify property extraction for present and absent values

### Task 3: Add Immunization node type (P1)

Add Immunization as a graph node type with full integration:

1. `_upsert_immunization()` method — extract `vaccineCode` coding, status, `occurrenceDateTime`, `encounter_fhir_id`, store `fhir_resource`
2. Add to `_ENCOUNTER_RELATIONSHIPS`: `("Immunization", "HAS_IMMUNIZATION", "ADMINISTERED", "im")`
3. Add unique constraint on `Immunization.fhir_id` + index on `encounter_fhir_id` in `ensure_indexes()`
4. Add dispatch case in `build_from_fhir()`
5. Add to `search_nodes_by_name` searchable list: `("Immunization", "HAS_IMMUNIZATION", "display")`
6. Add `get_verified_immunizations()` query method (status = "completed")
7. Add `immunizations` field to `VerifiedLayer` schema

**Files**: `backend/app/services/graph.py`, `backend/app/schemas/context.py`, `backend/tests/test_graph.py`, `backend/tests/conftest.py`
**Depends on**: Nothing
**Acceptance**:
- Immunization nodes created with correct properties from FHIR bundle
- `Patient -[:HAS_IMMUNIZATION]-> Immunization` relationship exists
- `Encounter -[:ADMINISTERED]-> Immunization` relationship exists
- `search_nodes_by_name("covid")` finds Immunization nodes by vaccine name
- `get_verified_immunizations()` returns parsed FHIR for completed immunizations
- VerifiedLayer includes immunizations list

### Task 4: Add CarePlan node type (P2)

Add CarePlan as a graph node type with clinical reasoning edges:

1. `_upsert_careplan()` method — extract `title` or first `category` display as display property, status, period, `encounter_fhir_id` if present, store `fhir_resource`. Extract `addresses` references as `addresses_fhir_ids` (list of Condition fhir_ids).
2. Add unique constraint on `CarePlan.fhir_id` in `ensure_indexes()`
3. Add dispatch case in `build_from_fhir()`
4. Add clinical reasoning relationship: `CarePlan -[:ADDRESSES]-> Condition` (using `addresses` references, UNWIND pattern matching Condition.fhir_id)
5. **Do not** add to `search_nodes_by_name` (no good searchable display property)
6. **Do not** add to VerifiedLayer (retrieved via traversal only)

**Files**: `backend/app/services/graph.py`, `backend/tests/test_graph.py`, `backend/tests/conftest.py`
**Depends on**: Nothing
**Acceptance**:
- CarePlan nodes created with correct properties from FHIR bundle
- `Patient -[:HAS_CARE_PLAN]-> CarePlan` relationship exists
- `CarePlan -[:ADDRESSES]-> Condition` relationship exists (for CarePlans with `addresses` references)
- Properties are populated correctly including status and period

### Task 5: Re-seed database and verify (P1)

After all graph changes are merged, re-seed the database to rebuild the graph with new properties and node types. Verify counts match expectations.

**Commands**: `uv run python -m app.scripts.seed_database`
**Depends on**: Tasks 1-4
**Acceptance**:
- All Encounter nodes have `fhir_resource` populated
- Observation.category populated on 832 nodes (381 vital-signs, 181 laboratory, etc.)
- Encounter.reason_display populated on 118 nodes
- Condition.abatement_date populated on 127 nodes
- 73 Immunization nodes created with Encounter relationships
- 13 CarePlan nodes created with Condition ADDRESSES relationships
- All existing tests pass

## Dependency Graph

```
Task 1 (Encounter fhir_resource) ──┐
Task 2 (node properties)         ──┤
Task 3 (Immunization)            ──┼──> Task 5 (re-seed & verify)
Task 4 (CarePlan)                ──┘
```

Tasks 1-4 are fully parallel. Task 5 runs after all are merged.

## Interaction with In-Flight Work

- **CruxMD-md2** (ContextEngine redesign): Currently being implemented. Uses `graph.search_nodes_by_name()` and traversal methods. The Encounter `fhir_resource` bug (Task 1) affects it — if md2 tries to include Encounter data in traversal results, it will get None. The worker should be notified. Tasks 2-4 are additive and won't conflict.
- **CruxMD-4wt** (agent tools): Creates tool wrappers around graph methods. No conflict — new properties and node types are transparent to existing tool schemas.

## References

- Knowledge graph: `backend/app/services/graph.py`
- Context schemas: `backend/app/schemas/context.py`
- Graph tests: `backend/tests/test_graph.py`
- Test fixtures: `backend/tests/conftest.py`
- FHIR loader: `backend/app/services/fhir_loader.py`
- Seed script: `backend/app/scripts/seed_database.py`
- Agent data access plan: `docs/plans/2026-01-31-feat-agent-data-access-redesign-plan.md`
