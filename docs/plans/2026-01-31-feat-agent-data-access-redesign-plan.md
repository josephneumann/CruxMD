---
title: "feat: Agent data access redesign — graph-centric context + tool-use"
type: feat
date: 2026-01-31
---

# Agent Data Access Redesign

## Overview

Two-phase redesign of how the CruxMD agent accesses patient data. Phase 1 makes the context engine query-adaptive using graph traversal. Phase 2 gives the agent tools to dynamically fetch data mid-reasoning.

Brainstorm: `docs/brainstorms/2026-01-31-agent-data-access-redesign-brainstorm.md`

## Problem Statement

The agent currently gets demographics + active conditions/meds/allergies from the graph, and nearly nothing from vector search (0.7 threshold, real scores are 0.5). All 832 Observations, 210 Encounters, 371 DiagnosticReports, 820 Procedures are invisible. The knowledge graph has rich traversal methods (`get_encounter_events`, `get_medications_treating_condition`, etc.) that the context engine never calls.

## Architecture Decisions

1. **Concept extraction starts simple**: keyword/fuzzy matching against graph node `display` properties. No LLM-based extraction in Phase 1.
2. **Graph traversal returns parsed FHIR**: Existing traversal methods return raw node dicts — must return `json.loads(node["fhir_resource"])` for consistency with verified layer.
3. **New `graph_traversal` reason on RetrievedResource**: Distinguishes graph-retrieved from vector-retrieved.
4. **Vector threshold drops to 0.4**: Simple config change.
5. **Phase 2 uses OpenAI Responses API `tools` parameter**: Function definitions alongside structured output. Agent loop handles tool calls.

## Phase 1: Graph-Centric Context Assembly

### Task 1: Graph node search + fix traversal return types

Add `search_nodes_by_name(patient_id, query_terms, resource_types)` to `KnowledgeGraph` — fuzzy matches node `display` properties against query terms. Returns matched `fhir_id` + `resource_type` pairs. Fix existing traversal methods to return parsed FHIR resources.

**Files**: `backend/app/services/graph.py`, `backend/tests/test_graph.py`
**Depends on**: Nothing

### Task 2: Query concept extraction module

Create `query_parser.py` — tokenize query, remove stop words, match tokens/bigrams against graph node display names. Returns `ConceptMatch(term, resource_type_hint)` list.

**Files**: `backend/app/services/query_parser.py`, `backend/tests/test_query_parser.py`
**Depends on**: Nothing

### Task 3: Context schema extensions

Extend `RetrievedResource.reason` Literal to include `"graph_traversal"`. Add `graph_traversal_count` to `RetrievalStats`.

**Files**: `backend/app/schemas/context.py`, tests
**Depends on**: Nothing

### Task 4: Redesign `ContextEngine.build_context()` for graph-centric retrieval

Core Phase 1 task. Modify `build_context()` to:
1. Call query parser to extract concepts
2. Call `graph.search_nodes_by_name()` to find matching nodes
3. Traverse 1-2 hops from matched nodes via existing graph methods
4. Merge into `RetrievedLayer` with `reason="graph_traversal"`
5. Run vector search (threshold 0.4) for supplemental discovery
6. Deduplicate (same `fhir_id` from both graph and vector)
7. Verified layer unchanged

**Files**: `backend/app/services/context_engine.py`, `backend/tests/test_context_engine.py`
**Depends on**: Tasks 1, 2, 3

### Task 5: Lower vector threshold + dedup helper

Change `DEFAULT_SIMILARITY_THRESHOLD` from 0.7 to 0.4. Add dedup logic to prevent vector results duplicating graph-traversed resources.

**Files**: `backend/app/services/context_engine.py`, tests
**Depends on**: Task 4

## Phase 2: Agent Tool-Use (Function Calling)

### Task 6: Agent tool schemas and implementations

Create `agent_tools.py` with 5 tools wrapping graph/Postgres:
- `search_patient_data(query)` — concept extraction + graph search + vector
- `get_encounter_details(encounter_id)` — `graph.get_encounter_events()`
- `get_lab_history(lab_name, limit)` — Observations by name, ordered by date
- `find_related_resources(resource_id)` — graph traversal from node
- `get_patient_timeline(start_date, end_date)` — encounters in date range

Each returns formatted text for LLM consumption (not raw FHIR).

**Files**: `backend/app/services/agent_tools.py`, `backend/tests/test_agent_tools.py`
**Depends on**: Task 1

### Task 7: Integrate tool-use into AgentService

Add tool execution loop to `generate_response()` and `generate_response_stream()`:
1. Pass `tools` to OpenAI Responses API
2. Detect `function_call` in output
3. Execute tool, feed result back, continue generation
4. Handle multi-turn tool calls
5. Update system prompt to describe tools

**Files**: `backend/app/services/agent.py`, `backend/tests/test_agent.py`
**Depends on**: Task 6

### Task 8: SSE streaming events for tool-use

Emit `tool_call` and `tool_result` SSE events during streaming so frontend can show the agent's data-fetching activity.

**Files**: `backend/app/routes/chat.py`, tests
**Depends on**: Task 7, streaming epic (CruxMD-3f0) complete

## Dependency Graph

```
Phase 1:
  Task 1 (graph search) ──┐
  Task 2 (query parser) ──┼──> Task 4 (context engine) ──> Task 5 (threshold)
  Task 3 (schema)       ──┘

Phase 2:
  Task 1 ──> Task 6 (tool defs) ──> Task 7 (agent integration) ──> Task 8 (SSE)
```

Tasks 1, 2, 3 are fully parallel. Task 6 can start once Task 1 is done (parallel with 4-5).

## Acceptance Criteria

- [ ] User asks "What were the last lab results?" → agent sees relevant Observations and DiagnosticReports
- [ ] User asks "Tell me about recent encounters" → agent sees Encounter resources with associated events
- [ ] Vector search returns results at 0.4 threshold as supplemental discovery
- [ ] Graph-traversed resources are labeled distinctly from vector-retrieved
- [ ] Agent can call tools mid-reasoning to fetch additional data (Phase 2)
- [ ] SSE stream emits tool_call/tool_result events (Phase 2)
- [ ] All existing tests pass

## References

- Knowledge graph: `backend/app/services/graph.py`
- Context engine: `backend/app/services/context_engine.py`
- Agent service: `backend/app/services/agent.py`
- Embedding templates: `backend/app/services/embeddings.py`
- Vector search: `backend/app/services/vector_search.py`
- Context schemas: `backend/app/schemas/context.py`
