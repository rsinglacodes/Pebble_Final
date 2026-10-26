"""User profile API routes."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from backend.app.core.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.auth import (
    UserResponse,
    UserUpdateRequest,
)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/me", response_model=UserResponse, summary="Get current authenticated user profile")
def get_me(current_user: User = Depends(get_current_user)) -> UserResponse:
    """Return the profile for the currently authenticated user."""
    return current_user


@router.patch("/me", response_model=UserResponse, summary="Update user profile name")
def update_me(
    req: UserUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """Update profile name for the current authenticated user."""
    updated = UserRepository.update_name(db, current_user, req.name.strip())
    db.commit()
    return updated
