"""Authentication service orchestrating registration and login."""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.core.security import create_access_token, hash_password, verify_password
from backend.app.models.user import User
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.auth import TokenResponse, UserLoginRequest, UserRegisterRequest


class AuthService:
    """Service handling user account registration and login authentication."""

    def __init__(self, user_repo: UserRepository = None):
        self.user_repo = user_repo or UserRepository()

    def register(self, db: Session, req: UserRegisterRequest) -> User:
        """Register a new user account with argon2 password hashing."""
        existing = self.user_repo.get_by_email(db, req.email)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="User with this email already exists",
            )

        hashed = hash_password(req.password)
        user = self.user_repo.create(
            db=db,
            name=req.name,
            email=req.email,
            password_hash=hashed,
            onboarding_completed=False,
        )
        db.commit()
        db.refresh(user)
        return user

    def login(self, db: Session, req: UserLoginRequest) -> TokenResponse:
        """Authenticate user credentials and issue JWT access token."""
        user = self.user_repo.get_by_email(db, req.email)
        if not user or not user.password_hash:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not verify_password(req.password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        token = create_access_token(subject=str(user.id))
        return TokenResponse(access_token=token, token_type="bearer")
