# CLAUDE.md

Project-specific guidance for CruxMD. Workflow docs loaded from `~/.claude/CLAUDE.md`.

## Project Summary

CruxMD v2 is a **Medical Context Engine** — an LLM-native platform for clinical intelligence demos. Unlike traditional CRUD applications with bolted-on chat features, this is an **agent-first** system where the LLM is the core brain of every interaction. Primary use cases include chatting with patient data, clinical reasoning demos, semantic search over healthcare records, and knowledge graph traversal for precise clinical facts.


## Local Development (Docker)

**All services run in Docker locally.** Always use Makefile commands — run `make help` to see all available commands.

```bash
# Start & Stop
make dev              # Start dev environment (foreground, rebuilds)
make dev-detached     # Start dev environment (background, rebuilds)
make rebuild          # Rebuild and restart after code changes
make down             # Stop and remove containers
make restart          # Restart all containers
make ps               # Show container status

# Logs & Debugging
make logs             # Tail all logs
make logs-backend     # Tail backend logs
make logs-frontend    # Tail frontend logs
make shell-backend    # Shell into backend container
make psql             # Connect to PostgreSQL

# Testing & Quality
make test             # Run backend tests
make lint             # Run linters
make format           # Format code

# Database
make migrate          # Run migrations
make seed             # Load fixtures
make seed-admin       # Create admin user

# Deploy
make deploy           # Deploy to production (app.cruxmd.ai)
```

**Services:**
| Service | Port | Description |
|---------|------|-------------|
| backend | 8000 | FastAPI API server |
| frontend | 3000 | Next.js app |
| db | 5432 | PostgreSQL 16 + pgvector |
| neo4j | 7474, 7687 | Neo4j knowledge graph (browser, bolt) |
| caddy | 80, 443 | Reverse proxy |

**After code changes**: Always run `make rebuild` before testing locally. The backend and frontend containers build from local Dockerfiles, so code changes aren't reflected until you rebuild.

## Critical Rules

- **Always use Makefile commands** — When a `make` target exists for an operation, use it instead of raw commands. Run `make help` to see available commands. **Makefile commands must be run from the project root** (`/Users/jneumann/Code/CruxMD`).
- **Single Python environment in `backend/`** — All Python code, dependencies, and tests live in `backend/`. There is only one `pyproject.toml` and `uv.lock` (in `backend/`). Never create Python config files at the project root.
- **NEVER edit pyproject.toml directly** — Always use `cd backend && uv add <package>` for dependencies
- **FHIR-native by default** — Store and pass raw FHIR JSON. Only extract specific fields when there's a concrete performance or UX need.
- **LLM decides, UI renders** — When tempted to add a new page or predefined view, ask: "Could the agent generate this dynamically?" If yes, don't build the static version.
- **Follow conventional commits** — `feat:`, `fix:`, `docs:`, `refactor:`, etc.
- **NEVER merge a PR without explicit user confirmation** — Always ask and wait for approval before running `gh pr merge` or any equivalent.
- **Never use built-in plan mode for planning** — When asked to "plan", "brainstorm", or "deepen a plan", use the custom skills (`/plan`, `/brainstorm`, `/deepen-plan`), never the built-in `EnterPlanMode` tool.

## Commands

See `make help` for all available commands. Key ones:

```bash
make rebuild          # Rebuild containers after code changes
make test             # Run tests
make migrate          # Apply migrations
make seed             # Load test data
make logs-backend     # Debug backend issues
make deploy           # Deploy to production
```

For migration generation (requires message):
```bash
make migrate-generate msg="add user preferences table"
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
- **Simple deployment** — Single VPS + Docker Compose. No CI/CD complexity. VPS uses SSH deploy key at `/root/.ssh/id_ed25519` for GitHub access. Deploy with: `make deploy`
- **Fixture-based testing** — Deterministic, fast tests using Synthea patient bundles.
