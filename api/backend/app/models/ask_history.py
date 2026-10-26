"""AskHistory model for tracking user question history."""

import uuid
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import DateTime, ForeignKey, Index, String, Uuid, func, text as sql_text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.db.base import Base


class AskHistory(Base):
    """User query history entry."""

    __tablename__ = "ask_history"
    __table_args__ = (
        Index("ix_ask_history_user_id_created_at", "user_id", sql_text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    text: Mapped[str] = mapped_column(String(5000), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    problem_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("problems.id", ondelete="SET NULL"), nullable=True, index=True
    )
    programming_language: Mapped[Optional[str]] = mapped_column(
        String(10), nullable=True, default="python"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        server_default=func.now(),
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship("User")
    problem: Mapped[Optional["Problem"]] = relationship("Problem")
