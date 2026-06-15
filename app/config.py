"""Configuration and settings loading for CarbonCompass.

This module loads environment variables and parses configuration settings
using Pydantic's BaseSettings.
"""

import os
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables and defaults.

    Attributes:
        GEMINI_API_KEY (str): API key for the Google Gemini generative AI.
        ENV (str): Application execution environment (e.g. production, testing).
        APP_NAME (str): The name of the application.
        APP_VERSION (str): The semantic version of the application.
        APP_TAGLINE (str): Tagline for the application.
        APP_DESCRIPTION (str): Detailed description of the application.
    """

    GEMINI_API_KEY: str = os.getenv("GEMINI_API_KEY", "")
    ENV: str = os.getenv("ENV", "production")

    # Application metadata
    APP_NAME: str = "CarbonCompass"
    APP_VERSION: str = "1.0.0"
    APP_TAGLINE: str = "Navigate Towards a Greener Future"
    APP_DESCRIPTION: str = "AI-powered carbon footprint tracking and reduction platform"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )


@lru_cache()
def get_settings() -> Settings:
    """Load and return the cached application configuration settings.

    Returns:
        Settings: The application settings instance.

    Raises:
        RuntimeError: If the GEMINI_API_KEY environment variable is not configured.
    """
    settings = Settings()
    if (
        not settings.GEMINI_API_KEY
        or settings.GEMINI_API_KEY == "your_gemini_api_key_here"
    ):
        raise RuntimeError("GEMINI_API_KEY environment variable not set")
    return settings
