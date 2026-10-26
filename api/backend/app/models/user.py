"""User and authentication related SQLAlchemy 2.0 ORM models."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base


class User(Base):
    """User account entity."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, index=True, nullable=False
    )
    password_hash: Mapped[Optional[str]] = mapped_column(
        String(255), nullable=True
    )
    onboarding_completed: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    auth_identities: Mapped[list["AuthIdentity"]] = relationship(
        "AuthIdentity", back_populates="user", cascade="all, delete-orphan"
    )
    preferences: Mapped["UserPreference"] = relationship(
        "UserPreference", back_populates="user", uselist=False, cascade="all, delete-orphan"
    )


class AuthIdentity(Base):
    """External OAuth and auth identities mapped to a user."""

    __tablename__ = "auth_identities"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    provider: Mapped[str] = mapped_column(String(50), nullable=False)
    provider_subject: Mapped[str] = mapped_column(String(255), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="auth_identities")

    __table_args__ = (
        UniqueConstraint("provider", "provider_subject", name="uq_auth_identities_provider_subject"),
    )


class UserPreference(Base):
    """Personalized learning preferences for a user."""

    __tablename__ = "user_preferences"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), unique=True, nullable=False, index=True
    )
    experience_level: Mapped[str] = mapped_column(String(50), nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(50), nullable=False)
    explanation_language: Mapped[str] = mapped_column(String(10), nullable=False)
    explanation_style: Mapped[str] = mapped_column(String(50), nullable=False)
    learning_goal: Mapped[str] = mapped_column(String(255), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user: Mapped["User"] = relationship("User", back_populates="preferences")
