"""Pydantic schemas for Conversation and Message entities."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class ConversationCreateRequest(BaseModel):
    """Payload for creating a new conversation."""

    title: Optional[str] = Field(default="New conversation", max_length=255, description="Initial conversation title")


class ConversationUpdateRequest(BaseModel):
    """Payload for renaming/updating a conversation title."""

    title: str = Field(..., min_length=1, max_length=255, description="New conversation title")


class MessageCreateRequest(BaseModel):
    """Payload for appending a message to a conversation."""

    role: str = Field(..., min_length=1, max_length=50, description="Message sender role (e.g. user, assistant)")
    content: str = Field(..., min_length=1, description="Text message content")
    mode: Optional[str] = Field(default=None, max_length=50, description="Optional interaction mode")
    meta: Optional[Dict[str, Any]] = Field(default=None, description="Structured ask/video metadata")


class MessageMetaUpdateRequest(BaseModel):
    """Payload for updating/patching message metadata."""

    meta: Dict[str, Any] = Field(..., description="Structured metadata to update or merge")


class MessageResponse(BaseModel):
    """Safe schema for an individual message."""

    id: uuid.UUID
    conversation_id: uuid.UUID
    role: str
    content: str
    mode: Optional[str] = None
    meta: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationResponse(BaseModel):
    """Summary schema for a conversation thread without messages list."""

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ConversationDetailResponse(BaseModel):
    """Detailed schema for a conversation including its complete message history."""

    id: uuid.UUID
    user_id: uuid.UUID
    title: str
    created_at: datetime
    updated_at: datetime
    messages: List[MessageResponse] = []

    model_config = ConfigDict(from_attributes=True)
