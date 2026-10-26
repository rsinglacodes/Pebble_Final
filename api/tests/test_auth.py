"""Tests for authentication endpoints and security behaviors."""

import pytest
from fastapi import status
from sqlalchemy.orm import Session
from backend.app.repositories.user_repository import UserRepository


@pytest.mark.db
def test_register_ok(client, db_session: Session):
    """Register ok: returns 201, safe user object, and stores Argon2 password hash."""
    plain_password = "SecurePassword123!"
    payload = {
        "name": "Jane Doe",
        "email": "  Jane.Doe@Example.COM  ",
        "password": plain_password,
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()
    assert data["name"] == "Jane Doe"
    assert data["email"] == "jane.doe@example.com"
    assert data["onboarding_completed"] is False
    assert "id" in data
    assert "password_hash" not in data

    # Verify stored password hash in DB starts with $argon2 and is not plaintext
    user = UserRepository.get_by_email(db_session, "jane.doe@example.com")
    assert user is not None
    assert user.password_hash is not None
    assert user.password_hash.startswith("$argon2")
    assert user.password_hash != plain_password


@pytest.mark.db
def test_register_duplicate_email_409(client):
    """Duplicate email registration returns 409 Conflict."""
    payload = {
        "name": "Alice Smith",
        "email": "alice.duplicate@example.com",
        "password": "Password123!",
    }
    resp1 = client.post("/auth/register", json=payload)
    assert resp1.status_code == status.HTTP_201_CREATED

    resp2 = client.post("/auth/register", json=payload)
    assert resp2.status_code == status.HTTP_409_CONFLICT
    assert "already exists" in resp2.json()["message"].lower() or "already exists" in resp2.text.lower()


@pytest.mark.db
def test_register_weak_password_422(client):
    """Password shorter than 8 characters returns 422 Unprocessable Entity."""
    response = client.post(
        "/auth/register",
        json={
            "name": "Weak Pass User",
            "email": "weak@example.com",
            "password": "short",
        },
    )
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


@pytest.mark.db
def test_login_wrong_password_and_unknown_email_same_message(client):
    """Wrong password returns 401; unknown email gives the SAME message as wrong password."""
    email = "registered.user@example.com"
    client.post(
        "/auth/register",
        json={
            "name": "Registered User",
            "email": email,
            "password": "CorrectPassword123!",
        },
    )

    # Wrong password attempt
    wrong_pw_resp = client.post(
        "/auth/login",
        json={"email": email, "password": "WrongPassword999!"},
    )
    assert wrong_pw_resp.status_code == status.HTTP_401_UNAUTHORIZED
    wrong_pw_msg = wrong_pw_resp.json().get("message") or wrong_pw_resp.json().get("detail")

    # Unknown email attempt
    unknown_email_resp = client.post(
        "/auth/login",
        json={"email": "nonexistent.user@example.com", "password": "AnyPassword123!"},
    )
    assert unknown_email_resp.status_code == status.HTTP_401_UNAUTHORIZED
    unknown_email_msg = unknown_email_resp.json().get("message") or unknown_email_resp.json().get("detail")

    # Ensure both return the identical error message to avoid enumeration
    assert wrong_pw_msg == unknown_email_msg
    assert "invalid email or password" in wrong_pw_msg.lower()


@pytest.mark.db
def test_login_rate_limit_429(client):
    """Login rate limit returns 429 after 5 attempts per minute."""
    payload = {"email": "rate.limit@example.com", "password": "WrongPassword123!"}
    for _ in range(5):
        resp = client.post("/auth/login", json=payload)
        assert resp.status_code == status.HTTP_401_UNAUTHORIZED

    # 6th attempt should be blocked with 429 Too Many Requests
    blocked_resp = client.post("/auth/login", json=payload)
    assert blocked_resp.status_code == status.HTTP_429_TOO_MANY_REQUESTS


def test_auth_no_token_401(client):
    """Accessing protected endpoint without a token returns 401 Unauthorized."""
    resp = client.get("/users/me")
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED


def test_auth_garbage_token_401(client):
    """Accessing protected endpoint with garbage token returns 401 Unauthorized."""
    resp = client.get("/users/me", headers={"Authorization": "Bearer not.a.valid.jwt.token"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
