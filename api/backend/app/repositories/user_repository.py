"""User repository for database access."""

import uuid
from typing import Optional, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.models.user import User


class UserRepository:
    """Repository handling database operations for User model."""

    @staticmethod
    def create(
        db: Session,
        name: str,
        email: str,
        password_hash: Optional[str] = None,
        onboarding_completed: bool = False,
    ) -> User:
        """Create and persist a new user entity."""
        user = User(
            name=name,
            email=email,
            password_hash=password_hash,
            onboarding_completed=onboarding_completed,
        )
        db.add(user)
        db.flush()
        db.refresh(user)
        return user

    @staticmethod
    def get_by_id(db: Session, user_id: Union[uuid.UUID, str]) -> Optional[User]:
        """Fetch user by primary key UUID."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        stmt = select(User).where(User.id == user_id)
        return db.scalars(stmt).first()

    @staticmethod
    def get_by_email(db: Session, email: str) -> Optional[User]:
        """Fetch user by unique email address."""
        stmt = select(User).where(User.email == email)
        return db.scalars(stmt).first()

    @staticmethod
    def update_name(db: Session, user: User, name: str) -> User:
        """Update a user's display name."""
        user.name = name
        db.add(user)
        db.flush()
        db.refresh(user)
        return user

    @staticmethod
    def set_onboarding_completed(db: Session, user: User, completed: bool = True) -> User:
        """Mark onboarding status for a user."""
        user.onboarding_completed = completed
        db.add(user)
        db.flush()
        db.refresh(user)
        return user
