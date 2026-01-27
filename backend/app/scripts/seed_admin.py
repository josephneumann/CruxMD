"""Seed an admin user into Better-Auth tables.

Reads ADMIN_EMAIL and ADMIN_PASSWORD from environment / .env and creates
user + account + session records so the admin can log in immediately.

Usage:
    uv run python -m app.scripts.seed_admin

Idempotent — skips if a user with the admin email already exists.
"""

import asyncio
import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, text

from app.config import settings
from app.database import async_session_maker, engine
from app.models.auth import BetterAuthAccount, BetterAuthSession, BetterAuthUser


def _hash_password(password: str) -> str:
    """Hash password using scrypt, matching Better-Auth's format.

    Better-Auth uses: scrypt(N=16384, r=16, p=1, dkLen=64)
    Output format: hex(salt):hex(derived_key)
    """
    import hashlib
    import os

    salt_hex = os.urandom(16).hex()
    # Better-Auth passes the hex string (not raw bytes) as salt to scrypt
    key = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt_hex.encode("utf-8"),
        n=16384,
        r=16,
        p=1,
        dklen=64,
        maxmem=128 * 16384 * 16 * 2,
    )
    return f"{salt_hex}:{key.hex()}"


async def seed_admin() -> None:
    email = settings.admin_email
    password = settings.admin_password

    first_name = settings.admin_first_name
    last_name = settings.admin_last_name

    if not email or not password:
        print("ERROR: ADMIN_EMAIL and ADMIN_PASSWORD must be set in .env")
        return

    name = f"{first_name} {last_name}".strip() or "Admin"

    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    print("  PostgreSQL: connected")

    async with async_session_maker() as session:
        # Check if admin already exists
        result = await session.execute(
            select(BetterAuthUser).where(BetterAuthUser.email == email)
        )
        existing = result.scalar_one_or_none()

        if existing:
            print(f"  Admin user already exists: {email} (id={existing.id})")
            return

        now = datetime.now(timezone.utc)
        user_id = str(uuid.uuid4())
        account_id = str(uuid.uuid4())
        session_id = str(uuid.uuid4())
        session_token = str(uuid.uuid4())

        # Create user
        user = BetterAuthUser(
            id=user_id,
            name=name,
            email=email,
            emailVerified=True,
            createdAt=now,
            updatedAt=now,
        )
        session.add(user)
        await session.flush()

        # Create credential account (email/password)
        account = BetterAuthAccount(
            id=account_id,
            accountId=user_id,
            providerId="credential",
            userId=user_id,
            password=_hash_password(password),
            createdAt=now,
            updatedAt=now,
        )
        session.add(account)

        # Create an active session so bearer token works immediately
        auth_session = BetterAuthSession(
            id=session_id,
            token=session_token,
            userId=user_id,
            expiresAt=now + timedelta(days=7),
            createdAt=now,
            updatedAt=now,
        )
        session.add(auth_session)

        await session.commit()
        print(f"  Admin user created: {email} (id={user_id})")


if __name__ == "__main__":
    asyncio.run(seed_admin())
