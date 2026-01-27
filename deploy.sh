#!/usr/bin/env bash
# CruxMD Production Deployment Script
# Usage: ./deploy.sh
#
# Prerequisites:
# - .env file with required environment variables
# - Docker and Docker Compose installed
# - DNS configured for DOMAIN

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Change to script directory (project root)
cd "$(dirname "$0")"

# Check for .env file
if [[ ! -f .env ]]; then
    log_error ".env file not found. Copy .env.example to .env and configure."
    exit 1
fi

# Source .env to check required variables
set -a
source .env
set +a

# Validate required environment variables
REQUIRED_VARS=(
    "DB_PASSWORD"
    "NEO4J_PASSWORD"
    "OPENAI_API_KEY"
    "BETTER_AUTH_SECRET"
    "ADMIN_EMAIL"
    "ADMIN_PASSWORD"
    "DOMAIN"
)

missing_vars=()
for var in "${REQUIRED_VARS[@]}"; do
    if [[ -z "${!var:-}" ]]; then
        missing_vars+=("$var")
    fi
done

if [[ ${#missing_vars[@]} -gt 0 ]]; then
    log_error "Missing required environment variables:"
    for var in "${missing_vars[@]}"; do
        echo "  - $var"
    done
    exit 1
fi

log_info "Deploying CruxMD to ${DOMAIN}"

# Pull latest code
log_info "Pulling latest code..."
git pull origin main

# Build and start containers
log_info "Building and starting containers..."
docker compose -f docker-compose.prod.yml build
docker compose -f docker-compose.prod.yml up -d

# Wait for database to be healthy
log_info "Waiting for database to be ready..."
max_attempts=30
attempt=0
while ! docker compose -f docker-compose.prod.yml exec -T db pg_isready -U postgres > /dev/null 2>&1; do
    attempt=$((attempt + 1))
    if [[ $attempt -ge $max_attempts ]]; then
        log_error "Database failed to become ready after $max_attempts attempts"
        exit 1
    fi
    echo -n "."
    sleep 2
done
echo ""
log_info "Database is ready"

# Migrations and admin seed run automatically via entrypoint.sh
# Wait briefly for backend to finish startup
log_info "Waiting for backend startup (migrations + admin seed)..."
sleep 5

# Show status
log_info "Deployment complete! Service status:"
docker compose -f docker-compose.prod.yml ps

log_info "CruxMD is now running at https://${DOMAIN}"
