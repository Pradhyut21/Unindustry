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

    # Groq API (OpenAI-compatible)
    groq_api_key: str = ""
    # llama-3.3-70b-versatile — strong quality, fast on Groq
    groq_extraction_model: str = "llama-3.3-70b-versatile"
    # Vision model — llama-4-scout requires upgraded Groq tier.
    # Set to empty string to fall back to text-only image description.
    # If you have access: "meta-llama/llama-4-scout-17b-16e-instruct"
    groq_vision_model: str = ""  # leave blank if not on vision tier

    # Pipeline behaviour
    confidence_threshold: float = 0.7  # fields below this go to HITL queue
    min_sources_for_verified: int = 2   # how many independent sources must agree

    # App
    environment: str = "development"
    version: str = "0.1.0"


settings = Settings()
