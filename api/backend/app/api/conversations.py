"""Conversation and message API routes."""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy.orm import Session
from backend.app.core.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.repositories.conversation_repository import ConversationRepository
from backend.app.schemas.conversation import (
    ConversationCreateRequest,
    ConversationDetailResponse,
    ConversationResponse,
    ConversationUpdateRequest,
    MessageCreateRequest,
    MessageMetaUpdateRequest,
    MessageResponse,
)

router = APIRouter(prefix="/conversations", tags=["Conversations"])


def get_conversation_repository() -> ConversationRepository:
    """Dependency injector for ConversationRepository."""
    return ConversationRepository()


@router.get(
    "",
    response_model=List[ConversationResponse],
    summary="List all conversations for the authenticated user",
)
def list_conversations(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    repo: ConversationRepository = Depends(get_conversation_repository),
) -> List[ConversationResponse]:
    """Retrieve paginated conversations belonging to the current user, newest updated first."""
    return repo.list_by_user(db, current_user.id, limit=limit, offset=offset)


@router.post(
    "",
    response_model=ConversationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new conversation thread",
)
def create_conversation(
    req: Optional[ConversationCreateRequest] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    repo: ConversationRepository = Depends(get_conversation_repository),
) -> ConversationResponse:
    """Create a new conversation for the authenticated user."""
    title = req.title if req and req.title else "New conversation"
    return repo.create(db, current_user.id, title=title)


@router.get(
    "/{conversation_id}",
    response_model=ConversationDetailResponse,
    summary="Get conversation detail with its message history",
)
def get_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    repo: ConversationRepository = Depends(get_conversation_repository),
) -> ConversationDetailResponse:
    """Fetch conversation and messages. Returns 404 if not found or owned by another user."""
    conv = repo.get_by_id(db, conversation_id, current_user.id)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conv


@router.post(
    "/{conversation_id}/messages",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Append a new message to a conversation",
)
def add_message(
    conversation_id: uuid.UUID,
    req: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    repo: ConversationRepository = Depends(get_conversation_repository),
) -> MessageResponse:
    """Append a message to a user conversation. Updates conversation title from first user message."""
    msg = repo.add_message(
        db,
        conversation_id=conversation_id,
        user_id=current_user.id,
        role=req.role,
        content=req.content,
        mode=req.mode,
        meta=req.meta,
    )
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return msg


@router.patch(
    "/{conversation_id}",
    response_model=ConversationResponse,
    summary="Rename a conversation title",
)
def rename_conversation(
    conversation_id: uuid.UUID,
    req: ConversationUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    repo: ConversationRepository = Depends(get_conversation_repository),
) -> ConversationResponse:
    """Rename a conversation title. Returns 404 if conversation does not belong to user."""
    conv = repo.update_title(db, conversation_id, current_user.id, req.title)
    if not conv:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return conv


@router.delete(
    "/{conversation_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a conversation and all its messages",
)
def delete_conversation(
    conversation_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    repo: ConversationRepository = Depends(get_conversation_repository),
) -> Response:
    """Delete a conversation. Returns 404 if conversation does not exist or belongs to another user."""
    deleted = repo.delete(db, conversation_id, current_user.id)
    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversation not found",
        )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch(
    "/{conversation_id}/messages/{message_id}",
    response_model=MessageResponse,
    summary="Update message metadata",
)
def update_message_meta(
    conversation_id: uuid.UUID,
    message_id: uuid.UUID,
    req: MessageMetaUpdateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    repo: ConversationRepository = Depends(get_conversation_repository),
) -> MessageResponse:
    """Update or merge metadata for a message. Returns 404 if message or conversation not found."""
    msg = repo.update_message_meta(
        db,
        conversation_id=conversation_id,
        message_id=message_id,
        user_id=current_user.id,
        meta=req.meta,
    )
    if not msg:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Message or conversation not found",
        )
    return msg
