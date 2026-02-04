# CruxMD

**Human Presence. Machine Precision.**

CruxMD is a clinical thinking partner for primary care physicians. It synthesizes complete patient context from medical records, surfaces patterns humans miss, and handles the cognitive overhead that buries clinicians in busywork.

## The Problem

Primary care physicians spend more time on documentation and chart review than with patients. Critical findings hide in dense medical records. Drug interactions get missed. Patterns across visits go unnoticed. The cognitive load is unsustainable.

## The Solution

CruxMD is an **agent-first** clinical intelligence system. Unlike traditional EHRs with bolted-on AI features, the LLM is the core brain of every interaction:

- **Conversational chart review** — Ask questions in natural language, get answers with citations from the patient's actual records
- **Clinical reasoning partner** — Surface drug interactions, flag critical lab values, identify patterns across visits
- **Autonomous pre-visit prep** — AI agents review charts before appointments, highlighting what matters

## What Makes CruxMD Different

### FHIR-Native Architecture

Medical data stays in its native [FHIR R4](https://hl7.org/fhir/R4/) format. No lossy transformations, no proprietary schemas. Raw FHIR JSON flows from EHR to database to LLM context. This means:

- **Interoperability by default** — Standard format in, standard format out
- **No data loss** — Every FHIR extension and edge case preserved
- **Portable** — Swap data sources without schema migrations

### Hybrid Retrieval: Knowledge Graph + Vector Search

Most clinical AI uses basic RAG (retrieve chunks, stuff into prompt). CruxMD uses **dual-layer retrieval**:

```
┌─────────────────────────────────────────────────────────────────┐
│                     VERIFIED LAYER (HIGH)                       │
│   Neo4j Knowledge Graph — Structured clinical facts             │
│   • Active conditions, medications, allergies                   │
│   • Drug-condition relationships                                │
│   • Lab trends and reference ranges                             │
│   • Generates safety constraints for LLM                        │
└─────────────────────────────────────────────────────────────────┘
                              +
┌─────────────────────────────────────────────────────────────────┐
│                    RETRIEVED LAYER (MEDIUM)                     │
│   pgvector Semantic Search — Relevant context chunks            │
│   • Progress notes, clinical narratives                         │
│   • Procedure reports, discharge summaries                      │
│   • Ranked by semantic similarity to query                      │
└─────────────────────────────────────────────────────────────────┘
```

The **verified layer** provides high-confidence facts the LLM can trust. The **retrieved layer** adds relevant context. Safety constraints are generated automatically from allergies and medications — the LLM cannot recommend contraindicated treatments.

### LLM as Operating System

Traditional EHRs force physicians into predefined screens and workflows. CruxMD inverts this:

- **The LLM decides what's relevant** — No clicking through tabs to find information
- **Navigation emerges from conversation** — Ask a question, get exactly what you need
- **Structured outputs** — Responses include insights, visualizations, and suggested follow-ups

## Demo Scenarios

The homepage features interactive demos of clinical reasoning scenarios:

| Scenario | Clinical Challenge |
|----------|-------------------|
| **Heart Failure** | Fluid management with renal considerations |
| **QT Prolongation** | Medication interaction risk assessment |
| **Young Athlete** | HCM screening decision support |
| **Hypoglycemia** | Diabetes medication cascade analysis |

## Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    Conversational Canvas                         │
│              Next.js 15 • shadcn/ui • Tailwind                  │
└──────────────────────────────┬───────────────────────────────────┘
                               │
                               ▼
┌──────────────────────────────────────────────────────────────────┐
│                      FastAPI Backend                             │
│         Python 3.12 • Async SQLAlchemy • Pydantic               │
└──────────────────────────────┬───────────────────────────────────┘
                               │
              ┌────────────────┼────────────────┐
              ▼                ▼                ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  Context Engine │  │   LLM Agent     │  │ FHIR Loader     │
│  Hybrid search  │  │   GPT-5 + tools │  │ Bundle ingest   │
└────────┬────────┘  └────────┬────────┘  └────────┬────────┘
         │                    │                    │
         ▼                    ▼                    ▼
┌─────────────────────────────────────────────────────────────────┐
│                        Data Layer                                │
│  PostgreSQL 16 + pgvector │ Neo4j Knowledge Graph │ FHIR JSON   │
└─────────────────────────────────────────────────────────────────┘
```

## Tech Stack

| Layer | Technology |
|-------|------------|
| **Frontend** | Next.js 15, TypeScript, shadcn/ui, Tailwind CSS |
| **Backend** | Python 3.12, FastAPI, SQLAlchemy (async), Pydantic |
| **Database** | PostgreSQL 16 + pgvector (embeddings) |
| **Knowledge Graph** | Neo4j 5.x (clinical relationships) |
| **LLM** | OpenAI GPT-5 with structured outputs |
| **Auth** | Better-Auth (email/password, bearer tokens) |
| **Deployment** | Docker Compose, single VPS |

## Quick Start

### Prerequisites

- Docker and Docker Compose
- OpenAI API key

### Setup

```bash
# Clone and configure
git clone https://github.com/josephneumann/CruxMD.git
cd CruxMD
cp .env.example .env
# Edit .env with your credentials
```

### Run with Docker

```bash
make dev                    # Start all services (foreground)
# or
make dev-detached           # Start in background
```

Services start at:
- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **Neo4j Browser**: http://localhost:7474

### Load Demo Data

```bash
make seed-admin             # Create admin user
make seed                   # Load Synthea patient fixtures
```

### Development Commands

```bash
make rebuild               # Rebuild after code changes
make logs-backend          # Tail backend logs
make logs-frontend         # Tail frontend logs
make test                  # Run backend tests
make psql                  # Connect to PostgreSQL
make deploy                # Deploy to production
```

Run `make help` for all available commands.

## Project Structure

```
cruxmd/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry point
│   │   ├── services/
│   │   │   ├── agent.py            # LLM reasoning (723 lines)
│   │   │   ├── context_engine.py   # Hybrid retrieval (648 lines)
│   │   │   ├── graph.py            # Neo4j knowledge graph (1337 lines)
│   │   │   ├── vector_search.py    # pgvector semantic search
│   │   │   └── fhir_loader.py      # FHIR bundle ingestion
│   │   ├── routes/                 # API endpoints
│   │   ├── models/                 # SQLAlchemy models
│   │   └── schemas/                # Pydantic schemas
│   └── tests/
│
├── frontend/
│   ├── app/
│   │   ├── page.tsx                # Homepage with demo
│   │   ├── chat/                   # Conversational canvas
│   │   ├── sessions/               # Session management
│   │   └── (auth)/                 # Login, register
│   ├── components/
│   │   ├── canvas/                 # Chat UI components
│   │   ├── demo/                   # Interactive demo
│   │   └── ui/                     # shadcn components
│   └── lib/
│       └── demo-scenarios/         # Clinical scenario scripts
│
├── fixtures/                       # Synthea patient bundles
└── docker-compose.yml
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DB_PASSWORD` | Yes | PostgreSQL password |
| `NEO4J_PASSWORD` | Yes | Neo4j password |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `BETTER_AUTH_SECRET` | Yes | Session signing secret |
| `ADMIN_EMAIL` | Yes | Admin user email |
| `ADMIN_PASSWORD` | Yes | Admin user password |
| `RESEND_API_KEY` | No | Transactional email (console fallback) |

## Key Design Principles

1. **FHIR-native** — Store raw FHIR JSON, preserve full fidelity
2. **LLM decides, UI renders** — No predefined screens, navigation emerges from conversation
3. **Verified + Retrieved** — Knowledge graph for facts, vector search for context
4. **Safety constraints** — Allergies and medications generate automatic guardrails
5. **Simple deployment** — Single VPS, Docker Compose, no Kubernetes complexity

## License

Private — All rights reserved.

---

Built by [Joe Neumann](https://github.com/josephneumann)
