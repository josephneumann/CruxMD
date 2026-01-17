# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

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
uv run python -m app.scripts.load_synthea  # Load Synthea patient bundles
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
- **Simple deployment** — Single VPS + Docker Compose. No CI/CD complexity. `git pull && docker compose up`.
- **Fixture-based testing** — Deterministic, fast tests using Synthea patient bundles.

---

## Philosophy: Parallel Agentic Development

This project uses a specific approach to AI-assisted development:

1. **Parallel by default** — Multiple Claude sessions work simultaneously on independent tasks, each in isolated git worktrees.

2. **Orchestrator + Workers** — One session orients and identifies parallelizable work; worker sessions execute discrete tasks. The orchestrator sees the big picture, workers focus deeply.

3. **Task isolation** — Each task gets its own branch/worktree, preventing conflicts and enabling clean PRs.

4. **Bounded autonomy** — Claude can work autonomously (ralph mode) but within bounds: clear acceptance criteria, test-driven completion, iteration limits.

5. **Handoffs over context bloat** — When context grows large, hand off to a fresh session rather than degrading quality.

6. **Tests as the contract** — "Done" means tests pass. No subjective completion criteria.

7. **Human remains in control** — Clarifying questions before implementation, PR approval, task prioritization stays with human.

8. **Session summaries for coordination** — Detailed output enables asynchronous coordination between sessions.

9. **Context window discipline** — No single task should exhaust the context window. Break big tasks into smaller ones.

10. **Routine tasks become skills** — Anything you do repeatedly should be codified as a skill or automation.

---

## Agent Workflow Skills

This project uses custom Claude Code skills for multi-agent task management with beads (`bd`). Tasks can run in **manual mode** (interactive) or **ralph mode** (autonomous iteration until tests pass).

---

### `/orient` — Project Orientation

Builds project context and identifies parallelizable work. Use at session start.

1. Reads core docs (CLAUDE.md, AGENTS.md, PROJECT_SPEC.md)
2. Reviews beads task state (`bd list`, `bd ready`, dependencies)
3. Outputs orientation report with recommended parallel work streams

---

### `/dispatch` — Spawn Parallel Workers

Spawns multiple Claude Code workers for parallel task execution. Use from an orchestrator session.

**Usage:**
```bash
/dispatch --count 3                              # Auto-select 3 ready tasks
/dispatch MoneyPrinter-ajq MoneyPrinter-4b3      # Specific tasks
/dispatch MoneyPrinter-ajq:"Use PriceCache"      # With custom handoff context
/dispatch MoneyPrinter-ajq --no-ralph            # Manual mode (no ralph-loop)
```

**What it does:**
1. Identifies tasks (from args or `bd ready`)
2. Generates handoff context for each task
3. Shows summary and asks for confirmation
4. Runs `mp-spawn` for each task (creates worktrees, spawns workers in iTerm2 tabs)
5. Provides guidance on attaching to workers

**After dispatch:**
1. Switch to iTerm2 (`Cmd+Tab`)
2. Answer the trust prompt for each worktree
3. Paste the command (`Cmd+V`) and press Enter
4. Use `Cmd+1/2/3` to navigate between worker tabs

---

### `/start-task <task-id> [flags]` — Start Working on a Task

Sets up isolated environment for a beads task. Two modes available:

| Mode | Command | Behavior |
|------|---------|----------|
| **Manual** | `/start-task <id>` | Interactive implementation with human guidance |
| **Ralph** | `/start-task <id> --ralph` | Autonomous loop until tests pass |

**Setup (both modes):**
1. Validates task, creates git worktree, sets `BEADS_NO_DAEMON=1`
2. Claims task (`bd update --status in_progress`)
3. Asks clarifying questions before implementation
4. Waits for "Ready to begin?" confirmation

**Flags:**
| Flag | Description |
|------|-------------|
| `--handoff "<text>"` | Context from previous session |
| `--ralph` | Enable autonomous ralph-loop mode |
| `--max-iterations N` | Ralph iteration limit (default: 10) |

**Examples:**
```bash
/start-task 46j.1                                       # Manual mode
/start-task 46j.1 --handoff "Use PriceCache for OHLCV"  # Manual + handoff context
/start-task 46j.1 --ralph                               # Ralph mode (10 iterations max)
/start-task 46j.1 --ralph --max-iterations 50           # Ralph mode (50 iterations)
/start-task 46j.1 --ralph --handoff "Use 3% tolerance"  # Ralph + handoff context
```

---

### Ralph-Loop Mode (Autonomous Implementation)

When `--ralph` is used, after setup and Q&A confirmation:

1. **Loop activates** — Claude implements iteratively, running tests frequently
2. **Success** — When all tests pass, outputs `<promise>ALL TESTS PASSING</promise>`
3. **Exit** — Loop ends, prompts "Run `/finish-task <id>`"
4. **Max iterations** — If limit reached, outputs handoff command for new session

**Best Practices for Ralph Mode:**

| Do | Don't |
|----|-------|
| Use for well-defined implementation tasks | Use for research or exploration |
| Ensure task has clear acceptance criteria | Use for tasks requiring design decisions |
| Start with existing test patterns to follow | Use for greenfield without test examples |
| Set realistic `--max-iterations` (10-30) | Set unlimited iterations |
| Answer clarifying questions thoroughly | Rush through the Q&A step |

