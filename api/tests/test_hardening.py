"""Tests for Phase B8 hardening: route cleanliness, body size limits, rate limiting, and log scrubbing."""

import json
import logging
import pytest
from fastapi.testclient import TestClient

from backend.app.core.logging import SensitiveDataFilter
from backend.app.core.middleware import MAX_BODY_SIZE_BYTES
from backend.app.main import create_app


def test_plain_routes_only():
    """Verify that duplicate /api/v1 routes are removed and only plain paths are mounted."""
    app = create_app()
    with TestClient(app) as client:
        # Plain paths should be reachable (not 404)
        health_res = client.get("/health")
        assert health_res.status_code == 200

        # /api/v1 duplicates must return 404
        assert client.get("/api/v1/health").status_code == 404
        assert client.get("/api/v1/auth/login").status_code == 404
        assert client.get("/api/v1/conversations").status_code == 404
        assert client.get("/api/v1/video-jobs").status_code == 404
        assert client.get("/api/v1/roadmap").status_code == 404


def test_request_body_size_limit():
    """Verify that request bodies exceeding 200 KB return HTTP 413 Payload Too Large."""
    app = create_app()
    with TestClient(app) as client:
        # 1. Payload within limit (e.g. 5 KB payload to /auth/login)
        normal_payload = {"email": "test@example.com", "password": "password123"}
        res = client.post("/auth/login", json=normal_payload)
        # Should not be rejected with 413 (may be 401 or 400 depending on credentials)
        assert res.status_code != 413

        # 2. Oversized payload: 250 KB (> 200 KB)
        large_text = "x" * (250 * 1024)
        large_payload = {"email": "test@example.com", "password": large_text}
        large_json = json.dumps(large_payload)

        res_large = client.post(
            "/auth/login",
            content=large_json,
            headers={"Content-Type": "application/json"},
        )
        assert res_large.status_code == 413
        data = res_large.json()
        assert data["error"] == "payload_too_large"
        assert "exceeds maximum allowed size" in data["message"]


def test_sensitive_data_logging_filter():
    """Verify that passwords, tokens, connection strings, and full user code are scrubbed in logs."""
    log_filter = SensitiveDataFilter()

    # 1. JWT token scrubbing
    fake_jwt = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.doNotLeakThisSignature123"
    rec1 = logging.LogRecord("test", logging.INFO, "test.py", 10, f"User token: {fake_jwt}", (), None)
    log_filter.filter(rec1)
    assert fake_jwt not in rec1.msg
    assert "[REDACTED_JWT_TOKEN]" in rec1.msg

    # 2. Bearer header scrubbing
    rec2 = logging.LogRecord("test", logging.INFO, "test.py", 11, "Authorization: Bearer secret_access_token_12345", (), None)
    log_filter.filter(rec2)
    assert "secret_access_token_12345" not in rec2.msg
    assert "Bearer [REDACTED_TOKEN]" in rec2.msg

    # 3. Password scrubbing in JSON
    rec3 = logging.LogRecord("test", logging.INFO, "test.py", 12, '{"email": "a@b.com", "password": "supersecretpassword"}', (), None)
    log_filter.filter(rec3)
    assert "supersecretpassword" not in rec3.msg
    assert '"password": "[REDACTED]"' in rec3.msg

    # 4. Database connection string scrubbing
    rec4 = logging.LogRecord("test", logging.INFO, "test.py", 13, "Connecting to postgresql://admin:super_secret_db_pass@ep-sample.neon.tech/neondb", (), None)
    log_filter.filter(rec4)
    assert "super_secret_db_pass" not in rec4.msg
    assert "postgresql://admin:[REDACTED]@ep-sample.neon.tech/neondb" in rec4.msg

    # 5. Full user code scrubbing
    long_code = 'def solution():\n    ' + '\n    '.join([f"x = {i}" for i in range(50)])
    rec5 = logging.LogRecord("test", logging.INFO, "test.py", 14, f'{{"code": "{long_code}"}}', (), None)
    log_filter.filter(rec5)
    assert "x = 49" not in rec5.msg
    assert "[REDACTED_FULL_USER_CODE]" in rec5.msg

    # 6. Dictionary argument sanitization
    rec6 = logging.LogRecord(
        "test", logging.INFO, "test.py", 15, "Payload: %s",
        ({"password": "secret", "user_code": "a" * 100, "user_id": 42},),
        None,
    )
    log_filter.filter(rec6)
    sanitized_dict = rec6.args if isinstance(rec6.args, dict) else rec6.args[0]
    assert sanitized_dict["password"] == "[REDACTED]"
    assert "[FULL_CODE_REDACTED" in sanitized_dict["user_code"]
    assert sanitized_dict["user_id"] == 42
