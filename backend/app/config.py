"""
Configuration management using pydantic-settings.

This module loads settings from environment variables (or a .env file).
In production, secrets like API keys come from environment variables
set by your deployment platform — never hardcoded in source code.
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    anthropic_api_key: str
    braintrust_api_key: str | None = None
    model_name: str = "claude-sonnet-4-5"
    max_tokens: int = 1024

    model_config = {
        "env_file": ".env",        # Load from .env file if it exists
        "env_file_encoding": "utf-8",
    }


# Create a single settings instance used across the app
settings = Settings()