**Good ralph candidates:**
- Adding a new module following existing patterns
- Implementing a feature with clear spec
- Bug fixes with reproducible test cases
- Database schema additions with defined fields

**Poor ralph candidates:**
- Research tasks (no clear "done" state)
- UI/UX work (subjective success criteria)
- Architecture decisions (need human judgment)
- Tasks requiring external API exploration

**Completion signal:**
```
<promise>ALL TESTS PASSING</promise>
```
Only output when tests show 0 failures. Never output false promises to escape the loop.

---

### `/finish-task <task-id>` — Complete a Task

Closes out a task with full verification. **Work is NOT complete until git push succeeds.**

1. Verifies task state and worktree location
2. Runs tests — **must pass to continue**
3. Reviews/updates documentation if needed
4. Creates follow-up issues for any remaining work (`bd create`)
5. Commits with conventional format + `Closes: <task-id>`
6. Syncs beads (`bd sync`), pushes to remote
7. Closes task (`bd close <task-id>`)
8. Creates PR (`gh pr create`)
9. Offers to merge PR (squash) and cleanup worktree
10. Outputs detailed session summary for orchestrating agents

**Critical:** Tests must pass before closing. Never close a task with failing tests.

---

### `/handoff-task <task-id>` — Generate Handoff Context

Generates session-specific context to pass to another agent session.

1. Validates task exists
2. Reads task scope (title, dependencies, priority)
3. Summarizes decisions, gotchas, and recommendations from current session
4. Outputs copy-pasteable `/start-task` command with `--handoff` context

**Output format:**
```
==============================================
HANDOFF: <task-id>
==============================================
Task: <title>
Priority: <priority>

To start this task in a new session, run:
/start-task <task-id> --handoff "<context>"
==============================================
```

**Use case:** When an orchestrating session identifies work for a parallel worker, or when handing off incomplete work to a new session.

---

### `/summarize-session <task-id>` — Session Summary (Read-only)

Generates detailed summary without committing, pushing, or closing. Useful for progress check-ins.

1. Gathers context (task state, git status, recent commits)
2. Identifies files created/modified
3. Checks test status
4. Outputs structured summary for orchestrating agents

**Output includes:** Task overview, implementation summary, files changed, tests, git activity, dependencies unblocked, architectural notes, handoff context.

---

### Workflow Examples

**Manual parallel workflow:**
```
Session A (Orchestrator):   /orient → identifies 46j.1, 46j.2, 46j.3
Session B (Worker):         /start-task 46j.1 → implement → /finish-task 46j.1
Session C (Worker):         /start-task 46j.2 → implement → /finish-task 46j.2
```

**Ralph autonomous workflow:**
```
Session B (Worker):
  /start-task 46j.1 --ralph
  → Setup completes, Q&A answered
  → "Ready to begin?" confirmed
  → Ralph loop runs autonomously
  → Tests pass → "Run /finish-task 46j.1"
  /finish-task 46j.1
```

**Ralph with handoff (max iterations reached):**
```
Session B:
  /start-task 46j.1 --ralph --max-iterations 20
  → Loop hits 20 iterations without tests passing
  → Outputs: /start-task 46j.1 --ralph --handoff "Continued from ralph-loop..."

Session C (new session):
  /start-task 46j.1 --ralph --handoff "Continued from ralph-loop..."
  → Continues work with previous context
```

**Orchestrator dispatch workflow:**
```
Session A (Orchestrator):
  /orient                           # Identify ready work
  /dispatch --count 3 --ralph       # Spawn 3 workers
  → Workers spawn in iTerm2 tabs
  → Switch to iTerm2, paste commands, answer trust prompts
  → Use Cmd+1/2/3 to switch between worker tabs
```

---

## Shell Utilities

These shell utilities support the multi-agent workflow. They are installed via the `claude-config` repo's `install.sh`.

### `mp-spawn` — Spawn a Worker

Spawns a Claude Code worker in a new iTerm2 tab (via AppleScript).

```bash
mp-spawn <task-id> [options]

Options:
  --dir /path/to/project  Project directory (default: current directory)
  --handoff "text"        Handoff context from previous session
  --ralph                 Enable autonomous ralph-loop mode
  --max-iterations N      Max ralph iterations (default: 10)
```

**Examples:**
```bash
mp-spawn MoneyPrinter-ajq --ralph
mp-spawn MoneyPrinter-ajq --dir "$(pwd)" --handoff "Use PriceCache pattern"
```

**After spawn:**
1. Switch to iTerm2 (`Cmd+Tab`)
2. Answer the trust prompt for the worktree directory
3. Paste the command (`Cmd+V`) — it's already on your clipboard
4. Press Enter to start the task

### iTerm2 Integration

- Uses AppleScript to create new iTerm2 tabs directly
- Copies `/start-task` command to clipboard (paste after trust prompt)
- Switch between workers with `Cmd+1/2/3` or `Cmd+Shift+[/]`
- Each tab is named with the task short ID (e.g., "ajq")
