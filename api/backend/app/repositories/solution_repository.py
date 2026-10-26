"""Solution repository for database access."""

import uuid
from typing import List, Optional, Tuple, Union
from sqlalchemy import select
from sqlalchemy.orm import Session
from backend.app.models.solution import Solution


class SolutionRepository:
    """Repository handling database operations for Solution model."""

    @staticmethod
    def get_by_id(db: Session, solution_id: Union[uuid.UUID, str]) -> Optional[Solution]:
        """Fetch solution by UUID."""
        if isinstance(solution_id, str):
            solution_id = uuid.UUID(solution_id)
        stmt = select(Solution).where(Solution.id == solution_id)
        return db.scalars(stmt).first()

    @staticmethod
    def get_by_problem_and_language(
        db: Session, problem_id: uuid.UUID, language: str
    ) -> Optional[Solution]:
        """Fetch solution for a problem by programming language."""
        stmt = select(Solution).where(
            Solution.problem_id == problem_id,
            Solution.language == language.lower(),
        )
        return db.scalars(stmt).first()

    @staticmethod
    def get_by_problem_and_url(
        db: Session, problem_id: uuid.UUID, source_url: str
    ) -> Optional[Solution]:
        """Fetch solution for a problem by source URL."""
        stmt = select(Solution).where(
            Solution.problem_id == problem_id,
            Solution.source_url == source_url,
        )
        return db.scalars(stmt).first()

    @staticmethod
    def get_by_problem_id(
        db: Session, problem_id: uuid.UUID, language: Optional[str] = None
    ) -> List[Solution]:
        """Fetch solutions for a problem, optionally filtered by programming language."""
        stmt = select(Solution).where(Solution.problem_id == problem_id)
        if language:
            stmt = stmt.where(Solution.language == language.lower())
        stmt = stmt.order_by(Solution.source_url.asc())
        return list(db.scalars(stmt).all())

    @staticmethod
    def upsert(
        db: Session,
        problem_id: uuid.UUID,
        language: str,
        code: str,
        source_type: str,
        source_url: str,
        content_hash: str,
        commit_sha: str,
        validated: bool = True,
    ) -> Tuple[Solution, bool, bool]:
        """Upsert a solution for a problem and language.
        
        Returns:
            Tuple[Solution, created, updated]:
            created is True if a new row was added.
            updated is True if content_hash differed and row was updated.
        """
        existing = SolutionRepository.get_by_problem_and_language(db, problem_id, language)
        if existing:
            if existing.content_hash != content_hash:
                existing.code = code
                existing.content_hash = content_hash
                existing.source_url = source_url
                existing.commit_sha = commit_sha
                existing.validated = validated
                db.flush()
                return existing, False, True
            return existing, False, False

        solution = Solution(
            problem_id=problem_id,
            language=language.lower(),
            code=code,
            source_type=source_type,
            source_url=source_url,
            content_hash=content_hash,
            commit_sha=commit_sha,
            validated=validated,
            validation_status="verified" if validated else "not_tested",
        )
        db.add(solution)
        db.flush()
        return solution, True, False

