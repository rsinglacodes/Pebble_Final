"""Solution, SolutionTest, and ExecutionTrace SQLAlchemy 2.0 ORM models."""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base


class Solution(Base):
    """DSA Solution entity associated with a Problem."""

    __tablename__ = "solutions"
    __table_args__ = (
        UniqueConstraint("problem_id", "language", name="uq_solutions_problem_language"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    language: Mapped[str] = mapped_column(String(50), nullable=False)
    code: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(String(50), nullable=False)
    source_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    content_hash: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    validation_status: Mapped[str] = mapped_column(String(50), default="not_tested", nullable=False)
    validated: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    commit_sha: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    problem: Mapped["Problem"] = relationship("Problem", back_populates="solutions")
    tests: Mapped[list["SolutionTest"]] = relationship(
        "SolutionTest", back_populates="solution", cascade="all, delete-orphan"
    )
    traces: Mapped[list["ExecutionTraceModel"]] = relationship(
        "ExecutionTraceModel", back_populates="solution", cascade="all, delete-orphan"
    )


class SolutionTest(Base):
    """Validation test run summary for a solution."""

    __tablename__ = "solution_tests"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    solution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("solutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    test_type: Mapped[str] = mapped_column(String(50), nullable=False)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    test_summary: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    solution: Mapped["Solution"] = relationship("Solution", back_populates="tests")


class ExecutionTraceModel(Base):
    """Execution trace metadata linking to stored trace objects."""

    __tablename__ = "execution_traces"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    solution_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("solutions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    trace_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    trace_storage_key: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    solution: Mapped["Solution"] = relationship("Solution", back_populates="traces")
