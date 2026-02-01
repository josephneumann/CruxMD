# Brainstorm: Agent Data Access Redesign

**Date**: 2026-01-31
**Status**: Ready for planning

## Problem Statement

The chat agent currently receives a minimal static context snapshot: demographics, active conditions, medications, and allergies from the Neo4j graph. Vector search (pgvector) is supposed to supplement this with query-relevant resources, but the 0.7 similarity threshold filters out nearly everything — real similarity scores for clinical queries land in the 0.5 range.

Despite having 2,799 embedded FHIR resources in Postgres (832 Observations, 371 DiagnosticReports, 210 Encounters, 820 Procedures) and a rich knowledge graph with encounter-centric relationships (`DIAGNOSED`, `PRESCRIBED`, `RECORDED`, `REPORTED`), the agent never sees labs, encounters, procedures, or diagnostic reports.

The agent also has no ability to dynamically query for more data mid-response. It gets one context snapshot and must answer from that alone.

## Root Causes

1. **Verified layer too narrow**: `ContextEngine._build_verified_layer()` only calls `get_verified_conditions()`, `get_verified_medications()`, `get_verified_allergies()`. The graph has Encounters, Observations, Procedures, DiagnosticReports with full relationship edges — but they're never queried.

2. **Vector search threshold too high**: Production threshold is 0.7, but actual similarity scores for clinical queries are 0.5-0.53. "hemoglobin A1c" returns zero results even at 0.5.

3. **Embedding text templates are generic**: Templates produce text like `"Observation: Protocol for Responding to..."` without actual clinical values, making semantic matching weak.

4. **No dynamic retrieval**: Agent cannot go back and query for more data mid-reasoning. Single-shot context assembly only.

## Proposed Solution

**Phased Approach A: Graph-Centric Context + Agent Tools**

### Phase 1: Smart Graph-Based Context Assembly

Redesign context assembly to use the knowledge graph as the primary retrieval engine, query-adapted per request.

**How it works:**
1. Parse the user's query to identify clinical concepts (condition names, lab types, med names, temporal references)
2. Match those concepts to graph nodes (fuzzy match on node display names / SNOMED codes)
3. Traverse 1-2 hops from matched nodes — pull connected encounters, labs, meds, procedures via existing graph edges
4. Always include the baseline verified layer (active conditions, meds, allergies)
5. Vector search supplements with semantically related resources the graph traversal didn't connect

**Example:** User asks "What were the results of the last metabolic panel?"
1. Concept extraction: "metabolic panel" → DiagnosticReport / Observation
2. Graph match: Find DiagnosticReport nodes matching "metabolic panel"
3. Traverse: Pull the Encounter it was `REPORTED` in, all Observations it `CONTAINS_RESULT`, the Conditions `DIAGNOSED` in that encounter
4. Baseline: Still include active conditions/meds/allergies
5. Vector fallback: Search for semantically similar Observations that weren't graph-connected

### Phase 2: Agent Tool-Use (Function Calling)

Give the agent tools to dynamically query the knowledge graph and Postgres mid-reasoning via OpenAI Responses API function calling.

**Tools to implement:**
- `search_patient_data(query: str)` — Semantic + graph search for a clinical concept
- `get_encounter_details(encounter_id: str)` — Full encounter with all associated resources
- `get_lab_history(lab_name: str, limit: int)` — Historical lab values for trending
- `find_related_resources(resource_id: str)` — Graph traversal from a specific resource
- `get_patient_timeline(start_date?, end_date?)` — Chronological view of encounters

**Agent decides** when static context isn't sufficient and calls tools mid-reasoning. This is the core "intelligent agent" differentiator for demos.

## Key Decisions

- **Graph-first retrieval**: Knowledge graph is primary retrieval, not vector search. Graph gives structured, relationship-aware clinical facts. Vector search is for discovery/fuzzy matching.
- **Query-adaptive context**: What gets pulled depends on the question — not a fixed set of resource types.
- **Phased delivery**: Phase 1 (graph context) ships first, Phase 2 (tool-use) follows. Phase 1 alone is a major improvement.
- **Keep vector search**: Don't remove it — it's useful for discovery of resources the graph doesn't directly connect. But lower the threshold and improve templates.

## Scope

### In Scope
- Redesign `ContextEngine.build_context()` for graph-traversal-based retrieval
- Query concept extraction (can start simple — keyword/entity matching)
- Graph traversal queries (1-2 hops from matched nodes)
- Lower vector search threshold + improve embedding templates
- Agent tool definitions and function calling integration
- Update system prompt to explain available tools

### Out of Scope
- Multi-agent orchestration (single agent with tools is sufficient)
- Real-time data ingestion (still using Synthea fixtures)
- FHIR API endpoints for external systems
- Graph schema changes (existing edges are sufficient)

## Open Questions

- How to handle concept extraction from free-text queries? Simple keyword matching vs. LLM-based extraction vs. embedding-based node matching?
- Token budget management when graph traversal returns many connected resources — how aggressively to trim?
- Should tool-use results be cached within a conversation to avoid re-querying the same data?
- How does tool-use interact with streaming? (Tool calls pause the stream, results resume it)

## Constraints

- Must work with existing Neo4j graph schema (no new edge types needed — existing relationships cover the use cases)
- Must work with OpenAI Responses API function calling (not Assistants API)
- Token budget still applies — can't send unlimited context
- Streaming SSE pipeline (being built now) must accommodate tool-use pauses

## Risks

- **Concept extraction quality**: If query parsing is bad, graph traversal starts from wrong nodes. Mitigation: Start with simple keyword matching, iterate.
- **Tool-use latency**: Each tool call adds a round-trip. Mitigation: Rich initial context reduces need for tool calls; tools are for edge cases.
- **Token explosion**: Graph traversal could surface too many resources. Mitigation: Token budget trimming already exists; rank by relevance to query.
