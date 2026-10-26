"""Pydantic schemas matching docs/api-contract.md and health contract."""

from typing import List, Literal, Optional, Union
from pydantic import BaseModel, Field

# Core union types matching TypeScript definitions
Level = Literal["beginner", "intermediate", "advanced"]
Lang = Literal["python", "java", "cpp", "javascript"]
ExplanationLanguage = Literal["en", "hi"]
ExplanationStyle = Literal["beginner", "technical", "both"]
VideoJobStatus = Literal["queued", "running", "completed", "failed"]


class Preferences(BaseModel):
    """User learning preferences contract."""

    experience_level: Level
    preferred_language: Lang
    explanation_language: ExplanationLanguage
    explanation_style: ExplanationStyle
    learning_goal: str


class ProblemSummary(BaseModel):
    """Problem metadata summary in chat learning result."""

    id: Optional[int] = None
    slug: Optional[str] = None
    title: str
    source_url: Optional[str] = None


class SolutionSummary(BaseModel):
    """Code solution metadata and validation status."""

    language: Union[Lang, str]
    code: str
    validated: bool
    source_url: Optional[str] = None


class ChatResult(BaseModel):
    """Result payload attached to chat response."""

    problem: Optional[ProblemSummary] = None
    solution: Optional[SolutionSummary] = None
    available_languages: List[str] = Field(default_factory=list)


# Backward-compatibility alias
LearningResult = ChatResult


class ChatResponse(BaseModel):
    """Chat message response conforming to docs/api-contract.md."""

    conversation_id: str
    message_id: str
    reply_text: str
    result: Optional[ChatResult] = None
    needs_clarification: Optional[str] = None
    out_of_scope: Optional[bool] = None


class VideoJob(BaseModel):
    """Video job status conforming to docs/api-contract.md."""

    id: str
    status: VideoJobStatus
    stage: str
    video_url: Optional[str] = None
    error: Optional[str] = None


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: Literal["ok"] = "ok"
    db: bool
