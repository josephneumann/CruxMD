# Brainstorm: Pre-compiled Base Context + Agent-Driven Search

**Date**: 2026-02-01
**Status**: Ready for planning

## Problem Statement

Today, every user message triggers a full retrieval pipeline: verified layer from Neo4j, graph traversal with synonym expansion, and pgvector semantic search. This is expensive, slow, and the pre-retrieval often guesses wrong about what the agent needs. Meanwhile, the agent already has tools for on-demand search but receives a pre-fetched context dump that may not match the user's actual intent.

The architecture should separate **what the agent always needs** (stable patient facts) from **what the agent discovers on demand** (query-specific clinical data).

## Proposed Solution

**Pre-compiled Patient Summary**: Generate a structured base context at seed time (and on any data update) containing everything an agent needs to orient to a patient. This loads instantly on every query with zero retrieval cost.

**Agent-Driven Search**: Remove the per-query retrieval pipeline (graph traversal + vector search). The agent decides what additional data it needs based on conversation context and calls existing tools to fetch it. Graph traversal is used *internally* by tools (e.g., `search_patient_data`, `find_related_resources`), not exposed as a standalone tool.

## Key Decisions

- **Pre-compile at seed time, recompile on data changes**: Since this is a demo platform with controlled data loads, recompilation is triggered by known events (seed script, bundle loads). No cache infrastructure needed.
- **Full last encounter in base context**: Include all observations, procedures, diagnostics from the most recent encounter — gives the agent a complete clinical snapshot without tool calls.
- **Agent always decides what to search**: No pre-fetching based on query patterns. The agent is guided via system prompt to proactively search when needed. Simpler architecture, agent has full control.
- **Graph traversal is internal to tools, not a standalone tool**: Existing tools already use graph traversal internally (e.g., `search_patient_data` does concept extraction + graph search + vector search). The agent calls high-level tools; graph traversal is an implementation detail.

## Base Context Contents

The pre-compiled patient summary includes:

1. **Patient demographics** (name, DOB, gender, ID)
2. **Patient profile summary** (occupation, living situation, motivation — from generated profiles)
3. **Active conditions** with onset dates
4. **Active medications** with status
5. **Known allergies** with criticality
6. **Completed immunizations**
7. **Safety constraints** derived from verified facts (drug allergies, active meds, clinically-significant conditions)
8. **Last encounter full context** (all observations, procedures, diagnostics, medications from most recent visit)

## Scope

### In Scope
- Pre-compiled patient summary artifact (generated at seed time, stored persistently)
- Recompilation trigger on data changes (bundle load, seed)
- Remove per-query graph traversal and vector search from context engine
- System prompt restructured to present base context and guide agent to use tools
- Existing tools (search_patient_data, get_lab_history, find_related_resources, get_encounter_details, get_patient_timeline) remain available and use graph traversal internally

### Out of Scope
- Real-time data ingestion pipeline (data changes are batch/seed events)
- Conversation-level context caching (messages, prior tool results)
- Multi-patient context (agent always works with one patient)
- Changes to the frontend or streaming architecture

## Open Questions

- **Storage format for pre-compiled summary**: JSON column on patient record? Separate table? File artifact?
- **How to represent "last encounter"**: Most recent by date? Most recent by type (e.g., skip phone calls)?
- **Token budget for base context**: How much of the context window should the summary consume? Need to leave room for conversation history and tool results.
- **System prompt design**: How to instruct the agent about what it has (summary) vs what it can get (tools) — critical for good tool-use behavior.

## Diff Against Existing Plan

Reference: `docs/plans/2026-01-31-feat-agent-data-access-redesign-plan.md`

Phase 1 of that plan (Tasks 1-5) is **complete** — graph-centric context assembly, query parsing, synonym expansion, and graph traversal in the context engine are all implemented and working.

Phase 2 (Tasks 6-7) is **complete** — agent tools exist (`agent_tools.py`) and tool-use is integrated into `AgentService`. The 5 tools (`search_patient_data`, `get_encounter_details`, `get_lab_history`, `find_related_resources`, `get_patient_timeline`) already use graph traversal internally.

Phase 2 Task 8 (CruxMD-ij0) is **open** — SSE streaming events for tool-use. This brainstorm does not affect it.

**What this brainstorm changes vs the existing plan:**

| Aspect | Existing plan | This brainstorm |
|--------|--------------|-----------------|
| Per-query retrieval | Graph traversal + vector search runs on every message as pre-fetch | **Removed**. No pre-fetch on messages. |
| Base context | Built fresh per-query from verified layer | **Pre-compiled** at seed time, loaded instantly |
| Tools role | Supplemental — agent can fetch more beyond pre-fetched context | **Primary** — tools are the only path for query-specific data |
| Last encounter | Not in base context | **Included** with full visit details |
| Context engine | Central orchestrator of retrieval pipeline | Simplified to loading pre-compiled summary |

**What stays the same:**
- All 5 agent tools and their implementations
- Tool-use integration in AgentService (tool rounds, streaming)
- Graph traversal as internal implementation of tools
- Safety constraints derived from verified facts
- SSE streaming architecture

## Constraints

- Must work with existing OpenAI Responses API (structured output + tool calling)
- Base context must fit comfortably within model context window alongside conversation history
- Recompilation must be fast enough to run in the seed script without significant overhead
- Agent tools must return results in a format the LLM can reason about

## Risks

- **Agent may over-rely on base context**: If the summary is too comprehensive, the agent might not call tools when it should. Mitigation: system prompt explicitly states the summary is a starting point.
- **Stale summaries**: If recompilation pipeline misses a data change, agent works with outdated info. Mitigation: recompile on every known data mutation path; log warnings if summary age exceeds threshold.
- **Tool round-trip latency**: Agent needs an extra API round-trip for every tool call. Mitigation: base context covers the most common needs; tools are for specific drill-downs.
