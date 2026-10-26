"""Pydantic schemas package exports."""

from backend.app.schemas.ask import (
    AskRequest,
    AskResponse,
    CandidateInfo,
    ProblemInfo,
    SolutionInfo,
)
from backend.app.schemas.auth import (
    TokenResponse,
    UserLoginRequest,
    UserRegisterRequest,
    UserResponse,
    UserUpdateRequest,
)
from backend.app.schemas.contracts import (
    ExplanationLanguage,
    ExplanationStyle,
    HealthResponse,
    Lang,
    Level,
    VideoJob,
    VideoJobStatus,
)
from backend.app.schemas.history import (
    HistoryItemResponse,
    HistoryProblemInfo,
)
from backend.app.schemas.video import (
    CreateVideoJobRequest,
    SolutionResultResponse,
    VideoJobResponse,
    VideoResultResponse,
)

__all__ = [
    "AskRequest",
    "AskResponse",
    "CandidateInfo",
    "ExplanationLanguage",
    "ExplanationStyle",
    "HealthResponse",
    "HistoryItemResponse",
    "HistoryProblemInfo",
    "Lang",
    "Level",
    "ProblemInfo",
    "SolutionInfo",
    "TokenResponse",
    "UserLoginRequest",
    "UserRegisterRequest",
    "UserResponse",
    "UserUpdateRequest",
    "VideoJob",
    "VideoJobStatus",
    "CreateVideoJobRequest",
    "VideoJobResponse",
    "VideoResultResponse",
    "SolutionResultResponse",
]
