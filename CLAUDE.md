# CLAUDE.md

Project-specific guidance for CruxMD. Workflow docs loaded from `~/.claude/CLAUDE.md`.

## Project Summary

CruxMD v2 is a **Medical Context Engine** — an LLM-native platform for clinical intelligence demos. Unlike traditional CRUD applications with bolted-on chat features, this is an **agent-first** system where the LLM is the core brain of every interaction. Primary use cases include chatting with patient data, clinical reasoning demos, semantic search over healthcare records, and knowledge graph traversal for precise clinical facts.

See `cruxmd-v2-plan.md` for the complete specification and implementation plan.

## Development

```bash
# Backend
cd backend
uv sync                          # Install Python dependencies
uv run pytest                    # Run tests
uv run alembic upgrade head      # Run migrations

# Frontend
cd frontend
pnpm install                     # Install Node dependencies
pnpm dev                         # Start dev server

# Full stack (Docker)
docker compose up                # Start all services
docker compose up -d             # Start in background
```

## Critical Rules

- **NEVER edit pyproject.toml directly** — Always use `uv add <package>` for dependencies
- **FHIR-native by default** — Store and pass raw FHIR JSON. Only extract specific fields when there's a concrete performance or UX need.
- **LLM decides, UI renders** — When tempted to add a new page or predefined view, ask: "Could the agent generate this dynamically?" If yes, don't build the static version.
- **Follow conventional commits** — `feat:`, `fix:`, `docs:`, `refactor:`, etc.

## Commands

```bash
# Backend API
uv run uvicorn app.main:app --reload     # Start FastAPI dev server

# Database
uv run alembic upgrade head              # Apply migrations
uv run alembic revision --autogenerate   # Generate migration

# Load test data
uv run python -m app.scripts.seed_database  # Seed database with Synthea fixtures + profiles
```

## Architecture

```
cruxmd/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── config.py            # Settings (env vars)
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models.py            # FhirResource model
│   │   ├── routes/              # API endpoints (chat, patients, fhir, search)
│   │   ├── services/            # Business logic
│   │   │   ├── fhir_loader.py   # Bundle loading
│   │   │   ├── embeddings.py    # Embedding generation
│   │   │   ├── graph.py         # Neo4j knowledge graph
│   │   │   ├── context_engine.py # Hybrid retrieval (graph + vector)
│   │   │   └── agent.py         # LLM agent logic
│   │   └── schemas/             # Pydantic schemas
│   └── tests/
│
├── frontend/
│   ├── app/                     # Next.js App Router
│   │   └── chat/page.tsx        # Conversational canvas
│   └── components/
│       ├── canvas/              # Chat UI components
│       ├── clinical/            # InsightCard, LabResultsChart, etc.
│       └── patient/             # PatientSelector, PatientHeader
│
└── docker-compose.yml
```

**Stack**: Python 3.12, FastAPI, PostgreSQL 16 + pgvector, Neo4j 5.x, SQLAlchemy (async), Next.js 15, TypeScript, shadcn/ui, Tailwind CSS, OpenAI (GPT-4o), Docker Compose

## Key Design Decisions

- **LLM as Operating System** — The LLM decides what information is relevant, not predefined screens. Navigation emerges from conversation.
- **FHIR-native data layer** — Raw FHIR JSON stored in PostgreSQL JSONB. No heavy normalization. Views for common queries, not tables.
- **Hybrid retrieval** — Vector search (pgvector) + Knowledge Graph (Neo4j) for context assembly.
- **Conversational Canvas UI** — Single scrollable conversation; agent responses contain narrative, visualizations, insights, and suggested follow-ups.
- **Simple deployment** — Single VPS + Docker Compose. No CI/CD complexity. VPS uses SSH deploy key at `/root/.ssh/id_ed25519` for GitHub access. Deploy with: `ssh cruxmd "cd /root/CruxMD && git pull && docker compose up -d --build"`
- **Fixture-based testing** — Deterministic, fast tests using Synthea patient bundles.
