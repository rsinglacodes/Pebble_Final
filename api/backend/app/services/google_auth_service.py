"""Google OAuth authentication service verifying GIS ID tokens."""

from fastapi import HTTPException, status
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.config import get_settings
from backend.app.core.security import create_access_token
from backend.app.models.user import AuthIdentity, User
from backend.app.schemas.auth import TokenResponse


class GoogleAuthService:
    """Service handling verification of Google Identity Services ID tokens and account linking."""

    def authenticate(self, db: Session, credential: str) -> TokenResponse:
        """Verify Google ID token and return a JWT access token for existing or newly created user."""
        settings = get_settings()
        audience = settings.GOOGLE_CLIENT_ID if settings.GOOGLE_CLIENT_ID else None

        try:
            payload = id_token.verify_oauth2_token(
                credential,
                google_requests.Request(),
                audience=audience,
            )
        except (ValueError, GoogleAuthError, Exception):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Require verified email
        email_verified = payload.get("email_verified")
        if email_verified is not True and email_verified != "true":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Google email is not verified",
                headers={"WWW-Authenticate": "Bearer"},
            )

        sub = payload.get("sub")
        email = payload.get("email")
        if not sub or not email:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Google token claims",
                headers={"WWW-Authenticate": "Bearer"},
            )

        clean_email = email.strip().lower()
        name = payload.get("name") or clean_email.split("@")[0]

        # 1. Find existing AuthIdentity(provider="google", provider_subject=sub)
        stmt = select(AuthIdentity).where(
            AuthIdentity.provider == "google",
            AuthIdentity.provider_subject == sub,
        )
        identity = db.scalars(stmt).first()

        if identity:
            user = db.scalars(select(User).where(User.id == identity.user_id)).first()
            if not user:
                user = User(
                    name=name,
                    email=clean_email,
                    password_hash=None,
                    onboarding_completed=False,
                )
                db.add(user)
                db.flush()
                identity.user_id = user.id
                db.commit()
                db.refresh(user)
        else:
            # 2. Check if user with this email exists (link identity) or create new user
            user = db.scalars(select(User).where(User.email == clean_email)).first()
            if user:
                new_identity = AuthIdentity(
                    user_id=user.id,
                    provider="google",
                    provider_subject=sub,
                )
                db.add(new_identity)
                db.commit()
                db.refresh(user)
            else:
                user = User(
                    name=name,
                    email=clean_email,
                    password_hash=None,
                    onboarding_completed=False,
                )
                db.add(user)
                db.flush()
                new_identity = AuthIdentity(
                    user_id=user.id,
                    provider="google",
                    provider_subject=sub,
                )
                db.add(new_identity)
                db.commit()
                db.refresh(user)

        # Return a JWT using the existing helper in core/security.py
        token = create_access_token(subject=str(user.id))
        return TokenResponse(access_token=token, token_type="bearer")
