"""Application configuration using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # PostgreSQL Database
    database_url: str = "postgresql+asyncpg://postgres:password@localhost:5432/cruxmd"

    # Neo4j Knowledge Graph
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "password"

    # Authentication
    api_key: str = "dev-api-key"

    # OpenAI
    openai_api_key: str = ""

    # Application
    debug: bool = False


settings = Settings()
