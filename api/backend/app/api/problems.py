"""Problem search and catalog API routes."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from backend.app.core.dependencies import get_current_user
from backend.app.db.session import get_db
from backend.app.models.user import User
from backend.app.schemas.problem import (
    ProblemDetailResponse,
    ProblemResolveResponse,
    SolutionItem,
)
from backend.app.services.problem_service import ProblemService

router = APIRouter(prefix="/problems", tags=["Problems"])


def get_problem_service() -> ProblemService:
    """Dependency injector for ProblemService."""
    return ProblemService()


@router.get(
    "/resolve",
    response_model=ProblemResolveResponse,
    summary="Resolve problem by exact number/slug/URL or fuzzy title",
)
def resolve_problem(
    q: str = Query(..., description="Query string: number, slug, LeetCode URL, or title"),
    language: Optional[str] = Query(None, description="Preferred language for solution"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ProblemService = Depends(get_problem_service),
) -> ProblemResolveResponse:
    """Resolve a problem by exact match or pg_trgm fuzzy title match (requires authentication)."""
    return service.resolve_problem(db, q, language)


@router.get(
    "/{id}",
    response_model=ProblemDetailResponse,
    summary="Get problem by number, UUID, or slug",
)
def get_problem(
    id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ProblemService = Depends(get_problem_service),
) -> ProblemDetailResponse:
    """Fetch problem details (requires authentication)."""
    return service.get_problem(db, id)


@router.get(
    "/{id}/solutions",
    response_model=List[SolutionItem],
    summary="Get solutions for a problem",
)
def get_solutions(
    id: str,
    language: Optional[str] = Query(None, description="Filter solutions by language"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
    service: ProblemService = Depends(get_problem_service),
) -> List[SolutionItem]:
    """Fetch solutions for a problem (requires authentication). Returns empty list when language is missing."""
    return service.get_solutions(db, id, language)
