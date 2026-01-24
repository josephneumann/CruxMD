# CruxMD v2: Medical Context Engine

## Project Planning Document

**Version:** 2.1
**Date:** January 2025
**Status:** Planning (Ready for Implementation)

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Background & Lessons Learned](#background--lessons-learned)
3. [Vision & Goals](#vision--goals)
4. [Design Philosophy & Principles](#design-philosophy--principles)
5. [Technical Risks & Mitigations](#technical-risks--mitigations)
6. [Demo Scale Definition](#demo-scale-definition)
7. [Cost Estimation](#cost-estimation)
8. [Architecture Overview](#architecture-overview)
9. [Infrastructure & Hosting](#infrastructure--hosting)
10. [Data Layer Design](#data-layer-design)
11. [Knowledge Graph Architecture](#knowledge-graph-architecture)
12. [FHIR-Native Query Patterns](#fhir-native-query-patterns)
13. [Authentication](#authentication)
14. [Security Beyond API Key](#security-beyond-api-key)
15. [Backup and Recovery Strategy](#backup-and-recovery-strategy)
16. [Medical Disclaimer Strategy](#medical-disclaimer-strategy)
17. [Frontend Error States](#frontend-error-states)
18. [DataQuery Resolution](#dataquery-resolution)
19. [Scaling Contingency](#scaling-contingency)
20. [Frontend Architecture: Conversational Canvas](#frontend-architecture-conversational-canvas)
21. [Agent Response Schema](#agent-response-schema)
22. [Component Catalog](#component-catalog)
23. [Context Engine](#context-engine)
24. [API Design](#api-design)
25. [Testing Strategy](#testing-strategy)
26. [Synthetic Patient Profiles](#synthetic-patient-profiles)
27. [Synthetic Clinical Notes (P2)](#synthetic-clinical-notes-p2)
28. [Project Structure](#project-structure)
29. [Implementation Phases](#implementation-phases)
30. [Technical Specifications](#technical-specifications)
31. [P4: Semantic Memory Layer](#p4-semantic-memory-layer)
32. [P4: LLM-Based Data Ingestion](#p4-llm-based-data-ingestion)
33. [Open Questions](#open-questions)

---

## Executive Summary

CruxMD v2 is a **Medical Context Engine** - an LLM-native platform for clinical intelligence demos. Unlike traditional CRUD applications with bolted-on chat features, this is an **agent-first** system where the LLM is the core brain of every interaction.

**Primary Use Cases:**
- Chat with individual patient data
- Clinical reasoning and decision support demos
- Semantic search over healthcare records
- Knowledge graph traversal for precise clinical facts
- Patient cohort analysis (future)

**Key Differentiators from v1:**
- FHIR-native data layer (no heavy normalization)
- Hybrid retrieval: Vector search + Knowledge Graph (Neo4j)
- Conversational Canvas UI (emergent navigation)
- 90% reduction in codebase complexity
- Single VPS deployment (no CI/CD complexity)
- Fixture-based testing (deterministic, fast)

---

## Background & Lessons Learned

### What Went Wrong in v1

#### 1. Over-Normalized FHIR Schema
- Built **47 flattened tables** with ~7,000 lines of processing code
- `fhir_models.py` (1,397 lines), `fhir_flattener.py` (2,354 lines), `fhir_serialization.py` (2,693 lines)
- Every new FHIR resource type required touching 3+ files, writing migrations, updating serialization
- Enterprise-grade EHR architecture for what was essentially a research/demo platform

#### 2. Two-Phase Ingestion Pipeline
- Raw → Flattened pipeline added unnecessary complexity
- Maintained two data representations for data that didn't need sub-millisecond query performance

#### 3. Frontend Aesthetic Over Function
- CRT monitor effect was visually interesting but:
  - Custom animations were brittle
  - Text streaming added state complexity
  - Every UI change required fighting the aesthetic
  - Not building a consumer product—needed a workbench

#### 4. Deployment Complexity
- Cloud Run (2 services) + Neon PostgreSQL + GitHub Actions (5+ workflows)
- Many failure modes when CI breaks
- Debugging infrastructure instead of building features

#### 5. Feature Sprawl
- Document generator, embedding worker, synthea integration, email verification, password reset
- Many 60%-complete features competing for attention

### What to Preserve
- Synthea integration concepts (but simplify)
- Basic FHIR validation logic (lightweight)
- Understanding of FHIR data structures

---

## Vision & Goals

### Vision Statement
Build an **LLM-native medical context engine** where clinical intelligence emerges from conversation, not predefined screens. The interface adapts to clinical questions, surfacing relevant data, insights, and actions dynamically.

### Goals

| Priority | Goal | Success Metric |
|----------|------|----------------|
| P0 | Chat with single patient data | Working demo |
| P0 | Simple deployment | `git pull && docker compose up` |
| P0 | Load Synthea bundles | 5 patients loaded, queryable |
| P1 | Semantic search over patient records | Relevant results for clinical queries |
| P1 | Structured clinical insights | LLM generates typed response schema |
| P1 | Knowledge Graph for verified facts | Graph populated during ingestion |
| P2 | Lab results visualization | Charts render from FHIR data |
| P2 | Medication analysis | Drug interactions, timeline |
| P2 | Synthetic clinical notes | Progress notes, imaging reports searchable |
| P3 | Knowledge graph visualization | Patient data as interactive graph |
| P3 | Conversation persistence | Sessions stored and retrievable |
| P4 | Semantic Memory Layer | Cross-session insights, derived observations |
| P4 | LLM-based data ingestion | Extract FHIR from free text |
| P5 | Medical ontology integration | UMLS/SNOMED/LOINC grounding |
| P5 | Multi-patient queries | Cohort analysis |

### Non-Goals (For Now)
- Multi-user authentication system
- Email verification / password reset
- Production-scale performance
- Mobile-responsive design
- HIPAA compliance (synthetic data only)

---

## Design Philosophy & Principles

This section captures the **intent** behind our architectural decisions. When facing ambiguous choices during implementation, these principles should guide decision-making.

### Core Philosophy: The LLM as Operating System

Traditional applications treat AI as a feature—a chatbot sidebar, a summarization button, an autocomplete. CruxMD v2 inverts this: **the LLM is the operating system, and the UI is just a rendering layer for its outputs.**

This means:
- The LLM decides what information is relevant, not predefined screens
- Navigation emerges from conversation, not from menu hierarchies
- The interface adapts to the clinical question being asked
- "Features" can emerge without writing new code—they're latent in the LLM's reasoning

**Implication for implementers:** When you're tempted to add a new page, route, or predefined view, ask: "Could the agent generate this dynamically based on user intent?" If yes, don't build the static version.

### Principle 1: FHIR as the Native Language

**Why FHIR-native matters beyond simplicity:**

FHIR (Fast Healthcare Interoperability Resources) is the universal language of modern healthcare data. By keeping data in FHIR format rather than flattening it into custom schemas, we gain:

1. **LLM Comprehension**: Modern LLMs understand FHIR structure. They can read a FHIR Observation and understand it contains a lab result with a LOINC code, value, units, and reference range. Flattening loses semantic context the LLM could use.

2. **Interoperability by Default**: Any FHIR bundle from any EHR can be loaded without schema changes. The "flattening" problem becomes the LLM's problem, not ours.

3. **Rich Contextual Queries**: FHIR resources reference each other (an Observation references an Encounter which references a Practitioner). These relationships are semantic gold for clinical reasoning.

4. **Future-Proofing**: New FHIR resource types (e.g., GenomicStudy, NutritionOrder) can be loaded immediately—they're just JSON. The LLM can reason about them even if we haven't built custom UI.

**The hybrid approach:** We store raw FHIR but create **views** (not tables) for common query patterns. This gives us:
- Fast structured queries when we know exactly what we want (all labs for patient X)
- Full FHIR fidelity when we need rich context (send to LLM for reasoning)
- No migration burden—views are just SQL over the same data

**Implication for implementers:** Default to storing and passing raw FHIR. Only extract specific fields when you have a concrete performance or UX need. When in doubt, give the LLM more context, not less.

### Principle 2: Conversational Canvas, Not Page-Based Navigation

**Why this matters:**

Traditional clinical applications are built around **tasks and screens**:
- Patient list → Patient detail → Labs tab → Specific lab
- Each screen is a fixed viewport into the data

This model fails for exploratory clinical reasoning because:
- Clinicians don't think in tabs—they think in questions
- The "right" view depends on the clinical context
- Important insights often span multiple traditional "screens"

**The Conversational Canvas model:**

The interface is a single, scrollable conversation where each agent response can contain:
- Narrative text (the reasoning)
- Data visualizations (charts, tables)
- Clinical insights (highlighted findings)
- Suggested actions
- Follow-up questions (emergent navigation)

The "navigation" happens through follow-up questions. Ask "What about kidney function?" and the canvas extends with renal data. This mirrors how clinical reasoning actually works—iterative, question-driven, context-accumulating.

**Implication for implementers:** Resist the urge to build separate pages for labs, medications, conditions, etc. Instead, make the agent capable of generating those views inline when asked. The only "navigation" should be patient selection.

### Principle 3: Structured Generation, Not Free Text

**Why typed responses matter:**

The agent doesn't just return a text blob—it returns a **structured JSON response** that maps to a predefined component catalog. This gives us:

1. **Predictable Rendering**: We know exactly what UI elements can appear
2. **Type Safety**: Frontend can trust the response shape
3. **Controlled Vocabulary**: Insight types, visualization types, action types are constrained
4. **Graceful Degradation**: If a component type isn't supported, we can fall back cleanly

**The component catalog as a contract:**

Think of the response schema as an API contract between the LLM and the frontend:
- The LLM can only request components we've defined
- Each component has typed props
- New capabilities require schema changes (intentional friction)

This prevents the "anything goes" problem of pure generative UI while still allowing rich, dynamic responses.

**Implication for implementers:** When adding new capabilities, first add them to the response schema, then implement the component. The schema is the source of truth for what the agent can express.

### Principle 4: Semantic + Structured Retrieval

**Why both matter:**

Structured queries (SQL) and semantic search (embeddings) serve different purposes:

| Query Type | Good For | Example |
|------------|----------|---------|
| Structured | Precise, known requirements | "All HbA1c results in the last year" |
| Semantic | Exploratory, vague intent | "Anything related to diabetes management" |

The Context Engine uses both:
1. **Always include** active conditions, medications, recent encounters (structured)
2. **Focus with semantic search** based on the user's question

This ensures the LLM has essential context while surfacing query-relevant details.

**Implication for implementers:** Don't try to anticipate every query with structured retrieval. Build a solid baseline of always-included context, then let semantic search handle the long tail.

### Principle 5: Simplicity as a Feature

**Why less is more:**

v1 failed because it was too ambitious. Every feature added was a future maintenance burden. v2 succeeds by doing less, better.

**Concrete simplicity targets:**
- **One database table** (with views) instead of 47
- **One deployment target** (VPS) instead of multi-service cloud
- **One CI workflow** instead of 5+
- **One page** (Conversational Canvas) instead of route-per-feature
- **~2,000 lines of backend** instead of 10,000+

**The "do we need this?" test:** Before adding any feature, ask:
1. Does this directly enable a P0/P1 goal?
2. Can we ship without this and add it later?
3. Will this require ongoing maintenance?

If the answers are "no, yes, yes"—don't build it.

**Implication for implementers:** When facing a choice between elegant and simple, choose simple. When facing a choice between complete and shippable, choose shippable.

### Principle 6: Demo-Grade, Not Production-Grade

**What this means:**

This is a demo platform for clinical AI capabilities, not a production EHR. This changes many decisions:

| Concern | Production Approach | Demo Approach |
|---------|-------------------|---------------|
| Auth | Full user management, roles | Single API key |
| Scale | Auto-scaling, load balancing | Single VPS, fixed capacity |
| Data | HIPAA compliance, encryption | Synthetic data only |
| Uptime | 99.9% SLA, monitoring | "Usually works" |
| Testing | Comprehensive coverage | Happy path coverage |

**Implication for implementers:** Don't over-engineer for hypothetical production requirements. Build for demos that work reliably for an audience of 1-10 people. We can harden later if/when this becomes a real product.

### Principle 7: Developer Experience Matters

**Why DX is a priority:**

The project stalled because development became frustrating. Every change required fighting infrastructure, CI, and complex code. v2 prioritizes developer experience:

- **Local-first development**: Everything runs with `docker compose up`
- **No CI surprises**: Tests use committed fixtures, not generated data
- **Simple deployment**: `git pull && docker compose up -d`
- **Readable code**: Fewer abstractions, more inline clarity
- **Fast feedback**: Tests complete in seconds, not minutes

**Implication for implementers:** If something is annoying to work with, fix it immediately. Accumulated friction kills projects.

### Principle 8: Emergent Features Through Capable Context

**The magic of rich context:**

When you give an LLM comprehensive, well-structured patient data, "features" emerge without explicit implementation:

- **Drug interaction checking**: The LLM sees all medications and conditions, notices conflicts
- **Trend analysis**: The LLM sees lab history, identifies concerning patterns
- **Differential diagnosis**: The LLM sees symptoms and history, reasons about possibilities
- **Care gap identification**: The LLM sees what's missing (overdue screenings, etc.)

None of these require dedicated code paths. They emerge from:
1. Rich FHIR context
2. Good embeddings for semantic retrieval
3. Capable reasoning model
4. Structured output schema that can express findings

**Implication for implementers:** Invest in context quality over feature code. A better Context Engine enables more emergent capabilities than a hundred hand-coded features.

### Principle 9: FHIR-Native Context with Trust Differentiation

**The problem with undifferentiated context:**

If you dump all patient data into one big JSON blob for the LLM, you lose critical signals:
- What's verified vs. what's inferred?
- What's about the patient vs. their family?
- What's current vs. historical?
- What's relevant to this query vs. background noise?

**The solution: Layered context with explicit trust levels**

Context sent to the LLM should be structured into layers:

1. **Verified Layer** (HIGH CONFIDENCE): Facts confirmed via knowledge graph relationships
   - Active conditions, current medications, known allergies
   - Source: Neo4j graph traversal
   - Trust: Ground truth for clinical assertions

2. **Retrieved Layer** (MEDIUM CONFIDENCE): Resources from semantic search
   - Query-relevant clinical notes, observations, encounters
   - Source: pgvector similarity search
   - Trust: Relevant but verify against verified layer

3. **Metadata Layer**: Context about the context
   - Query intent, retrieval strategy, token budget
   - Enables debugging and audit

4. **Constraints Layer**: Guardrails derived from verified facts
   - Drug allergies → "Do not recommend X"
   - Current medications → "Consider interactions with Y"

**FHIR as the native language:**

Each layer contains raw FHIR resources—not custom dataclasses that duplicate FHIR concepts. We don't create `ConditionFact` or `MedicationFact`. We use actual FHIR Condition and MedicationRequest resources, but we *organize* them by provenance.

This gives us:
- Interoperability (can export as FHIR Bundles)
- No schema drift from FHIR standard
- LLM sees actual FHIR (which it understands well)
- Clear provenance signals for trust calibration

**Focused composition, not everything:**

Context should be query-focused, not "dump the whole patient record":
- Always include: verified facts (conditions, meds, allergies) ~500-1000 tokens
- Query-specific: semantic search results relevant to the question
- Token-aware: stop adding when budget reached

**Implication for implementers:** The Context Engine is not just retrieval—it's *curation*. Structure context to help the LLM distinguish verified facts from potentially relevant background. Use FHIR natively but wrap it in a trust-signaling structure.

### Summary: The Mental Model

Think of CruxMD v2 as:

```
         ┌─────────────────────────────────────────────┐
         │           User's Clinical Question          │
         └─────────────────────┬───────────────────────┘
                               │
                               ▼
         ┌─────────────────────────────────────────────┐
         │              Context Engine                 │
         │   "What does the LLM need to know to       │
         │    answer this question well?"              │
         └─────────────────────┬───────────────────────┘
                               │
                               ▼
         ┌─────────────────────────────────────────────┐
         │           FHIR Data (native format)         │
         │   Rich, semantic, interlinked clinical data │
         └─────────────────────┬───────────────────────┘
                               │
                               ▼
         ┌─────────────────────────────────────────────┐
         │             Reasoning Agent (LLM)           │
         │   "Given this context, what's the answer,  │
         │    what's important, what should I show?"   │
         └─────────────────────┬───────────────────────┘
                               │
                               ▼
         ┌─────────────────────────────────────────────┐
         │          Structured Response (JSON)         │
         │   Typed schema: narrative, insights,        │
         │   visualizations, actions, follow-ups       │
         └─────────────────────┬───────────────────────┘
                               │
                               ▼
         ┌─────────────────────────────────────────────┐
         │          Component Catalog (React)          │
         │   Render the response using predefined      │
         │   clinical components                       │
         └─────────────────────┬───────────────────────┘
                               │
                               ▼
         ┌─────────────────────────────────────────────┐
         │           Conversational Canvas             │
         │   User sees narrative + data + suggestions │
         │   Continues the conversation naturally      │
         └─────────────────────────────────────────────┘
```

This is the system. Everything else is implementation detail.

---

## Technical Risks & Mitigations

### Risk 1: PostgreSQL/Neo4j Data Consistency

**Problem:** Writing to two databases without distributed transactions. If Neo4j fails after PostgreSQL commits, data becomes inconsistent.

**Mitigation Strategy:**
1. **Ordered writes:** PostgreSQL first (source of truth), then Neo4j (derived view)
2. **Idempotent graph operations:** Use `MERGE` not `CREATE` so replays are safe
3. **Reconciliation on startup:** Compare PostgreSQL patient list with Neo4j, rebuild missing graphs
4. **Accept eventual consistency:** For demo purposes, manual rebuild via admin endpoint is acceptable

```python
# backend/app/services/admin.py

async def reconcile_graph(db: AsyncSession, graph: KnowledgeGraph):
    """Rebuild Neo4j graph from PostgreSQL source of truth."""

    # Get all patients from PostgreSQL
    patients = await db.execute(
        select(FhirResource).where(FhirResource.resource_type == "Patient")
    )

    for patient_row in patients:
        patient_id = str(patient_row.id)

        # Check if patient exists in Neo4j
        exists = await graph.patient_exists(patient_id)
        if not exists:
            # Rebuild graph for this patient
            resources = await get_all_resources_for_patient(db, patient_row.id)
            await graph.build_from_fhir(patient_id, resources)
            logger.info(f"Rebuilt graph for patient {patient_id}")
```

### Risk 2: LLM Output Validation

**Problem:** GPT-4o may return malformed JSON or hallucinate FHIR resource IDs in citations.

**Mitigation Strategy:**
1. **Pydantic validation:** Parse LLM output through `AgentResponse` schema
2. **Graceful degradation:** If structured output fails, return narrative-only response
3. **Citation verification:** Check that cited FHIR IDs exist before including

```python
# backend/app/services/agent.py

async def generate_response(
    context: PatientContext,
    message: str
) -> AgentResponse:
    """Generate agent response with validation and fallback."""

    raw_response = await llm.chat(
        model="gpt-4o",
        messages=[...],
        response_format={"type": "json_object"}
    )

    try:
        # Attempt to parse structured response
        parsed = AgentResponse.model_validate_json(raw_response.content)

        # Verify citations exist
        if parsed.insights:
            for insight in parsed.insights:
                insight.citations = await verify_citations(
                    context.meta.patient_id,
                    insight.citations or []
                )

        return parsed

    except ValidationError as e:
        # Fallback: return narrative-only response
        logger.warning(f"LLM output validation failed: {e}")
        return AgentResponse(
            narrative=extract_narrative_fallback(raw_response.content),
            insights=[Insight(
                type="warning",
                title="Response Format Issue",
                content="Some structured data could not be parsed."
            )]
        )


async def verify_citations(patient_id: str, citations: list[str]) -> list[str]:
    """Filter citations to only include valid FHIR resource IDs."""
    valid = []
    for fhir_id in citations:
        exists = await db.execute(
            select(FhirResource.id)
            .where(FhirResource.patient_id == patient_id)
            .where(FhirResource.fhir_id == fhir_id)
        )
        if exists.scalar():
            valid.append(fhir_id)
    return valid
```

### Risk 3: Cost Overruns

**Problem:** No budget controls on OpenAI API usage.

**Mitigation Strategy:**
1. **Track usage:** Log tokens per request
2. **Daily budget alerts:** Monitor cumulative spend
3. **Rate limiting:** Cap requests per minute/hour
4. **Caching:** Cache embeddings (they're deterministic)

See [Cost Estimation](#cost-estimation) section for projected costs.

### Risk 4: VPS Resource Constraints

**Problem:** PostgreSQL + Neo4j + FastAPI + Next.js on single 8GB VPS.

**Mitigation Strategy:**
1. **Monitor memory:** Set up basic alerting for >80% memory
2. **Neo4j memory caps:** Already configured (512MB-1GB heap)
3. **Connection pooling:** Limit concurrent DB connections
4. **Contingency plan:** If performance degrades, split services (see [Scaling Contingency](#scaling-contingency))

### Risk 5: LLM Hallucination of Clinical Facts

**Problem:** LLM may assert clinical facts not present in the data.

**Mitigation Strategy:**
1. **Citation requirement:** System prompt requires citations for clinical assertions
2. **Trust layer labeling:** Explicit "VERIFIED" vs "RETRIEVED" in context
3. **Medical disclaimer:** Prominent UI disclaimer (see [Medical Disclaimer Strategy](#medical-disclaimer-strategy))
4. **Constraint enforcement:** Hard constraints from verified allergies/conditions

---

## Demo Scale Definition

**This plan targets the following scale:**

| Dimension | Target | Rationale |
|-----------|--------|-----------|
| **Patients** | 100 | Enough for varied demos, manageable data size |
| **Concurrent users** | 1-3 | Demo/presentation context, not production |
| **Resources per patient** | <1,000 | Typical Synthea output for 5-10 year history |
| **Total FHIR resources** | ~100,000 | 100 patients × 1,000 resources |
| **Database size** | ~500MB PostgreSQL, ~200MB Neo4j | Fits comfortably on VPS |
| **Chat sessions/day** | <100 | Demo usage pattern |
| **Embeddings** | ~100,000 vectors | 1536 dimensions × 100K = ~600MB |

**Performance targets at demo scale:**
- Patient load time: <30 seconds (including embeddings)
- Chat response time: <5 seconds (excluding LLM latency)
- Semantic search: <500ms
- Graph traversal: <100ms

---

## Cost Estimation

### One-Time Setup Costs

| Item | Cost | Notes |
|------|------|-------|
| Domain (cruxmd.ai) | ~$15/year | Already owned |
| Hetzner VPS (CX31: 8GB RAM, 4 vCPU, 80GB) | ~$15/month | Or CX41 for more headroom |
| **Total infrastructure** | **~$15/month** | |

### OpenAI API Costs

#### Embedding Generation (One-Time per Patient Load)

| Component | Calculation | Cost |
|-----------|-------------|------|
| Tokens per resource | ~500 tokens average | |
| Resources per patient | 1,000 | |
| Tokens per patient | 500,000 | |
| text-embedding-3-small | $0.02 / 1M tokens | |
| **Cost per patient** | 500K × $0.00002 | **$0.01** |
| **100 patients** | | **$1.00** |

#### Chat (Ongoing Usage)

| Component | Calculation | Cost |
|-----------|-------------|------|
| Context tokens (input) | ~6,000 tokens | |
| Response tokens (output) | ~1,000 tokens | |
| GPT-4o input | $2.50 / 1M tokens | $0.015 |
| GPT-4o output | $10.00 / 1M tokens | $0.010 |
| **Cost per chat turn** | | **~$0.025** |
| **100 chats/day** | | **$2.50/day** |
| **Monthly (active use)** | | **~$75/month** |

#### Profile Generation (One-Time)

| Component | Calculation | Cost |
|-----------|-------------|------|
| Input tokens per profile | ~2,000 (patient data) | |
| Output tokens per profile | ~500 (profile JSON) | |
| **Cost per profile** | | **~$0.01** |
| **100 profiles** | | **$1.00** |

#### Note Generation (One-Time, P2)

| Component | Calculation | Cost |
|-----------|-------------|------|
| Notes per patient | ~20 (encounters) | |
| Cost per note | ~$0.02 | |
| **100 patients × 20 notes** | | **~$40** |

### Monthly Cost Summary

| Scenario | Infrastructure | API (OpenAI) | Total |
|----------|---------------|--------------|-------|
| **Development** (light use) | $15 | ~$10 | **$25/month** |
| **Active demos** (daily use) | $15 | ~$75 | **$90/month** |
| **Heavy use** (constant demos) | $15 | ~$150 | **$165/month** |

### Cost Controls

```python
# backend/app/services/cost_tracking.py

from datetime import date
from collections import defaultdict

class CostTracker:
    """Track OpenAI API costs."""

    PRICES = {
        "gpt-4o": {"input": 2.50 / 1_000_000, "output": 10.00 / 1_000_000},
        "text-embedding-3-small": {"input": 0.02 / 1_000_000},
    }

    daily_costs: dict[date, float] = defaultdict(float)
    DAILY_BUDGET = 10.00  # Alert threshold

    def record_usage(self, model: str, input_tokens: int, output_tokens: int = 0):
        prices = self.PRICES.get(model, {})
        cost = (
            input_tokens * prices.get("input", 0) +
            output_tokens * prices.get("output", 0)
        )
        self.daily_costs[date.today()] += cost

        if self.daily_costs[date.today()] > self.DAILY_BUDGET:
            logger.warning(f"Daily API budget exceeded: ${self.daily_costs[date.today()]:.2f}")

        return cost

cost_tracker = CostTracker()
```

---

## Architecture Overview

### Comprehensive System Architecture

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              EXTERNAL SERVICES                                   │
│                                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐              │
│  │     OpenAI      │    │  Hetzner VPS    │    │     GitHub      │              │
│  │  ┌───────────┐  │    │   CX31 (8GB)    │    │                 │              │
│  │  │  GPT-4o   │  │    │                 │    │  • Source code  │              │
│  │  │  (chat)   │  │    │  Runs all       │    │  • Test fixtures│              │
│  │  └───────────┘  │    │  containers     │    │    (5 patients) │              │
│  │  ┌───────────┐  │    │                 │    │  • CI/CD        │              │
│  │  │ Embedding │  │    │                 │    │                 │              │
│  │  │  (embed)  │  │    │                 │    │                 │              │
│  │  └───────────┘  │    │                 │    │                 │              │
│  └─────────────────┘    └─────────────────┘    └─────────────────┘              │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                         RUNTIME FLOW (per chat request)                          │
│                                                                                  │
│   ┌──────────┐     ┌──────────────────┐     ┌─────────────────────────────┐     │
│   │          │     │   Next.js App    │     │      FastAPI Backend        │     │
│   │  Browser │────▶│   /api/chat      │────▶│      /api/chat              │     │
│   │          │     │  (adds API key)  │     │                             │     │
│   └──────────┘     └──────────────────┘     └──────────────┬──────────────┘     │
│                                                            │                     │
│                                                            ▼                     │
│                              ┌─────────────────────────────────────────┐         │
│                              │           CONTEXT ENGINE                │         │
│                              │                                         │         │
│                              │  1. Load patient + profile              │         │
│                              │  2. Get verified facts (graph)          │         │
│                              │  3. Semantic search (vectors)           │         │
│                              │  4. Build constraints                   │         │
│                              │  5. Assemble PatientContext             │         │
│                              └────────────────┬────────────────────────┘         │
│                                               │                                  │
│                         ┌─────────────────────┼─────────────────────┐            │
│                         │                     │                     │            │
│                         ▼                     ▼                     ▼            │
│              ┌──────────────────┐  ┌──────────────────┐  ┌──────────────────┐   │
│              │      Neo4j       │  │    PostgreSQL    │  │     OpenAI       │   │
│              │                  │  │                  │  │                  │   │
│              │ • HAS_CONDITION  │  │ • fhir_resources │  │  Embed query     │   │
│              │ • TAKES_MED      │  │ • JSONB data     │  │  for semantic    │   │
│              │ • HAS_ALLERGY    │  │ • profiles       │  │  search          │   │
│              │                  │  │                  │  │                  │   │
│              │ Returns: FHIR    │  │ Returns: FHIR    │  │                  │   │
│              │ resources with   │  │ resources by     │  │                  │   │
│              │ verified status  │  │ vector similarity│  │                  │   │
│              └──────────────────┘  └──────────────────┘  └──────────────────┘   │
│                         │                     │                                  │
│                         └─────────────────────┼──────────────────────────────────│
│                                               ▼                                  │
│                              ┌─────────────────────────────────────────┐         │
│                              │         PatientContext                  │         │
│                              │  • patient (FHIR Patient)               │         │
│                              │  • profile_summary (narrative)          │         │
│                              │  • verified (conditions, meds, allergy) │         │
│                              │  • retrieved (semantic matches)         │         │
│                              │  • constraints (safety rules)           │         │
│                              └────────────────┬────────────────────────┘         │
│                                               │                                  │
│                                               ▼                                  │
│                              ┌─────────────────────────────────────────┐         │
│                              │           REASONING AGENT               │         │
│                              │                                         │         │
│                              │  OpenAI GPT-4o + System Prompt          │         │
│                              │  + PatientContext + User Query          │         │
│                              │                                         │         │
│                              │  → Structured JSON (AgentResponse)      │         │
│                              └────────────────┬────────────────────────┘         │
│                                               │                                  │
│                                               ▼                                  │
│                              ┌─────────────────────────────────────────┐         │
│                              │         AgentResponse                   │         │
│                              │  • narrative (markdown)                 │         │
│                              │  • insights (warnings, info)            │         │
│                              │  • visualizations (with resolved data)  │         │
│                              │  • tables (with resolved data)          │         │
│                              │  • actions (suggested next steps)       │         │
│                              │  • followUps (suggested questions)      │         │
│                              └─────────────────────────────────────────┘         │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                      INGESTION FLOW (one-time data loading)                      │
│                                                                                  │
│   ┌─────────────────┐                                                           │
│   │     Synthea     │  Generate synthetic patients                              │
│   │   (local run)   │  with deterministic seed                                  │
│   └────────┬────────┘                                                           │
│            │                                                                     │
│            ▼                                                                     │
│   ┌─────────────────┐     ┌─────────────────┐                                   │
│   │   FHIR Bundle   │────▶│ Profile Generator│  LLM creates patient narrative   │
│   │   (per patient) │     │    (GPT-4o)      │                                   │
│   └────────┬────────┘     └────────┬────────┘                                   │
│            │                       │                                             │
│            └───────────┬───────────┘                                             │
│                        ▼                                                         │
│            ┌─────────────────────────────────────────┐                          │
│            │            BUNDLE LOADER                 │                          │
│            │                                          │                          │
│            │  For each resource in bundle:            │                          │
│            │  1. Store in PostgreSQL (FHIR JSON)      │                          │
│            │  2. Create Neo4j node + relationships    │                          │
│            │  3. Generate embedding text              │                          │
│            │  4. Call OpenAI embedding API            │                          │
│            │  5. Store embedding vector               │                          │
│            │                                          │                          │
│            │  Attach profile to Patient resource      │                          │
│            └─────────────────────────────────────────┘                          │
│                        │                                                         │
│          ┌─────────────┼─────────────┐                                          │
│          ▼             ▼             ▼                                          │
│   ┌────────────┐ ┌────────────┐ ┌────────────┐                                  │
│   │ PostgreSQL │ │   Neo4j    │ │  pgvector  │                                  │
│   │            │ │            │ │            │                                  │
│   │ FHIR JSON  │ │  Patient   │ │ Embeddings │                                  │
│   │ + profiles │ │    ↓       │ │ (1536 dim) │                                  │
│   │            │ │ Condition  │ │            │                                  │
│   │ ~500MB     │ │ Medication │ │ ~600MB     │                                  │
│   │            │ │ Allergy    │ │            │                                  │
│   │            │ │            │ │            │                                  │
│   │            │ │ ~200MB     │ │            │                                  │
│   └────────────┘ └────────────┘ └────────────┘                                  │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────────┐
│                              DEPLOYMENT TOPOLOGY                                 │
│                                                                                  │
│   ┌─────────────────────────────────────────────────────────────────────────┐   │
│   │                        Hetzner VPS (Docker Compose)                      │   │
│   │                                                                          │   │
│   │   ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │   │
│   │   │  Caddy  │  │ Next.js │  │ FastAPI │  │Postgres │  │  Neo4j  │      │   │
│   │   │  :443   │─▶│  :3000  │  │  :8000  │  │  :5432  │  │  :7687  │      │   │
│   │   │         │  │         │  │         │  │         │  │         │      │   │
│   │   │ HTTPS   │  │ Frontend│  │ Backend │  │ + vector│  │  Graph  │      │   │
│   │   │ Reverse │  │ + API   │  │ + Auth  │  │         │  │         │      │   │
│   │   │ Proxy   │  │ Proxy   │  │         │  │         │  │         │      │   │
│   │   └─────────┘  └─────────┘  └─────────┘  └─────────┘  └─────────┘      │   │
│   │                                                                          │   │
│   │   URLs:                                                                  │   │
│   │   • https://app.cruxmd.ai  → Next.js                                    │   │
│   │   • https://api.cruxmd.ai  → FastAPI                                    │   │
│   │                                                                          │   │
│   └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### High-Level Architecture (Simplified)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         USER INTERFACE                              │
│                                                                     │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │              Conversational Canvas                          │   │
│   │  • Natural language input                                   │   │
│   │  • Structured JSON responses (non-streaming)                │   │
│   │  • Dynamic component rendering                              │   │
│   │  • Emergent navigation via follow-ups                       │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                              │                                      │
└──────────────────────────────┼──────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                         BACKEND API                                 │
│                                                                     │
│   ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐     │
│   │   /api/chat  │  │ /api/patient │  │ /api/fhir/load      │     │
│   └──────┬───────┘  └──────────────┘  └──────────────────────┘     │
│          │                                                          │
│          ▼                                                          │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    Context Engine                           │   │
│   │  • Hybrid retrieval: Graph (verified) + Vector (relevant)   │   │
│   │  • Verified facts from Neo4j (conditions, meds, allergies)  │   │
│   │  • Semantic search for query-relevant resources             │   │
│   └─────────────────────────────────────────────────────────────┘   │
│          │                                                          │
│          ▼                                                          │
│   ┌─────────────────────────────────────────────────────────────┐   │
│   │                    Reasoning Agent                          │   │
│   │  • Analyze clinical question                                │   │
│   │  • Generate structured response (typed JSON)                │   │
│   │  • Produce insights, visualizations, actions                │   │
│   └─────────────────────────────────────────────────────────────┘   │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
                               │
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        DATA LAYER                                   │
│                                                                     │
│  ┌────────────────────────────────┐ ┌────────────────────────────┐  │
│  │       PostgreSQL + pgvector    │ │          Neo4j             │  │
│  │                                │ │                            │  │
│  │  fhir_resources (single table) │ │  Knowledge Graph           │  │
│  │  ├── id (UUID)                 │ │  ├── Patient nodes         │  │
│  │  ├── resource_type             │ │  ├── Condition nodes       │  │
│  │  ├── patient_id                │ │  ├── Medication nodes      │  │
│  │  ├── data (JSONB)              │ │  ├── Allergy nodes         │  │
│  │  ├── embedding (vector)        │ │  └── Typed relationships   │  │
│  │  └── embedding_text            │ │                            │  │
│  │                                │ │  Queries:                  │  │
│  │  Purpose: Raw FHIR storage,    │ │  • Verified clinical facts │  │
│  │  semantic search, full context │ │  • Relationship traversal  │  │
│  └────────────────────────────────┘ └────────────────────────────┘  │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Rationale |
|-------|------------|-----------|
| **Backend Framework** | FastAPI | Async, fast, great OpenAPI support |
| **Backend Language** | Python 3.12 | ML ecosystem, FHIR libraries |
| **Relational Database** | PostgreSQL 16 + pgvector | JSONB queries + vector search |
| **Graph Database** | Neo4j 5.x | Knowledge graph, Cypher queries, learning investment |
| **ORM** | SQLAlchemy (async) | Mature, flexible |
| **Package Manager** | uv | Fast, modern Python PM |
| **Frontend Framework** | Next.js 15 | App Router, React Server Components |
| **Frontend Language** | TypeScript (strict) | Type safety |
| **UI Components** | shadcn/ui | Unstyled, composable, accessible |
| **Styling** | Tailwind CSS | Utility-first, fast iteration |
| **LLM Provider** | OpenAI (GPT-4o) | Best structured output support |
| **Embeddings** | text-embedding-3-small | Good quality, low cost |
| **Deployment** | Single VPS + Docker Compose | Simple, predictable |
| **Reverse Proxy** | Caddy | Automatic HTTPS |

---

## Infrastructure & Hosting

### Recommended Setup: Single VPS

**Provider:** Hetzner
**Instance:** CX32 (4 vCPU, 8GB RAM) - €7.50/month
**OS:** Ubuntu 24.04 LTS

#### Why Single VPS Over Cloud Run

| Aspect | Cloud Run (v1) | Single VPS (v2) |
|--------|---------------|-----------------|
| Deployment | Complex CI/CD, multiple workflows | `git pull && docker compose up -d` |
| Debugging | Cloud logs, IAM issues | SSH and `docker logs` |
| Cost | Variable, cold starts | Fixed €7.50/month |
| Complexity | High (multiple services) | Low (one server) |
| Control | Limited | Full |

### Docker Compose Configuration

```yaml
# docker-compose.yml
services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=postgresql+asyncpg://postgres:${DB_PASSWORD}@db:5432/cruxmd
      - NEO4J_URI=bolt://neo4j:7687
      - NEO4J_USER=neo4j
      - NEO4J_PASSWORD=${NEO4J_PASSWORD}
      - OPENAI_API_KEY=${OPENAI_API_KEY}
      - API_KEY=${API_KEY}
    depends_on:
      db:
        condition: service_healthy
      neo4j:
        condition: service_healthy
    restart: unless-stopped

  db:
    image: pgvector/pgvector:pg16
    volumes:
      - postgres_data:/var/lib/postgresql/data
    environment:
      - POSTGRES_PASSWORD=${DB_PASSWORD}
      - POSTGRES_DB=cruxmd
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    environment:
      - API_KEY=${API_KEY}  # Server-side only, not NEXT_PUBLIC_
    depends_on:
      - backend
    restart: unless-stopped

  neo4j:
    image: neo4j:5.26-community
    ports:
      - "7474:7474"  # Browser UI
      - "7687:7687"  # Bolt protocol
    environment:
      - NEO4J_AUTH=neo4j/${NEO4J_PASSWORD}
      - NEO4J_server_memory_heap_initial__size=512m
      - NEO4J_server_memory_heap_max__size=1G
    volumes:
      - neo4j_data:/data
    healthcheck:
      test: ["CMD-SHELL", "wget -q http://localhost:7474 -O /dev/null || exit 1"]
      interval: 10s
      timeout: 10s
      retries: 5
    restart: unless-stopped

  caddy:
    image: caddy:2
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - caddy_data:/data
      - caddy_config:/config
    depends_on:
      - backend
      - frontend
    restart: unless-stopped

volumes:
  postgres_data:
  neo4j_data:
  caddy_data:
  caddy_config:
```

### Caddyfile (Automatic HTTPS)

```
# Caddyfile
api.cruxmd.ai {
    reverse_proxy backend:8000
}

app.cruxmd.ai {
    reverse_proxy frontend:3000
}
```

### Deployment Script

```bash
#!/bin/bash
# deploy.sh - Run on VPS

cd /opt/cruxmd
git pull origin main
docker compose pull
docker compose up -d --build
docker compose logs -f --tail=50
```

### Environment Variables

```bash
# .env (on VPS, not in repo)
DB_PASSWORD=<strong-password>
OPENAI_API_KEY=sk-...
API_KEY=<shared-secret-for-demo-access>
API_URL=https://api.cruxmd.ai
```

---

## Data Layer Design

### Core Principle: FHIR-Native Storage

Instead of flattening FHIR into 47 relational tables, store FHIR resources in their native JSON format and query using PostgreSQL's powerful JSONB operators.

**Benefits:**
- Preserves full FHIR fidelity
- No schema migrations for new resource types
- LLMs can read/interpret raw FHIR
- Query flexibility via JSONB operators and FHIRPath
- Add structure incrementally via views (not tables)

### Patient Identifier Strategy

**Decision:** The PostgreSQL-generated UUID (`FhirResource.id`) is the **canonical patient identifier** throughout the system.

| Identifier | Source | Usage |
|------------|--------|-------|
| `FhirResource.id` (UUID) | PostgreSQL auto-generated | **Canonical** - used in URLs, APIs, foreign keys, Neo4j node IDs |
| `FhirResource.fhir_id` | Synthea-generated | Preserved for FHIR compliance, used within FHIR references |

**Rationale:**
- UUIDs are guaranteed unique across systems
- Synthea IDs are only unique within a bundle
- PostgreSQL UUID is the foreign key in `patient_id` column
- Neo4j nodes use the same UUID for consistency

**Mapping:**
```python
# When loading a bundle, the Patient resource's PostgreSQL UUID becomes canonical
patient_uuid = fhir_resource.id  # Use this everywhere
synthea_id = fhir_resource.fhir_id  # Preserved but not used as key
```

### Database Schema

```sql
-- One table to rule them all
CREATE TABLE fhir_resources (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- Identifiers
    fhir_id VARCHAR(255) NOT NULL,      -- Original FHIR ID (from Synthea)
    resource_type VARCHAR(50) NOT NULL,
    patient_id UUID,  -- References the Patient's fhir_resources.id (canonical)

    -- The actual FHIR resource
    data JSONB NOT NULL,

    -- Semantic layer
    embedding vector(1536),
    embedding_text TEXT,

    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT now(),

    -- Constraints
    UNIQUE(fhir_id, resource_type)
);

-- Indexes for common access patterns
CREATE INDEX idx_fhir_patient ON fhir_resources(patient_id);
CREATE INDEX idx_fhir_type ON fhir_resources(resource_type);
CREATE INDEX idx_fhir_type_patient ON fhir_resources(resource_type, patient_id);
CREATE INDEX idx_fhir_data_gin ON fhir_resources USING gin(data);
CREATE INDEX idx_fhir_embedding ON fhir_resources
    USING ivfflat(embedding vector_cosine_ops) WITH (lists = 100);
```

### Embedding Generation Timing

**Decision:** Embeddings are generated **synchronously during bundle loading** (not as background jobs).

**Rationale:**
- **Demo scale:** With 100 patients and ~1,000 resources per patient, embedding generation completes in ~30 seconds per patient
- **Simplicity:** No background job infrastructure, task queues, or worker processes needed
- **Consistency:** Resources are immediately searchable after load—no "eventual consistency" confusion
- **Fixture workflow:** Embeddings generated once during fixture creation, committed to repo (or regenerated on seed)

**Implementation:**

```python
# backend/app/services/fhir_loader.py

async def load_bundle(db: AsyncSession, bundle: dict, generate_embeddings: bool = True) -> UUID:
    """
    Load a FHIR bundle into PostgreSQL and Neo4j.

    Embeddings are generated synchronously by default (suitable for demo scale).
    For large-scale ingestion, set generate_embeddings=False and batch separately.
    """
    patient_id = None
    resources_to_embed = []

    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        resource_type = resource.get("resourceType")

        # Store resource
        fhir_resource = FhirResource(
            fhir_id=resource.get("id"),
            resource_type=resource_type,
            patient_id=patient_id,
            data=resource
        )
        db.add(fhir_resource)

        # Track for embedding
        if resource_type in EMBEDDABLE_TYPES:
            resources_to_embed.append((fhir_resource, resource))

        # Track patient ID
        if resource_type == "Patient":
            patient_id = fhir_resource.id

    # Generate embeddings synchronously
    if generate_embeddings and resources_to_embed:
        await generate_embeddings_batch(db, resources_to_embed)

    await db.commit()
    return patient_id


EMBEDDABLE_TYPES = {
    "Condition", "Observation", "MedicationRequest",
    "AllergyIntolerance", "Procedure", "Encounter",
    "DiagnosticReport", "DocumentReference", "CarePlan"
}
```

### Embedding Text Templates

**Critical:** Different FHIR resource types need different embedding strategies. Raw JSON is verbose and wastes tokens. These templates extract semantically meaningful text for embedding.

```python
# backend/app/services/embeddings.py

def create_embedding_text(resource: dict) -> str:
    """
    Generate human-readable text for embedding a FHIR resource.

    Strategy: Extract clinically meaningful content in natural language.
    This text is what gets embedded and searched against user queries.
    """
    resource_type = resource.get("resourceType")

    generators = {
        "Condition": _embed_condition,
        "Observation": _embed_observation,
        "MedicationRequest": _embed_medication,
        "AllergyIntolerance": _embed_allergy,
        "Procedure": _embed_procedure,
        "Encounter": _embed_encounter,
        "DiagnosticReport": _embed_diagnostic_report,
        "DocumentReference": _embed_document_reference,
        "CarePlan": _embed_care_plan,
    }

    generator = generators.get(resource_type, _embed_generic)
    return generator(resource)


def _embed_condition(r: dict) -> str:
    """
    Condition embedding: diagnosis name, status, onset, severity.

    Example output:
    "Diagnosis: Type 2 Diabetes Mellitus. Status: active.
     Onset: 2020-03-15. Clinical notes: Patient diagnosed during routine checkup."
    """
    code = _get_display(r.get("code", {}))
    status = r.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "unknown")
    verification = r.get("verificationStatus", {}).get("coding", [{}])[0].get("code", "")
    onset = r.get("onsetDateTime", r.get("onsetPeriod", {}).get("start", ""))
    severity = _get_display(r.get("severity", {}))
    notes = " ".join(n.get("text", "") for n in r.get("note", []))

    parts = [f"Diagnosis: {code}"]
    if status: parts.append(f"Status: {status}")
    if verification: parts.append(f"Verification: {verification}")
    if onset: parts.append(f"Onset: {onset}")
    if severity: parts.append(f"Severity: {severity}")
    if notes: parts.append(f"Notes: {notes}")

    return ". ".join(parts)


def _embed_observation(r: dict) -> str:
    """
    Observation embedding: what was measured, value, interpretation.

    Example output:
    "Lab result: Hemoglobin A1c (LOINC 4548-4). Value: 8.2%.
     Interpretation: High. Date: 2024-01-15."
    """
    code = _get_display(r.get("code", {}))
    loinc = _get_code(r.get("code", {}), "http://loinc.org")

    # Handle different value types
    value_str = ""
    if "valueQuantity" in r:
        vq = r["valueQuantity"]
        value_str = f"{vq.get('value', '')} {vq.get('unit', '')}".strip()
    elif "valueCodeableConcept" in r:
        value_str = _get_display(r["valueCodeableConcept"])
    elif "valueString" in r:
        value_str = r["valueString"]

    interpretation = _get_display(r.get("interpretation", [{}])[0]) if r.get("interpretation") else ""
    category = _get_display(r.get("category", [{}])[0]) if r.get("category") else ""
    effective = r.get("effectiveDateTime", "")

    parts = []
    if category: parts.append(f"{category} result")
    parts.append(f"{code}")
    if loinc: parts.append(f"(LOINC {loinc})")
    if value_str: parts.append(f"Value: {value_str}")
    if interpretation: parts.append(f"Interpretation: {interpretation}")
    if effective: parts.append(f"Date: {effective[:10]}")

    return ". ".join(parts)


def _embed_medication(r: dict) -> str:
    """
    MedicationRequest embedding: drug name, dosage, reason.

    Example output:
    "Medication: Metformin 500mg. Dosage: Take twice daily with meals.
     Status: active. Prescribed for: Type 2 Diabetes."
    """
    med = _get_display(r.get("medicationCodeableConcept", {}))
    rxnorm = _get_code(r.get("medicationCodeableConcept", {}), "http://www.nlm.nih.gov/research/umls/rxnorm")
    status = r.get("status", "")
    dosage = r.get("dosageInstruction", [{}])[0].get("text", "")
    reason = _get_display(r.get("reasonCode", [{}])[0]) if r.get("reasonCode") else ""
    authored = r.get("authoredOn", "")[:10] if r.get("authoredOn") else ""

    parts = [f"Medication: {med}"]
    if rxnorm: parts.append(f"(RxNorm {rxnorm})")
    if dosage: parts.append(f"Dosage: {dosage}")
    if status: parts.append(f"Status: {status}")
    if reason: parts.append(f"Prescribed for: {reason}")
    if authored: parts.append(f"Prescribed: {authored}")

    return ". ".join(parts)


def _embed_allergy(r: dict) -> str:
    """
    AllergyIntolerance embedding: allergen, reaction, severity.

    Example output:
    "Allergy: Penicillin. Criticality: high. Reaction: Anaphylaxis.
     Category: medication. Status: active."
    """
    allergen = _get_display(r.get("code", {}))
    criticality = r.get("criticality", "")
    category = ", ".join(r.get("category", []))
    status = r.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "")

    reactions = []
    for reaction in r.get("reaction", []):
        manifestations = [_get_display(m) for m in reaction.get("manifestation", [])]
        severity = reaction.get("severity", "")
        if manifestations:
            reaction_text = ", ".join(manifestations)
            if severity: reaction_text += f" ({severity})"
            reactions.append(reaction_text)

    parts = [f"Allergy: {allergen}"]
    if criticality: parts.append(f"Criticality: {criticality}")
    if reactions: parts.append(f"Reaction: {'; '.join(reactions)}")
    if category: parts.append(f"Category: {category}")
    if status: parts.append(f"Status: {status}")

    return ". ".join(parts)


def _embed_procedure(r: dict) -> str:
    """
    Procedure embedding: what was done, when, outcome.

    Example output:
    "Procedure: Coronary artery bypass graft. Date: 2023-06-15.
     Status: completed. Body site: Heart."
    """
    code = _get_display(r.get("code", {}))
    status = r.get("status", "")
    performed = r.get("performedDateTime", r.get("performedPeriod", {}).get("start", ""))
    body_site = _get_display(r.get("bodySite", [{}])[0]) if r.get("bodySite") else ""
    outcome = _get_display(r.get("outcome", {}))
    reason = _get_display(r.get("reasonCode", [{}])[0]) if r.get("reasonCode") else ""

    parts = [f"Procedure: {code}"]
    if performed: parts.append(f"Date: {performed[:10]}")
    if status: parts.append(f"Status: {status}")
    if body_site: parts.append(f"Body site: {body_site}")
    if reason: parts.append(f"Reason: {reason}")
    if outcome: parts.append(f"Outcome: {outcome}")

    return ". ".join(parts)


def _embed_encounter(r: dict) -> str:
    """
    Encounter embedding: visit type, reason, timeframe.

    Example output:
    "Encounter: Office visit (ambulatory). Date: 2024-01-10.
     Reason: Annual wellness exam. Duration: 30 minutes."
    """
    enc_class = r.get("class", {}).get("code", "")
    enc_type = _get_display(r.get("type", [{}])[0]) if r.get("type") else ""
    status = r.get("status", "")
    period = r.get("period", {})
    start = period.get("start", "")[:10] if period.get("start") else ""
    reason = _get_display(r.get("reasonCode", [{}])[0]) if r.get("reasonCode") else ""

    parts = []
    if enc_type:
        parts.append(f"Encounter: {enc_type}")
    if enc_class:
        parts.append(f"({enc_class})")
    if start:
        parts.append(f"Date: {start}")
    if status:
        parts.append(f"Status: {status}")
    if reason:
        parts.append(f"Reason: {reason}")

    return ". ".join(parts)


def _embed_diagnostic_report(r: dict) -> str:
    """
    DiagnosticReport embedding: report type, conclusion, results.

    Example output:
    "Diagnostic Report: Chest X-ray. Date: 2024-01-12.
     Conclusion: No acute cardiopulmonary abnormality."
    """
    code = _get_display(r.get("code", {}))
    status = r.get("status", "")
    effective = r.get("effectiveDateTime", "")[:10] if r.get("effectiveDateTime") else ""
    conclusion = r.get("conclusion", "")
    category = _get_display(r.get("category", [{}])[0]) if r.get("category") else ""

    parts = [f"Diagnostic Report: {code}"]
    if category: parts.append(f"Category: {category}")
    if effective: parts.append(f"Date: {effective}")
    if status: parts.append(f"Status: {status}")
    if conclusion: parts.append(f"Conclusion: {conclusion}")

    return ". ".join(parts)


def _embed_document_reference(r: dict) -> str:
    """
    DocumentReference embedding: document type and content.

    For clinical notes, extract the actual text content.
    """
    doc_type = _get_display(r.get("type", {}))
    status = r.get("status", "")
    date = r.get("date", "")[:10] if r.get("date") else ""
    description = r.get("description", "")

    # Extract content from attachment
    content_text = ""
    for content in r.get("content", []):
        attachment = content.get("attachment", {})
        if attachment.get("contentType") == "text/plain":
            # Base64 decode if needed
            if attachment.get("data"):
                import base64
                content_text = base64.b64decode(attachment["data"]).decode("utf-8")
            elif attachment.get("url"):
                content_text = f"[Document at {attachment['url']}]"

    parts = [f"Document: {doc_type}"]
    if date: parts.append(f"Date: {date}")
    if status: parts.append(f"Status: {status}")
    if description: parts.append(f"Description: {description}")
    if content_text: parts.append(f"Content: {content_text[:1000]}")  # Truncate long content

    return ". ".join(parts)


def _embed_care_plan(r: dict) -> str:
    """CarePlan embedding: goals, activities, conditions addressed."""
    title = r.get("title", "")
    status = r.get("status", "")
    intent = r.get("intent", "")
    description = r.get("description", "")

    activities = []
    for activity in r.get("activity", []):
        detail = activity.get("detail", {})
        act_desc = _get_display(detail.get("code", {})) or detail.get("description", "")
        if act_desc: activities.append(act_desc)

    parts = [f"Care Plan: {title or 'Untitled'}"]
    if status: parts.append(f"Status: {status}")
    if intent: parts.append(f"Intent: {intent}")
    if description: parts.append(f"Description: {description}")
    if activities: parts.append(f"Activities: {'; '.join(activities[:5])}")

    return ". ".join(parts)


def _embed_generic(r: dict) -> str:
    """Fallback: resource type and any identifiable text."""
    resource_type = r.get("resourceType", "Unknown")
    code = _get_display(r.get("code", {}))
    text = r.get("text", {}).get("div", "")

    parts = [f"Resource: {resource_type}"]
    if code: parts.append(f"Code: {code}")
    if text: parts.append(f"Text: {text[:500]}")

    return ". ".join(parts)


# Helper functions

def _get_display(codeable_concept: dict) -> str:
    """Extract display text from CodeableConcept."""
    if not codeable_concept:
        return ""
    # Try text first
    if codeable_concept.get("text"):
        return codeable_concept["text"]
    # Then try first coding display
    codings = codeable_concept.get("coding", [])
    if codings and codings[0].get("display"):
        return codings[0]["display"]
    # Fall back to code
    if codings and codings[0].get("code"):
        return codings[0]["code"]
    return ""


def _get_code(codeable_concept: dict, system: str) -> str:
    """Extract code from CodeableConcept for a specific system."""
    for coding in codeable_concept.get("coding", []):
        if coding.get("system") == system:
            return coding.get("code", "")
    return ""
```

```python
async def generate_embeddings_batch(
    db: AsyncSession,
    resources: list[tuple[FhirResource, dict]]
):
    """Generate embeddings for a batch of resources."""
    texts = [create_embedding_text(resource) for _, resource in resources]
    embeddings = await get_embeddings_batch(texts)  # OpenAI batch API

    for (fhir_resource, _), embedding, text in zip(resources, embeddings, texts):
        fhir_resource.embedding = embedding
        fhir_resource.embedding_text = text
```

**Alternative for Production Scale:**

If scaling beyond demo (thousands of patients), switch to background job pattern:

```python
# Background job approach (not implemented for demo)
async def load_bundle_async(db: AsyncSession, bundle: dict) -> UUID:
    patient_id = await load_bundle(db, bundle, generate_embeddings=False)
    await enqueue_embedding_job(patient_id)  # Celery, ARQ, etc.
    return patient_id
```

### SQLAlchemy Model

```python
# backend/app/models.py
from sqlalchemy import Column, String, DateTime, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import declarative_base
import uuid

Base = declarative_base()

class FhirResource(Base):
    __tablename__ = "fhir_resources"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Identifiers
    fhir_id = Column(String(255), nullable=False)
    resource_type = Column(String(50), nullable=False, index=True)
    patient_id = Column(UUID(as_uuid=True), index=True)

    # The actual FHIR resource
    data = Column(JSONB, nullable=False)

    # Semantic layer
    embedding = Column(Vector(1536))
    embedding_text = Column(String)

    # Metadata
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))

    __table_args__ = (
        Index('idx_fhir_type_patient', 'resource_type', 'patient_id'),
        Index('idx_fhir_data_gin', 'data', postgresql_using='gin'),
    )
```

### Views for Common Query Patterns

Instead of separate tables, create views that "flatten on read":

```sql
-- Lab results view
CREATE VIEW v_lab_results AS
SELECT
    fr.id,
    fr.patient_id,
    fr.fhir_id,
    fr.data->'code'->'coding'->0->>'code' as loinc_code,
    fr.data->'code'->'coding'->0->>'display' as test_name,
    (fr.data->'valueQuantity'->>'value')::numeric as value,
    fr.data->'valueQuantity'->>'unit' as unit,
    fr.data->'referenceRange'->0->'low'->>'value' as ref_low,
    fr.data->'referenceRange'->0->'high'->>'value' as ref_high,
    fr.data->'interpretation'->0->'coding'->0->>'code' as interpretation,
    (fr.data->>'effectiveDateTime')::timestamp as effective_date,
    fr.data as raw_fhir
FROM fhir_resources fr
WHERE fr.resource_type = 'Observation'
AND fr.data->'category' @> '[{"coding": [{"code": "laboratory"}]}]';

-- Active medications view
CREATE VIEW v_active_medications AS
SELECT
    fr.id,
    fr.patient_id,
    fr.fhir_id,
    fr.data->'medicationCodeableConcept'->'coding'->0->>'code' as rxnorm_code,
    fr.data->'medicationCodeableConcept'->'coding'->0->>'display' as medication_name,
    fr.data->>'status' as status,
    fr.data->'dosageInstruction'->0->>'text' as dosage,
    (fr.data->>'authoredOn')::timestamp as prescribed_date,
    fr.data as raw_fhir
FROM fhir_resources fr
WHERE fr.resource_type = 'MedicationRequest'
AND fr.data->>'status' IN ('active', 'on-hold');

-- Active conditions view
CREATE VIEW v_active_conditions AS
SELECT
    fr.id,
    fr.patient_id,
    fr.fhir_id,
    fr.data->'code'->'coding'->0->>'code' as snomed_code,
    fr.data->'code'->'coding'->0->>'display' as condition_name,
    fr.data->'clinicalStatus'->'coding'->0->>'code' as clinical_status,
    fr.data->'verificationStatus'->'coding'->0->>'code' as verification_status,
    (fr.data->>'onsetDateTime')::timestamp as onset_date,
    fr.data as raw_fhir
FROM fhir_resources fr
WHERE fr.resource_type = 'Condition'
AND fr.data->'clinicalStatus'->'coding' @> '[{"code": "active"}]';

-- Patient summary view
CREATE VIEW v_patient_summary AS
SELECT
    fr.id,
    fr.fhir_id,
    fr.data->'name'->0->>'family' as family_name,
    fr.data->'name'->0->'given'->>0 as given_name,
    fr.data->>'birthDate' as birth_date,
    fr.data->>'gender' as gender,
    fr.data->'address'->0->>'city' as city,
    fr.data->'address'->0->>'state' as state,
    fr.data as raw_fhir
FROM fhir_resources fr
WHERE fr.resource_type = 'Patient';
```

---

## Knowledge Graph Architecture

### Why Knowledge Graphs Are Essential (P2 Priority)

Vector search finds *similarity*, not *truth*. In clinical contexts, this distinction is critical for patient safety.

**The Dangerous Failure Mode:**

```
User Query: "Is this patient allergic to Penicillin?"

Patient Record Contains:
- Note 1: "Patient denies drug allergies"
- Note 2: "Family history: Father has penicillin allergy"

Vector Search Behavior:
- Embeds "penicillin allergy"
- Finds Note 2 (high cosine similarity)
- Returns it as relevant context

LLM Conclusion: "The patient has a penicillin allergy" ❌ DANGEROUS ERROR
```

The vector search cannot distinguish between:
- The patient IS allergic
- The patient's RELATIVE is allergic
- The patient was TESTED for an allergy
- The patient's allergy was RESOLVED

**The Knowledge Graph Solution:**

A knowledge graph encodes precise, typed relationships that can be traversed for verified facts:

```
(Patient:John) --[HAS_ALLERGY]--> (Drug:Penicillin)     ← Check this edge: DOES NOT EXIST
(Patient:John) --[HAS_RELATIVE]--> (Person:Father)
(Person:Father) --[HAS_ALLERGY]--> (Drug:Penicillin)   ← Different relationship path

Query: "Does John have a penicillin allergy?"
Graph Traversal: Check for direct edge (John) --[HAS_ALLERGY]--> (Penicillin)
Result: No direct edge exists → Patient does NOT have allergy ✅ CORRECT
```

### Design Decision: Neo4j

We chose Neo4j over simpler alternatives (PostgreSQL recursive CTEs, in-memory NetworkX) for several reasons:

| Option | Complexity | Query Power | Learning Value | Decision |
|--------|------------|-------------|----------------|----------|
| PostgreSQL + recursive CTEs | Low | Limited | Low | ❌ Insufficient for complex traversals |
| Apache AGE (Postgres extension) | Medium | Good | Medium | Considered but less mature |
| NetworkX (in-memory Python) | Low | Good | Low | ❌ Doesn't scale, no persistence |
| **Neo4j** | Medium | Excellent | **High** | ✅ **Selected** |

**Neo4j Advantages:**
- Cypher query language is purpose-built for graph traversal
- Native vector search in Neo4j 5.x (potential future consolidation)
- Industry standard with extensive documentation
- Free tier (Aura Free) available for production demos
- Learning investment pays off for future medical ontology work
- APOC library provides advanced graph algorithms

### Graph Schema: Patient-Specific Layer

```cypher
// Node Types
(:Patient {id, fhir_id, name, birth_date, gender})
(:Condition {id, fhir_id, code, display, system, clinical_status})
(:Medication {id, fhir_id, code, display, system, status})
(:Observation {id, fhir_id, code, display, value, unit, effective_date})
(:Allergy {id, fhir_id, code, display, criticality, status})
(:Procedure {id, fhir_id, code, display, performed_date})
(:Encounter {id, fhir_id, class, type, period_start, period_end})
(:Practitioner {id, fhir_id, name, specialty})

// Relationship Types
(Patient)-[:HAS_CONDITION {onset_date, recorded_date}]->(Condition)
(Patient)-[:TAKES_MEDICATION {start_date, end_date, dosage}]->(Medication)
(Patient)-[:HAS_OBSERVATION {recorded_date}]->(Observation)
(Patient)-[:HAS_ALLERGY {recorded_date, reaction}]->(Allergy)
(Patient)-[:HAD_PROCEDURE {performed_date}]->(Procedure)
(Patient)-[:HAD_ENCOUNTER]->(Encounter)
(Encounter)-[:INVOLVED_PRACTITIONER]->(Practitioner)
(Encounter)-[:RESULTED_IN]->(Condition|Observation|Procedure)

// Clinical Relationships
(Medication)-[:TREATS]->(Condition)
(Medication)-[:CONTRAINDICATED_FOR]->(Condition)
(Medication)-[:INTERACTS_WITH]->(Medication)
(Observation)-[:INDICATES]->(Condition)
(Observation)-[:MONITORS]->(Condition)
(Condition)-[:COMPLICATION_OF]->(Condition)
```

### Python Integration

```python
# backend/app/services/graph.py
from neo4j import AsyncGraphDatabase
from app.config import settings

class KnowledgeGraph:
    def __init__(self):
        self.driver = AsyncGraphDatabase.driver(
            settings.NEO4J_URI,
            auth=(settings.NEO4J_USER, settings.NEO4J_PASSWORD)
        )

    async def close(self):
        await self.driver.close()

    async def patient_has_allergy(self, patient_id: str, drug_code: str) -> bool:
        """Check if patient has a specific allergy - precise graph lookup."""
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (p:Patient {id: $patient_id})-[:HAS_ALLERGY]->(a:Allergy)
                WHERE a.code = $drug_code OR a.display CONTAINS $drug_code
                RETURN a
            """, patient_id=patient_id, drug_code=drug_code)
            return await result.single() is not None

    async def get_verified_facts(self, patient_id: str) -> dict:
        """Get verified clinical facts from graph (not vector search)."""
        async with self.driver.session() as session:
            # Active conditions
            conditions = await session.run("""
                MATCH (p:Patient {id: $patient_id})-[:HAS_CONDITION]->(c:Condition)
                WHERE c.clinical_status = 'active'
                RETURN c.display as name, c.code as code
            """, patient_id=patient_id)

            # Current medications
            medications = await session.run("""
                MATCH (p:Patient {id: $patient_id})-[:TAKES_MEDICATION]->(m:Medication)
                WHERE m.status IN ['active', 'on-hold']
                RETURN m.display as name, m.code as code
            """, patient_id=patient_id)

            # Allergies
            allergies = await session.run("""
                MATCH (p:Patient {id: $patient_id})-[:HAS_ALLERGY]->(a:Allergy)
                WHERE a.status = 'active'
                RETURN a.display as name, a.criticality as criticality
            """, patient_id=patient_id)

            return {
                "conditions": [dict(r) async for r in conditions],
                "medications": [dict(r) async for r in medications],
                "allergies": [dict(r) async for r in allergies]
            }

    async def check_drug_interactions(self, patient_id: str, new_drug_code: str) -> list[dict]:
        """Check for drug-drug interactions with current medications."""
        async with self.driver.session() as session:
            result = await session.run("""
                MATCH (p:Patient {id: $patient_id})-[:TAKES_MEDICATION]->(current:Medication)
                WHERE current.status = 'active'
                MATCH (current)-[:INTERACTS_WITH]-(new:Medication {code: $new_code})
                RETURN current.display as current_med, new.display as new_med,
                       relationship(current, new).severity as severity
            """, patient_id=patient_id, new_code=new_drug_code)
            return [dict(r) async for r in result]

    async def build_from_fhir(self, patient_id: str, fhir_resources: list[dict]):
        """Build/update graph from FHIR resources during ingestion."""
        async with self.driver.session() as session:
            for resource in fhir_resources:
                resource_type = resource.get("resourceType")

                if resource_type == "Patient":
                    await self._upsert_patient(session, patient_id, resource)
                elif resource_type == "Condition":
                    await self._upsert_condition(session, patient_id, resource)
                elif resource_type == "MedicationRequest":
                    await self._upsert_medication(session, patient_id, resource)
                elif resource_type == "AllergyIntolerance":
                    await self._upsert_allergy(session, patient_id, resource)
                elif resource_type == "Observation":
                    await self._upsert_observation(session, patient_id, resource)
                elif resource_type == "Procedure":
                    await self._upsert_procedure(session, patient_id, resource)
                elif resource_type == "Encounter":
                    await self._upsert_encounter(session, patient_id, resource)
```

### Graph Population During FHIR Loading

**Decision:** Graph nodes are created **synchronously during bundle loading**, mirroring the embedding generation approach.

**Rationale:**
- Same demo-scale reasoning as embeddings: seconds to complete for 5-10 patients
- Ensures PostgreSQL and Neo4j stay in sync without complex reconciliation
- Verified facts immediately available for queries

**Implementation Details:**

```python
# backend/app/services/graph.py (extended)

class KnowledgeGraph:
    """Neo4j graph service with FHIR-aware node creation."""

    async def _upsert_patient(self, session, patient_id: str, resource: dict):
        """Create or update Patient node with full FHIR resource stored."""
        name = resource.get("name", [{}])[0]
        await session.run("""
            MERGE (p:Patient {id: $patient_id})
            SET p.fhir_id = $fhir_id,
                p.fhir_resource = $fhir_resource,
                p.name = $name,
                p.birth_date = $birth_date,
                p.gender = $gender,
                p.updated_at = datetime()
        """, {
            "patient_id": patient_id,
            "fhir_id": resource.get("id"),
            "fhir_resource": json.dumps(resource),
            "name": f"{name.get('given', [''])[0]} {name.get('family', '')}".strip(),
            "birth_date": resource.get("birthDate"),
            "gender": resource.get("gender")
        })

    async def _upsert_condition(self, session, patient_id: str, resource: dict):
        """Create Condition node and HAS_CONDITION relationship."""
        coding = resource.get("code", {}).get("coding", [{}])[0]
        clinical_status = resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "unknown")

        await session.run("""
            MATCH (p:Patient {id: $patient_id})
            MERGE (c:Condition {id: $condition_id})
            SET c.fhir_id = $fhir_id,
                c.fhir_resource = $fhir_resource,
                c.code = $code,
                c.system = $system,
                c.display = $display,
                c.clinical_status = $clinical_status,
                c.onset_date = $onset_date,
                c.updated_at = datetime()
            MERGE (p)-[r:HAS_CONDITION]->(c)
            SET r.recorded_date = $recorded_date,
                r.onset_date = $onset_date
        """, {
            "patient_id": patient_id,
            "condition_id": resource.get("id"),
            "fhir_id": resource.get("id"),
            "fhir_resource": json.dumps(resource),
            "code": coding.get("code"),
            "system": coding.get("system"),
            "display": coding.get("display"),
            "clinical_status": clinical_status,
            "onset_date": resource.get("onsetDateTime"),
            "recorded_date": resource.get("recordedDate")
        })

    async def _upsert_medication(self, session, patient_id: str, resource: dict):
        """Create Medication node and TAKES_MEDICATION relationship."""
        med_concept = resource.get("medicationCodeableConcept", {})
        coding = med_concept.get("coding", [{}])[0]
        status = resource.get("status", "unknown")

        await session.run("""
            MATCH (p:Patient {id: $patient_id})
            MERGE (m:Medication {id: $medication_id})
            SET m.fhir_id = $fhir_id,
                m.fhir_resource = $fhir_resource,
                m.code = $code,
                m.system = $system,
                m.display = $display,
                m.status = $status,
                m.updated_at = datetime()
            MERGE (p)-[r:TAKES_MEDICATION]->(m)
            SET r.start_date = $authored_on,
                r.status = $status,
                r.dosage = $dosage
        """, {
            "patient_id": patient_id,
            "medication_id": resource.get("id"),
            "fhir_id": resource.get("id"),
            "fhir_resource": json.dumps(resource),
            "code": coding.get("code"),
            "system": coding.get("system"),
            "display": coding.get("display"),
            "status": status,
            "authored_on": resource.get("authoredOn"),
            "dosage": resource.get("dosageInstruction", [{}])[0].get("text")
        })

    async def _upsert_allergy(self, session, patient_id: str, resource: dict):
        """Create Allergy node and HAS_ALLERGY relationship."""
        coding = resource.get("code", {}).get("coding", [{}])[0]
        clinical_status = resource.get("clinicalStatus", {}).get("coding", [{}])[0].get("code", "active")

        await session.run("""
            MATCH (p:Patient {id: $patient_id})
            MERGE (a:Allergy {id: $allergy_id})
            SET a.fhir_id = $fhir_id,
                a.fhir_resource = $fhir_resource,
                a.code = $code,
                a.system = $system,
                a.display = $display,
                a.criticality = $criticality,
                a.status = $status,
                a.updated_at = datetime()
            MERGE (p)-[r:HAS_ALLERGY]->(a)
            SET r.recorded_date = $recorded_date,
                r.criticality = $criticality
        """, {
            "patient_id": patient_id,
            "allergy_id": resource.get("id"),
            "fhir_id": resource.get("id"),
            "fhir_resource": json.dumps(resource),
            "code": coding.get("code"),
            "system": coding.get("system"),
            "display": coding.get("display"),
            "criticality": resource.get("criticality", "unknown"),
            "status": clinical_status,
            "recorded_date": resource.get("recordedDate")
        })

    async def _upsert_observation(self, session, patient_id: str, resource: dict):
        """Create Observation node and HAS_OBSERVATION relationship."""
        coding = resource.get("code", {}).get("coding", [{}])[0]
        value_quantity = resource.get("valueQuantity", {})

        await session.run("""
            MATCH (p:Patient {id: $patient_id})
            MERGE (o:Observation {id: $observation_id})
            SET o.fhir_id = $fhir_id,
                o.fhir_resource = $fhir_resource,
                o.code = $code,
                o.display = $display,
                o.value = $value,
                o.unit = $unit,
                o.effective_date = $effective_date,
                o.updated_at = datetime()
            MERGE (p)-[r:HAS_OBSERVATION]->(o)
            SET r.recorded_date = $effective_date
        """, {
            "patient_id": patient_id,
            "observation_id": resource.get("id"),
            "fhir_id": resource.get("id"),
            "fhir_resource": json.dumps(resource),
            "code": coding.get("code"),
            "display": coding.get("display"),
            "value": value_quantity.get("value"),
            "unit": value_quantity.get("unit"),
            "effective_date": resource.get("effectiveDateTime")
        })

    async def _upsert_procedure(self, session, patient_id: str, resource: dict):
        """Create Procedure node and HAD_PROCEDURE relationship."""
        coding = resource.get("code", {}).get("coding", [{}])[0]

        await session.run("""
            MATCH (p:Patient {id: $patient_id})
            MERGE (proc:Procedure {id: $procedure_id})
            SET proc.fhir_id = $fhir_id,
                proc.fhir_resource = $fhir_resource,
                proc.code = $code,
                proc.display = $display,
                proc.performed_date = $performed_date,
                proc.status = $status,
                proc.updated_at = datetime()
            MERGE (p)-[r:HAD_PROCEDURE]->(proc)
            SET r.performed_date = $performed_date
        """, {
            "patient_id": patient_id,
            "procedure_id": resource.get("id"),
            "fhir_id": resource.get("id"),
            "fhir_resource": json.dumps(resource),
            "code": coding.get("code"),
            "display": coding.get("display"),
            "performed_date": resource.get("performedDateTime") or resource.get("performedPeriod", {}).get("start"),
            "status": resource.get("status")
        })

    async def _upsert_encounter(self, session, patient_id: str, resource: dict):
        """Create Encounter node and HAD_ENCOUNTER relationship."""
        encounter_class = resource.get("class", {})
        period = resource.get("period", {})

        await session.run("""
            MATCH (p:Patient {id: $patient_id})
            MERGE (e:Encounter {id: $encounter_id})
            SET e.fhir_id = $fhir_id,
                e.fhir_resource = $fhir_resource,
                e.class = $class,
                e.status = $status,
                e.period_start = $period_start,
                e.period_end = $period_end,
                e.updated_at = datetime()
            MERGE (p)-[r:HAD_ENCOUNTER]->(e)
            SET r.period_start = $period_start
        """, {
            "patient_id": patient_id,
            "encounter_id": resource.get("id"),
            "fhir_id": resource.get("id"),
            "fhir_resource": json.dumps(resource),
            "class": encounter_class.get("code"),
            "status": resource.get("status"),
            "period_start": period.get("start"),
            "period_end": period.get("end")
        })
```

### Integrated FHIR Loader with Graph Population

The bundle loader orchestrates both PostgreSQL and Neo4j storage:

```python
# backend/app/services/fhir_loader.py (complete)

from app.services.graph import KnowledgeGraph

async def load_bundle(
    db: AsyncSession,
    graph: KnowledgeGraph,
    bundle: dict,
    generate_embeddings: bool = True
) -> UUID:
    """
    Load FHIR bundle into PostgreSQL and Neo4j simultaneously.

    1. Parse bundle and store resources in PostgreSQL
    2. Populate Neo4j graph with typed relationships
    3. Generate embeddings for semantic search

    All operations are synchronous for demo-scale consistency.
    """
    patient_id = None
    resources_to_embed = []
    fhir_resources = []

    # Phase 1: Parse and store in PostgreSQL
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        resource_type = resource.get("resourceType")

        # Create PostgreSQL record
        fhir_resource = FhirResource(
            fhir_id=resource.get("id"),
            resource_type=resource_type,
            data=resource
        )

        # Set patient_id for Patient resource (used as foreign key)
        if resource_type == "Patient":
            patient_id = fhir_resource.id
            fhir_resource.patient_id = patient_id
        else:
            # Will be set after we know patient_id
            pass

        db.add(fhir_resource)
        fhir_resources.append(resource)

        # Track embeddable resources
        if resource_type in EMBEDDABLE_TYPES:
            resources_to_embed.append((fhir_resource, resource))

    # Update patient_id for all non-Patient resources
    await db.flush()  # Get generated IDs
    for entry in bundle.get("entry", []):
        resource = entry.get("resource", {})
        if resource.get("resourceType") != "Patient":
            await db.execute(
                update(FhirResource)
                .where(FhirResource.fhir_id == resource.get("id"))
                .values(patient_id=patient_id)
            )

    # Phase 2: Populate Neo4j graph
    await graph.build_from_fhir(str(patient_id), fhir_resources)

    # Phase 3: Generate embeddings
    if generate_embeddings and resources_to_embed:
        await generate_embeddings_batch(db, resources_to_embed)

    await db.commit()
    return patient_id

### Integration with Context Engine

The Knowledge Graph integrates with the Context Engine (see [Context Engine](#context-engine) section for full details) to provide **hybrid retrieval**:

1. **Graph provides verified facts**: `get_verified_facts()` returns high-confidence clinical data
2. **PostgreSQL provides semantic context**: Vector search finds query-relevant resources
3. **Context Engine combines both**: Structures them into trust-differentiated layers for the LLM

The `KnowledgeGraph.get_verified_facts()` method is called by the Context Engine during context assembly. The graph returns actual FHIR resources (not custom dataclasses), preserving FHIR as the native data language throughout the pipeline.

### Future Expansion: Medical Ontology Integration

The patient-specific graph is the foundation. The future expansion connects it to **universal medical knowledge** via UMLS (Unified Medical Language System) and standard terminologies.

#### The Vision: Two-Layer Graph

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                     UNIVERSAL ONTOLOGY LAYER                                │
│                     (Shared across all patients)                            │
│                                                                             │
│  ┌─────────────────┐         ┌─────────────────┐         ┌──────────────┐  │
│  │ SNOMED:44054006 │──IS_A──▶│ SNOMED:73211009 │──IS_A──▶│  Endocrine   │  │
│  │ Type 2 Diabetes │         │ Diabetes Mellitus│         │  Disorder    │  │
│  └────────┬────────┘         └─────────────────┘         └──────────────┘  │
│           │                                                                 │
│           ├──TREATED_BY──▶ (RxNorm:6809 "Metformin")                       │
│           │                      │                                          │
│           │                      └──DRUG_CLASS──▶ "Biguanide"              │
│           │                                                                 │
│           └──MONITORED_BY──▶ (LOINC:4548-4 "Hemoglobin A1c")              │
│                                   │                                         │
│                                   └──MEASURES──▶ "Glycemic Control"        │
│                                                                             │
│  ┌─────────────────┐                                                        │
│  │  LOINC:2339-0   │──MEASURES──▶ "Blood Glucose"                          │
│  │ Glucose [Mass]  │                                                        │
│  └─────────────────┘                                                        │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                    │
                                    │ LINKS VIA CODE MAPPINGS
                                    ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│                     PATIENT-SPECIFIC LAYER                                  │
│                     (Per-patient clinical data)                             │
│                                                                             │
│  (Patient:John)──HAS_CONDITION──▶(Condition)──CODED_AS──▶(SNOMED:44054006) │
│        │                                                                    │
│        ├──TAKES_MEDICATION──▶(Medication)──CODED_AS──▶(RxNorm:6809)        │
│        │                                                                    │
│        └──HAS_OBSERVATION──▶(Observation:HbA1c=8.2%)──CODED_AS──▶(LOINC:4548-4)
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

#### What Ontology Integration Enables

**1. Query Expansion**
```
User: "Does this patient have any metabolic disorders?"

Without Ontology:
  - Search for literal string "metabolic disorder"
  - Miss: Type 2 Diabetes, Thyroid disorders, etc.

With Ontology:
  - Expand "metabolic disorder" via IS_A relationships
  - Includes: Diabetes (Type 1, Type 2, Gestational), Thyroid disorders, etc.
  - Find: Patient has Type 2 Diabetes
  - Return: "Yes, Type 2 Diabetes (classified as a metabolic disorder)"
```

**2. Clinical Inference**
```
Graph Facts:
- Patient has HbA1c = 8.2% (LOINC:4548-4)
- Target HbA1c for diabetics: < 7%
- LOINC:4548-4 --MEASURES--> "Glycemic Control"
- "Glycemic Control" --RELEVANT_TO--> "Diabetes"
- Patient --HAS_CONDITION--> Diabetes

Inference: "Patient's diabetes is suboptimally controlled"
(Derived from graph traversal, not stated in any note)
```

**3. Drug-Condition-Lab Triangulation**
```
User: "What labs should I order for this diabetic patient on Metformin?"

Graph Traversal:
1. Patient --HAS_CONDITION--> Diabetes
2. Diabetes --MONITORED_BY--> HbA1c, Fasting Glucose, Renal Panel
3. Patient --TAKES--> Metformin
4. Metformin --REQUIRES_MONITORING--> B12, Renal Function (Metformin risk)
5. Metformin --CONTRAINDICATED_IF--> eGFR < 30

Synthesized Response:
"Recommend ordering:
- HbA1c (diabetes monitoring)
- Comprehensive Metabolic Panel (includes renal function for Metformin safety)
- B12 level (Metformin can cause B12 deficiency)
Note: Verify eGFR > 30 before continuing Metformin."
```

#### Data Sources for Ontology Layer

| Ontology | Coverage | Source | License |
|----------|----------|--------|---------|
| **SNOMED CT** | Clinical terms, conditions, procedures | [UMLS](https://www.nlm.nih.gov/research/umls/) | Free with UMLS license |
| **LOINC** | Lab tests, measurements, vital signs | [loinc.org](https://loinc.org/) | Free |
| **RxNorm** | Medications, ingredients, brands, classes | [NLM RxNorm](https://www.nlm.nih.gov/research/umls/rxnorm/) | Free |
| **ICD-10-CM** | Diagnosis codes (billing/admin) | [CMS](https://www.cms.gov/medicare/coding/icd10) | Free |
| **CPT** | Procedure codes (billing) | AMA | Paid license |

#### Implementation Phases for Ontology

| Phase | Scope | Priority |
|-------|-------|----------|
| **P2 (Current)** | Patient-specific graph only | ✅ Building now |
| **P3** | Graph visualization in UI | After chat MVP |
| **Future v1** | Import LOINC subset (~2000 common codes) | When needed |
| **Future v2** | Import SNOMED core subset (~20K concepts) | When needed |
| **Future v3** | Import RxNorm with drug interactions | When needed |
| **Future v4** | Full UMLS Metathesaurus integration | Major project |

---

## FHIR-Native Query Patterns

### Pattern 1: Direct JSONB Queries

```python
# Get all lab results for a patient
async def get_labs(db: AsyncSession, patient_id: UUID) -> list[dict]:
    result = await db.execute(
        text("""
            SELECT data FROM fhir_resources
            WHERE patient_id = :patient_id
            AND resource_type = 'Observation'
            AND data->'category' @> '[{"coding": [{"code": "laboratory"}]}]'
            ORDER BY (data->>'effectiveDateTime')::timestamp DESC
        """),
        {"patient_id": patient_id}
    )
    return [row.data for row in result.fetchall()]

# Get conditions by SNOMED code
async def get_conditions_by_code(
    db: AsyncSession,
    patient_id: UUID,
    snomed_code: str
) -> list[dict]:
    result = await db.execute(
        text("""
            SELECT data FROM fhir_resources
            WHERE patient_id = :patient_id
            AND resource_type = 'Condition'
            AND data->'code'->'coding' @> :code_filter
        """),
        {
            "patient_id": patient_id,
            "code_filter": json.dumps([{
                "system": "http://snomed.info/sct",
                "code": snomed_code
            }])
        }
    )
    return [row.data for row in result.fetchall()]

# Get medications with specific status
async def get_medications(
    db: AsyncSession,
    patient_id: UUID,
    status: list[str] = ["active", "on-hold"]
) -> list[dict]:
    result = await db.execute(
        text("""
            SELECT data FROM fhir_resources
            WHERE patient_id = :patient_id
            AND resource_type = 'MedicationRequest'
            AND data->>'status' = ANY(:statuses)
        """),
        {"patient_id": patient_id, "statuses": status}
    )
    return [row.data for row in result.fetchall()]
```

### Pattern 2: View-Based Queries

```python
# Query using views for cleaner code
async def get_abnormal_labs(db: AsyncSession, patient_id: UUID) -> list[dict]:
    result = await db.execute(
        text("""
            SELECT * FROM v_lab_results
            WHERE patient_id = :patient_id
            AND interpretation IN ('H', 'L', 'HH', 'LL', 'A')
            ORDER BY effective_date DESC
            LIMIT 20
        """),
        {"patient_id": patient_id}
    )
    return [dict(row._mapping) for row in result.fetchall()]
```

### Pattern 3: FHIRPath Queries

```python
from fhirpathpy import evaluate

async def query_fhirpath(
    db: AsyncSession,
    patient_id: UUID,
    fhirpath_expression: str
) -> list:
    """Query patient data using FHIRPath expressions."""

    # Get all resources for patient
    result = await db.execute(
        text("SELECT data FROM fhir_resources WHERE patient_id = :pid"),
        {"pid": patient_id}
    )

    # Build a FHIR Bundle
    bundle = {
        "resourceType": "Bundle",
        "entry": [{"resource": row.data} for row in result.fetchall()]
    }

    # Evaluate FHIRPath expression
    return evaluate(bundle, fhirpath_expression)

# Usage examples:
# Get all medication names
meds = await query_fhirpath(
    db, patient_id,
    "Bundle.entry.resource.where(resourceType='MedicationRequest')"
    ".medicationCodeableConcept.coding.display"
)

# Get all abnormal observations
abnormal = await query_fhirpath(
    db, patient_id,
    "Bundle.entry.resource.where(resourceType='Observation')"
    ".where(interpretation.coding.code='H' or interpretation.coding.code='L')"
)
```

### Pattern 4: Semantic Search

```python
async def semantic_search(
    db: AsyncSession,
    patient_id: UUID,
    query: str,
    top_k: int = 20,
    resource_types: list[str] | None = None
) -> list[dict]:
    """Find relevant FHIR resources using semantic similarity."""

    # Embed the query
    embedding = await get_embedding(query)

    # Build query with optional type filter
    type_filter = ""
    if resource_types:
        type_filter = "AND resource_type = ANY(:types)"

    result = await db.execute(
        text(f"""
            SELECT
                data,
                resource_type,
                1 - (embedding <=> :embedding) as similarity
            FROM fhir_resources
            WHERE patient_id = :patient_id
            AND embedding IS NOT NULL
            {type_filter}
            ORDER BY embedding <=> :embedding
            LIMIT :top_k
        """),
        {
            "patient_id": patient_id,
            "embedding": embedding,
            "top_k": top_k,
            "types": resource_types
        }
    )

    return [
        {
            "resource": row.data,
            "resource_type": row.resource_type,
            "similarity": float(row.similarity)
        }
        for row in result.fetchall()
    ]
```

---

## Authentication

### Architecture: Server-Side API Key Proxy

For a demo platform, we use a simple API key but keep it **server-side only**. The frontend never sees the API key—all requests go through Next.js API routes that add the key before forwarding to the backend.

```
┌─────────────┐     ┌─────────────────────┐     ┌─────────────┐
│   Browser   │ ──▶ │  Next.js API Route  │ ──▶ │   FastAPI   │
│  (no key)   │     │  (adds X-API-Key)   │     │   Backend   │
└─────────────┘     └─────────────────────┘     └─────────────┘
```

**Why this approach:**
- API key never exposed in client JavaScript bundle
- No CORS issues (same-origin requests)
- Can add rate limiting at the proxy layer
- Easy to swap for real auth later

### Backend: API Key Verification

```python
# backend/app/auth.py
from fastapi import Header, HTTPException, Depends
from fastapi.security import APIKeyHeader
from app.config import settings

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=True)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verify API key from header."""
    if api_key != settings.API_KEY:
        raise HTTPException(
            status_code=401,
            detail="Invalid API key"
        )
    return True

# Usage in routes
@router.post("/chat")
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_api_key)
):
    ...
```

### Frontend: Next.js API Route Proxy

```typescript
// frontend/app/api/chat/route.ts
import { NextRequest, NextResponse } from "next/server";

const BACKEND_URL = process.env.BACKEND_URL || "http://backend:8000";
const API_KEY = process.env.API_KEY;  // Server-side only, NOT NEXT_PUBLIC_

export async function POST(request: NextRequest) {
  const body = await request.json();

  const response = await fetch(`${BACKEND_URL}/api/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY!,
    },
    body: JSON.stringify(body),
  });

  if (!response.ok) {
    const errorBody = await response.text();
    console.error(`Backend error: ${response.status}`, errorBody);
    return NextResponse.json(
      { error: "Backend request failed", detail: errorBody },
      { status: response.status }
    );
  }

  // Non-streaming: return JSON directly
  // Streaming deferred to P3+ (structured JSON doesn't stream well)
  const data = await response.json();
  return NextResponse.json(data);
}
```

### Frontend: Client API Helper

```typescript
// frontend/lib/api.ts
// No API key here - requests go to our own API routes

export async function apiClient<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  // All requests go to /api/* which proxies to backend
  const response = await fetch(`/api${endpoint}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
  });

  if (!response.ok) {
    throw new Error(`API error: ${response.status}`);
  }

  return response.json();
}

// Usage
const response = await apiClient<AgentResponse>("/chat", {
  method: "POST",
  body: JSON.stringify({ patient_id, message }),
});
```

### Future: Multi-User Auth

If multi-user support becomes necessary, options include:

1. **Clerk** - Managed auth, easy integration
2. **NextAuth.js** - Self-hosted, flexible
3. **Supabase Auth** - If also using Supabase

For now, the single API key approach is sufficient for demos with synthetic data.

### Security Beyond API Key

While the API key protects against unauthorized access, additional security measures are needed:

#### CORS Configuration

```python
# backend/app/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://app.cruxmd.ai",
        "http://localhost:3000",  # Local development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)
```

#### Rate Limiting

```python
# backend/app/middleware/rate_limit.py
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

# Apply to app
app.state.limiter = limiter

# Usage on endpoints
@router.post("/chat")
@limiter.limit("30/minute")  # 30 requests per minute per IP
async def chat(...):
    ...

@router.post("/fhir/load-bundle")
@limiter.limit("10/minute")  # More restrictive for data ingestion
async def load_bundle(...):
    ...
```

#### Input Validation & Sanitization

```python
# backend/app/schemas/chat.py
from pydantic import BaseModel, Field, validator
import bleach

class ChatRequest(BaseModel):
    patient_id: UUID
    message: str = Field(..., max_length=10000)  # Prevent huge payloads
    conversation_id: str | None = Field(None, max_length=36)

    @validator('message')
    def sanitize_message(cls, v):
        # Strip any HTML/script tags (defense in depth)
        return bleach.clean(v, tags=[], strip=True)
```

#### Request Size Limits

```python
# backend/app/main.py

# Limit request body size (1MB default, increase for bundle uploads)
app = FastAPI()

@app.middleware("http")
async def limit_request_size(request: Request, call_next):
    content_length = request.headers.get("content-length")
    if content_length:
        if int(content_length) > 10 * 1024 * 1024:  # 10MB max
            return JSONResponse(
                status_code=413,
                content={"detail": "Request too large"}
            )
    return await call_next(request)
```

#### Frontend XSS Prevention

```typescript
// frontend/components/clinical/NarrativeRenderer.tsx
import DOMPurify from 'dompurify';
import ReactMarkdown from 'react-markdown';

export function NarrativeRenderer({ content }: { content: string }) {
  // Sanitize markdown before rendering
  const sanitized = DOMPurify.sanitize(content);

  return (
    <ReactMarkdown
      // Disable dangerous HTML in markdown
      components={{
        // Override to prevent script injection
        script: () => null,
        iframe: () => null,
      }}
    >
      {sanitized}
    </ReactMarkdown>
  );
}
```

---

## Backup and Recovery Strategy

### Automated Backups

```bash
#!/bin/bash
# scripts/backup.sh - Run daily via cron

BACKUP_DIR="/opt/backups"
DATE=$(date +%Y%m%d_%H%M%S)

# PostgreSQL backup
docker compose exec -T postgres pg_dump -U postgres cruxmd | gzip > "$BACKUP_DIR/postgres_$DATE.sql.gz"

# Neo4j backup (requires stopping writes briefly)
docker compose exec -T neo4j neo4j-admin database dump neo4j --to-path=/backups
mv /opt/neo4j/backups/neo4j.dump "$BACKUP_DIR/neo4j_$DATE.dump"

# Retain last 7 days
find "$BACKUP_DIR" -name "*.gz" -mtime +7 -delete
find "$BACKUP_DIR" -name "*.dump" -mtime +7 -delete

# Optional: Upload to S3/B2 for offsite storage
# aws s3 sync "$BACKUP_DIR" s3://cruxmd-backups/
```

### Cron Setup

```bash
# /etc/cron.d/cruxmd-backup
0 3 * * * root /opt/cruxmd/scripts/backup.sh >> /var/log/cruxmd-backup.log 2>&1
```

### Recovery Procedure

```bash
#!/bin/bash
# scripts/restore.sh BACKUP_DATE

DATE=$1
BACKUP_DIR="/opt/backups"

# Stop services
cd /opt/cruxmd
docker compose down

# Restore PostgreSQL
gunzip -c "$BACKUP_DIR/postgres_$DATE.sql.gz" | docker compose exec -T postgres psql -U postgres cruxmd

# Restore Neo4j
docker compose exec -T neo4j neo4j-admin database load neo4j --from-path=/backups/neo4j_$DATE.dump --overwrite-destination

# Restart services
docker compose up -d
```

### Disaster Recovery

If the VPS is lost entirely:

1. Provision new Hetzner VPS
2. Clone repository: `git clone https://github.com/yourusername/cruxmd-v2`
3. Restore `.env` from secure storage (1Password, etc.)
4. Restore backups from offsite storage
5. Run migrations: `docker compose run backend alembic upgrade head`
6. Verify data integrity

**Recovery Time Objective (RTO):** ~1 hour
**Recovery Point Objective (RPO):** 24 hours (daily backups)

---

## Medical Disclaimer Strategy

### UI Disclaimer

```typescript
// frontend/components/layout/MedicalDisclaimer.tsx

export function MedicalDisclaimer() {
  return (
    <div className="bg-amber-50 border-l-4 border-amber-400 p-4 mb-4">
      <div className="flex">
        <div className="flex-shrink-0">
          <AlertTriangle className="h-5 w-5 text-amber-400" />
        </div>
        <div className="ml-3">
          <p className="text-sm text-amber-700">
            <strong>For demonstration purposes only.</strong> This system uses
            synthetic patient data and AI-generated insights. Do not use for
            actual clinical decision-making. Always verify information with
            authoritative sources.
          </p>
        </div>
      </div>
    </div>
  );
}
```

### Placement

- **Persistent banner** at top of Conversational Canvas
- **Footer text** on every page: "Demo system with synthetic data. Not for clinical use."
- **Session start** message from agent acknowledges limitations

### System Prompt Addition

```python
CLINICAL_SYSTEM_PROMPT = """
...

## Important Limitations

You are a demonstration system using synthetic patient data. Always:
1. Remind users this is a demo with synthetic data when appropriate
2. Never claim certainty about diagnoses or treatments
3. Recommend verification with authoritative sources for any clinical assertion
4. Acknowledge when data is incomplete or ambiguous

If asked about real clinical decisions, remind the user this is a demo system.
"""
```

---

## Frontend Error States

### Error Handling Architecture

```typescript
// frontend/lib/errors.ts

export type ErrorType =
  | "network"        // Backend unreachable
  | "auth"           // API key invalid
  | "validation"     // Invalid request
  | "llm_failure"    // LLM returned invalid response
  | "not_found"      // Patient/resource not found
  | "rate_limit"     // Too many requests
  | "unknown";       // Catch-all

export interface AppError {
  type: ErrorType;
  message: string;
  detail?: string;
  retryable: boolean;
}

export function classifyError(status: number, body?: any): AppError {
  switch (status) {
    case 401:
      return { type: "auth", message: "Authentication failed", retryable: false };
    case 404:
      return { type: "not_found", message: "Resource not found", retryable: false };
    case 422:
      return { type: "validation", message: body?.detail || "Invalid request", retryable: false };
    case 429:
      return { type: "rate_limit", message: "Too many requests. Please wait.", retryable: true };
    case 500:
      return { type: "llm_failure", message: "Failed to generate response", detail: body?.detail, retryable: true };
    default:
      return { type: "unknown", message: "Something went wrong", retryable: true };
  }
}
```

### Error UI Components

```typescript
// frontend/components/canvas/ErrorMessage.tsx

export function ErrorMessage({ error, onRetry }: { error: AppError; onRetry?: () => void }) {
  const icons = {
    network: <WifiOff className="h-5 w-5" />,
    auth: <Lock className="h-5 w-5" />,
    llm_failure: <AlertCircle className="h-5 w-5" />,
    rate_limit: <Clock className="h-5 w-5" />,
    not_found: <Search className="h-5 w-5" />,
    validation: <AlertTriangle className="h-5 w-5" />,
    unknown: <AlertCircle className="h-5 w-5" />,
  };

  return (
    <div className="rounded-lg border border-red-200 bg-red-50 p-4">
      <div className="flex items-start gap-3">
        <div className="text-red-500">{icons[error.type]}</div>
        <div className="flex-1">
          <p className="font-medium text-red-800">{error.message}</p>
          {error.detail && (
            <p className="mt-1 text-sm text-red-600">{error.detail}</p>
          )}
        </div>
        {error.retryable && onRetry && (
          <button
            onClick={onRetry}
            className="text-sm text-red-600 hover:text-red-800 underline"
          >
            Retry
          </button>
        )}
      </div>
    </div>
  );
}
```

### Loading States

```typescript
// frontend/components/canvas/ThinkingIndicator.tsx

export function ThinkingIndicator() {
  return (
    <div className="flex items-center gap-2 text-gray-500 py-4">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span>Analyzing patient data...</span>
    </div>
  );
}
```

### Empty States

```typescript
// frontend/components/patient/EmptyPatientState.tsx

export function EmptyPatientState() {
  return (
    <div className="text-center py-12 text-gray-500">
      <User className="h-12 w-12 mx-auto mb-4 opacity-50" />
      <p className="text-lg">No patient selected</p>
      <p className="text-sm">Choose a patient from the dropdown to begin.</p>
    </div>
  );
}
```

---

## DataQuery Resolution

### Decision: Backend Resolves DataQueries

When the LLM includes `visualizations` or `tables` with `dataQuery` objects, the **backend** resolves them before sending the response. The frontend receives pre-fetched data, not queries to execute.

**Rationale:**
- Simpler frontend (no query execution logic)
- Single round-trip (no fetch-after-render)
- Backend can enforce access control on data
- Consistent data fetching patterns

### Implementation

```python
# backend/app/services/agent.py

async def generate_response(
    context: PatientContext,
    message: str
) -> AgentResponse:
    """Generate response and resolve any data queries."""

    # Get LLM response
    raw_response = await llm.chat(...)
    parsed = AgentResponse.model_validate_json(raw_response.content)

    # Resolve data queries in visualizations
    if parsed.visualizations:
        for viz in parsed.visualizations:
            viz.data = await resolve_data_query(
                context.meta.patient_id,
                viz.data_query
            )

    # Resolve data queries in tables
    if parsed.tables:
        for table in parsed.tables:
            table.rows = await resolve_data_query(
                context.meta.patient_id,
                table.data_query
            )

    return parsed


async def resolve_data_query(patient_id: str, query: DataQuery) -> list[dict]:
    """Execute a DataQuery and return results."""

    filters = []
    params = {"patient_id": patient_id}

    # Resource type filter
    if query.resource_types:
        filters.append("resource_type = ANY(:types)")
        params["types"] = query.resource_types

    # Time range filter
    if query.time_range:
        cutoff = calculate_cutoff(query.time_range)
        filters.append("(data->>'effectiveDateTime')::timestamp > :cutoff")
        params["cutoff"] = cutoff

    where_clause = " AND ".join(filters) if filters else "TRUE"

    result = await db.execute(
        text(f"""
            SELECT data FROM fhir_resources
            WHERE patient_id = :patient_id AND {where_clause}
            ORDER BY (data->>'effectiveDateTime')::timestamp DESC
            LIMIT :limit
        """),
        {**params, "limit": query.limit or 50}
    )

    return [row.data for row in result.fetchall()]
```

### Updated Response Schema

```python
# backend/app/schemas/agent.py

class Visualization(BaseModel):
    type: Literal["line_chart", "bar_chart", "timeline", "vitals_grid"]
    title: str
    description: str | None = None
    data_query: DataQuery        # What the LLM requested
    data: list[dict] | None = None  # Resolved data (populated by backend)
    config: dict | None = None
```

---

## Scaling Contingency

### When to Scale

Monitor these metrics. If consistently exceeded, implement scaling:

| Metric | Threshold | Action |
|--------|-----------|--------|
| Memory usage | >80% sustained | Add RAM or split services |
| Response time | >5s p95 | Optimize queries or add caching |
| Neo4j heap | >900MB | Increase limits or dedicated instance |
| Concurrent users | >5 | Add connection pooling |

### Scaling Options

#### Option 1: Vertical Scaling (Simplest)

Upgrade Hetzner VPS:
- CX31 (8GB) → CX41 (16GB): ~$30/month
- CX41 (16GB) → CX51 (32GB): ~$60/month

#### Option 2: Split Databases (Moderate)

Move PostgreSQL and/or Neo4j to managed services:

```yaml
# docker-compose.prod.yml (app-only)
services:
  backend:
    environment:
      - DATABASE_URL=postgresql://user:pass@managed-postgres.host:5432/cruxmd
      - NEO4J_URI=bolt://managed-neo4j.host:7687

  frontend:
    # ... unchanged
```

**Managed options:**
- PostgreSQL: Neon (free tier), Supabase, or Hetzner managed
- Neo4j: Neo4j Aura (free tier available)

#### Option 3: Horizontal Scaling (Complex)

If truly needed (unlikely for demo):

```yaml
# docker-compose.prod.yml
services:
  backend:
    deploy:
      replicas: 2

  nginx:
    image: nginx
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    # Load balance across backend replicas
```

### Implementation Order

1. **First:** Optimize queries and add caching
2. **Second:** Vertical scaling (bigger VPS)
3. **Third:** Managed databases
4. **Last resort:** Horizontal scaling

---

## Frontend Architecture: Conversational Canvas

### Core Concept

No fixed pages or predefined navigation. The interface is a **conversational canvas** where:
1. User asks questions in natural language
2. Agent generates structured responses
3. Responses render as dynamic compositions of clinical components
4. Follow-up suggestions enable emergent navigation

### UI Layout

```
┌─────────────────────────────────────────────────────────────────┐
│  CruxMD                                    [Select Patient ▼]   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                                                         │   │
│  │              Message History                            │   │
│  │              (scrollable)                               │   │
│  │                                                         │   │
│  │  Each message can contain:                              │   │
│  │  • Narrative text (markdown)                            │   │
│  │  • Insight cards (info, warning, critical)              │   │
│  │  • Visualizations (charts, tables, timelines)           │   │
│  │  • Action buttons                                       │   │
│  │  • Data citations                                       │   │
│  │                                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  [Suggested follow-up 1] [Follow-up 2] [Follow-up 3]    │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  💬 Ask about this patient...                       [→] │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                 │
└─────────────────────────────────────────────────────────────────┘
```

### Page Structure

```
frontend/
├── app/
│   ├── layout.tsx              # Root layout
│   ├── page.tsx                # Redirect to /chat
│   ├── chat/
│   │   └── page.tsx            # Main conversational canvas
│   └── api/                    # API routes (if needed)
├── components/
│   ├── canvas/
│   │   ├── ConversationalCanvas.tsx
│   │   ├── MessageHistory.tsx
│   │   ├── AgentMessage.tsx
│   │   ├── UserMessage.tsx
│   │   ├── ChatInput.tsx
│   │   ├── FollowUpSuggestions.tsx
│   │   └── ThinkingIndicator.tsx
│   ├── clinical/
│   │   ├── InsightCard.tsx
│   │   ├── LabResultsChart.tsx
│   │   ├── LabResultsTable.tsx
│   │   ├── MedicationList.tsx
│   │   ├── ConditionList.tsx
│   │   ├── VitalsChart.tsx
│   │   ├── Timeline.tsx
│   │   └── ActionButton.tsx
│   ├── patient/
│   │   ├── PatientSelector.tsx
│   │   └── PatientHeader.tsx
│   └── ui/                     # shadcn/ui components
└── lib/
    ├── api.ts
    ├── types.ts
    └── utils.ts
```

---

## Agent Response Schema

### TypeScript Definition

```typescript
// frontend/lib/types.ts

export interface AgentResponse {
  // Optional thinking/reasoning (can show/hide)
  thinking?: string;

  // Main narrative response (markdown)
  narrative: string;

  // Clinical insights (highlighted callouts)
  insights?: Insight[];

  // Visualizations to render
  visualizations?: Visualization[];

  // Data tables
  tables?: DataTable[];

  // Suggested actions
  actions?: Action[];

  // Follow-up questions (emergent navigation)
  followUps?: FollowUp[];
}

export interface Insight {
  type: "info" | "warning" | "critical" | "positive";
  title: string;
  content: string;
  citations?: string[];  // FHIR resource IDs for reference
}

export interface Visualization {
  type: "line_chart" | "bar_chart" | "timeline" | "vitals_grid";
  title: string;
  description?: string;
  dataQuery: DataQuery;
  config?: Record<string, unknown>;
}

export interface DataQuery {
  // What data to fetch - resolved by frontend or backend
  resourceTypes: string[];
  filters?: Record<string, unknown>;
  timeRange?: string;  // "7D", "1M", "6M", "1Y", "all"
  limit?: number;
}

export interface DataTable {
  title: string;
  columns: TableColumn[];
  dataQuery: DataQuery;
}

export interface TableColumn {
  key: string;
  header: string;
  format?: "text" | "date" | "number" | "badge";
}

export interface Action {
  label: string;
  type: "order" | "refer" | "document" | "alert" | "link";
  description?: string;
  payload?: Record<string, unknown>;
}

export interface FollowUp {
  question: string;
  intent?: string;  // For analytics/debugging
}
```

### Backend Pydantic Schema

```python
# backend/app/schemas/agent.py
from pydantic import BaseModel
from typing import Literal

class Insight(BaseModel):
    type: Literal["info", "warning", "critical", "positive"]
    title: str
    content: str
    citations: list[str] | None = None

class DataQuery(BaseModel):
    resource_types: list[str]
    filters: dict | None = None
    time_range: str | None = None
    limit: int | None = None

class Visualization(BaseModel):
    type: Literal["line_chart", "bar_chart", "timeline", "vitals_grid"]
    title: str
    description: str | None = None
    data_query: DataQuery
    config: dict | None = None

class TableColumn(BaseModel):
    key: str
    header: str
    format: Literal["text", "date", "number", "badge"] | None = None

class DataTable(BaseModel):
    title: str
    columns: list[TableColumn]
    data_query: DataQuery

class Action(BaseModel):
    label: str
    type: Literal["order", "refer", "document", "alert", "link"]
    description: str | None = None
    payload: dict | None = None

class FollowUp(BaseModel):
    question: str
    intent: str | None = None

class AgentResponse(BaseModel):
    thinking: str | None = None
    narrative: str
    insights: list[Insight] | None = None
    visualizations: list[Visualization] | None = None
    tables: list[DataTable] | None = None
    actions: list[Action] | None = None
    follow_ups: list[FollowUp] | None = None
```

---

## Component Catalog

### Clinical Components

#### InsightCard

```typescript
// components/clinical/InsightCard.tsx
interface InsightCardProps {
  type: "info" | "warning" | "critical" | "positive";
  title: string;
  content: string;
  citations?: string[];
  onCitationClick?: (id: string) => void;
}

export function InsightCard({ type, title, content, citations, onCitationClick }: InsightCardProps) {
  const styles = {
    info: "border-blue-200 bg-blue-50",
    warning: "border-yellow-200 bg-yellow-50",
    critical: "border-red-200 bg-red-50",
    positive: "border-green-200 bg-green-50",
  };

  const icons = {
    info: InfoIcon,
    warning: AlertTriangleIcon,
    critical: AlertCircleIcon,
    positive: CheckCircleIcon,
  };

  const Icon = icons[type];

  return (
    <div className={cn("rounded-lg border p-4", styles[type])}>
      <div className="flex items-start gap-3">
        <Icon className="h-5 w-5 mt-0.5" />
        <div>
          <h4 className="font-medium">{title}</h4>
          <p className="text-sm mt-1">{content}</p>
          {citations && citations.length > 0 && (
            <div className="flex gap-1 mt-2">
              {citations.map((id, i) => (
                <button
                  key={i}
                  onClick={() => onCitationClick?.(id)}
                  className="text-xs text-blue-600 hover:underline"
                >
                  [{i + 1}]
                </button>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
```

#### LabResultsChart

```typescript
// components/clinical/LabResultsChart.tsx
interface LabResultsChartProps {
  patientId: string;
  labCodes: string[];  // LOINC codes
  timeRange: string;
  title: string;
}

export function LabResultsChart({ patientId, labCodes, timeRange, title }: LabResultsChartProps) {
  const { data, isLoading } = useLabResults(patientId, labCodes, timeRange);

  if (isLoading) return <Skeleton className="h-64" />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent>
        <ResponsiveContainer width="100%" height={250}>
          <LineChart data={data}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey="date" />
            <YAxis />
            <Tooltip />
            <Legend />
            {labCodes.map((code, i) => (
              <Line
                key={code}
                type="monotone"
                dataKey={code}
                stroke={COLORS[i % COLORS.length]}
                dot={{ r: 4 }}
              />
            ))}
            {/* Reference range bands */}
            {data[0]?.referenceRange && (
              <ReferenceArea
                y1={data[0].referenceRange.low}
                y2={data[0].referenceRange.high}
                fill="#22c55e"
                fillOpacity={0.1}
              />
            )}
          </LineChart>
        </ResponsiveContainer>
      </CardContent>
    </Card>
  );
}
```

#### MedicationList

```typescript
// components/clinical/MedicationList.tsx
interface MedicationListProps {
  patientId: string;
  filter?: "active" | "all";
  showDiscontinued?: boolean;
}

export function MedicationList({ patientId, filter = "active", showDiscontinued }: MedicationListProps) {
  const { data: medications, isLoading } = useMedications(patientId, filter);

  if (isLoading) return <Skeleton className="h-32" />;

  return (
    <Card>
      <CardHeader>
        <CardTitle>Medications</CardTitle>
      </CardHeader>
      <CardContent>
        <ul className="space-y-2">
          {medications?.map((med) => (
            <li key={med.id} className="flex justify-between items-center">
              <div>
                <span className="font-medium">{med.medicationName}</span>
                {med.dosage && (
                  <span className="text-sm text-muted-foreground ml-2">
                    {med.dosage}
                  </span>
                )}
              </div>
              <Badge variant={med.status === "active" ? "default" : "secondary"}>
                {med.status}
              </Badge>
            </li>
          ))}
        </ul>
      </CardContent>
    </Card>
  );
}
```

#### ActionButton

```typescript
// components/clinical/ActionButton.tsx
interface ActionButtonProps {
  label: string;
  type: "order" | "refer" | "document" | "alert" | "link";
  description?: string;
  onClick?: () => void;
}

export function ActionButton({ label, type, description, onClick }: ActionButtonProps) {
  const icons = {
    order: ClipboardListIcon,
    refer: UserPlusIcon,
    document: FileTextIcon,
    alert: BellIcon,
    link: ExternalLinkIcon,
  };

  const Icon = icons[type];

  return (
    <Button variant="outline" onClick={onClick} className="gap-2">
      <Icon className="h-4 w-4" />
      {label}
    </Button>
  );
}
```

#### FollowUpSuggestions

```typescript
// components/canvas/FollowUpSuggestions.tsx
interface FollowUpSuggestionsProps {
  suggestions: Array<{ question: string; intent?: string }>;
  onSelect: (question: string) => void;
}

export function FollowUpSuggestions({ suggestions, onSelect }: FollowUpSuggestionsProps) {
  if (!suggestions.length) return null;

  return (
    <div className="flex flex-wrap gap-2">
      {suggestions.map((suggestion, i) => (
        <button
          key={i}
          onClick={() => onSelect(suggestion.question)}
          className="text-sm px-3 py-1.5 rounded-full bg-muted hover:bg-muted/80 transition-colors"
        >
          {suggestion.question}
        </button>
      ))}
    </div>
  );
}
```

---

## Context Engine

### Intent & Principles

The Context Engine is the heart of CruxMD—it bridges raw patient data and the reasoning LLM. Its job is not just retrieval but **curation**: assembling the right context, in the right structure, with the right trust signals.

**Core Principles:**

1. **FHIR-Native**: All clinical data remains as raw FHIR resources. No custom `ConditionFact` or `MedicationFact` dataclasses that duplicate FHIR concepts. The wrapper provides structure; FHIR provides the content.

2. **Trust Differentiation**: Context is layered by confidence level:
   - Verified (from graph): High confidence, use as ground truth
   - Retrieved (from vectors): Relevant but verify against verified layer

3. **Focused Composition**: Query-specific retrieval with token budgeting. Not "everything we know" but "what's relevant to this question."

4. **Constraint Generation**: Automatically derive reasoning guardrails from verified facts (allergies → drug warnings).

5. **Debuggability**: Metadata tracks retrieval strategy, token usage, and provenance for audit/debugging.

### Context Object Schema

The Context Object is what gets sent to the LLM. It wraps FHIR resources in a trust-differentiated structure.

```python
# backend/app/services/context_engine.py

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID
import json

# ==============================================================================
# CONTEXT METADATA
# ==============================================================================

@dataclass
class ContextMeta:
    """Metadata about this context retrieval - enables debugging and audit."""
    patient_id: str
    query: str
    timestamp: datetime
    retrieval_strategy: str       # "query_focused" | "comprehensive" | "recent"
    token_budget: int             # Target token limit
    tokens_used: int              # Actual tokens in context
    verified_source: str = "neo4j"
    retrieved_source: str = "pgvector"


# ==============================================================================
# VERIFIED LAYER (HIGH CONFIDENCE - from Knowledge Graph)
# ==============================================================================

@dataclass
class VerifiedLayer:
    """
    Facts verified via knowledge graph relationships.

    Contains raw FHIR resources - NO custom schemas.
    These have explicit typed relationships confirmed in Neo4j.

    Trust Level: HIGH - use as ground truth for clinical assertions.
    """
    conditions: list[dict] = field(default_factory=list)      # FHIR Condition resources
    medications: list[dict] = field(default_factory=list)     # FHIR MedicationRequest resources
    allergies: list[dict] = field(default_factory=list)       # FHIR AllergyIntolerance resources

    def to_bundle(self) -> dict:
        """Export as valid FHIR Bundle."""
        entries = []
        for c in self.conditions:
            entries.append({"resource": c})
        for m in self.medications:
            entries.append({"resource": m})
        for a in self.allergies:
            entries.append({"resource": a})
        return {
            "resourceType": "Bundle",
            "type": "collection",
            "entry": entries
        }

    def token_estimate(self) -> int:
        # ~4 characters per token on average for JSON content
        return len(json.dumps(self.to_bundle())) // 4


# ==============================================================================
# RETRIEVED LAYER (MEDIUM CONFIDENCE - from Semantic Search)
# ==============================================================================

@dataclass
class RetrievedResource:
    """A FHIR resource retrieved via semantic search, with relevance metadata."""
    resource: dict           # Raw FHIR resource (unchanged)
    resource_type: str       # "Observation", "Encounter", etc.
    score: float             # Similarity score (0.0-1.0)
    reason: str              # "semantic_match" | "recent" | "query_focus"


@dataclass
class RetrievedLayer:
    """
    Resources from semantic search or structured queries.

    Contains raw FHIR resources with retrieval metadata.
    Query-relevant but relationships not graph-verified.

    Trust Level: MEDIUM - relevant but cross-reference with verified layer.
    """
    resources: list[RetrievedResource] = field(default_factory=list)

    def to_bundle(self) -> dict:
        """Export as FHIR Bundle with search scores."""
        return {
            "resourceType": "Bundle",
            "type": "searchset",
            "entry": [
                {
                    "resource": r.resource,
                    "search": {"mode": "match", "score": r.score}
                }
                for r in self.resources
            ]
        }

    def token_estimate(self) -> int:
        return sum(len(json.dumps(r.resource)) // 4 for r in self.resources)


# ==============================================================================
# PATIENT CONTEXT (THE MAIN CONTEXT OBJECT)
# ==============================================================================

@dataclass
class PatientContext:
    """
    FHIR-native context with explicit trust layers.

    Design principles:
    - All clinical data is raw FHIR (no custom dataclasses for conditions, meds, etc.)
    - Resources grouped by provenance, not duplicated
    - Focused retrieval: include what's relevant, not everything
    - Token-aware: stay within budget
    - Constraints derived from verified facts
    """

    # Metadata about this context retrieval
    meta: ContextMeta

    # The patient resource (always included, from graph)
    patient: dict  # FHIR Patient

    # Patient profile summary (from generated profiles, for personalization)
    profile_summary: str | None = None

    # HIGH CONFIDENCE: Facts verified via knowledge graph traversal
    verified: VerifiedLayer

    # MEDIUM CONFIDENCE: Resources from semantic/structured retrieval
    retrieved: RetrievedLayer

    # Query-specific reasoning constraints (derived from verified facts)
    constraints: list[str] = field(default_factory=list)

    def token_estimate(self) -> int:
        """Total estimated tokens in this context."""
        # ~4 characters per token on average for JSON content
        patient_tokens = len(json.dumps(self.patient)) // 4
        profile_tokens = len(self.profile_summary or "") // 4
        return patient_tokens + profile_tokens + self.verified.token_estimate() + self.retrieved.token_estimate()
```

### Context Assembly

```python
# backend/app/services/context_engine.py (continued)

async def build_patient_context(
    db: AsyncSession,
    graph: KnowledgeGraph,
    patient_id: UUID,
    query: str,
    token_budget: int = 6000
) -> PatientContext:
    """
    Build focused context for a clinical query.

    Strategy:
    1. Always include: patient demographics, verified facts (from graph)
    2. Query-focused: semantic search results relevant to the question
    3. Token-aware: stop adding when budget reached
    4. Generate constraints from verified facts

    Args:
        db: PostgreSQL async session
        graph: Neo4j KnowledgeGraph instance
        patient_id: Patient UUID
        query: The clinical question being asked
        token_budget: Maximum tokens for context (default 6000)

    Returns:
        PatientContext with trust-differentiated layers
    """

    tokens_used = 0

    # -------------------------------------------------------------------------
    # 1. Patient demographics (always included, ~200-300 tokens)
    # -------------------------------------------------------------------------
    patient_resource = await get_patient_with_profile(db, patient_id)
    if not patient_resource:
        raise ValueError(f"Patient {patient_id} not found")

    patient = patient_resource.data  # FHIR Patient resource
    profile_summary = format_profile_summary(patient_resource.profile) if patient_resource.profile else None

    tokens_used += len(json.dumps(patient)) // 4
    tokens_used += len(profile_summary or "") // 4

    # -------------------------------------------------------------------------
    # 2. Verified facts from knowledge graph (always included, ~500-1000 tokens)
    # -------------------------------------------------------------------------
    # Get FHIR resources for graph-verified relationships
    verified_conditions = await graph.get_verified_conditions(str(patient_id))
    verified_medications = await graph.get_verified_medications(str(patient_id))
    verified_allergies = await graph.get_verified_allergies(str(patient_id))

    verified_layer = VerifiedLayer(
        conditions=verified_conditions,   # Actual FHIR Condition resources
        medications=verified_medications, # Actual FHIR MedicationRequest resources
        allergies=verified_allergies      # Actual FHIR AllergyIntolerance resources
    )
    tokens_used += verified_layer.token_estimate()

    # -------------------------------------------------------------------------
    # 3. Query-focused retrieval (fill remaining budget)
    # -------------------------------------------------------------------------
    remaining_budget = token_budget - tokens_used
    retrieved_resources = []

    if query and remaining_budget > 500:
        # Semantic search focused on the query
        search_results = await semantic_search(
            db, patient_id, query,
            top_k=30,  # Get more than we need, then filter by budget
            exclude_types=["Patient"]  # Already have patient
        )

        # Add resources until budget exhausted
        for result in search_results:
            resource = result["resource"]
            resource_tokens = len(json.dumps(resource)) // 4

            if tokens_used + resource_tokens > token_budget:
                break  # Budget exhausted

            retrieved_resources.append(RetrievedResource(
                resource=resource,
                resource_type=result["resource_type"],
                score=result["similarity"],
                reason="semantic_match"
            ))
            tokens_used += resource_tokens

    elif remaining_budget > 500:
        # No query: include recent encounters and observations
        recent = await get_recent_resources(db, patient_id, limit=20)
        for resource in recent:
            resource_tokens = len(json.dumps(resource)) // 4
            if tokens_used + resource_tokens > token_budget:
                break
            retrieved_resources.append(RetrievedResource(
                resource=resource,
                resource_type=resource.get("resourceType", "Unknown"),
                score=1.0,
                reason="recent"
            ))
            tokens_used += resource_tokens

    retrieved_layer = RetrievedLayer(resources=retrieved_resources)

    # -------------------------------------------------------------------------
    # 4. Generate reasoning constraints from verified facts
    # -------------------------------------------------------------------------
    constraints = build_constraints(verified_layer)

    # -------------------------------------------------------------------------
    # 5. Assemble final context
    # -------------------------------------------------------------------------
    return PatientContext(
        meta=ContextMeta(
            patient_id=str(patient_id),
            query=query,
            timestamp=datetime.utcnow(),
            retrieval_strategy="query_focused" if query else "recent",
            token_budget=token_budget,
            tokens_used=tokens_used
        ),
        patient=patient,
        profile_summary=profile_summary,  # Include patient profile
        verified=verified_layer,
        retrieved=retrieved_layer,
        constraints=constraints
    )


async def get_patient_with_profile(db: AsyncSession, patient_id: UUID) -> FhirResource | None:
    """Get Patient FHIR resource with attached profile."""
    result = await db.execute(
        select(FhirResource)
        .where(FhirResource.id == patient_id)
        .where(FhirResource.resource_type == "Patient")
    )
    return result.scalar_one_or_none()


def format_profile_summary(profile: dict) -> str:
    """
    Format patient profile for LLM context.

    Concise summary focusing on clinically-relevant personalization factors.
    """
    if not profile:
        return ""

    lines = [
        f"PATIENT PROFILE:",
        f"- Preferred name: {profile.get('preferred_name', 'Unknown')}",
        f"- {profile.get('occupation', '')}",
        f"- {profile.get('family_summary', '')}",
        f"- Interests: {', '.join(profile.get('hobbies', [])[:3])}",
        f"- Health motivation: {profile.get('primary_motivation', '')}",
        f"- Communication style: {profile.get('communication_style', '')}",
        f"- Key barriers: {profile.get('barriers', '')}",
    ]

    return "\n".join(line for line in lines if line.split(": ", 1)[-1].strip())


def build_constraints(verified: VerifiedLayer) -> list[str]:
    """
    Generate reasoning constraints from verified clinical facts.

    These constraints guide the LLM to avoid dangerous recommendations
    based on known patient factors.
    """
    constraints = []

    # Drug allergy constraints
    for allergy in verified.allergies:
        # Extract drug name from FHIR AllergyIntolerance
        codings = allergy.get("code", {}).get("coding", [])
        for coding in codings:
            drug_name = coding.get("display", "")
            if drug_name:
                criticality = allergy.get("criticality", "unknown")
                constraints.append(
                    f"ALLERGY: Patient has {criticality} criticality allergy to {drug_name}. "
                    f"Do not recommend this medication or related drugs."
                )
                break

    # Polypharmacy awareness
    if len(verified.medications) >= 5:
        constraints.append(
            f"POLYPHARMACY: Patient is on {len(verified.medications)} medications. "
            f"Consider drug interactions carefully before recommending additions."
        )

    # Condition-specific constraints (examples)
    for condition in verified.conditions:
        codings = condition.get("code", {}).get("coding", [])
        for coding in codings:
            code = coding.get("code", "")
            display = coding.get("display", "")

            # Renal impairment
            if "kidney" in display.lower() or code in ["585", "N18"]:  # CKD codes
                constraints.append(
                    f"RENAL: Patient has {display}. Adjust renally-cleared medications."
                )

            # Hepatic impairment
            if "liver" in display.lower() or "hepatic" in display.lower():
                constraints.append(
                    f"HEPATIC: Patient has {display}. Adjust hepatically-metabolized medications."
                )

    return constraints
```

### LLM Prompt Formatting

```python
# backend/app/services/prompts.py

def format_context_for_llm(context: PatientContext) -> str:
    """
    Format PatientContext as structured prompt for the LLM.

    Explicitly labels trust levels to help LLM calibrate confidence.
    """

    # Format constraints as a bulleted list
    constraints_text = "\n".join(f"- {c}" for c in context.constraints) if context.constraints else "None"

    return f"""## Clinical Context for Query

### Metadata
- Patient ID: {context.meta.patient_id}
- Query: "{context.meta.query}"
- Retrieval Strategy: {context.meta.retrieval_strategy}
- Context Tokens: {context.meta.tokens_used}/{context.meta.token_budget}

---

### Patient Demographics (FHIR Patient)
```json
{json.dumps(context.patient, indent=2)}
```

---

### VERIFIED CLINICAL FACTS (HIGH CONFIDENCE)

**Source:** Knowledge Graph (Neo4j)
**Trust Level:** HIGH - These facts are verified through explicit clinical relationships.
Use these as ground truth when making clinical assertions.

**Active Conditions ({len(context.verified.conditions)}):**
```json
{json.dumps(context.verified.conditions, indent=2)}
```

**Current Medications ({len(context.verified.medications)}):**
```json
{json.dumps(context.verified.medications, indent=2)}
```

**Known Allergies ({len(context.verified.allergies)}):**
```json
{json.dumps(context.verified.allergies, indent=2)}
```

---

### RETRIEVED CONTEXT (MEDIUM CONFIDENCE)

**Source:** Semantic Search (pgvector)
**Trust Level:** MEDIUM - These resources are semantically relevant to the query.
Cross-reference with verified facts before making clinical assertions.
Information here may be about family members, historical conditions, or tangentially related.

**Retrieved Resources ({len(context.retrieved.resources)}):**
```json
{json.dumps([r.resource for r in context.retrieved.resources], indent=2)}
```

---

### REASONING CONSTRAINTS

These constraints are derived from verified clinical facts. Adhere to them strictly.

{constraints_text}

---

### User Query

{context.meta.query}
"""


CLINICAL_SYSTEM_PROMPT = """You are a clinical decision support assistant helping physicians analyze patient data.

## Your Role
- Analyze patient data in FHIR R4 format
- Provide clinical insights and reasoning
- Identify important findings and trends
- Suggest relevant follow-up questions
- Be concise but thorough

## Understanding Context Trust Levels

You receive patient context in two layers with different trust levels:

### VERIFIED CLINICAL FACTS (HIGH CONFIDENCE)
- Source: Knowledge Graph with verified relationships
- Trust: Use as ground truth
- When citing: State facts confidently ("The patient has Type 2 Diabetes")

### RETRIEVED CONTEXT (MEDIUM CONFIDENCE)
- Source: Semantic search over clinical notes and records
- Trust: Relevant but may contain information about family members, historical conditions, or tangentially related data
- When citing: Qualify statements ("The records suggest..." or "Notes indicate...")

**CRITICAL:** If VERIFIED FACTS and RETRIEVED CONTEXT conflict, trust VERIFIED FACTS.

## FHIR Resources You'll See
- Patient: Demographics and identifiers
- Condition: Diagnoses with clinical status
- Observation: Labs, vitals, measurements
- MedicationRequest: Prescriptions with dosages
- AllergyIntolerance: Drug and other allergies
- Encounter: Visits and admissions
- Procedure: Surgical and clinical procedures

## Reasoning Constraints
Always check the REASONING CONSTRAINTS section. These are derived from verified patient facts and must be followed. For example:
- ALLERGY constraints: Never recommend the allergenic medication
- RENAL constraints: Adjust renally-cleared drug doses
- POLYPHARMACY constraints: Consider interactions carefully

## Response Guidelines
1. Reference specific data from the patient record
2. Use standard medical terminology
3. Flag critical or concerning findings prominently
4. Acknowledge limitations in available data
5. Suggest clinically relevant follow-up questions

## Response Format
You must respond with a JSON object matching this schema:
{
  "thinking": "optional reasoning process",
  "narrative": "main response text in markdown",
  "insights": [{"type": "info|warning|critical|positive", "title": "...", "content": "...", "citations": ["fhir_id"]}],
  "visualizations": [{"type": "line_chart|bar_chart|timeline", "title": "...", "data_query": {...}}],
  "tables": [{"title": "...", "columns": [...], "data_query": {...}}],
  "actions": [{"label": "...", "type": "order|refer|document", "description": "..."}],
  "follow_ups": [{"question": "...", "intent": "..."}]
}

Only include fields that are relevant to your response. The narrative field is required."""
```

### Graph Service Updates

The `KnowledgeGraph` service needs methods that return actual FHIR resources (not just extracted fields):

```python
# backend/app/services/graph.py (additions)

async def get_verified_conditions(self, patient_id: str) -> list[dict]:
    """
    Get FHIR Condition resources for graph-verified active conditions.

    Returns actual FHIR resources, not extracted fields.
    """
    async with self.driver.session() as session:
        result = await session.run("""
            MATCH (p:Patient {id: $patient_id})-[:HAS_CONDITION]->(c:Condition)
            WHERE c.clinical_status = 'active'
            RETURN c.fhir_resource as resource
        """, patient_id=patient_id)
        return [record["resource"] async for record in result]

async def get_verified_medications(self, patient_id: str) -> list[dict]:
    """Get FHIR MedicationRequest resources for active medications."""
    async with self.driver.session() as session:
        result = await session.run("""
            MATCH (p:Patient {id: $patient_id})-[:TAKES_MEDICATION]->(m:Medication)
            WHERE m.status IN ['active', 'on-hold']
            RETURN m.fhir_resource as resource
        """, patient_id=patient_id)
        return [record["resource"] async for record in result]

async def get_verified_allergies(self, patient_id: str) -> list[dict]:
    """Get FHIR AllergyIntolerance resources for known allergies."""
    async with self.driver.session() as session:
        result = await session.run("""
            MATCH (p:Patient {id: $patient_id})-[:HAS_ALLERGY]->(a:Allergy)
            WHERE a.status = 'active'
            RETURN a.fhir_resource as resource
        """, patient_id=patient_id)
        return [record["resource"] async for record in result]
```

**Note:** Graph nodes store the full FHIR resource in a `fhir_resource` property. This preserves FHIR as the native language while enabling graph traversal for relationship verification.

---

## API Design

### Endpoints

```python
# backend/app/routes/__init__.py

# Chat endpoint - main interface
POST /api/chat
  Request: { patient_id: UUID, message: str, conversation_id?: str }
  Response: AgentResponse (JSON, non-streaming)

# Note: Streaming is deferred (P3+). Structured JSON responses don't stream well.
# Future: Stream narrative first, then send complete structured data.

# Patient endpoints
GET  /api/patients                    # List patients
GET  /api/patients/{id}               # Get patient summary
GET  /api/patients/{id}/resources     # Get all FHIR resources for patient

# Data endpoints (for visualizations)
GET  /api/patients/{id}/labs          # Lab results with filters
GET  /api/patients/{id}/medications   # Medications with filters
GET  /api/patients/{id}/conditions    # Conditions with filters
GET  /api/patients/{id}/timeline      # Clinical timeline

# FHIR ingestion
POST /api/fhir/load-bundle            # Load a FHIR bundle
POST /api/fhir/generate-embeddings    # Trigger embedding generation

# Search
POST /api/search/semantic             # Semantic search
POST /api/search/fhirpath             # FHIRPath query
```

### Chat Endpoint Implementation

```python
# backend/app/routes/chat.py
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from app.schemas.chat import ChatRequest, AgentResponse
from app.services.context_engine import build_patient_context
from app.services.agent import generate_response
from app.auth import verify_api_key

router = APIRouter(prefix="/api/chat", tags=["chat"])

@router.post("", response_model=AgentResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_api_key)
):
    """Chat about a patient's clinical data."""

    # Build clinical context
    context = await build_patient_context(
        db,
        request.patient_id,
        query=request.message
    )

    # Generate response
    response = await generate_response(
        context=context,
        message=request.message,
        conversation_history=request.conversation_history
    )

    return response


# Streaming endpoint deferred to P3+
# Rationale: Structured JSON (AgentResponse) doesn't stream well.
# The LLM must complete its response before we can validate and parse the JSON.
# Future approach: Stream narrative first via SSE, then send complete structured data.
```

---

## Testing Strategy

### Core Principle: Fixture-Based Testing

No Synthea generation in CI. Use pre-generated, committed fixtures for deterministic tests.

### Fixture Generation

```python
# scripts/generate_fixtures.py
"""
Generate test fixtures from Synthea.
Run locally, commit results to repo.
"""
import subprocess
import json
import shutil
from pathlib import Path

FIXTURES_DIR = Path("tests/fixtures/synthea")
SYNTHEA_JAR = Path("synthea/synthea-with-dependencies.jar")

def generate_patients(count: int = 5):
    """Generate Synthea patients and save as fixtures."""

    # Clear existing
    if FIXTURES_DIR.exists():
        shutil.rmtree(FIXTURES_DIR)
    FIXTURES_DIR.mkdir(parents=True)

    # Run Synthea
    output_dir = FIXTURES_DIR / "raw"
    subprocess.run([
        "java", "-jar", str(SYNTHEA_JAR),
        "-p", str(count),
        "--exporter.fhir.export", "true",
        "--exporter.ccda.export", "false",
        "--exporter.csv.export", "false",
        "--exporter.baseDirectory", str(output_dir)
    ], check=True)

    # Process bundles
    fhir_dir = output_dir / "fhir"
    for i, bundle_path in enumerate(sorted(fhir_dir.glob("*.json"))):
        if "hospital" in bundle_path.name.lower():
            continue  # Skip hospital info bundles

        # Copy to numbered fixture
        dest = FIXTURES_DIR / f"patient_bundle_{i+1}.json"
        shutil.copy(bundle_path, dest)
        print(f"Created: {dest}")

    # Cleanup raw output
    shutil.rmtree(output_dir)

    print(f"\nGenerated {count} patient fixtures in {FIXTURES_DIR}")

if __name__ == "__main__":
    generate_patients(5)
```

### Fixture Strategy: Small in Git, Full Generated Locally

**Problem:** 100 patients × ~1MB per bundle = ~100MB of JSON. Don't bloat the git repo.

**Solution:**
- **Git:** Commit only 5 test patients for CI/unit tests (~5MB)
- **Local:** Generate full 100-patient dataset via script with deterministic seed
- **Reproducibility:** Same seed = same synthetic patients every time

```
tests/
├── fixtures/
│   └── synthea/
│       ├── patient_bundle_1.json           # FHIR Bundle (committed)
│       ├── patient_bundle_1.profile.json   # Patient profile (committed)
│       ├── patient_bundle_2.json           # (committed)
│       ├── ...                             # 5 patients total in git
│       └── patient_bundle_5.profile.json
├── conftest.py
├── test_fhir_loader.py
├── test_context_engine.py
├── test_semantic_search.py
├── test_chat.py
└── test_api.py

data/                                        # NOT in git (.gitignore)
├── synthea/
│   ├── patient_bundle_1.json               # Full 100 patients
│   ├── patient_bundle_1.profile.json       # Generated locally
│   ├── ...
│   └── patient_bundle_100.profile.json
└── generation_manifest.json                 # Tracks what was generated
```

### Fixture Generation Script

```python
# scripts/generate_fixtures.py
"""
Generate synthetic patient data.

Usage:
  python scripts/generate_fixtures.py --count 5 --output tests/fixtures/synthea  # For git
  python scripts/generate_fixtures.py --count 100 --output data/synthea          # For local
"""
import subprocess
import shutil
from pathlib import Path
import argparse

SYNTHEA_SEED = 12345  # Deterministic: same seed = same patients

def generate_patients(count: int, output_dir: Path):
    """Generate Synthea patients with deterministic seed."""

    output_dir.mkdir(parents=True, exist_ok=True)

    # Run Synthea with seed for reproducibility
    raw_dir = output_dir / "raw"
    subprocess.run([
        "java", "-jar", "synthea/synthea-with-dependencies.jar",
        "-p", str(count),
        "-s", str(SYNTHEA_SEED),  # Deterministic seed
        "--exporter.fhir.export", "true",
        "--exporter.ccda.export", "false",
        "--exporter.csv.export", "false",
        "--exporter.baseDirectory", str(raw_dir)
    ], check=True)

    # Process and rename bundles
    fhir_dir = raw_dir / "fhir"
    for i, bundle_path in enumerate(sorted(fhir_dir.glob("*.json")), 1):
        if "hospital" in bundle_path.name.lower():
            continue
        dest = output_dir / f"patient_bundle_{i}.json"
        shutil.copy(bundle_path, dest)
        print(f"Created: {dest}")

    # Cleanup raw output
    shutil.rmtree(raw_dir)
    print(f"\nGenerated {count} patients in {output_dir}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--output", type=Path, default=Path("tests/fixtures/synthea"))
    args = parser.parse_args()
    generate_patients(args.count, args.output)
```

### Local Setup Script

```bash
#!/bin/bash
# scripts/setup_local_data.sh

# Generate full dataset if not present
if [ ! -d "data/synthea" ]; then
    echo "Generating 100 synthetic patients..."
    python scripts/generate_fixtures.py --count 100 --output data/synthea

    echo "Generating patient profiles..."
    python scripts/generate_patient_profiles.py --input data/synthea

    echo "Loading into database..."
    python scripts/seed_database.py --input data/synthea
fi
```

### .gitignore Addition

```gitignore
# Large generated data (not committed)
/data/
```

### Pytest Configuration

```python
# tests/conftest.py
import pytest
import json
from pathlib import Path
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from app.models import Base

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "synthea"

@pytest.fixture
def sample_bundle() -> dict:
    """Load first patient bundle fixture."""
    with open(FIXTURES_DIR / "patient_bundle_1.json") as f:
        return json.load(f)

@pytest.fixture
def all_bundles() -> list[dict]:
    """Load all patient bundle fixtures."""
    bundles = []
    for path in sorted(FIXTURES_DIR.glob("patient_bundle_*.json")):
        with open(path) as f:
            bundles.append(json.load(f))
    return bundles

@pytest.fixture
async def db_session():
    """Create test database session."""
    engine = create_async_engine(
        "postgresql+asyncpg://postgres:test@localhost:5432/cruxmd_test",
        echo=False
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with AsyncSession(engine) as session:
        yield session
        await session.rollback()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)

@pytest.fixture
async def seeded_db(db_session, sample_bundle):
    """Database seeded with one patient."""
    from app.services.fhir_loader import load_bundle
    await load_bundle(db_session, sample_bundle)
    return db_session
```

### Neo4j Test Configuration

```python
# tests/conftest.py (continued)

from neo4j import AsyncGraphDatabase
from app.services.graph import KnowledgeGraph

@pytest.fixture
async def neo4j_session():
    """Create test Neo4j session with isolated database."""
    # Use a separate test database (or clear before each test)
    driver = AsyncGraphDatabase.driver(
        "bolt://localhost:7687",
        auth=("neo4j", "test-password")
    )

    # Clear all nodes before test
    async with driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")

    yield driver

    # Cleanup after test
    async with driver.session() as session:
        await session.run("MATCH (n) DETACH DELETE n")

    await driver.close()


@pytest.fixture
async def graph(neo4j_session) -> KnowledgeGraph:
    """KnowledgeGraph instance for testing."""
    return KnowledgeGraph(neo4j_session)


@pytest.fixture
async def seeded_db_with_graph(db_session, neo4j_session, sample_bundle):
    """Database and graph seeded with one patient."""
    from app.services.fhir_loader import load_bundle
    graph = KnowledgeGraph(neo4j_session)
    await load_bundle(db_session, graph, sample_bundle)
    return db_session, graph
```

### Integration Test Example

```python
# tests/test_context_engine.py

import pytest
from app.services.context_engine import build_patient_context

@pytest.mark.asyncio
async def test_build_context_includes_verified_facts(seeded_db_with_graph):
    """Context engine should include graph-verified conditions."""
    db, graph = seeded_db_with_graph

    # Get patient ID from seeded data
    patient_id = await get_first_patient_id(db)

    context = await build_patient_context(
        db=db,
        graph=graph,
        patient_id=patient_id,
        query="What conditions does this patient have?"
    )

    # Verified layer should have conditions from graph
    assert len(context.verified.conditions) > 0
    assert all(c.get("resourceType") == "Condition" for c in context.verified.conditions)


@pytest.mark.asyncio
async def test_graph_allergy_verification(seeded_db_with_graph):
    """Graph should correctly verify patient allergies."""
    db, graph = seeded_db_with_graph
    patient_id = await get_first_patient_id(db)

    allergies = await graph.get_verified_allergies(str(patient_id))

    # Synthea patients typically have some allergies
    # Verify the structure is correct FHIR
    for allergy in allergies:
        assert allergy.get("resourceType") == "AllergyIntolerance"
        assert "code" in allergy
```

### CI Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  backend-tests:
    runs-on: ubuntu-latest

    services:
      postgres:
        image: pgvector/pgvector:pg16
        env:
          POSTGRES_PASSWORD: test
          POSTGRES_DB: cruxmd_test
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5

      neo4j:
        image: neo4j:5.26-community
        env:
          NEO4J_AUTH: neo4j/test-password
          NEO4J_server_memory_heap_initial__size: 256m
          NEO4J_server_memory_heap_max__size: 512m
        ports:
          - 7687:7687
        options: >-
          --health-cmd "wget -q http://localhost:7474 -O /dev/null || exit 1"
          --health-interval 10s
          --health-timeout 10s
          --health-retries 5

    steps:
      - uses: actions/checkout@v4

      - name: Install uv
        uses: astral-sh/setup-uv@v4

      - name: Set up Python
        run: uv python install 3.12

      - name: Install dependencies
        run: cd backend && uv sync

      - name: Run tests
        run: cd backend && uv run pytest -v
        env:
          DATABASE_URL: postgresql+asyncpg://postgres:test@localhost:5432/cruxmd_test
          NEO4J_URI: bolt://localhost:7687
          NEO4J_USER: neo4j
          NEO4J_PASSWORD: test-password
          OPENAI_API_KEY: ${{ secrets.OPENAI_API_KEY }}

  frontend-checks:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup pnpm
        uses: pnpm/action-setup@v2
        with:
          version: 9

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: 20
          cache: pnpm
          cache-dependency-path: frontend/pnpm-lock.yaml

      - name: Install dependencies
        run: cd frontend && pnpm install

      - name: Lint
        run: cd frontend && pnpm lint

      - name: Type check
        run: cd frontend && pnpm type-check

      - name: Build
        run: cd frontend && pnpm build
```

---

## Synthetic Patient Profiles

> **Priority:** P1 (Generated during fixture creation)
> **Purpose:** Make demos feel human by giving patients a life beyond their clinical data

### Intent & Motivation

Clinical data alone is sterile. "Patient ID 12345, female, DOB 1957, Type 2 Diabetes" doesn't create an emotional connection during a demo. But "Maria Garcia, a 67-year-old retired teacher who loves gardening and wants to stay healthy enough to dance at her granddaughter's wedding" transforms the experience.

**Why this matters for demos:**
- Colleagues remember stories, not data points
- Personalized context helps the LLM give more natural responses
- Shows the system can integrate social/behavioral context with clinical reasoning
- Creates a "wow factor" that pure clinical data lacks

### Profile Schema

```python
# backend/app/schemas/patient_profile.py

from pydantic import BaseModel

class PatientProfile(BaseModel):
    """Non-clinical narrative about the patient's life."""

    # Identity
    preferred_name: str              # "Maria" (vs legal name "Maria Elena Garcia")
    pronouns: str                    # "she/her"
    occupation: str                  # "Retired elementary school teacher"

    # Family & Social
    family_summary: str              # "Married to Roberto for 42 years. Three children, five grandchildren."
    living_situation: str            # "Lives with husband in a single-story home"
    social_connections: str          # "Active in church community, weekly bingo with friends"

    # Life Story
    background: str                  # "Grew up in a small town, first in family to attend college..."
    personality: str                 # "Warm and talkative, tends to minimize symptoms"
    communication_style: str         # "Prefers detailed explanations, asks many questions"

    # Interests & Lifestyle
    hobbies: list[str]               # ["Gardening", "Baking", "Reading mystery novels"]
    daily_routine: str               # "Early riser, tends garden in morning, afternoon rest"
    diet_preferences: str            # "Traditional Mexican cooking, trying to reduce carbs"
    exercise_habits: str             # "Walks 20 minutes daily, water aerobics twice weekly"

    # Health Motivations
    health_goals: str                # "Wants to stay active for grandchildren"
    primary_motivation: str          # "Dancing at granddaughter's quinceañera next year"
    health_concerns: str             # "Worried about vision loss from diabetes"
    barriers: str                    # "Hard time saying no to family gatherings with rich food"

    # Behavioral Insights
    adherence_factors: str           # "Better with routines, tends to skip evening meds"
    stress_factors: str              # "Worries about adult son's job situation"
    support_system: str              # "Husband very supportive, daughter helps with appointments"
```

### Generation Approach

Profiles are generated during Synthea fixture creation, not at runtime.

```python
# scripts/generate_patient_profiles.py

import json
from pathlib import Path
from openai import OpenAI

PROFILE_PROMPT = """
Based on this patient's clinical data, create a rich, believable personal profile.

PATIENT DATA:
{patient_summary}

CLINICAL CONTEXT:
- Age: {age}
- Gender: {gender}
- Active Conditions: {conditions}
- Recent Encounters: {encounters}

Create a profile that:
1. Feels like a real person with a coherent life story
2. Has interests and motivations that feel natural for their demographics
3. Includes health motivations connected to their personal life
4. Has realistic barriers and support systems
5. Shows personality in how they might interact with healthcare

The profile should subtly reflect their clinical situation:
- A diabetic patient might mention dietary challenges
- Someone with chronic pain might have adapted hobbies
- An elderly patient might mention family support structures

Output valid JSON matching this schema:
{schema}
"""

async def generate_profile_for_patient(
    client: OpenAI,
    patient_bundle: dict
) -> dict:
    """Generate a narrative profile from Synthea FHIR data."""

    # Extract relevant info from bundle
    patient = extract_patient_resource(patient_bundle)
    conditions = extract_conditions(patient_bundle)
    encounters = extract_recent_encounters(patient_bundle)

    patient_summary = format_patient_summary(patient)

    response = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": PROFILE_PROMPT.format(
                patient_summary=patient_summary,
                age=calculate_age(patient),
                gender=patient.get("gender", "unknown"),
                conditions=format_conditions(conditions),
                encounters=format_encounters(encounters),
                schema=PatientProfile.model_json_schema()
            )
        }],
        response_format={"type": "json_object"}
    )

    return json.loads(response.choices[0].message.content)


async def generate_all_profiles(fixtures_dir: Path):
    """Generate profiles for all patient fixtures."""

    client = OpenAI()
    profiles = {}

    for bundle_path in fixtures_dir.glob("patient_bundle_*.json"):
        with open(bundle_path) as f:
            bundle = json.load(f)

        patient_id = extract_patient_id(bundle)
        print(f"Generating profile for {bundle_path.name}...")

        profile = await generate_profile_for_patient(client, bundle)
        profiles[patient_id] = profile

        # Also save alongside the bundle
        profile_path = bundle_path.with_suffix(".profile.json")
        with open(profile_path, "w") as f:
            json.dump(profile, f, indent=2)

    # Save combined profiles file
    with open(fixtures_dir / "patient_profiles.json", "w") as f:
        json.dump(profiles, f, indent=2)

    print(f"Generated {len(profiles)} patient profiles")
```

### Storage & Integration

```python
# backend/app/models.py (extended)

class FhirResource(Base):
    # ... existing fields ...

    # Patient profile (only for Patient resources)
    profile = Column(JSON, nullable=True)  # PatientProfile data


# Loading profile with patient
async def load_bundle_with_profile(
    db: AsyncSession,
    bundle: dict,
    profile: dict | None = None
):
    """Load FHIR bundle and attach profile to Patient resource."""

    patient_id = await load_bundle(db, bundle)

    if profile:
        await db.execute(
            update(FhirResource)
            .where(
                FhirResource.patient_id == patient_id,
                FhirResource.resource_type == "Patient"
            )
            .values(profile=profile)
        )

    return patient_id
```

### Context Engine Integration

The patient profile becomes part of the verified context (it's a known fact about the patient):

```python
# backend/app/services/context_engine.py (extended)

async def build_patient_context(...) -> PatientContext:
    # ... existing code ...

    # Get patient with profile
    patient = await get_patient_resource(db, patient_id)
    profile = patient.get("_profile")  # Stored in extension or separate field

    # Include profile summary in verified layer metadata
    if profile:
        verified_layer.profile_summary = format_profile_summary(profile)

    # ...


def format_profile_summary(profile: dict) -> str:
    """Create concise profile summary for LLM context."""
    return f"""
PATIENT PROFILE:
- {profile['preferred_name']}, {profile['occupation']}
- {profile['family_summary']}
- Interests: {', '.join(profile['hobbies'])}
- Health motivation: {profile['primary_motivation']}
- Communication style: {profile['communication_style']}
- Key barriers: {profile['barriers']}
"""
```

### System Prompt Integration

```python
CLINICAL_SYSTEM_PROMPT = """
...

## Patient Profile

When provided, the PATIENT PROFILE gives you insight into who this person is beyond their clinical data. Use this to:
- Address them by their preferred name
- Reference their motivations when discussing treatment adherence
- Consider their lifestyle when making suggestions
- Acknowledge their support system and barriers
- Match their communication style

Example: Instead of "You should exercise more," try "Maria, I know you enjoy your morning garden time. Could you extend that walk around the yard to 30 minutes?"

The profile is for personalization—it does not override clinical facts.
"""
```

### Fixture Structure (Updated)

```
tests/fixtures/synthea/
├── patient_bundle_1.json           # FHIR Bundle
├── patient_bundle_1.profile.json   # Generated profile
├── patient_bundle_2.json
├── patient_bundle_2.profile.json
├── ...
└── patient_profiles.json           # Combined profiles file
```

---

## Project Structure

```
cruxmd-v2/
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py                 # FastAPI app entry point
│   │   ├── config.py               # Settings (env vars)
│   │   ├── database.py             # SQLAlchemy setup
│   │   ├── models.py               # FhirResource model (~50 lines)
│   │   ├── auth.py                 # Simple API key auth
│   │   │
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   ├── chat.py             # Chat endpoints
│   │   │   ├── patients.py         # Patient CRUD
│   │   │   ├── fhir.py             # FHIR ingestion
│   │   │   └── search.py           # Search endpoints
│   │   │
│   │   ├── services/
│   │   │   ├── __init__.py
│   │   │   ├── fhir_loader.py      # Bundle loading (~150 lines)
│   │   │   ├── embeddings.py       # Embedding generation
│   │   │   ├── graph.py            # Neo4j knowledge graph service
│   │   │   ├── context_engine.py   # Hybrid retrieval (graph + vector)
│   │   │   ├── agent.py            # LLM agent logic
│   │   │   ├── prompts.py          # System prompts
│   │   │   └── search.py           # Semantic & FHIRPath search
│   │   │
│   │   └── schemas/
│   │       ├── __init__.py
│   │       ├── agent.py            # AgentResponse schema
│   │       ├── chat.py             # Chat request/response
│   │       └── fhir.py             # FHIR-related schemas
│   │
│   ├── tests/
│   │   ├── fixtures/
│   │   │   └── synthea/
│   │   │       └── patient_bundle_*.json
│   │   ├── conftest.py
│   │   └── test_*.py
│   │
│   ├── alembic/
│   │   ├── env.py
│   │   └── versions/
│   │
│   ├── pyproject.toml
│   ├── uv.lock
│   └── Dockerfile
│
├── frontend/
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx
│   │   └── chat/
│   │       └── page.tsx            # Main conversational canvas
│   │
│   ├── components/
│   │   ├── canvas/
│   │   │   ├── ConversationalCanvas.tsx
│   │   │   ├── MessageHistory.tsx
│   │   │   ├── AgentMessage.tsx
│   │   │   ├── UserMessage.tsx
│   │   │   ├── ChatInput.tsx
│   │   │   └── ThinkingIndicator.tsx
│   │   │
│   │   ├── clinical/
│   │   │   ├── InsightCard.tsx
│   │   │   ├── LabResultsChart.tsx
│   │   │   ├── LabResultsTable.tsx
│   │   │   ├── MedicationList.tsx
│   │   │   ├── ConditionList.tsx
│   │   │   ├── Timeline.tsx
│   │   │   ├── ActionButton.tsx
│   │   │   └── KnowledgeGraphView.tsx  # Interactive graph visualization (P4)
│   │   │
│   │   ├── patient/
│   │   │   ├── PatientSelector.tsx
│   │   │   └── PatientHeader.tsx
│   │   │
│   │   └── ui/                     # shadcn/ui components
│   │
│   ├── lib/
│   │   ├── api.ts
│   │   ├── types.ts
│   │   └── utils.ts
│   │
│   ├── hooks/
│   │   ├── use-chat.ts
│   │   ├── use-patient.ts
│   │   └── use-labs.ts
│   │
│   ├── package.json
│   ├── pnpm-lock.yaml
│   ├── tsconfig.json
│   ├── tailwind.config.ts
│   ├── next.config.js
│   └── Dockerfile
│
├── scripts/
│   ├── generate_fixtures.py        # Generate Synthea fixtures
│   ├── generate_patient_profiles.py # Generate LLM patient profiles (P1)
│   ├── generate_clinical_notes.py  # Generate synthetic notes (P3)
│   ├── seed_local.py               # Seed local dev database
│   └── deploy.sh                   # VPS deployment script
│
├── docker-compose.yml              # Local development
├── docker-compose.prod.yml         # Production
├── Caddyfile                       # Reverse proxy config
├── .env.example
├── .gitignore
├── README.md
└── .github/
    └── workflows/
        └── ci.yml
```

### Line Count Targets

| File | Target Lines | vs v1 |
|------|--------------|-------|
| `models.py` | ~50 | 1,397 |
| `fhir_loader.py` | ~150 | 1,710 |
| `graph.py` | ~250 | N/A (new) |
| `context_engine.py` | ~200 | N/A |
| `agent.py` | ~150 | N/A |
| Total backend | ~2,500 | ~10,000+ |

---

## Implementation Phases

### P0: Foundation

**Goal:** Basic infrastructure running locally and on VPS, with rich patient fixtures

**Tasks:**
- [ ] Create new repository
- [ ] Set up backend with FastAPI + uv
- [ ] Implement FhirResource model and PostgreSQL database
- [ ] Create initial Alembic migration from models
- [ ] Set up Neo4j container and verify connectivity
- [ ] Create simplified FHIR bundle loader with graph population
- [ ] Generate Synthea fixtures (5 patients)
- [ ] **Generate patient profiles** (LLM-generated narratives for each patient)
- [ ] Commit fixtures + profiles to repo
- [ ] Set up Next.js frontend with shadcn/ui
- [ ] Configure OpenAPI schema generation and TypeScript client
- [ ] Provision Hetzner VPS
- [ ] Configure Docker Compose + Caddy (including Neo4j)
- [ ] Deploy to VPS

**Deliverable:** App running at app.cruxmd.ai with patients loaded (including personal profiles) in both PostgreSQL and Neo4j

### P1: Chat MVP + Knowledge Graph

**Goal:** Working chat with hybrid retrieval (vectors + graph)

**Tasks:**
- [ ] Implement embedding generation for FHIR resources (sync during bundle load)
- [ ] Build Knowledge Graph service (Neo4j integration)
- [ ] Implement graph building from FHIR during ingestion
- [ ] Create verified facts retrieval (conditions, meds, allergies from graph)
- [ ] Build context engine with hybrid retrieval (graph + vector)
- [ ] Implement chat endpoint with structured output
- [ ] Create ConversationalCanvas component
- [ ] Implement AgentMessage renderer
- [ ] Add PatientSelector component
- [ ] Create InsightCard component
- [ ] Wire up streaming responses

**Deliverable:** Can select patient and chat, with verified facts from graph and relevant context from vectors

### P2: Visualizations + Synthetic Notes

**Goal:** Rich clinical data visualizations and realistic clinical documentation

**Tasks:**
- [ ] Implement LabResultsChart component
- [ ] Implement MedicationList component
- [ ] Implement ConditionList component
- [ ] Create data fetching hooks (useLabs, useMedications, etc.)
- [ ] Add Timeline component
- [ ] Implement visualization data queries from agent responses
- [ ] Add ActionButton component (placeholder actions)
- [ ] **Generate synthetic progress notes** from Synthea encounters
- [ ] **Generate synthetic imaging reports** from DiagnosticReports
- [ ] Store notes as DocumentReference FHIR resources
- [ ] Embed notes for semantic search
- [ ] Commit note fixtures to repo

**Deliverable:** Agent can generate charts/tables, and notes are searchable context for clinical queries

### P3: Polish & Graph Visualization

**Goal:** Demo-ready platform with knowledge graph UI

**Tasks:**
- [ ] Conversation persistence (database storage)
- [ ] Better error handling and fallbacks
- [ ] Loading states and skeletons
- [ ] Mobile responsiveness (basic)
- [ ] **Knowledge graph visualization component** (patient data as interactive graph)
- [ ] Add more clinical components as needed
- [ ] Drug interaction checking via graph traversal

**Deliverable:** Demo-ready platform with graph visualization for work presentations

### P4: Semantic Memory Layer

**Goal:** Persistent memory across sessions with derived insights

**Tasks:**
- [ ] Session persistence (store conversation history)
- [ ] Session summary generation at session end
- [ ] Semantic retrieval of past session context
- [ ] Derived observations with mandatory FHIR grounding
- [ ] Clinical pattern detection (batch analysis)
- [ ] Validation workflow for derived insights

**Deliverable:** Continuity across conversations, pattern recognition, grounded insights

### P4: LLM-Based Data Ingestion

**Goal:** Extract structured FHIR from unstructured clinical text

**Tasks:**
- [ ] Build extraction pipeline (LLM with FHIR schema output)
- [ ] Terminology normalization service (LOINC, SNOMED, RxNorm lookup)
- [ ] Deduplication logic (detect existing resources)
- [ ] Provenance tracking (link extracted facts to source text)
- [ ] Knowledge Graph integration with `source: "extracted"` edges
- [ ] Validation against ground truth (closed-loop testing with generated notes)

**Deliverable:** Ability to ingest messy real-world clinical documents

### P5: Medical Ontology Integration

**Goal:** Connect patient-specific graphs to universal medical knowledge

**Tasks:**
- [ ] Import LOINC subset (~2000 common lab codes)
- [ ] Import SNOMED CT core subset (~20K concepts)
- [ ] Import RxNorm with drug classes and interactions
- [ ] Link patient conditions/medications to ontology nodes
- [ ] Implement query expansion via ontology traversal
- [ ] Implement clinical inference from ontology relationships

**Deliverable:** Graph-powered clinical reasoning with ontology grounding

### P5: Multi-Patient Queries

**Goal:** Cohort analysis and population-level insights

**Tasks:**
- [ ] Design cohort query interface
- [ ] Implement cross-patient aggregation queries
- [ ] Build cohort visualization components
- [ ] Add comparative analysis features

**Deliverable:** Ability to ask questions across multiple patients

---

## Technical Specifications

### Backend Dependencies

```toml
# backend/pyproject.toml
[project]
name = "cruxmd-backend"
version = "0.1.0"
requires-python = ">=3.12"
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.32.0",
    "sqlalchemy[asyncio]>=2.0.0",
    "asyncpg>=0.30.0",
    "pgvector>=0.3.0",
    "alembic>=1.14.0",
    "pydantic>=2.0.0",
    "pydantic-settings>=2.0.0",
    "openai>=1.50.0",
    "httpx>=0.27.0",
    # "fhirpathpy>=0.1.0",       # Future: FHIRPath queries (P5+)
    "python-multipart>=0.0.12",
    "neo4j>=5.26.0",              # Knowledge graph database driver
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.24.0",
    "pytest-cov>=6.0.0",
    "ruff>=0.7.0",
]
```

### Frontend Dependencies

```json
// frontend/package.json
{
  "name": "cruxmd-frontend",
  "version": "0.1.0",
  "scripts": {
    "dev": "next dev --turbopack",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "type-check": "tsc --noEmit"
  },
  "dependencies": {
    "next": "^15.0.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0",
    "tailwindcss": "^3.4.0",
    "@tailwindcss/typography": "^0.5.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.0.0",
    "tailwind-merge": "^2.0.0",
    "lucide-react": "^0.460.0",
    "recharts": "^2.13.0",
    "react-markdown": "^9.0.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "typescript": "^5.6.0",
    "@types/react": "^19.0.0",
    "@types/node": "^22.0.0",
    "eslint": "^9.0.0",
    "eslint-config-next": "^15.0.0"
  }
}
```

### Environment Variables

```bash
# .env.example

# PostgreSQL Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/cruxmd

# Neo4j Knowledge Graph
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=your-neo4j-password

# Authentication
API_KEY=your-api-key-here

# OpenAI
OPENAI_API_KEY=sk-...

# Frontend
NEXT_PUBLIC_API_URL=http://localhost:8000
NEXT_PUBLIC_API_KEY=your-api-key-here
```

### TypeScript Type Sharing Strategy

**Goal:** Ensure frontend TypeScript types stay in sync with backend Pydantic schemas without manual duplication.

**Approach:** Generate TypeScript client from OpenAPI schema using `@hey-api/openapi-ts`.

**Implementation:**

```json
// frontend/package.json (scripts)
{
  "scripts": {
    "generate-api": "openapi-ts --input ../backend/openapi.json --output ./lib/api/generated --client fetch"
  }
}
```

**Workflow:**

1. **Backend generates OpenAPI schema:**
   ```python
   # backend/app/main.py
   from fastapi import FastAPI
   from fastapi.openapi.utils import get_openapi
   import json

   app = FastAPI()

   # Export schema during build/startup
   def export_openapi_schema():
       schema = get_openapi(
           title=app.title,
           version=app.version,
           routes=app.routes,
       )
       with open("openapi.json", "w") as f:
           json.dump(schema, f, indent=2)
   ```

2. **Frontend generates TypeScript types:**
   ```bash
   cd frontend && pnpm generate-api
   ```

3. **Pre-commit hook ensures sync:**
   ```yaml
   # .pre-commit-config.yaml
   - repo: local
     hooks:
       - id: generate-api-types
         name: Generate API TypeScript types
         entry: bash -c 'cd frontend && pnpm generate-api'
         language: system
         files: 'backend/.*\.py$'
   ```

**Generated Types Example:**

```typescript
// frontend/lib/api/generated/types.ts (auto-generated)
export interface AgentResponse {
  thinking?: string;
  narrative: string;
  insights?: Insight[];
  visualizations?: Visualization[];
  tables?: DataTable[];
  actions?: Action[];
  followUps?: FollowUp[];
}

export interface ChatRequest {
  patient_id: string;
  message: string;
  conversation_history?: Message[];
}

// ... all types from backend Pydantic schemas
```

**Usage in Frontend:**

```typescript
// frontend/lib/api.ts
import type { AgentResponse, ChatRequest } from "./api/generated/types";
import { chatChat, chatStream } from "./api/generated/services";

// Type-safe API calls
export async function sendChatMessage(request: ChatRequest): Promise<AgentResponse> {
  return chatChat({ body: request });
}
```

**Benefits:**
- Single source of truth (backend Pydantic models)
- Compile-time type checking catches API mismatches
- No manual synchronization of types
- IDE autocompletion for API responses

---

## P4: Semantic Memory Layer

> **Priority:** P4
> **Dependencies:** Context Engine (P2), Knowledge Graph (P2)

### Intent & Motivation

The current Context Engine provides excellent **per-query** context assembly: verified facts from the graph, relevant resources from vector search, all trust-differentiated. But it has no memory across sessions or ability to build longitudinal patient understanding.

A Semantic Memory Layer would enable:
- **Continuity**: "Last time we discussed your diabetes management..."
- **Pattern Recognition**: "Your HbA1c tends to spike after winter holidays"
- **Derived Insights**: Observations synthesized by the LLM from raw data
- **Grounded Reasoning**: Every insight cites underlying FHIR resources

### Episodic vs Semantic Memory

This distinction from cognitive science maps directly to clinical data:

| Memory Type | Definition | Clinical Example | Storage |
|-------------|------------|------------------|---------|
| **Episodic** | Specific events with temporal context | "MedicationRequest for Metformin 500mg on 2024-03-15" | Raw FHIR resources (existing) |
| **Semantic** | Consolidated facts without temporal binding | "Patient is currently on Metformin for diabetes" | Knowledge Graph (existing) |
| **Derived** | Synthesized observations from patterns | "Patient shows medication non-adherence pattern based on refill gaps" | Semantic Memory (new) |

**Key insight:** Our existing architecture already handles episodic (FHIR resources) and semantic (Knowledge Graph verified facts). The Semantic Memory Layer adds the **derived** tier—LLM-synthesized insights that must be explicitly grounded in source data.

### Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                         SEMANTIC MEMORY LAYER                               │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  SESSION MEMORY                                                      │   │
│  │  ─────────────────                                                   │   │
│  │  Purpose: Maintain context within and across conversation sessions   │   │
│  │                                                                      │   │
│  │  • Conversation history (messages, not just text)                    │   │
│  │  • Topics discussed with patient context                             │   │
│  │  • Conclusions reached (with confidence levels)                      │   │
│  │  • Questions asked but not fully answered                            │   │
│  │  • Session summaries (LLM-generated, stored for retrieval)           │   │
│  │                                                                      │   │
│  │  Storage: PostgreSQL (sessions table, linked to patient)             │   │
│  │  Retrieval: By patient_id, recency, or semantic similarity           │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  PATIENT MEMORY (Derived Observations)                               │   │
│  │  ────────────────────────────────────────                           │   │
│  │  Purpose: LLM-synthesized insights grounded in FHIR data             │   │
│  │                                                                      │   │
│  │  Examples:                                                           │   │
│  │  • "Likely non-compliant with Metformin (3 refill gaps > 30 days)"  │   │
│  │  • "Anxiety appears correlated with ER visits (4/5 visits)"         │   │
│  │  • "Responds positively to lifestyle counseling (A1c drops)"        │   │
│  │                                                                      │   │
│  │  Each observation MUST include:                                      │   │
│  │  • Confidence level (low/medium/high)                                │   │
│  │  • Supporting FHIR resource IDs (grounding)                          │   │
│  │  • Derivation timestamp                                              │   │
│  │  • Source session ID (provenance)                                    │   │
│  │                                                                      │   │
│  │  Storage: PostgreSQL (patient_observations table)                    │   │
│  │  Validation: Periodic review, can be marked disputed/confirmed       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │  CLINICAL PATTERNS                                                   │   │
│  │  ─────────────────                                                   │   │
│  │  Purpose: Temporal and behavioral patterns detected across data      │   │
│  │                                                                      │   │
│  │  Examples:                                                           │   │
│  │  • "HbA1c rises 0.3-0.5% in Q4 (observed 2022, 2023, 2024)"         │   │
│  │  • "BP spikes precede migraines by 24-48 hours"                     │   │
│  │  • "Hospitalization risk increases when >3 meds missed"             │   │
│  │                                                                      │   │
│  │  Each pattern MUST include:                                          │   │
│  │  • Pattern type (temporal, correlation, threshold)                   │   │
│  │  • Supporting FHIR resource IDs (full citation list)                 │   │
│  │  • Statistical confidence (if applicable)                            │   │
│  │  • Date range observed                                               │   │
│  │  • Last validation date                                              │   │
│  │                                                                      │   │
│  │  Storage: PostgreSQL (patient_patterns table) or Neo4j (as nodes)    │   │
│  │  Integration: Can be added to Knowledge Graph as derived edges       │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Data Models

```python
# backend/app/models/memory.py

from sqlalchemy import Column, String, DateTime, ForeignKey, JSON, Enum
from sqlalchemy.dialects.postgresql import UUID, ARRAY
from sqlalchemy.orm import relationship
import enum

class ConfidenceLevel(enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

class ObservationStatus(enum.Enum):
    ACTIVE = "active"
    DISPUTED = "disputed"
    CONFIRMED = "confirmed"
    SUPERSEDED = "superseded"


class Session(Base):
    """A conversation session with a patient's data."""
    __tablename__ = "sessions"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID, ForeignKey("fhir_resources.patient_id"), nullable=False)
    started_at = Column(DateTime, nullable=False)
    ended_at = Column(DateTime, nullable=True)

    # Session summary (LLM-generated at session end)
    summary = Column(String, nullable=True)
    topics_discussed = Column(ARRAY(String), default=[])
    key_conclusions = Column(JSON, default=[])  # [{text, confidence, fhir_refs}]

    # For semantic retrieval of past sessions
    summary_embedding = Column(Vector(1536), nullable=True)

    messages = relationship("Message", back_populates="session")


class Message(Base):
    """Individual message in a session."""
    __tablename__ = "messages"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID, ForeignKey("sessions.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" | "assistant"
    content = Column(String, nullable=False)
    timestamp = Column(DateTime, nullable=False)

    # For assistant messages: structured response stored
    structured_response = Column(JSON, nullable=True)

    session = relationship("Session", back_populates="messages")


class PatientObservation(Base):
    """
    LLM-derived observation about a patient.

    CRITICAL: Must be grounded in specific FHIR resources.
    """
    __tablename__ = "patient_observations"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID, nullable=False)

    # The observation itself
    observation = Column(String, nullable=False)
    observation_type = Column(String, nullable=False)  # "adherence", "correlation", "risk", etc.

    # GROUNDING - mandatory citations
    supporting_fhir_ids = Column(ARRAY(UUID), nullable=False)  # Must have at least 1
    reasoning = Column(String, nullable=False)  # How the observation was derived

    # Confidence and provenance
    confidence = Column(Enum(ConfidenceLevel), nullable=False)
    status = Column(Enum(ObservationStatus), default=ObservationStatus.ACTIVE)
    derived_at = Column(DateTime, nullable=False)
    source_session_id = Column(UUID, ForeignKey("sessions.id"), nullable=True)

    # For semantic retrieval
    embedding = Column(Vector(1536), nullable=True)


class ClinicalPattern(Base):
    """
    Temporal or behavioral pattern detected in patient data.

    CRITICAL: Must cite all supporting FHIR resources.
    """
    __tablename__ = "clinical_patterns"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    patient_id = Column(UUID, nullable=False)

    # Pattern description
    pattern = Column(String, nullable=False)
    pattern_type = Column(String, nullable=False)  # "temporal", "correlation", "threshold"

    # GROUNDING - full citation list
    supporting_fhir_ids = Column(ARRAY(UUID), nullable=False)
    date_range_start = Column(DateTime, nullable=False)
    date_range_end = Column(DateTime, nullable=False)

    # Statistical backing (if applicable)
    statistical_confidence = Column(String, nullable=True)  # e.g., "p < 0.05", "r = 0.72"
    occurrences = Column(Integer, nullable=True)  # How many times pattern observed

    # Validation
    last_validated = Column(DateTime, nullable=False)
    status = Column(Enum(ObservationStatus), default=ObservationStatus.ACTIVE)

    # For semantic retrieval
    embedding = Column(Vector(1536), nullable=True)
```

### Grounding Protocol

**Every derived insight MUST be grounded.** This is non-negotiable for clinical safety.

```python
# backend/app/services/memory.py

from dataclasses import dataclass

@dataclass
class GroundedObservation:
    """An observation with mandatory FHIR grounding."""
    text: str
    confidence: ConfidenceLevel
    supporting_resources: list[dict]  # Actual FHIR resources, not just IDs
    reasoning: str

    def validate(self) -> bool:
        """Ensure observation is properly grounded."""
        if not self.supporting_resources:
            raise ValueError("Observation must cite at least one FHIR resource")
        if not self.reasoning:
            raise ValueError("Observation must include derivation reasoning")
        return True

    def to_display(self) -> dict:
        """Format for display with citations."""
        return {
            "observation": self.text,
            "confidence": self.confidence.value,
            "citations": [
                {
                    "resource_type": r.get("resourceType"),
                    "id": r.get("id"),
                    "summary": self._summarize_resource(r)
                }
                for r in self.supporting_resources
            ],
            "reasoning": self.reasoning
        }

    def _summarize_resource(self, resource: dict) -> str:
        """Create human-readable summary of FHIR resource."""
        rt = resource.get("resourceType", "Unknown")
        if rt == "MedicationRequest":
            med = resource.get("medicationCodeableConcept", {}).get("text", "Unknown medication")
            date = resource.get("authoredOn", "Unknown date")
            return f"{med} prescribed on {date}"
        elif rt == "Observation":
            code = resource.get("code", {}).get("text", "Unknown observation")
            value = resource.get("valueQuantity", {}).get("value", "N/A")
            unit = resource.get("valueQuantity", {}).get("unit", "")
            return f"{code}: {value} {unit}"
        # ... other resource types
        return f"{rt} resource"


async def derive_observation(
    llm: LLMClient,
    patient_context: PatientContext,
    observation_prompt: str
) -> GroundedObservation | None:
    """
    Ask LLM to derive an observation with mandatory grounding.

    The LLM must cite specific FHIR resources from the context.
    If it cannot ground the observation, it should return null.
    """
    system_prompt = """
    You are analyzing patient data to derive clinical observations.

    RULES:
    1. You may ONLY make observations that can be directly supported by the provided FHIR resources
    2. You MUST cite specific resource IDs for every claim
    3. If you cannot find supporting evidence, respond with {"observation": null}
    4. Explain your reasoning for how the cited resources support the observation

    Output JSON:
    {
        "observation": "The derived observation text",
        "confidence": "low" | "medium" | "high",
        "supporting_resource_ids": ["id1", "id2", ...],
        "reasoning": "How these resources support this observation"
    }
    """

    response = await llm.generate(
        system=system_prompt,
        user=f"Context:\n{patient_context.to_json()}\n\nDerive observation about: {observation_prompt}",
        response_format={"type": "json_object"}
    )

    data = json.loads(response)
    if not data.get("observation"):
        return None

    # Retrieve actual FHIR resources for the cited IDs
    resource_ids = data["supporting_resource_ids"]
    resources = await get_resources_by_ids(patient_context.db, resource_ids)

    # Validate that cited resources exist
    if len(resources) != len(resource_ids):
        raise ValueError(f"LLM cited non-existent resources: {resource_ids}")

    return GroundedObservation(
        text=data["observation"],
        confidence=ConfidenceLevel(data["confidence"]),
        supporting_resources=resources,
        reasoning=data["reasoning"]
    )
```

### Session Memory Integration

```python
# backend/app/services/session_memory.py

async def get_relevant_session_history(
    db: AsyncSession,
    patient_id: UUID,
    current_query: str,
    max_sessions: int = 3
) -> list[dict]:
    """
    Retrieve summaries from relevant past sessions.

    Uses semantic similarity to find sessions where similar topics were discussed.
    """
    query_embedding = await get_embedding(current_query)

    result = await db.execute(
        text("""
            SELECT
                id,
                started_at,
                summary,
                topics_discussed,
                key_conclusions,
                1 - (summary_embedding <=> :embedding) as similarity
            FROM sessions
            WHERE patient_id = :patient_id
            AND summary IS NOT NULL
            AND ended_at IS NOT NULL
            ORDER BY similarity DESC
            LIMIT :max_sessions
        """),
        {
            "patient_id": patient_id,
            "embedding": query_embedding,
            "max_sessions": max_sessions
        }
    )

    return [
        {
            "session_id": str(row.id),
            "date": row.started_at.isoformat(),
            "summary": row.summary,
            "topics": row.topics_discussed,
            "conclusions": row.key_conclusions,
            "relevance": float(row.similarity)
        }
        for row in result.fetchall()
    ]


async def generate_session_summary(
    llm: LLMClient,
    session: Session
) -> str:
    """
    Generate a summary at the end of a session.

    Called when session ends (user leaves or timeout).
    """
    messages = await get_session_messages(session.id)

    system_prompt = """
    Summarize this clinical consultation session.

    Include:
    1. Main topics discussed
    2. Key clinical questions asked
    3. Important findings or conclusions
    4. Any unresolved questions or follow-ups needed

    Be concise but capture the essential clinical context for future reference.
    """

    summary = await llm.generate(
        system=system_prompt,
        user=format_messages_for_summary(messages)
    )

    return summary
```

### Context Engine Integration

When the Semantic Memory Layer is implemented, the Context Engine will be extended:

```python
# Extended PatientContext (future)

@dataclass
class PatientContext:
    # Existing fields
    meta: ContextMeta
    patient: dict
    verified: VerifiedLayer
    retrieved: RetrievedLayer
    constraints: list[str]

    # NEW: Semantic Memory fields
    session_history: list[dict] | None = None      # Relevant past session summaries
    derived_observations: list[dict] | None = None  # Grounded patient observations
    clinical_patterns: list[dict] | None = None     # Detected patterns with citations


async def build_patient_context_with_memory(
    db: AsyncSession,
    graph: KnowledgeGraph,
    patient_id: UUID,
    query: str,
    token_budget: int = 6000,
    include_memory: bool = True
) -> PatientContext:
    """
    Build context with semantic memory integration.

    Memory components are optional and token-budgeted.
    """
    # ... existing context building ...

    if include_memory and remaining_budget > 500:
        # Add relevant session history
        session_history = await get_relevant_session_history(
            db, patient_id, query, max_sessions=2
        )

        # Add relevant derived observations
        observations = await get_relevant_observations(
            db, patient_id, query, max_observations=5
        )

        # Add relevant patterns
        patterns = await get_relevant_patterns(
            db, patient_id, query, max_patterns=3
        )

    return PatientContext(
        # ... existing fields ...
        session_history=session_history,
        derived_observations=observations,
        clinical_patterns=patterns
    )
```

### System Prompt Update (Future)

```python
CLINICAL_SYSTEM_PROMPT_WITH_MEMORY = """
You are a clinical decision support assistant...

## Understanding Context Trust Levels

### VERIFIED CLINICAL FACTS (HIGH CONFIDENCE)
[existing content]

### RETRIEVED CONTEXT (MEDIUM CONFIDENCE)
[existing content]

### SEMANTIC MEMORY (VARIABLE CONFIDENCE)

You may receive three types of memory:

**SESSION HISTORY**: Summaries of past conversations about this patient.
- Use to maintain continuity ("As we discussed last time...")
- Note if conclusions from past sessions are still relevant

**DERIVED OBSERVATIONS**: LLM-synthesized insights with FHIR citations.
- Each observation includes supporting resource IDs
- Confidence levels indicate reliability
- Cross-reference with VERIFIED FACTS when possible
- If observation conflicts with VERIFIED FACTS, trust VERIFIED FACTS

**CLINICAL PATTERNS**: Detected temporal/behavioral patterns.
- Include date ranges and occurrence counts
- Cite all supporting resources
- Patterns may become stale—note if data is old

When using memory, ALWAYS mention if you're building on past session context.
"""
```

### Implementation Phases for Memory Layer

**Phase 1: Session Persistence (P4a)**
- Add Session and Message models
- Store conversation history
- Generate session summaries at session end
- Embed summaries for semantic retrieval

**Phase 2: Session Retrieval (P4b)**
- Retrieve relevant past sessions during context building
- Include in system prompt with appropriate trust signals
- UI to show "Related past conversations"

**Phase 3: Derived Observations (P4c)**
- Add PatientObservation model with grounding requirements
- Implement LLM-based observation derivation with mandatory citations
- Validation workflow (disputed/confirmed status)
- UI to show observations with clickable citations

**Phase 4: Clinical Patterns (P4d)**
- Add ClinicalPattern model
- Implement pattern detection (likely batch job, not real-time)
- Integration with Knowledge Graph as derived edges
- UI to visualize patterns with supporting evidence

### Open Questions for Memory Layer

1. **When to derive observations?** Real-time during conversation, or batch analysis?
2. **Observation lifecycle:** How long are observations valid? When to re-validate?
3. **User confirmation:** Should clinicians be able to confirm/dispute observations?
4. **Privacy:** If this were production, how would derived observations affect data retention policies?
5. **Cross-patient patterns:** Could we detect patterns across a patient cohort? (Significant complexity increase)

---

## Synthetic Clinical Notes (P2)

> **Priority:** P2
> **Dependencies:** Synthetic Patient Profiles (P1), Basic infrastructure (P1)
> **Purpose:** Create realistic narrative clinical documentation from Synthea's structured data

### Intent & Motivation

Real EHRs are full of narrative—progress notes, discharge summaries, radiology reports. Synthea produces clean FHIR resources, but no clinical notes. This creates two opportunities:

1. **Demo Realism**: Show the system handling unstructured text like a real EHR
2. **Test Bed for Ingestion**: Generated notes become test data for the LLM-based extraction pipeline (P4)

**The generation→ingestion loop:**
```
Synthea FHIR → LLM generates notes → Notes stored as fixtures
                                            ↓
                            LLM extracts facts (P4) → Validate against original FHIR
```

This creates a closed loop where we can measure extraction accuracy against known ground truth.

### Note Types (Initial Scope)

**Phase 1: Progress Notes + Imaging Reports**

| Note Type | Source FHIR Resources | Example Output |
|-----------|----------------------|----------------|
| **Progress Note** | Encounter + Observations + Conditions + MedicationRequests | "67 y/o F with history of DM2 presents for routine follow-up. Patient reports improved energy since starting Metformin. A1c today 7.2%, down from 8.1%. Continues with daily walks. Plan: Continue current regimen, follow-up 3 months." |
| **Imaging Report** | DiagnosticReport + ImagingStudy | "CHEST X-RAY, PA AND LATERAL\n\nCLINICAL INDICATION: Cough x 2 weeks\n\nFINDINGS: Heart size normal. No focal consolidation. No pleural effusion.\n\nIMPRESSION: Normal chest radiograph." |

**Future Expansion:**
- Discharge summaries (inpatient encounters)
- Procedure notes
- Referral letters
- Nursing assessments
- Consultation notes

### Generation Architecture

```python
# scripts/generate_clinical_notes.py

from dataclasses import dataclass
from enum import Enum

class NoteType(Enum):
    PROGRESS_NOTE = "progress_note"
    IMAGING_REPORT = "imaging_report"
    DISCHARGE_SUMMARY = "discharge_summary"


@dataclass
class NoteGenerationContext:
    """Context assembled for note generation."""
    patient_profile: dict           # From patient profile fixtures
    encounter: dict                 # FHIR Encounter resource
    related_observations: list[dict]
    related_conditions: list[dict]
    related_medications: list[dict]
    related_procedures: list[dict]
    diagnostic_reports: list[dict]  # For imaging reports


PROGRESS_NOTE_PROMPT = """
You are a physician writing a progress note for an outpatient encounter.

PATIENT PROFILE:
{patient_profile}

ENCOUNTER DETAILS:
{encounter_summary}

OBSERVATIONS FROM THIS ENCOUNTER:
{observations}

ACTIVE CONDITIONS:
{conditions}

CURRENT MEDICATIONS:
{medications}

Write a realistic progress note in standard SOAP format (Subjective, Objective, Assessment, Plan).
Include:
- Chief complaint relevant to this encounter type
- Relevant history incorporating the patient's personality/lifestyle from their profile
- Objective findings from the observations
- Assessment connecting observations to conditions
- Plan for ongoing management

Make it feel like a real note—not overly formal, with natural clinical shorthand.
Do NOT include information not supported by the provided data.

Output the note as plain text, as it would appear in an EHR.
"""


IMAGING_REPORT_PROMPT = """
You are a radiologist dictating a report for an imaging study.

PATIENT INFO:
- Age: {age}
- Gender: {gender}

STUDY DETAILS:
{study_type}
Date: {study_date}
Clinical indication: {indication}

RELATED CLINICAL CONTEXT:
{clinical_context}

Write a realistic radiology report with:
- EXAMINATION: Study type and views
- CLINICAL INDICATION: Why the study was ordered
- COMPARISON: "None available" or reference to prior if applicable
- TECHNIQUE: Brief description
- FINDINGS: Systematic description of findings (normal or abnormal based on patient's conditions)
- IMPRESSION: Summary assessment

Match the findings to the patient's known conditions where clinically appropriate.
Keep it professional and concise, as real reports are.
"""


async def generate_progress_note(
    llm: LLMClient,
    context: NoteGenerationContext
) -> str:
    """Generate a progress note from encounter context."""

    response = await llm.generate(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": PROGRESS_NOTE_PROMPT.format(
                patient_profile=format_profile_for_note(context.patient_profile),
                encounter_summary=format_encounter(context.encounter),
                observations=format_observations(context.related_observations),
                conditions=format_conditions(context.related_conditions),
                medications=format_medications(context.related_medications)
            )
        }]
    )

    return response.choices[0].message.content


async def generate_imaging_report(
    llm: LLMClient,
    context: NoteGenerationContext,
    diagnostic_report: dict
) -> str:
    """Generate an imaging report from DiagnosticReport context."""

    # Extract study type from DiagnosticReport
    study_code = diagnostic_report.get("code", {}).get("text", "Imaging Study")
    study_date = diagnostic_report.get("effectiveDateTime", "Unknown")

    # Get indication from ServiceRequest if available
    indication = extract_indication(context, diagnostic_report)

    response = await llm.generate(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": IMAGING_REPORT_PROMPT.format(
                age=calculate_age(context.patient_profile),
                gender=context.patient_profile.get("gender", "Unknown"),
                study_type=study_code,
                study_date=study_date,
                indication=indication,
                clinical_context=format_clinical_context(context)
            )
        }]
    )

    return response.choices[0].message.content
```

### Storage as FHIR DocumentReference

Generated notes are stored as FHIR DocumentReference resources, maintaining FHIR-native consistency:

```python
def create_document_reference(
    patient_id: str,
    encounter_id: str | None,
    note_type: NoteType,
    note_content: str,
    source_resource_ids: list[str]  # FHIR resources used to generate this note
) -> dict:
    """Create a FHIR DocumentReference for a generated clinical note."""

    return {
        "resourceType": "DocumentReference",
        "id": str(uuid.uuid4()),
        "status": "current",
        "type": {
            "coding": [{
                "system": "http://loinc.org",
                "code": NOTE_TYPE_LOINC_CODES[note_type],
                "display": note_type.value.replace("_", " ").title()
            }]
        },
        "subject": {"reference": f"Patient/{patient_id}"},
        "context": {
            "encounter": [{"reference": f"Encounter/{encounter_id}"}] if encounter_id else []
        },
        "date": datetime.utcnow().isoformat(),
        "content": [{
            "attachment": {
                "contentType": "text/plain",
                "data": base64.b64encode(note_content.encode()).decode()
            }
        }],
        # Custom extension to track generation provenance
        "extension": [{
            "url": "http://cruxmd.ai/fhir/StructureDefinition/generated-from",
            "valueString": ",".join(source_resource_ids)
        }]
    }
```

### Fixture Generation Workflow

```python
# scripts/generate_all_notes.py

async def generate_notes_for_patient(
    llm: LLMClient,
    patient_bundle: dict,
    patient_profile: dict
) -> list[dict]:
    """Generate all clinical notes for a patient's encounters."""

    notes = []
    encounters = extract_encounters(patient_bundle)

    for encounter in encounters:
        # Build context for this encounter
        context = build_note_context(patient_bundle, patient_profile, encounter)

        # Generate progress note for each encounter
        progress_note = await generate_progress_note(llm, context)
        doc_ref = create_document_reference(
            patient_id=extract_patient_id(patient_bundle),
            encounter_id=encounter.get("id"),
            note_type=NoteType.PROGRESS_NOTE,
            note_content=progress_note,
            source_resource_ids=get_context_resource_ids(context)
        )
        notes.append(doc_ref)

        # Generate imaging reports for any DiagnosticReports in this encounter
        for diag_report in context.diagnostic_reports:
            if is_imaging_report(diag_report):
                imaging_report = await generate_imaging_report(llm, context, diag_report)
                doc_ref = create_document_reference(
                    patient_id=extract_patient_id(patient_bundle),
                    encounter_id=encounter.get("id"),
                    note_type=NoteType.IMAGING_REPORT,
                    note_content=imaging_report,
                    source_resource_ids=[diag_report.get("id")]
                )
                notes.append(doc_ref)

    return notes


async def generate_all_patient_notes(fixtures_dir: Path):
    """Generate notes for all patient fixtures."""

    llm = LLMClient()

    for bundle_path in fixtures_dir.glob("patient_bundle_*.json"):
        # Load bundle and profile
        with open(bundle_path) as f:
            bundle = json.load(f)

        profile_path = bundle_path.with_suffix(".profile.json")
        with open(profile_path) as f:
            profile = json.load(f)

        print(f"Generating notes for {bundle_path.name}...")

        # Generate notes
        notes = await generate_notes_for_patient(llm, bundle, profile)

        # Save as separate notes fixture
        notes_path = bundle_path.parent / bundle_path.name.replace("bundle", "notes")
        with open(notes_path, "w") as f:
            json.dump({"notes": notes}, f, indent=2)

        print(f"  Generated {len(notes)} notes")
```

### Fixture Structure (Updated)

```
tests/fixtures/synthea/
├── patient_bundle_1.json           # FHIR Bundle (Synthea)
├── patient_bundle_1.profile.json   # Generated patient profile (P1)
├── patient_bundle_1.notes.json     # Generated clinical notes (P3)
├── patient_bundle_2.json
├── patient_bundle_2.profile.json
├── patient_bundle_2.notes.json
├── ...
└── generation_manifest.json        # Tracks what was generated when
```

### Integration with Context Engine

Generated notes are embedded and searchable:

```python
# Loading notes during patient ingestion
async def load_patient_with_notes(
    db: AsyncSession,
    bundle: dict,
    profile: dict,
    notes: list[dict]
):
    """Load patient bundle, profile, and generated notes."""

    # Load base bundle
    patient_id = await load_bundle(db, bundle)

    # Attach profile
    await attach_profile(db, patient_id, profile)

    # Load notes as additional FHIR resources
    for note in notes:
        await store_fhir_resource(
            db,
            patient_id=patient_id,
            resource=note,
            resource_type="DocumentReference"
        )

    # Generate embeddings for note content
    await generate_embeddings_for_notes(db, patient_id, notes)
```

---

## P4: LLM-Based Data Ingestion

> **Priority:** P4
> **Dependencies:** Synthetic Clinical Notes (P3), Context Engine (P2), Knowledge Graph (P2)
> **Purpose:** Extract structured FHIR resources from unstructured clinical text

### Intent & Motivation

The inverse of note generation: given free-text clinical documentation, extract structured FHIR resources. This capability enables:

1. **Real-World Data Handling**: Actual clinical data is messy—HL7v2 messages, scanned documents, faxed records
2. **Closed-Loop Validation**: Extract from generated notes and compare against source FHIR (known ground truth)
3. **Future Expansion**: Path to ingesting non-Synthea data sources

### The Extraction Pipeline

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        LLM-BASED DATA INGESTION PIPELINE                    │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────┐     ┌─────────────────┐     ┌─────────────────────────┐   │
│  │ Source Text │     │   Extraction    │     │   Candidate FHIR        │   │
│  │ (note, fax, │ ──▶ │   LLM with      │ ──▶ │   Resources             │   │
│  │  HL7v2)     │     │   FHIR Schema   │     │   (with confidence)     │   │
│  └─────────────┘     └─────────────────┘     └───────────┬─────────────┘   │
│                                                          │                  │
│                                                          ▼                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                    VALIDATION & ENRICHMENT                          │   │
│  │                                                                      │   │
│  │  1. Schema validation (valid FHIR R4?)                              │   │
│  │  2. Terminology lookup (normalize to LOINC/SNOMED/RxNorm)           │   │
│  │  3. Deduplication check (does this Condition already exist?)        │   │
│  │  4. Provenance attachment (link to source text span)                │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                          │                  │
│                                                          ▼                  │
│  ┌─────────────────────────────────────────────────────────────────────┐   │
│  │                         STORAGE LAYER                               │   │
│  │                                                                      │   │
│  │  PostgreSQL (fhir_resources table)                                  │   │
│  │  ├── resource with source: "extracted" metadata                     │   │
│  │  ├── extraction_confidence: 0.0-1.0                                 │   │
│  │  └── source_document_id: reference to DocumentReference             │   │
│  │                                                                      │   │
│  │  Neo4j (Knowledge Graph)                                            │   │
│  │  └── Edges typed as EXTRACTED_FROM_NOTE (lower confidence than      │   │
│  │      HAS_CONDITION edges from Synthea source-of-truth)              │   │
│  └─────────────────────────────────────────────────────────────────────┘   │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

### Extraction Schema

```python
# backend/app/schemas/extraction.py

from pydantic import BaseModel, Field
from typing import Literal

class ExtractedResource(BaseModel):
    """A FHIR resource extracted from unstructured text."""

    resource: dict                    # The extracted FHIR resource
    resource_type: str                # "Condition", "Observation", etc.
    confidence: float = Field(ge=0.0, le=1.0)
    source_text_span: str             # The exact text this was extracted from
    reasoning: str                    # Why the LLM believes this extraction is correct


class ExtractionResult(BaseModel):
    """Result of extracting from a clinical note."""

    source_document_id: str           # DocumentReference ID
    extracted_resources: list[ExtractedResource]
    extraction_warnings: list[str]    # Any issues encountered
    extraction_timestamp: str


class StoredExtractedResource(BaseModel):
    """How extracted resources are stored."""

    # Standard FHIR resource fields
    resource: dict

    # Extraction metadata
    source: Literal["extracted"] = "extracted"
    extraction_confidence: float
    source_document_id: str
    source_text_span: str
    extracted_at: str

    # Validation status
    validation_status: Literal["pending", "validated", "rejected"] = "pending"
    validated_by: str | None = None
    validated_at: str | None = None
```

### Extraction Prompts

```python
# backend/app/services/extraction.py

EXTRACTION_SYSTEM_PROMPT = """
You are a clinical NLP system that extracts structured FHIR R4 resources from clinical notes.

EXTRACTION RULES:
1. Only extract information EXPLICITLY stated in the text
2. Do NOT infer or assume information not present
3. Assign confidence scores based on clarity of the source text:
   - 0.9-1.0: Explicitly stated, unambiguous
   - 0.7-0.9: Clearly implied, high confidence
   - 0.5-0.7: Somewhat ambiguous, moderate confidence
   - Below 0.5: Do not extract (too uncertain)
4. Include the exact source text span for each extraction
5. Use standard terminologies where possible (LOINC, SNOMED, RxNorm)

FHIR RESOURCE TYPES TO EXTRACT:
- Condition: Diagnoses, problems, health concerns
- Observation: Lab results, vital signs, clinical findings
- MedicationRequest: Prescribed medications
- AllergyIntolerance: Drug or other allergies
- Procedure: Performed procedures

OUTPUT FORMAT:
Return a JSON array of extracted resources, each with:
{
    "resource": { <valid FHIR R4 resource> },
    "resource_type": "Condition" | "Observation" | etc,
    "confidence": 0.0-1.0,
    "source_text_span": "exact text from the note",
    "reasoning": "why this extraction is correct"
}
"""


PROGRESS_NOTE_EXTRACTION_PROMPT = """
{system_prompt}

CLINICAL NOTE TO PROCESS:
---
{note_content}
---

Extract all clinical facts as FHIR resources. Remember:
- Conditions mentioned should become Condition resources
- Lab values should become Observation resources with LOINC codes
- Medications should become MedicationRequest resources
- Include confidence and source text for each extraction
"""


async def extract_from_note(
    llm: LLMClient,
    note_content: str,
    note_type: NoteType
) -> list[ExtractedResource]:
    """Extract structured FHIR resources from a clinical note."""

    response = await llm.generate(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": PROGRESS_NOTE_EXTRACTION_PROMPT.format(
                system_prompt=EXTRACTION_SYSTEM_PROMPT,
                note_content=note_content
            )
        }],
        response_format={"type": "json_object"}
    )

    data = json.loads(response.choices[0].message.content)
    return [ExtractedResource(**item) for item in data.get("extractions", [])]
```

### Terminology Normalization

```python
# backend/app/services/terminology.py

class TerminologyService:
    """Normalize extracted terms to standard vocabularies."""

    async def normalize_condition(self, extracted: ExtractedResource) -> dict:
        """Normalize condition to SNOMED CT."""
        condition = extracted.resource
        coding = condition.get("code", {}).get("coding", [{}])[0]

        if not coding.get("system") == "http://snomed.info/sct":
            # Attempt to map to SNOMED
            display = coding.get("display", "")
            snomed_code = await self.lookup_snomed(display)
            if snomed_code:
                condition["code"]["coding"] = [{
                    "system": "http://snomed.info/sct",
                    "code": snomed_code["code"],
                    "display": snomed_code["display"]
                }]

        return condition

    async def normalize_observation(self, extracted: ExtractedResource) -> dict:
        """Normalize observation to LOINC."""
        observation = extracted.resource
        coding = observation.get("code", {}).get("coding", [{}])[0]

        if not coding.get("system") == "http://loinc.org":
            # Attempt to map to LOINC
            display = coding.get("display", "")
            loinc_code = await self.lookup_loinc(display)
            if loinc_code:
                observation["code"]["coding"] = [{
                    "system": "http://loinc.org",
                    "code": loinc_code["code"],
                    "display": loinc_code["display"]
                }]

        return observation

    async def lookup_snomed(self, term: str) -> dict | None:
        """Look up SNOMED CT code for a term."""
        # Future: Use UMLS API or local SNOMED subset
        # For now, return None (term not normalized)
        return None

    async def lookup_loinc(self, term: str) -> dict | None:
        """Look up LOINC code for a term."""
        # Future: Use LOINC API or local subset
        return None
```

### Knowledge Graph Integration

Extracted facts get different edge types to indicate their provenance:

```python
# backend/app/services/graph.py (extended)

class KnowledgeGraph:

    async def add_extracted_condition(
        self,
        patient_id: str,
        condition: dict,
        extraction_metadata: dict
    ):
        """Add an extracted condition with lower-confidence edge."""
        async with self.driver.session() as session:
            await session.run("""
                MATCH (p:Patient {id: $patient_id})
                MERGE (c:Condition {id: $condition_id})
                SET c.fhir_resource = $fhir_resource,
                    c.code = $code,
                    c.display = $display,
                    c.source = 'extracted',
                    c.extraction_confidence = $confidence,
                    c.source_document_id = $source_doc_id
                MERGE (p)-[r:EXTRACTED_CONDITION]->(c)
                SET r.confidence = $confidence,
                    r.extracted_at = datetime()
            """, {
                "patient_id": patient_id,
                "condition_id": condition.get("id"),
                "fhir_resource": json.dumps(condition),
                "code": condition.get("code", {}).get("coding", [{}])[0].get("code"),
                "display": condition.get("code", {}).get("coding", [{}])[0].get("display"),
                "confidence": extraction_metadata["confidence"],
                "source_doc_id": extraction_metadata["source_document_id"]
            })


    async def get_all_conditions(
        self,
        patient_id: str,
        include_extracted: bool = True
    ) -> list[dict]:
        """Get conditions, optionally including extracted ones."""

        if include_extracted:
            query = """
                MATCH (p:Patient {id: $patient_id})-[r:HAS_CONDITION|EXTRACTED_CONDITION]->(c:Condition)
                RETURN c.fhir_resource as resource,
                       type(r) as relationship_type,
                       CASE WHEN type(r) = 'EXTRACTED_CONDITION' THEN r.confidence ELSE 1.0 END as confidence
                ORDER BY confidence DESC
            """
        else:
            query = """
                MATCH (p:Patient {id: $patient_id})-[:HAS_CONDITION]->(c:Condition)
                RETURN c.fhir_resource as resource, 'HAS_CONDITION' as relationship_type, 1.0 as confidence
            """

        async with self.driver.session() as session:
            result = await session.run(query, patient_id=patient_id)
            return [
                {
                    "resource": json.loads(record["resource"]),
                    "source": "verified" if record["relationship_type"] == "HAS_CONDITION" else "extracted",
                    "confidence": record["confidence"]
                }
                async for record in result
            ]
```

### Validation Against Ground Truth

For generated notes, we can validate extraction accuracy:

```python
# scripts/validate_extraction_accuracy.py

async def validate_extraction_accuracy(
    fixtures_dir: Path
) -> dict:
    """
    Compare extracted resources against source Synthea FHIR.

    Since notes were generated FROM Synthea data, we can measure
    how well the extraction pipeline recovers the original facts.
    """

    results = {
        "total_source_resources": 0,
        "total_extracted": 0,
        "true_positives": 0,
        "false_positives": 0,
        "false_negatives": 0,
        "by_resource_type": {}
    }

    for bundle_path in fixtures_dir.glob("patient_bundle_*.json"):
        # Load source bundle (ground truth)
        with open(bundle_path) as f:
            source_bundle = json.load(f)

        # Load generated notes
        notes_path = bundle_path.parent / bundle_path.name.replace("bundle", "notes")
        with open(notes_path) as f:
            notes = json.load(f)["notes"]

        # Extract from notes
        extracted = []
        for note in notes:
            note_content = decode_note_content(note)
            extracted.extend(await extract_from_note(llm, note_content, get_note_type(note)))

        # Compare against source
        source_conditions = extract_conditions(source_bundle)
        extracted_conditions = [e for e in extracted if e.resource_type == "Condition"]

        # Calculate metrics
        matches = find_matches(source_conditions, extracted_conditions)
        results["true_positives"] += len(matches)
        results["false_positives"] += len(extracted_conditions) - len(matches)
        results["false_negatives"] += len(source_conditions) - len(matches)

    # Calculate precision, recall, F1
    results["precision"] = results["true_positives"] / max(results["true_positives"] + results["false_positives"], 1)
    results["recall"] = results["true_positives"] / max(results["true_positives"] + results["false_negatives"], 1)
    results["f1"] = 2 * (results["precision"] * results["recall"]) / max(results["precision"] + results["recall"], 0.001)

    return results
```

### Context Engine Integration

The Context Engine differentiates extracted vs verified facts:

```python
# Updated VerifiedLayer with extraction awareness

@dataclass
class VerifiedLayer:
    """
    Facts verified via knowledge graph relationships.

    Now includes source differentiation:
    - source="verified": From Synthea/direct FHIR ingestion (high confidence)
    - source="extracted": From LLM extraction (confidence varies)
    """
    conditions: list[dict] = field(default_factory=list)
    medications: list[dict] = field(default_factory=list)
    allergies: list[dict] = field(default_factory=list)

    # NEW: Track what's extracted vs verified
    extracted_conditions: list[dict] = field(default_factory=list)
    extracted_medications: list[dict] = field(default_factory=list)


def format_context_for_llm_with_extraction(context: PatientContext) -> str:
    """Format context with clear extraction provenance."""

    sections = []

    # Verified facts (high confidence)
    sections.append("## VERIFIED CLINICAL FACTS (HIGH CONFIDENCE)")
    sections.append("Source: Direct FHIR ingestion, ground truth")
    sections.append(format_verified_conditions(context.verified.conditions))
    sections.append(format_verified_medications(context.verified.medications))

    # Extracted facts (variable confidence)
    if context.verified.extracted_conditions or context.verified.extracted_medications:
        sections.append("\n## EXTRACTED FACTS (VARIABLE CONFIDENCE)")
        sections.append("Source: LLM extraction from clinical notes")
        sections.append("Note: Cross-reference with verified facts when possible")

        for condition in context.verified.extracted_conditions:
            conf = condition.get("_extraction_confidence", 0.5)
            sections.append(f"- [Confidence: {conf:.0%}] {format_condition(condition['resource'])}")

    return "\n".join(sections)
```

### Open Questions for Ingestion Pipeline

1. **Deduplication strategy:** How to detect if an extracted Condition matches an existing one? Exact code match? Semantic similarity?
2. **Confidence thresholds:** What confidence level is required to add to Knowledge Graph?
3. **Human-in-the-loop:** Should extracted facts require manual validation before being trusted?
4. **Conflict resolution:** If extracted fact contradicts verified fact, what happens?
5. **Batch vs real-time:** Extract on ingestion or as background job?

---

## Open Questions

### To Decide Before Starting

1. ~~**Domain name:** Use cruxmd.ai or something new?~~ **DECIDED:** cruxmd.ai

2. **Embedding model:** text-embedding-3-small (cheap, good) or text-embedding-3-large (better, more expensive)?

3. **LLM model:** GPT-4o (best structured output) or Claude 3.5 Sonnet (possibly better clinical reasoning)?

4. ~~**Conversation storage:** In-memory (simple) or database (persistent)?~~ **DECIDED:** Database (see P3/P4 for session persistence)

5. **Visualization library:** Recharts (simple, React-native) or something more powerful?

### Future Considerations

1. ~~**Knowledge graph:** NetworkX + vis.js or dedicated graph database (Neo4j)?~~ **DECIDED:** Neo4j for learning investment and future UMLS/ontology integration.

2. **Multi-patient queries:** How to handle cohort analysis UI? (P5)

3. **Action execution:** Should actions actually do anything or just be placeholders?

4. **Audit logging:** Need to track what queries are run for demo purposes?

5. **FHIRPath queries:** Currently noted as future enhancement. Useful for precise structured queries beyond SQL views.

---

## References

### Related Reading

- [Agentic UX & Design Patterns](https://manialabs.substack.com/p/agentic-ux-and-design-patterns)
- [Generative UI: Agent-Powered Interfaces](https://www.copilotkit.ai/generative-ui)
- [Google A2UI: AI Agents Building Native UIs](https://www.analyticsvidhya.com/blog/2025/12/google-a2ui-explained/)
- [Designing LLM-First Products](https://blog.logrocket.com/designing-llm-first-products/)
- [json-render](https://github.com/vercel-labs/json-render) - Vercel's JSON UI rendering
- [hashbrown](https://hashbrown.dev/) - TypeScript generative UI framework

### FHIR Resources

- [FHIR R4 Specification](https://hl7.org/fhir/R4/)
- [FHIRPath Specification](https://hl7.org/fhirpath/)
- [Synthea Patient Generator](https://synthetichealth.github.io/synthea/)

---

## Document History

| Version | Date | Changes |
|---------|------|---------|
| 1.0 | January 2025 | Initial planning document |
| 1.1 | January 2025 | Added Design Philosophy & Principles section |
| 1.2 | January 2025 | Elevated Knowledge Graph to P1, added Neo4j architecture |
| 1.3 | January 2025 | Added FHIR-Native Context Engine with trust differentiation |
| 1.4 | January 2025 | Added Semantic Memory Layer (P4) |
| 1.5 | January 2025 | Added Synthetic Patient Profiles (P0), Synthetic Clinical Notes (P2), LLM-Based Data Ingestion (P4) |
| 2.0 | January 2025 | Major revision: Unified P0-P5 priority system, removed week references, updated auth to server-side proxy, fixed Docker config, domain set to cruxmd.ai |
| 2.1 | January 2025 | Comprehensive review: Added Technical Risks & Mitigations, Demo Scale Definition (100 patients), Cost Estimation, Embedding Text Templates, Patient ID Strategy (UUID canonical), Security (CORS, rate limiting, XSS), Backup/Recovery, Medical Disclaimers, Frontend Error States, DataQuery Resolution (backend), Scaling Contingency, Neo4j test configuration, non-streaming responses |

---

*This document contains sufficient detail to hand off to a coding agent for implementation. Each section can be expanded into specific implementation tasks.*
