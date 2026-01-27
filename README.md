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
- **Auth**: Better-Auth (email/password), bearer token validation
- **Frontend**: Next.js 15, TypeScript, shadcn/ui, Tailwind CSS
- **LLM**: OpenAI GPT-4o
- **Deployment**: Docker Compose, single VPS

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Node.js 20+ and pnpm
- Python 3.12+ and uv
- OpenAI API key

### Setup

```bash
cp .env.example .env                 # Configure environment variables
# Edit .env with your credentials (DB_PASSWORD, BETTER_AUTH_SECRET, ADMIN_EMAIL, etc.)
```

### Development (local processes)

```bash
# Start infrastructure (PostgreSQL, Neo4j)
docker compose up db neo4j -d

# Backend
cd backend
uv sync                              # Install dependencies
uv run alembic upgrade head          # Run migrations
uv run python -m app.scripts.seed_admin     # Create admin user
uv run python -m app.scripts.seed_database  # Seed with Synthea fixtures
uv run uvicorn app.main:app --reload # Start dev server

# Frontend (in another terminal, with backend running)
cd frontend
pnpm install                         # Install dependencies
pnpm dev                             # Start dev server (http://localhost:3000)
```

### Full Stack (Docker)

```bash
make dev                             # or: docker compose up
# Migrations and admin seed run automatically on backend startup
```

### Authentication

CruxMD uses [Better-Auth](https://www.better-auth.com/) for authentication:

- **Email/password** login with email verification
- **Bearer token** validation in FastAPI (reads Better-Auth session table)
- **Admin user** seeded automatically from `ADMIN_EMAIL`/`ADMIN_PASSWORD` in `.env`
- All routes except `/` and `/design/*` require login
- Transactional email via Resend (falls back to console logging if `RESEND_API_KEY` unset)

## Project Structure

```
cruxmd/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI entry point
│   │   ├── auth.py              # Bearer token validation
│   │   ├── config.py            # Settings (env vars)
│   │   ├── database.py          # SQLAlchemy setup
│   │   ├── models/              # SQLAlchemy models (FHIR, auth, profiles)
│   │   ├── routes/              # API endpoints
│   │   ├── scripts/             # seed_admin, seed_database
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
│   ├── app/
│   │   ├── (auth)/              # Login, register, password reset pages
│   │   ├── api/auth/            # Better-Auth API routes
│   │   └── chat/                # Chat page
│   ├── lib/
│   │   ├── auth.ts              # Better-Auth server config
│   │   └── auth-client.ts       # Better-Auth client (useSession, signIn, etc.)
│   ├── middleware.ts             # Route protection (redirects to /login)
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

Copy `.env.example` to `.env` and configure. Key variables:

| Variable | Required | Description |
|----------|----------|-------------|
| `DB_PASSWORD` | Yes | PostgreSQL password |
| `NEO4J_PASSWORD` | Yes | Neo4j password |
| `OPENAI_API_KEY` | Yes | OpenAI API key |
| `BETTER_AUTH_SECRET` | Yes | Secret for session signing |
| `ADMIN_EMAIL` | Yes | Admin user email (seeded on startup) |
| `ADMIN_PASSWORD` | Yes | Admin user password (seeded on startup) |
| `RESEND_API_KEY` | No | Resend email API key (console fallback) |
| `DOMAIN` | Prod | Production domain |

## Documentation

- [Project Plan](docs/cruxmd-v2-plan.md) - Full specification and implementation plan
- [FHIR Reference Audit](docs/fhir-reference-audit.md) - FHIR resource type coverage

## License

Private - All rights reserved.
