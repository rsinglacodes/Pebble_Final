"""API routes for question history management."""

import logging
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.repositories.history_repository import HistoryRepository
from backend.app.schemas.history import HistoryItemResponse, HistoryProblemInfo

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/history", tags=["History"])


@router.get("", response_model=List[HistoryItemResponse])
def get_question_history(
    limit: int = Query(default=20, ge=1, le=50, description="Max history items to return (up to 50)"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[HistoryItemResponse]:
    """Retrieve current user's question history ordered newest first."""
    items = HistoryRepository.list_by_user(db=db, user_id=current_user.id, limit=limit)
    response = []
    for item in items:
        prob_info = None
        if item.problem:
            ext_id = int(item.problem.external_problem_id) if item.problem.external_problem_id.isdigit() else 0
            prob_info = HistoryProblemInfo(
                id=ext_id,
                slug=item.problem.slug,
                title=item.problem.title,
            )
        response.append(
            HistoryItemResponse(
                id=item.id,
                text=item.text,
                status=item.status,
                problem=prob_info,
                programming_language=item.programming_language,
                created_at=item.created_at,
            )
        )
    return response


@router.delete("/{history_id}")
def delete_single_history(
    history_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete a single history entry owned by current user. Another user's row returns 404."""
    try:
        parsed_id = uuid.UUID(history_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History entry not found",
        )
    deleted = HistoryRepository.delete_by_id(db=db, history_id=parsed_id, user_id=current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="History entry not found",
        )
    return {"status": "deleted"}


@router.delete("")
def delete_all_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Delete all history entries owned by current user."""
    deleted_count = HistoryRepository.delete_all_for_user(db=db, user_id=current_user.id)
    return {"status": "deleted", "deleted_count": deleted_count}
