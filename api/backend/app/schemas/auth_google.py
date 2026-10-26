"""Pydantic schema for Google OAuth authentication."""

from pydantic import BaseModel, Field


class GoogleLoginRequest(BaseModel):
    """Payload for Google Identity Services ID token authentication."""

    credential: str = Field(..., min_length=1, description="Google Identity Services ID token (JWT)")
