"""Tests for application configuration and settings."""

from backend.app.config import Settings


def test_default_settings():
    """Verify default setting values and types."""
    settings = Settings(
        APP_ENV="development",
        DATABASE_URL="postgresql+psycopg://user:pass@localhost:5432/testdb",
        CORS_ORIGINS=["http://localhost:5173"],
    )
    assert settings.APP_NAME == "Pebble"
    assert settings.APP_ENV == "development"
    assert settings.CORS_ORIGINS == ["http://localhost:5173"]
    assert settings.VIDEO_PROVIDER == "mock"


def test_cors_origins_json_parsing():
    """Verify CORS origins stringified JSON array parses correctly."""
    settings = Settings(
        CORS_ORIGINS='["http://localhost:5173", "http://127.0.0.1:5173"]'
    )
    assert "http://localhost:5173" in settings.CORS_ORIGINS
    assert "http://127.0.0.1:5173" in settings.CORS_ORIGINS


def test_cors_origins_comma_parsing():
    """Verify CORS origins comma separated string parses correctly."""
    settings = Settings(
        CORS_ORIGINS="http://localhost:5173, http://127.0.0.1:5173"
    )
    assert "http://localhost:5173" in settings.CORS_ORIGINS
    assert "http://127.0.0.1:5173" in settings.CORS_ORIGINS
