"""Tests for GET /health endpoint and CORS behavior."""

from unittest.mock import patch
from fastapi.testclient import TestClient
from backend.app.repositories.health_repository import HealthRepository


def test_health_endpoint_db_disconnected(client: TestClient):
    """GET /health when database is not connected or reachable."""
    with patch.object(HealthRepository, "ping_database", return_value=False):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "ok", "db": False}


def test_health_endpoint_db_connected(client: TestClient):
    """GET /health when database ping succeeds."""
    with patch.object(HealthRepository, "ping_database", return_value=True):
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data == {"status": "ok", "db": True}


def test_health_prefixed_route(client: TestClient):
    """GET /api/v1/health returns 404 since duplicate prefixed routes are removed in Phase B8."""
    response = client.get("/api/v1/health")
    assert response.status_code == 404


def test_health_repository_exception_safety():
    """Verify repository catches errors safely without raising unhandled exceptions."""
    with patch("backend.app.repositories.health_repository.get_engine", side_effect=Exception("Connection refused")):
        repo = HealthRepository()
        assert repo.ping_database() is False


def test_cors_headers(client: TestClient):
    """Verify CORS headers allow http://localhost:5173."""
    response = client.options(
        "/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert response.headers.get("access-control-allow-origin") == "http://localhost:5173"
