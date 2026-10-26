"""Authentication API routes."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session
from backend.app.core.rate_limit import limiter
from backend.app.db.session import get_db
from backend.app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest, UserResponse
from backend.app.services.auth_service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


def get_auth_service() -> AuthService:
    """Dependency injector for AuthService."""
    return AuthService()


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
def register(
    req: UserRegisterRequest,
    db: Session = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> UserResponse:
    """Create a new user account with argon2 hashed password."""
    return service.register(db, req)


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login to obtain a JWT access token",
)
@limiter.limit("5/minute")
def login(
    request: Request,
    req: UserLoginRequest,
    db: Session = Depends(get_db),
    service: AuthService = Depends(get_auth_service),
) -> TokenResponse:
    """Authenticate email and password, returning a 60-minute JWT token (max 5 attempts/minute)."""
    return service.login(db, req)
