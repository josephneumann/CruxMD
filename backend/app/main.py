"""FastAPI application entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config import settings
from app.routes import chat, data, fhir, patients, tasks
from app.services.graph import KnowledgeGraph

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan events for startup/shutdown."""
    # Startup: ensure Neo4j indexes exist
    graph = KnowledgeGraph()
    try:
        if await graph.verify_connectivity():
            await graph.ensure_indexes()
            logger.info("Neo4j indexes ensured")
        else:
            logger.warning("Neo4j not available - skipping index creation")
    finally:
        await graph.close()

    yield  # Application runs here

    # Shutdown: nothing needed currently


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Add security headers to all responses."""

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        # Prevent clickjacking
        response.headers["X-Frame-Options"] = "DENY"
        # Prevent MIME type sniffing
        response.headers["X-Content-Type-Options"] = "nosniff"
        # XSS protection (legacy, but still useful)
        response.headers["X-XSS-Protection"] = "1; mode=block"
        # Referrer policy
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        # Permissions policy (restrict sensitive APIs)
        response.headers["Permissions-Policy"] = (
            "geolocation=(), microphone=(), camera=()"
        )
        return response


app = FastAPI(
    title="CruxMD",
    description="Medical Context Engine - LLM-native platform for clinical intelligence",
    version="0.1.0",
    lifespan=lifespan,
)

# Security headers middleware (applied to all responses)
app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware for frontend
# Parse comma-separated origins from config
_cors_origins = [origin.strip() for origin in settings.cors_origins.split(",") if origin.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["X-API-Key", "Content-Type"],
)

# Include API routers
app.include_router(chat.router, prefix="/api")
app.include_router(patients.router, prefix="/api")
app.include_router(fhir.router, prefix="/api")
app.include_router(data.router, prefix="/api")
app.include_router(tasks.router, prefix="/api")


@app.get("/health")
async def health_check() -> dict:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict:
    """Root endpoint with API info."""
    return {
        "name": "CruxMD API",
        "version": "0.1.0",
        "docs": "/docs",
    }
