"""Pydantic schemas for POST /ask endpoint."""

from typing import List, Literal, Optional
from pydantic import BaseModel, ConfigDict, Field


class AskRequest(BaseModel):
    """Payload for POST /ask."""

    text: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Query text: problem name, number, DSA concept, or pasted code",
    )
    programming_language: Literal["python", "java", "cpp"] = Field(
        default="python",
        description="Target programming language (python, java, cpp)",
    )

    model_config = ConfigDict(extra="ignore")


class ProblemInfo(BaseModel):
    """Problem metadata."""

    id: int
    slug: str
    title: str
    source_url: Optional[str] = None


class SolutionInfo(BaseModel):
    """Code solution metadata and validation status."""

    language: str
    code: str
    validated: bool


class CandidateInfo(BaseModel):
    """Potential problem candidate for ambiguous queries."""

    id: int
    slug: str
    title: str


class AskResponse(BaseModel):
    """Response structure for POST /ask."""

    status: Literal["found", "no_solution", "clarify", "concept", "out_of_scope"]
    message: str
    problem: Optional[ProblemInfo] = None
    solution: Optional[SolutionInfo] = None
    available_languages: List[str] = Field(default_factory=list)
    candidates: Optional[List[CandidateInfo]] = None
    can_generate: bool
