"""Problem repository for database access."""

import uuid
from typing import Any, List, Optional, Tuple, Union
import sqlalchemy as sa
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.app.models.problem import Problem


class ProblemRepository:
    """Repository handling database operations for Problem model."""

    @staticmethod
    def create(
        db: Session,
        source: str,
        external_problem_id: str,
        title: str,
        slug: str,
        difficulty: str = "Medium",
        topics: Optional[Any] = None,
        canonical_url: Optional[str] = None,
        statement_hash: Optional[str] = None,
    ) -> Problem:
        """Create and persist a new problem entity."""
        problem = Problem(
            source=source,
            external_problem_id=external_problem_id,
            title=title,
            slug=slug,
            difficulty=difficulty,
            topics=topics,
            canonical_url=canonical_url,
            statement_hash=statement_hash,
        )
        db.add(problem)
        db.flush()
        db.refresh(problem)
        return problem

    @staticmethod
    def get_by_id(db: Session, problem_id: Union[uuid.UUID, str]) -> Optional[Problem]:
        """Fetch problem by primary key UUID."""
        if isinstance(problem_id, str):
            try:
                problem_id = uuid.UUID(problem_id)
            except ValueError:
                return None
        stmt = select(Problem).where(Problem.id == problem_id)
        return db.scalars(stmt).first()

    @staticmethod
    def get_by_slug(db: Session, slug: str) -> Optional[Problem]:
        """Fetch problem by unique slug."""
        stmt = select(Problem).where(Problem.slug == slug)
        return db.scalars(stmt).first()

    @staticmethod
    def get_by_external_id(db: Session, external_problem_id: str) -> Optional[Problem]:
        """Fetch problem by external source identifier (e.g. LeetCode problem ID)."""
        stmt = select(Problem).where(Problem.external_problem_id == external_problem_id)
        return db.scalars(stmt).first()

    @staticmethod
    def upsert(
        db: Session,
        source: str,
        external_problem_id: str,
        title: str,
        slug: str,
        canonical_url: Optional[str] = None,
        difficulty: str = "Medium",
    ) -> Tuple[Problem, bool, bool]:
        """Upsert problem by source and external_problem_id.
        
        Returns:
            Tuple[Problem, created, updated]
        """
        stmt = select(Problem).where(
            Problem.source == source,
            Problem.external_problem_id == external_problem_id,
        )
        existing = db.scalars(stmt).first()
        if existing:
            updated = False
            if existing.title != title or existing.slug != slug or existing.canonical_url != canonical_url:
                existing.title = title
                existing.slug = slug
                existing.canonical_url = canonical_url
                updated = True
                db.flush()
            return existing, False, updated

        problem = Problem(
            source=source,
            external_problem_id=external_problem_id,
            title=title,
            slug=slug,
            difficulty=difficulty,
            canonical_url=canonical_url,
        )
        db.add(problem)
        db.flush()
        return problem, True, False

    @staticmethod
    def search_by_title_trgm(
        db: Session, query: str, limit: int = 3
    ) -> List[Tuple[Problem, float]]:
        """Search problems by fuzzy title match using PostgreSQL pg_trgm similarity.
        
        Returns:
            List of (Problem, score) ordered by score descending.
        """
        score_col = func.similarity(Problem.title, query).label("score")
        stmt = (
            select(Problem, score_col)
            .where(func.similarity(Problem.title, query) > 0.0)
            .order_by(score_col.desc())
            .limit(limit)
        )
        try:
            results = db.execute(stmt).all()
            return [(row[0], float(row[1])) for row in results]
        except Exception:
            # Fallback if pg_trgm is unavailable (e.g. SQLite test engine)
            db.rollback()
            return []
