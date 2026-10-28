"""Shared pytest fixtures for Pebble backend."""

import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

# Ensure test configuration environment
os.environ["APP_ENV"] = "testing"
os.environ["DEBUG"] = "true"

from backend.app.config import get_settings
from backend.app.db.session import get_db
from backend.app.main import create_app


def pytest_configure(config):
    config.addinivalue_line("markers", "db: mark test that requires the database")


@pytest.fixture(scope="session")
def db_engine():
    """Create test engine, run Alembic migrations, and provide engine.
    Skips DB-marked tests if TEST_DATABASE_URL is not set.
    """
    settings = get_settings()
    test_url = settings.TEST_DATABASE_URL
    if not test_url:
        pytest.skip("TEST_DATABASE_URL not set - skipping DB tests.")

    # Convert plain postgres URL to psycopg driver string if needed
    if test_url.startswith("postgresql://"):
        test_url = test_url.replace("postgresql://", "postgresql+psycopg://", 1)
    elif test_url.startswith("postgres://"):
        test_url = test_url.replace("postgres://", "postgres+psycopg://", 1)

    from alembic import command
    from alembic.config import Config

    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", test_url)
    command.upgrade(alembic_cfg, "head")

    engine = create_engine(test_url, future=True)
    yield engine
    engine.dispose()


@pytest.fixture
def db_session(db_engine):
    """Provide a DB session wrapped in an outer transaction that rolls back.
    Used by API tests and DB repository tests to keep the test DB clean.
    """
    connection = db_engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    try:
        yield session
    finally:
        session.close()
        if transaction.is_active:
            transaction.rollback()
        connection.close()


@pytest.fixture
def client(request):
    """FastAPI TestClient.
    If the test or its fixtures require the database, overrides get_db with the transactional db_session.
    Otherwise runs as an in-memory client, so non-DB tests execute even if TEST_DATABASE_URL is unset.
    """
    from backend.app.core.rate_limit import limiter
    limiter.reset()

    app = create_app()

    if request.node.get_closest_marker("db") or "db_session" in request.fixturenames:
        db_session = request.getfixturevalue("db_session")

        def get_db_override():
            try:
                yield db_session
            finally:
                pass

        app.dependency_overrides[get_db] = get_db_override

    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
    limiter.reset()


@pytest.fixture(autouse=True)
def force_test_settings(monkeypatch):
    """Force VIDEO_PROVIDER=mock and INTENT_PROVIDER=off to decouple tests from local .env."""
    monkeypatch.setenv("VIDEO_PROVIDER", "mock")
    monkeypatch.setenv("INTENT_PROVIDER", "off")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()

