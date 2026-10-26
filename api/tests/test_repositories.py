"""Integration tests for UserRepository and ProblemRepository using TEST_DATABASE_URL.

Tests connect to the dedicated Neon test branch, run in isolated transactions,
and roll back all changes upon completion. If TEST_DATABASE_URL is not set,
tests are skipped with a clear message.
"""

import uuid
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from backend.app.config import get_settings
from backend.app.db.base import Base
from backend.app.repositories.problem_repository import ProblemRepository
from backend.app.repositories.user_repository import UserRepository



@pytest.mark.db
def test_user_repository_create_and_get(db_session: Session):
    """Test user creation and retrieval by ID and email."""
    unique_email = f"test_{uuid.uuid4().hex[:8]}@example.com"
    user = UserRepository.create(
        db=db_session,
        name="Test User",
        email=unique_email,
        onboarding_completed=False,
    )

    assert user.id is not None
    assert isinstance(user.id, uuid.UUID)
    assert user.name == "Test User"
    assert user.email == unique_email
    assert user.onboarding_completed is False

    # Get by ID
    by_id = UserRepository.get_by_id(db_session, user.id)
    assert by_id is not None
    assert by_id.id == user.id
    assert by_id.email == unique_email

    # Get by email
    by_email = UserRepository.get_by_email(db_session, unique_email)
    assert by_email is not None
    assert by_email.id == user.id

    # Nonexistent queries
    assert UserRepository.get_by_id(db_session, uuid.uuid4()) is None
    assert UserRepository.get_by_email(db_session, "nonexistent@example.com") is None


@pytest.mark.db
def test_problem_repository_create_and_get(db_session: Session):
    """Test problem creation and retrieval by ID, slug, and external ID."""
    rand_suffix = uuid.uuid4().hex[:6]
    slug = f"binary-search-{rand_suffix}"
    ext_id = f"LC-{rand_suffix}"

    problem = ProblemRepository.create(
        db=db_session,
        source="leetcode",
        external_problem_id=ext_id,
        title=f"Binary Search {rand_suffix}",
        slug=slug,
        difficulty="Easy",
        topics=["Array", "Binary Search"],
        canonical_url=f"https://leetcode.com/problems/{slug}/",
        statement_hash="hash123",
    )

    assert problem.id is not None
    assert isinstance(problem.id, uuid.UUID)
    assert problem.external_problem_id == ext_id
    assert problem.slug == slug
    assert problem.difficulty == "Easy"
    assert "Array" in problem.topics

    # Get by ID
    by_id = ProblemRepository.get_by_id(db_session, problem.id)
    assert by_id is not None
    assert by_id.id == problem.id

    # Get by slug
    by_slug = ProblemRepository.get_by_slug(db_session, slug)
    assert by_slug is not None
    assert by_slug.id == problem.id

    # Get by external ID
    by_ext = ProblemRepository.get_by_external_id(db_session, ext_id)
    assert by_ext is not None
    assert by_ext.id == problem.id

    # Nonexistent queries
    assert ProblemRepository.get_by_id(db_session, uuid.uuid4()) is None
    assert ProblemRepository.get_by_slug(db_session, "nonexistent-slug") is None
    assert ProblemRepository.get_by_external_id(db_session, "nonexistent-ext-id") is None
