"""Read-only models for Better-Auth tables.

Schema is created via Alembic migration (add_better_auth_tables).
Better-Auth reads/writes these tables. FastAPI only reads BetterAuthSession
for bearer token validation. BetterAuthUser and BetterAuthAccount are used
by the admin seed script.
"""

from datetime import datetime

from sqlalchemy import Boolean, DateTime, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class BetterAuthUser(Base):
    """Better-Auth user table."""

    __tablename__ = "user"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    emailVerified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    image: Mapped[str | None] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class BetterAuthSession(Base):
    """Better-Auth session table."""

    __tablename__ = "session"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    expiresAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    token: Mapped[str] = mapped_column(Text, unique=True, index=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    ipAddress: Mapped[str | None] = mapped_column(Text, nullable=True)
    userAgent: Mapped[str | None] = mapped_column(Text, nullable=True)
    userId: Mapped[str] = mapped_column(Text, nullable=False, index=True)


class BetterAuthAccount(Base):
    """Better-Auth account table."""

    __tablename__ = "account"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    accountId: Mapped[str] = mapped_column(Text, nullable=False)
    providerId: Mapped[str] = mapped_column(Text, nullable=False)
    userId: Mapped[str] = mapped_column(Text, nullable=False)
    accessToken: Mapped[str | None] = mapped_column(Text, nullable=True)
    refreshToken: Mapped[str | None] = mapped_column(Text, nullable=True)
    idToken: Mapped[str | None] = mapped_column(Text, nullable=True)
    accessTokenExpiresAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    refreshTokenExpiresAt: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    scope: Mapped[str | None] = mapped_column(Text, nullable=True)
    password: Mapped[str | None] = mapped_column(Text, nullable=True)
    createdAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updatedAt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
