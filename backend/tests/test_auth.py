"""Tests for bearer token authentication."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi import Depends, FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.auth import verify_bearer_token
from app.database import get_db
from app.models.auth import BetterAuthSession


@pytest.fixture
def protected_app(test_engine):
    """Create a test app with a protected endpoint and test DB."""
    app = FastAPI()

    test_session_maker = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async def override_get_db():
        async with test_session_maker() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise

    app.dependency_overrides[get_db] = override_get_db

    @app.get("/protected")
    async def protected_endpoint(user_id: str = Depends(verify_bearer_token)):
        return {"message": "success", "user_id": user_id}

    return app


@pytest.fixture
async def protected_client(protected_app):
    """Async test client for protected app."""
    async with AsyncClient(
        transport=ASGITransport(app=protected_app),
        base_url="http://test",
    ) as ac:
        yield ac


@pytest.fixture
async def seed_session(db_session: AsyncSession):
    """Create a valid session in the database."""
    session = BetterAuthSession(
        id="test-session-id",
        token="valid-test-token",
        userId="test-user-123",
        expiresAt=datetime.now(timezone.utc) + timedelta(hours=1),
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )
    db_session.add(session)
    await db_session.commit()
    return session


@pytest.fixture
async def seed_expired_session(db_session: AsyncSession):
    """Create an expired session in the database."""
    session = BetterAuthSession(
        id="expired-session-id",
        token="expired-test-token",
        userId="test-user-456",
        expiresAt=datetime.now(timezone.utc) - timedelta(hours=1),
        createdAt=datetime.now(timezone.utc),
        updatedAt=datetime.now(timezone.utc),
    )
    db_session.add(session)
    await db_session.commit()
    return session


@pytest.mark.asyncio
async def test_valid_bearer_token(protected_client, seed_session):
    """Test that valid bearer token allows access."""
    response = await protected_client.get(
        "/protected",
        headers={"Authorization": "Bearer valid-test-token"},
    )
    assert response.status_code == 200
    assert response.json()["user_id"] == "test-user-123"


@pytest.mark.asyncio
async def test_missing_token(protected_client):
    """Test that missing token returns 401."""
    response = await protected_client.get("/protected")
    assert response.status_code == 401
    assert response.json()["detail"] == "Missing authentication token"


@pytest.mark.asyncio
async def test_invalid_token(protected_client):
    """Test that invalid token returns 401."""
    response = await protected_client.get(
        "/protected",
        headers={"Authorization": "Bearer nonexistent-token"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"


@pytest.mark.asyncio
async def test_expired_token(protected_client, seed_expired_session):
    """Test that expired session token returns 401."""
    response = await protected_client.get(
        "/protected",
        headers={"Authorization": "Bearer expired-test-token"},
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid or expired token"
