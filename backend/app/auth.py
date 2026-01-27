"""Bearer token authentication via Better-Auth session table."""

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.auth import BetterAuthSession

bearer_scheme = HTTPBearer(auto_error=False)


async def verify_bearer_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> str:
    """Validate a bearer token against the Better-Auth session table.

    Returns:
        The authenticated user_id.

    Raises:
        HTTPException: 401 if token is missing, invalid, or expired.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication token",
        )

    token = credentials.credentials
    result = await db.execute(
        select(BetterAuthSession).where(
            BetterAuthSession.token == token,
            BetterAuthSession.expiresAt > datetime.now(timezone.utc),
        )
    )
    session = result.scalar_one_or_none()

    if session is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    return session.userId
