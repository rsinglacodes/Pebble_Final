"""Repository for ask_history table operations."""

import uuid
from typing import List, Optional
from sqlalchemy import delete, select
from sqlalchemy.orm import Session, joinedload

from backend.app.models.ask_history import AskHistory


class HistoryRepository:
    """Repository managing ask_history persistence and queries."""

    @staticmethod
    def create(
        db: Session,
        user_id: uuid.UUID,
        text: str,
        status: str,
        problem_id: Optional[uuid.UUID] = None,
        programming_language: Optional[str] = "python",
    ) -> AskHistory:
        """Create and persist a new question history entry."""
        entry = AskHistory(
            user_id=user_id,
            text=text,
            status=status,
            problem_id=problem_id,
            programming_language=programming_language,
        )
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry

    @staticmethod
    def list_by_user(
        db: Session,
        user_id: uuid.UUID,
        limit: int = 20,
    ) -> List[AskHistory]:
        """List user's question history ordered newest first."""
        stmt = (
            select(AskHistory)
            .options(joinedload(AskHistory.problem))
            .where(AskHistory.user_id == user_id)
            .order_by(AskHistory.created_at.desc())
            .limit(limit)
        )
        return list(db.scalars(stmt).all())

    @staticmethod
    def get_by_id(
        db: Session,
        history_id: uuid.UUID,
    ) -> Optional[AskHistory]:
        """Fetch history entry by ID."""
        stmt = select(AskHistory).where(AskHistory.id == history_id)
        return db.scalars(stmt).first()

    @staticmethod
    def delete_by_id(
        db: Session,
        history_id: uuid.UUID,
        user_id: uuid.UUID,
    ) -> bool:
        """Delete a single history entry owned by the user. Returns True if deleted, False if not found or unauthorized."""
        entry = HistoryRepository.get_by_id(db, history_id)
        if not entry or entry.user_id != user_id:
            return False
        db.delete(entry)
        db.commit()
        return True

    @staticmethod
    def delete_all_for_user(
        db: Session,
        user_id: uuid.UUID,
    ) -> int:
        """Delete all history entries owned by user. Returns count of deleted entries."""
        stmt = delete(AskHistory).where(AskHistory.user_id == user_id)
        result = db.execute(stmt)
        db.commit()
        return result.rowcount
