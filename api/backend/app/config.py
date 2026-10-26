"""Application configuration loaded from environment variables."""

from functools import lru_cache
from typing import List, Optional, Union
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
import json


class Settings(BaseSettings):
    """Core application settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    APP_ENV: str = Field(default="development", description="Application environment")
    APP_NAME: str = Field(default="Pebble", description="Application name")
    API_PREFIX: str = Field(default="/api/v1", description="Prefix for API routes")
    DEBUG: bool = Field(default=True, description="Debug mode")

    DATABASE_URL: str = Field(
        default="",
        description="NeonDB PostgreSQL connection string with psycopg 3 driver",
    )
    TEST_DATABASE_URL: Optional[str] = Field(
        default=None,
        description="NeonDB test branch connection string for integration testing",
    )

    SECRET_KEY: str = Field(
        default="dev-secret-key-change-in-production-min-32-chars",
        description="Secret key for security and token hashing",
    )
    JWT_SECRET: str = Field(
        default="dev-jwt-secret-key-change-in-production-min-32-chars",
        description="Secret key for JWT encoding and decoding",
    )
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT encoding algorithm",
    )
    ACCESS_TOKEN_EXPIRE_MINUTES: int = Field(
        default=60,
        description="Access token lifespan in minutes",
    )

    CORS_ORIGINS: Union[List[str], str] = Field(
        default=["http://localhost:5173"],
        description="Allowed CORS origins",
    )

    VIDEO_PROVIDER: str = Field(
        default="mock",
        description="Video generation provider (mock until Phase B11)",
    )
    VIDEO_ENGINE_URL: str = Field(
        default="http://localhost:8001",
        description="URL for teammate-owned video engine API",
    )
    VIDEO_ENGINE_API_KEY: str = Field(
        default="",
        description="X-API-Key header secret for video engine (optional)",
    )
    VIDEO_JOB_TIMEOUT_MINUTES: int = Field(
        default=30,
        description="Video generation job timeout in minutes",
    )

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, value: Union[str, List[str]]) -> List[str]:
        if isinstance(value, str):
            value = value.strip()
            if value.startswith("[") and value.endswith("]"):
                try:
                    return json.loads(value)
                except Exception:
                    pass
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value


@lru_cache
def get_settings() -> Settings:
    """Return cached application settings."""
    return Settings()
