"""Pydantic schemas for video generation jobs and results."""

from typing import Any, Dict, Optional, Union
from pydantic import BaseModel, Field, field_validator, model_validator
from backend.app.schemas.contracts import VideoJobStatus


class CreateVideoJobRequest(BaseModel):
    """Payload to initiate a video generation job."""

    problem_id: Optional[int] = Field(None, description="LeetCode problem number (optional)")
    text: Optional[str] = Field(None, max_length=300, description="Unmatched question or concept (max 300 chars)")
    user_code: Optional[str] = Field(None, description="User submitted code block (optional)")
    programming_language: str = Field(..., description="Target programming language (python, java, cpp)")
    title: Optional[str] = Field(None, description="Legacy problem title (optional)")
    explanation_language: Optional[str] = Field(None, description="Legacy explanation language (optional)")
    explanation_style: Optional[str] = Field(None, description="Legacy explanation style (optional)")

    @field_validator("programming_language")
    @classmethod
    def validate_programming_language(cls, v: str) -> str:
        clean = v.lower().strip()
        if clean not in ("python", "java", "cpp"):
            raise ValueError("programming_language must be python, java, or cpp")
        return clean

    @model_validator(mode="after")
    def validate_problem_or_text(self) -> "CreateVideoJobRequest":
        has_text = bool(self.text and self.text.strip())
        has_title = bool(self.title and self.title.strip())
        if self.problem_id is None and not has_text and not has_title:
            raise ValueError("Either problem_id or text is required")
        return self


class VideoJobResponse(BaseModel):
    """Video job lifecycle representation conforming to docs/api-contract.md."""

    id: str
    status: VideoJobStatus
    stage: str
    video_url: Optional[str] = None
    error: Optional[str] = None
    queue_position: Optional[int] = None
    elapsed_seconds: Optional[int] = None


class SolutionResultResponse(BaseModel):
    """Returned solution metadata and provenance."""

    code: str
    programming_language: str
    validated: bool
    origin: str  # 'repo' | 'user_code' | 'ai_generated'


class VideoResultResponse(BaseModel):
    """Result of completed video job."""

    video_url: str
    blob_name: str
    status: str = "completed"
    solution: Optional[Union[SolutionResultResponse, Dict[str, Any]]] = None
