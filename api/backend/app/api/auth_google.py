"""Google OAuth authentication API route."""

from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from backend.app.core.rate_limit import limiter
from backend.app.db.session import get_db
from backend.app.schemas.auth import TokenResponse
from backend.app.schemas.auth_google import GoogleLoginRequest
from backend.app.services.google_auth_service import GoogleAuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_google_auth_service() -> GoogleAuthService:
    """Dependency injector for GoogleAuthService."""
    return GoogleAuthService()


@router.post(
    "/google",
    response_model=TokenResponse,
    summary="Authenticate with Google Identity Services ID token",
)
@limiter.limit("5/minute")
def google_login(
    request: Request,
    req: GoogleLoginRequest,
    db: Session = Depends(get_db),
    service: GoogleAuthService = Depends(get_google_auth_service),
) -> TokenResponse:
    """Authenticate with Google ID token, returning a 60-minute JWT token (max 5 attempts/minute)."""
    return service.authenticate(db, req.credential)
