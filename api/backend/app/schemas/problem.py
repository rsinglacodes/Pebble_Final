"""Pydantic schemas for problem resolution, search, and details."""

import uuid
from typing import List, Optional
from pydantic import BaseModel, Field


class ProblemItem(BaseModel):
    """Problem metadata representation in API responses."""

    id: int = Field(..., description="LeetCode problem number")
    slug: str = Field(..., description="Normalized problem slug")
    title: str = Field(..., description="Problem title")
    source_url: Optional[str] = Field(None, description="Problem canonical or source URL")


class SolutionItem(BaseModel):
    """Solution representation attached to problem responses."""

    language: str = Field(..., description="Programming language: python, java, cpp")
    code: str = Field(..., description="Solution source code")
    validated: bool = Field(..., description="Whether solution is verified")
    source_url: Optional[str] = Field(None, description="GitHub URL of solution file")


class CandidateItem(BaseModel):
    """Fuzzy search candidate with trigram similarity score."""

    problem: ProblemItem
    score: float = Field(..., description="Trigram match similarity score [0.0 - 1.0]")


class ProblemResolveResponse(BaseModel):
    """Response returned by GET /problems/resolve."""

    resolved: bool
    problem: Optional[ProblemItem] = None
    solution: Optional[SolutionItem] = None
    available_languages: List[str] = Field(default_factory=list)
    candidates: Optional[List[CandidateItem]] = None


class ProblemDetailResponse(BaseModel):
    """Response returned by GET /problems/{id}."""

    id: int
    uuid: uuid.UUID
    title: str
    slug: str
    difficulty: str
    canonical_url: Optional[str] = None
    available_languages: List[str] = Field(default_factory=list)
