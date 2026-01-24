# CruxMD v2: Medical Context Engine

An LLM-native platform for clinical intelligence demos. Unlike traditional CRUD applications with bolted-on chat features, CruxMD is an **agent-first** system where the LLM is the core brain of every interaction.

## Primary Use Cases

- Chat with individual patient data
- Clinical reasoning and decision support demos
- Semantic search over healthcare records
- Knowledge graph traversal for precise clinical facts

## Architecture

```
┌─────────────────────────────────────────────┐
│           User's Clinical Question          │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│              Context Engine                 │
│   Hybrid retrieval: Knowledge Graph +       │
│   Vector search (pgvector)                  │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│           FHIR Data (native format)         │
│   PostgreSQL + Neo4j Knowledge Graph        │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│             Reasoning Agent (LLM)           │
│   GPT-4o with structured output             │
└─────────────────────┬───────────────────────┘
                      │
                      ▼
┌─────────────────────────────────────────────┐
│          Conversational Canvas (UI)         │
│   Next.js + shadcn/ui + Tailwind            │
└─────────────────────────────────────────────┘
```

## Tech Stack

- **Backend**: Python 3.12, FastAPI, SQLAlchemy (async)
- **Database**: PostgreSQL 16 + pgvector
- **Knowledge Graph**: Neo4j 5.x
- **Frontend**: Next.js 15, TypeScript, shadcn/ui, Tailwind CSS
- **LLM**: OpenAI GPT-4o
- **Deployment**: Docker Compose, single VPS

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 20+ and pnpm
- Python 3.12+ and uv
- OpenAI API key

### Development

```bash
# Start all services (PostgreSQL, Neo4j)
docker compose up -d

# Backend
cd backend
uv sync                              # Install dependencies
uv run alembic upgrade head          # Run migrations
uv run python -m app.scripts.seed_database  # Seed with Synthea fixtures
uv run uvicorn app.main:app --reload # Start dev server

# Frontend (in another terminal, with backend running)
cd frontend
pnpm install                         # Install dependencies
pnpm generate-api                    # Generate TypeScript client from OpenAPI
pnpm dev                             # Start dev server (http://localhost:3000)
```

### API Client Generation

The frontend uses `@hey-api/openapi-ts` to generate a type-safe API client from the FastAPI OpenAPI schema. After making backend API changes:

```bash
# Ensure backend is running
cd backend && uv run uvicorn app.main:app --reload

# In another terminal, regenerate the client
cd frontend && pnpm generate-api
```

This creates TypeScript types and functions in `frontend/lib/generated/`.

### Full Stack (Docker)

```bash
docker compose up                    # Start all services
docker compose up -d                 # Start in background
```

## Project Structure

```
cruxmd/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings (env vars)
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models.py            # FhirResource model
│   │   ├── routes/              # API endpoints
│   │   ├── services/            # Business logic
│   │   │   ├── fhir_loader.py   # Bundle loading
│   │   │   ├── embeddings.py    # Embedding generation
│   │   │   ├── graph.py         # Neo4j knowledge graph
│   │   │   ├── context_engine.py # Hybrid retrieval
│   │   │   └── agent.py         # LLM agent logic
│   │   └── schemas/             # Pydantic schemas
│   └── tests/
│
├── frontend/
│   ├── app/                     # Next.js App Router
│   └── components/
│       ├── canvas/              # Chat UI components
│       ├── clinical/            # InsightCard, LabResultsChart, etc.
│       └── patient/             # PatientSelector, PatientHeader
│
├── fixtures/                    # Synthea patient bundles
├── docs/                        # Project documentation
└── docker-compose.yml
```

## Key Design Decisions

1. **LLM as Operating System** - The LLM decides what information is relevant, not predefined screens
2. **FHIR-native data layer** - Raw FHIR JSON in PostgreSQL JSONB, no heavy normalization
3. **Hybrid retrieval** - Vector search (pgvector) + Knowledge Graph (Neo4j)
4. **Conversational Canvas UI** - Single scrollable conversation with dynamic visualizations
5. **Fixture-based testing** - Deterministic, fast tests using committed Synthea bundles

## Environment Variables

Copy `.env.example` to `.env` and configure:

```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/cruxmd
NEO4J_URI=bolt://localhost:7687
NEO4J_USER=neo4j
NEO4J_PASSWORD=password
OPENAI_API_KEY=sk-...
API_KEY=your-api-key
```

## Documentation

- [Project Plan](docs/cruxmd-v2-plan.md) - Full specification and implementation plan
- [FHIR Reference Audit](docs/fhir-reference-audit.md) - FHIR resource type coverage

## License

Private - All rights reserved.
