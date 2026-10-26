"""VideoJob and GeneratedVideo SQLAlchemy 2.0 ORM models."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base


class VideoJobModel(Base):
    """Tracks asynchronous video generation requests and lifecycle stages."""

    __tablename__ = "video_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    problem_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("problems.id", ondelete="SET NULL"), nullable=True, index=True
    )
    solution_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("solutions.id", ondelete="SET NULL"), nullable=True, index=True
    )
    fingerprint: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    provider_job_id: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    stage: Mapped[str] = mapped_column(String(50), nullable=False)
    error_code: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    videos: Mapped[list["GeneratedVideo"]] = relationship(
        "GeneratedVideo", back_populates="job", cascade="all, delete-orphan"
    )

    @property
    def cache_key(self) -> str:
        return self.fingerprint

    @cache_key.setter
    def cache_key(self, val: str) -> None:
        self.fingerprint = val


class GeneratedVideo(Base):
    """Completed reusable educational video artifacts stored in Azure Blob Storage."""

    __tablename__ = "generated_videos"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    video_job_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("video_jobs.id", ondelete="CASCADE"), nullable=False, index=True
    )
    fingerprint: Mapped[str] = mapped_column(
        String(64), unique=True, index=True, nullable=False
    )
    video_url: Mapped[str] = mapped_column(Text, nullable=False)
    blob_name: Mapped[str] = mapped_column(Text, nullable=False)
    solution_json: Mapped[Optional[dict]] = mapped_column(
        JSON().with_variant(JSONB, "postgresql"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    job: Mapped["VideoJobModel"] = relationship("VideoJobModel", back_populates="videos")

    @property
    def cache_key(self) -> str:
        return self.fingerprint

    @cache_key.setter
    def cache_key(self, val: str) -> None:
        self.fingerprint = val

    __table_args__ = (
        UniqueConstraint("fingerprint", name="uq_generated_videos_fingerprint"),
    )
