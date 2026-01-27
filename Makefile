.PHONY: help install dev dev-detached test test-verbose lint format format-check build build-no-cache deploy generate-fixtures seed seed-admin migrate migrate-generate generate-api clean clean-fixtures

# Default target
.DEFAULT_GOAL := help

help:
	@echo "CruxMD v2 - Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  make install          Install all dependencies (backend + frontend)"
	@echo "  make dev              Start development environment (docker compose)"
	@echo ""
	@echo "Testing & Quality:"
	@echo "  make test             Run all tests"
	@echo "  make lint             Run linters (ruff + eslint)"
	@echo "  make format           Format code (ruff)"
	@echo ""
	@echo "Build & Deploy:"
	@echo "  make build            Build Docker images for production"
	@echo "  make deploy           Deploy latest code to production (app.cruxmd.ai)"
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
	docker compose up

dev-detached:
	docker compose up -d

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
	ssh cruxmd "cd CruxMD && git pull && ./deploy.sh"

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
