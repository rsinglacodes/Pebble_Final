"""Problem catalog and test case SQLAlchemy 2.0 ORM models."""

import uuid
from datetime import datetime, timezone
from typing import Any, Optional
from sqlalchemy import DateTime, ForeignKey, JSON, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.app.db.base import Base


class Problem(Base):
    """DSA Problem catalog entity."""

    __tablename__ = "problems"
    __table_args__ = (
        UniqueConstraint("source", "external_problem_id", name="uq_problems_source_external_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    external_problem_id: Mapped[str] = mapped_column(
        String(100), index=True, nullable=False
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(255), index=True, nullable=False)
    difficulty: Mapped[str] = mapped_column(String(50), nullable=False)
    topics: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    canonical_url: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    statement_hash: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Relationships
    solutions: Mapped[list["Solution"]] = relationship(
        "Solution", back_populates="problem", cascade="all, delete-orphan"
    )
    tests: Mapped[list["ProblemTest"]] = relationship(
        "ProblemTest", back_populates="problem", cascade="all, delete-orphan"
    )


class ProblemTest(Base):
    """Verified input/output test cases for a problem."""

    __tablename__ = "problem_tests"

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    problem_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("problems.id", ondelete="CASCADE"), nullable=False, index=True
    )
    input_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    expected_json: Mapped[Any] = mapped_column(JSON, nullable=False)
    source: Mapped[str] = mapped_column(String(100), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    problem: Mapped["Problem"] = relationship("Problem", back_populates="tests")
