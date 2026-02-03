.PHONY: help install dev dev-detached rebuild down stop restart ps status logs logs-backend logs-frontend shell-backend shell-db psql test test-verbose lint format format-check build build-no-cache deploy generate-fixtures seed seed-admin migrate migrate-generate generate-api clean clean-fixtures

# Default target
.DEFAULT_GOAL := help

help:
	@echo "CruxMD v2 - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install all dependencies (backend + frontend)"
	@echo ""
	@echo "Development (Docker):"
	@echo "  make dev              Start dev environment (foreground, rebuilds)"
	@echo "  make dev-detached     Start dev environment (background, rebuilds)"
	@echo "  make rebuild          Rebuild and restart all containers"
	@echo "  make down             Stop and remove containers"
	@echo "  make stop             Stop containers (keep state)"
	@echo "  make restart          Restart all containers"
	@echo "  make ps               Show container status"
	@echo ""
	@echo "Logs & Debugging:"
	@echo "  make logs             Tail all container logs"
	@echo "  make logs-backend     Tail backend logs"
	@echo "  make logs-frontend    Tail frontend logs"
	@echo "  make shell-backend    Shell into backend container"
	@echo "  make shell-db         Shell into database container"
	@echo "  make psql             Connect to PostgreSQL"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test             Run all tests"
	@echo "  make lint             Run linters (ruff + eslint)"
	@echo "  make format           Format code (ruff)"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  make build            Build Docker images"
	@echo "  make deploy           Deploy to production (app.cruxmd.ai)"
	@echo ""
	@echo "Data & Database:"
	@echo "  make generate-fixtures  Generate Synthea patient fixtures"
	@echo "  make seed             Load fixtures into database"
	@echo "  make seed-admin       Create admin user from .env credentials"
	@echo "  make migrate          Run database migrations"
	@echo ""
	@echo "Code Generation:"
	@echo "  make generate-api     Generate frontend API client from OpenAPI"
	@echo ""
	@echo "Cleanup:"
	@echo "  make clean            Remove generated files and caches"
	@echo ""

# =============================================================================
# Setup
# =============================================================================

install:
	@echo "Installing backend dependencies..."
	cd backend && uv sync
	@echo ""
	@echo "Installing frontend dependencies..."
	cd frontend && pnpm install
	@echo ""
	@echo "Done! Run 'make dev' to start the development environment."

dev:
	docker compose up --build

dev-detached:
	docker compose up -d --build

rebuild:
	docker compose up -d --build

down:
	docker compose down

stop:
	docker compose stop

restart:
	docker compose restart

ps:
	docker compose ps

status: ps

logs:
	docker compose logs -f

logs-backend:
	docker compose logs -f backend

logs-frontend:
	docker compose logs -f frontend

shell-backend:
	docker compose exec backend bash

shell-db:
	docker compose exec db bash

psql:
	docker compose exec db psql -U postgres -d cruxmd

# =============================================================================
# Testing & Quality
# =============================================================================

test:
	cd backend && uv run pytest

test-verbose:
	cd backend && uv run pytest -v

lint:
	@echo "Linting backend..."
	cd backend && uv run ruff check .
	@echo ""
	@echo "Linting frontend..."
	cd frontend && pnpm lint

format:
	@echo "Formatting backend..."
	cd backend && uv run ruff format .
	cd backend && uv run ruff check --fix .

format-check:
	@echo "Checking backend formatting..."
	cd backend && uv run ruff format --check .
	cd backend && uv run ruff check .

# =============================================================================
# Build & Deploy
# =============================================================================

build:
	docker compose build

build-no-cache:
	docker compose build --no-cache

deploy:
	@echo "Deploying to production (app.cruxmd.ai)..."
	ssh cruxmd "cd CruxMD && ./deploy.sh"

# =============================================================================
# Data & Database
# =============================================================================

generate-fixtures:
	@echo "Generating Synthea fixtures..."
	@python scripts/generate_fixtures.py --count 5 --output fixtures/synthea

seed:
	@echo "Loading fixtures into database..."
	cd backend && uv run python -m app.scripts.seed_database

seed-admin:
	@echo "Creating admin user from .env credentials..."
	cd backend && uv run python -m app.scripts.seed_admin

migrate:
	@echo "Running database migrations..."
	cd backend && uv run alembic upgrade head

migrate-generate:
ifndef msg
	$(error Usage: make migrate-generate msg="migration description")
endif
	@echo "Generating new migration..."
	cd backend && uv run alembic revision --autogenerate -m "$(msg)"

# =============================================================================
# Code Generation
# =============================================================================

generate-api:
	@echo "Generating API client from OpenAPI spec..."
	cd frontend && pnpm generate-api

# =============================================================================
# Cleanup
# =============================================================================

clean:
	@echo "Cleaning up..."
	rm -rf backend/.pytest_cache
	rm -rf backend/.ruff_cache
	rm -rf frontend/.next
	rm -rf frontend/node_modules/.cache
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@echo "Done!"

clean-fixtures:
	@echo "Removing generated fixtures..."
	rm -rf fixtures/synthea/*.json
