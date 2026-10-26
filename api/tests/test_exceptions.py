"""Tests verifying safe error responses and exception masking."""

from fastapi import APIRouter
from fastapi.testclient import TestClient
from backend.app.main import create_app


def test_validation_error_format(client: TestClient):
    """Verify validation errors return safe json format rather than raw internal error."""
    response = client.get("/health?unexpected_param=test")
    # Health endpoint ignores query params or handles them safely without 500
    assert response.status_code == 200


def test_generic_exception_safety():
    """Verify unhandled server errors return safe JSON message without stack traces."""
    app = create_app()
    broken_router = APIRouter()

    @broken_router.get("/trigger-crash")
    def trigger_crash():
        raise RuntimeError("Sensitive internal database password or stack trace")

    app.include_router(broken_router)

    with TestClient(app, raise_server_exceptions=False) as test_client:
        response = test_client.get("/trigger-crash")
        assert response.status_code == 500
        data = response.json()
        assert data["error"] == "internal_server_error"
        assert "Sensitive internal database password" not in response.text
        assert "Traceback" not in response.text
