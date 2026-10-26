"""Problem search, resolution, and catalog service."""

import re
import uuid
from typing import List, Optional
from fastapi import HTTPException, status
from sqlalchemy.orm import Session
from backend.app.models.problem import Problem
from backend.app.models.solution import Solution
from backend.app.repositories.problem_repository import ProblemRepository
from backend.app.repositories.solution_repository import SolutionRepository
from backend.app.schemas.problem import (
    CandidateItem,
    ProblemDetailResponse,
    ProblemItem,
    ProblemResolveResponse,
    SolutionItem,
)


class ProblemService:
    """Service handling problem resolution, search with pg_trgm, and solution fetching."""

    def __init__(
        self,
        problem_repo: ProblemRepository = None,
        solution_repo: SolutionRepository = None,
    ):
        self.problem_repo = problem_repo or ProblemRepository()
        self.solution_repo = solution_repo or SolutionRepository()

    def _extract_slug_from_url(self, text: str) -> Optional[str]:
        """Extract problem slug from a LeetCode URL if present."""
        match = re.search(r"leetcode\.com/problems/([^/?#\s]+)", text, re.IGNORECASE)
        if match:
            return match.group(1).lower().strip()
        return None

    def _to_problem_item(self, problem: Problem) -> ProblemItem:
        """Convert Problem model to ProblemItem schema."""
        problem_num = int(problem.external_problem_id) if problem.external_problem_id.isdigit() else 0
        return ProblemItem(
            id=problem_num,
            slug=problem.slug,
            title=problem.title,
            source_url=problem.canonical_url,
        )

    def _to_solution_item(self, solution: Solution) -> SolutionItem:
        """Convert Solution model to SolutionItem schema."""
        return SolutionItem(
            language=solution.language,
            code=solution.code,
            validated=solution.validated,
            source_url=solution.source_url,
        )

    def resolve_problem(
        self, db: Session, q: str, language: Optional[str] = None
    ) -> ProblemResolveResponse:
        """Resolve a problem by exact match or pg_trgm fuzzy match.
        
        Resolution Order:
        1. Exact number (external_problem_id)
        2. LeetCode URL slug
        3. Exact slug
        4. Fuzzy title match with pg_trgm (threshold >= 0.4)
        """
        raw_q = q.strip()
        matched_problem: Optional[Problem] = None
        candidates_list: Optional[List[CandidateItem]] = None

        # (a) Exact match checks
        # Check LeetCode URL
        url_slug = self._extract_slug_from_url(raw_q)
        if url_slug:
            matched_problem = self.problem_repo.get_by_slug(db, url_slug)

        # Check exact problem number
        if not matched_problem and raw_q.isdigit():
            matched_problem = self.problem_repo.get_by_external_id(db, str(int(raw_q)))

        # Check exact slug
        if not matched_problem:
            matched_problem = self.problem_repo.get_by_slug(db, raw_q.lower())

        # (b) Fuzzy match using pg_trgm if no exact match found
        if not matched_problem:
            trgm_matches = self.problem_repo.search_by_title_trgm(db, raw_q, limit=3)
            candidates_list = [
                CandidateItem(
                    problem=self._to_problem_item(prob),
                    score=round(score, 4),
                )
                for prob, score in trgm_matches
            ]

            if candidates_list and candidates_list[0].score >= 0.4:
                matched_problem = trgm_matches[0][0]

        # If not resolved (best score < 0.4 or no candidates)
        if not matched_problem:
            return ProblemResolveResponse(
                resolved=False,
                problem=None,
                solution=None,
                available_languages=[],
                candidates=candidates_list or [],
            )

        # Fetch solutions and determine available languages
        all_solutions = self.solution_repo.get_by_problem_id(db, matched_problem.id)
        available_languages = sorted(list({s.language for s in all_solutions}))

        # Select solution for requested language if available
        selected_solution: Optional[SolutionItem] = None
        if language:
            target_lang = language.lower()
            matching_sols = [s for s in all_solutions if s.language.lower() == target_lang]
            if matching_sols:
                selected_solution = self._to_solution_item(matching_sols[0])

        return ProblemResolveResponse(
            resolved=True,
            problem=self._to_problem_item(matched_problem),
            solution=selected_solution,
            available_languages=available_languages,
            candidates=candidates_list,
        )

    def get_problem(self, db: Session, problem_id: str) -> ProblemDetailResponse:
        """Fetch problem details by external ID, UUID, or slug."""
        raw_id = problem_id.strip()
        problem: Optional[Problem] = None

        if raw_id.isdigit():
            problem = self.problem_repo.get_by_external_id(db, str(int(raw_id)))

        if not problem:
            problem = self.problem_repo.get_by_id(db, raw_id)

        if not problem:
            problem = self.problem_repo.get_by_slug(db, raw_id.lower())

        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Problem '{problem_id}' not found",
            )

        solutions = self.solution_repo.get_by_problem_id(db, problem.id)
        available_languages = sorted(list({s.language for s in solutions}))
        problem_num = int(problem.external_problem_id) if problem.external_problem_id.isdigit() else 0

        return ProblemDetailResponse(
            id=problem_num,
            uuid=problem.id,
            title=problem.title,
            slug=problem.slug,
            difficulty=problem.difficulty,
            canonical_url=problem.canonical_url,
            available_languages=available_languages,
        )

    def get_solutions(
        self, db: Session, problem_id: str, language: Optional[str] = None
    ) -> List[SolutionItem]:
        """Fetch solutions for a problem; returns empty list if language is missing or not present."""
        raw_id = problem_id.strip()
        problem: Optional[Problem] = None

        if raw_id.isdigit():
            problem = self.problem_repo.get_by_external_id(db, str(int(raw_id)))

        if not problem:
            problem = self.problem_repo.get_by_id(db, raw_id)

        if not problem:
            problem = self.problem_repo.get_by_slug(db, raw_id.lower())

        if not problem:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Problem '{problem_id}' not found",
            )

        if not language or not language.strip():
            return []

        solutions = self.solution_repo.get_by_problem_id(db, problem.id, language.strip())
        return [self._to_solution_item(s) for s in solutions]

