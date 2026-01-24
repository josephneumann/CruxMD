"""Application configuration using pydantic-settings."""

import warnings
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


# Sentinel values that indicate unconfigured credentials
_UNCONFIGURED_DB = "postgresql+asyncpg://postgres:CHANGE_ME@localhost:5432/cruxmd"
_UNCONFIGURED_NEO4J_PASSWORD = "CHANGE_ME"
_UNCONFIGURED_API_KEY = "CHANGE_ME"

# Find .env file: check backend dir first, then project root
_BACKEND_DIR = Path(__file__).parent.parent
_PROJECT_ROOT = _BACKEND_DIR.parent
_ENV_FILE = _BACKEND_DIR / ".env" if (_BACKEND_DIR / ".env").exists() else _PROJECT_ROOT / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    IMPORTANT: All sensitive credentials must be explicitly configured via
    environment variables or .env file. Default values use 'CHANGE_ME' sentinel
    to make misconfiguration obvious.
    """

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # PostgreSQL Database
    database_url: str = _UNCONFIGURED_DB

    # Neo4j Knowledge Graph
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = _UNCONFIGURED_NEO4J_PASSWORD

    # Authentication
    api_key: str = _UNCONFIGURED_API_KEY

    # OpenAI
    openai_api_key: str = ""

    # Anthropic
    anthropic_api_key: str = ""

    # Application
    debug: bool = False

    def model_post_init(self, __context) -> None:
        """Warn about unconfigured credentials."""
        if self.api_key == _UNCONFIGURED_API_KEY:
            warnings.warn(
                "API_KEY not configured! Set API_KEY environment variable.",
                UserWarning,
                stacklevel=2,
            )
        if self.neo4j_password == _UNCONFIGURED_NEO4J_PASSWORD:
            warnings.warn(
                "NEO4J_PASSWORD not configured! Set NEO4J_PASSWORD environment variable.",
                UserWarning,
                stacklevel=2,
            )
        if _UNCONFIGURED_DB in self.database_url or "CHANGE_ME" in self.database_url:
            warnings.warn(
                "DATABASE_URL not configured! Set DATABASE_URL environment variable.",
                UserWarning,
                stacklevel=2,
            )


settings = Settings()
