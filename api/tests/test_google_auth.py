"""Tests for Google Identity Services authentication endpoint and service."""

from unittest.mock import patch
import pytest
from fastapi import HTTPException, status
from google.oauth2 import id_token
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from backend.app.core.security import decode_access_token
from backend.app.db.base import Base
from backend.app.models.user import AuthIdentity, User
from backend.app.services.google_auth_service import GoogleAuthService


@pytest.fixture
def sqlite_session():
    """In-memory SQLite session for isolated database tests without external services."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_google_auth_bad_token_401(client, monkeypatch):
    """Bad or invalid token from Google verifier returns 401 Unauthorized."""
    def mock_verify(*args, **kwargs):
        raise ValueError("Token is invalid or expired")

    monkeypatch.setattr(id_token, "verify_oauth2_token", mock_verify)

    resp = client.post("/auth/google", json={"credential": "invalid-google-token"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    error_msg = resp.json().get("message") or resp.json().get("detail", "")
    assert "invalid google token" in error_msg.lower()


def test_google_auth_unverified_email_rejected_401(client, monkeypatch):
    """Google account with unverified email returns 401 Unauthorized."""
    def mock_verify(*args, **kwargs):
        return {
            "sub": "sub-unverified-123",
            "email": "unverified@example.com",
            "email_verified": False,
            "name": "Unverified User",
        }

    monkeypatch.setattr(id_token, "verify_oauth2_token", mock_verify)

    resp = client.post("/auth/google", json={"credential": "unverified-token"})
    assert resp.status_code == status.HTTP_401_UNAUTHORIZED
    error_msg = resp.json().get("message") or resp.json().get("detail", "")
    assert "not verified" in error_msg.lower()


def test_google_auth_service_new_user(sqlite_session: Session):
    """New Google user creates account with password_hash=None and AuthIdentity."""
    service = GoogleAuthService()
    mock_payload = {
        "sub": "google-sub-1001",
        "email": "newuser@example.com",
        "email_verified": True,
        "name": "Google Newbie",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_payload):
        token_resp = service.authenticate(sqlite_session, "valid-mock-token")

    assert token_resp.access_token is not None
    assert token_resp.token_type == "bearer"

    user_id = decode_access_token(token_resp.access_token)
    assert user_id is not None

    user = sqlite_session.scalars(select(User).where(User.email == "newuser@example.com")).first()
    assert user is not None
    assert str(user.id) == user_id
    assert user.name == "Google Newbie"
    assert user.password_hash is None
    assert user.onboarding_completed is False

    identity = sqlite_session.scalars(
        select(AuthIdentity).where(AuthIdentity.provider_subject == "google-sub-1001")
    ).first()
    assert identity is not None
    assert identity.provider == "google"
    assert identity.user_id == user.id


def test_google_auth_service_existing_email_linking(sqlite_session: Session):
    """Existing password-based user is linked with AuthIdentity upon Google sign-in."""
    existing_user = User(
        name="Original User",
        email="existing@example.com",
        password_hash="$argon2id$mockpasswordhash",
        onboarding_completed=True,
    )
    sqlite_session.add(existing_user)
    sqlite_session.commit()
    sqlite_session.refresh(existing_user)

    service = GoogleAuthService()
    mock_payload = {
        "sub": "google-sub-2002",
        "email": "  EXISTING@example.com  ",
        "email_verified": True,
        "name": "Google Name Ignored",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_payload):
        token_resp = service.authenticate(sqlite_session, "valid-mock-token")

    user_id = decode_access_token(token_resp.access_token)
    assert user_id == str(existing_user.id)

    # Verify existing user retained original password_hash
    user = sqlite_session.scalars(select(User).where(User.id == existing_user.id)).first()
    assert user.password_hash == "$argon2id$mockpasswordhash"
    assert user.onboarding_completed is True

    # Verify identity linked
    identity = sqlite_session.scalars(
        select(AuthIdentity).where(AuthIdentity.provider_subject == "google-sub-2002")
    ).first()
    assert identity is not None
    assert identity.user_id == existing_user.id
    assert identity.provider == "google"


def test_google_auth_service_repeat_login_existing_identity(sqlite_session: Session):
    """User who previously signed in via Google logs in again via existing AuthIdentity."""
    service = GoogleAuthService()
    mock_payload = {
        "sub": "google-sub-3003",
        "email": "returning@example.com",
        "email_verified": True,
        "name": "Returning User",
    }

    with patch("google.oauth2.id_token.verify_oauth2_token", return_value=mock_payload):
        token_resp1 = service.authenticate(sqlite_session, "valid-mock-token")
        token_resp2 = service.authenticate(sqlite_session, "valid-mock-token")

    user_id1 = decode_access_token(token_resp1.access_token)
    user_id2 = decode_access_token(token_resp2.access_token)
    assert user_id1 == user_id2

    # Verify no duplicate user or identity was created
    users = sqlite_session.scalars(select(User).where(User.email == "returning@example.com")).all()
    assert len(users) == 1

    identities = sqlite_session.scalars(
        select(AuthIdentity).where(AuthIdentity.provider_subject == "google-sub-3003")
    ).all()
    assert len(identities) == 1


@pytest.mark.db
def test_google_auth_api_new_user_db(client, monkeypatch):
    """Integration test with DB: POST /auth/google creates user and returns 200."""
    mock_payload = {
        "sub": "google-db-sub-1",
        "email": "db.newuser@example.com",
        "email_verified": True,
        "name": "DB Google User",
    }
    monkeypatch.setattr(id_token, "verify_oauth2_token", lambda *args, **kwargs: mock_payload)

    resp = client.post("/auth/google", json={"credential": "mock-valid-id-token"})
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.db
def test_google_auth_api_link_existing_user_db(client, monkeypatch):
    """Integration test with DB: POST /auth/google links existing email."""
    # Register user first
    reg_resp = client.post(
        "/auth/register",
        json={"name": "Existing Account", "email": "link.test@example.com", "password": "Password123!"},
    )
    assert reg_resp.status_code == status.HTTP_201_CREATED

    mock_payload = {
        "sub": "google-db-sub-linked",
        "email": "link.test@example.com",
        "email_verified": True,
        "name": "Google Name",
    }
    monkeypatch.setattr(id_token, "verify_oauth2_token", lambda *args, **kwargs: mock_payload)

    resp = client.post("/auth/google", json={"credential": "mock-valid-id-token"})
    assert resp.status_code == status.HTTP_200_OK
    assert "access_token" in resp.json()
