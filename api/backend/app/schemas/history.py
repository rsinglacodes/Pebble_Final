"""Pydantic schemas for question history endpoints."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class HistoryProblemInfo(BaseModel):
    """Problem metadata reference in history response."""

    id: int
    slug: str
    title: str


class HistoryItemResponse(BaseModel):
    """History item returned by GET /history."""

    id: uuid.UUID
    text: str
    status: str
    problem: Optional[HistoryProblemInfo] = None
    programming_language: Optional[str] = None
    created_at: datetime
