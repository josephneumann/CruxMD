#!/usr/bin/env bash
# Backend entrypoint: run migrations, seed admin, then start server
set -e

echo "Running database migrations..."
alembic upgrade head

echo "Seeding admin user..."
python -m app.scripts.seed_admin

echo "Starting server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000
