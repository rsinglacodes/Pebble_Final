"""API route for /ask endpoint."""

import logging
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session

from backend.app.core.dependencies import get_current_user
from backend.app.core.rate_limit import limiter
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.ask import AskRequest, AskResponse
from backend.app.services.ask_service import AskService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["Ask"])


@router.post("/ask", response_model=AskResponse)
@limiter.limit("30/minute")
def ask_question(
    request: Request,
    payload: AskRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> AskResponse:
    """Submit a DSA query or code snippet to Pebble.

    Rate limit: 30 requests/minute per authenticated user.
    The request text is strictly never logged and no database tables are modified.
    """
    logger.info("Processing /ask request for user_id=%s, language=%s", current_user.id, payload.programming_language)
    service = AskService()
    return service.ask(
        db=db,
        text=payload.text,
        programming_language=payload.programming_language,
        user=current_user,
    )
