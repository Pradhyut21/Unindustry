"""
App configuration via pydantic-settings.
All values can be overridden via environment variables or .env file.
"""

from __future__ import annotations

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = (
        "postgresql+asyncpg://producttruth:producttruth@localhost:5432/producttruth"
    )

    # Anthropic / Claude
    anthropic_api_key: str = ""
    claude_extraction_model: str = "claude-3-5-haiku-20241022"   # cheap, high-volume
    claude_verification_model: str = "claude-3-5-sonnet-20241022"  # stronger, used only for verify step

    # Pipeline behaviour
    confidence_threshold: float = 0.7  # fields below this go to HITL queue
    min_sources_for_verified: int = 2   # how many independent sources must agree

    # App
    environment: str = "development"
    version: str = "0.1.0"


settings = Settings()
