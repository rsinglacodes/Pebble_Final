"""Tests for fuzzy match intent verification and programming language extraction (TASK 1 & TASK 2)."""

import os
import uuid
import pytest
from unittest.mock import MagicMock

from backend.app.config import Settings
from backend.app.integrations.llm.mock import MockLLMProvider
from backend.app.models.problem import Problem
from backend.app.models.solution import Solution
from backend.app.repositories.problem_repository import ProblemRepository
from backend.app.repositories.solution_repository import SolutionRepository
from backend.app.schemas.ask import AskResponse
from backend.app.services.ask_service import AskService
from backend.app.services.ingest_service import IngestService
from backend.app.services.intent_service import IntentClassification, IntentService

FAKE_REPO_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "fake_repo")


@pytest.fixture
def mock_llm_provider():
    """Mock LLM provider with clean state."""
    provider = MockLLMProvider()
    provider.reset()
    return provider


@pytest.fixture
def seeded_db(db_session):
    """Seed test database with fake_repo problems and additional test problems."""
    service = IngestService()
    service.ingest(db=db_session, repo_path=FAKE_REPO_DIR, commit_sha="test_commit_sha_123")

    # Seed problem 56 (Merge Intervals)
    ProblemRepository.upsert(
        db=db_session,
        source="leetcode",
        external_problem_id="56",
        title="Merge Intervals",
        slug="merge-intervals",
        difficulty="Medium",
    )

    # Seed problem 79 (Word Search)
    prob_79, _, _ = ProblemRepository.upsert(
        db=db_session,
        source="leetcode",
        external_problem_id="79",
        title="Word Search",
        slug="word-search",
        difficulty="Medium",
    )
    sol = Solution(
        id=uuid.uuid4(),
        problem_id=prob_79.id,
        language="cpp",
        code="class Solution { public: bool exist() { return true; } };",
        source_type="github",
        source_url="https://github.com/test/repo/solutions/79/79.cpp",
        content_hash="test_hash_word_search_79",
        validated=True,
    )
    db_session.add(sol)
    db_session.commit()
    return db_session


# ---------------------------------------------------------------------------
# Task 1 & Task 2 Tests
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_two_sum_resolves_directly_no_classifier_call(seeded_db, monkeypatch, mock_llm_provider):
    """'two sum' resolves directly via exact match with no classifier call."""
    test_settings = Settings(INTENT_PROVIDER="mock")
    monkeypatch.setattr("backend.app.services.ask_service.get_settings", lambda: test_settings)

    spy_complete = MagicMock(wraps=mock_llm_provider.complete)
    mock_llm_provider.complete = spy_complete

    intent_service = IntentService(provider=mock_llm_provider)
    ask_service = AskService(intent_service=intent_service)

    resp = ask_service.ask(db=seeded_db, text="two sum", programming_language="python")

    assert resp.status == "found"
    assert resp.problem is not None
    assert resp.problem.id == 1
    assert resp.problem.slug == "two-sum"
    assert resp.can_generate is True

    # Classifier must NOT have been called
    spy_complete.assert_not_called()


@pytest.mark.db
def test_leetcode_56_resolves_directly_no_classifier_call(seeded_db, monkeypatch, mock_llm_provider):
    """'leetcode 56' resolves directly via problem number match with no classifier call."""
    test_settings = Settings(INTENT_PROVIDER="mock")
    monkeypatch.setattr("backend.app.services.ask_service.get_settings", lambda: test_settings)

    spy_complete = MagicMock(wraps=mock_llm_provider.complete)
    mock_llm_provider.complete = spy_complete

    intent_service = IntentService(provider=mock_llm_provider)
    ask_service = AskService(intent_service=intent_service)

    resp = ask_service.ask(db=seeded_db, text="leetcode 56", programming_language="python")

    assert resp.status in ("found", "no_solution")
    assert resp.problem is not None
    assert resp.problem.id == 56
    assert resp.problem.slug == "merge-intervals"
    assert resp.can_generate is True

    # Classifier must NOT have been called
    spy_complete.assert_not_called()


@pytest.mark.db
def test_dfs_search_in_cpp_does_not_return_word_search(seeded_db, monkeypatch, mock_llm_provider):
    """'DFS search in cpp' must NOT return Word Search, returns concept with language cpp."""
    test_settings = Settings(INTENT_PROVIDER="mock")
    monkeypatch.setattr("backend.app.services.ask_service.get_settings", lambda: test_settings)

    spy_complete = MagicMock(wraps=mock_llm_provider.complete)
    mock_llm_provider.complete = spy_complete

    intent_service = IntentService(provider=mock_llm_provider)
    ask_service = AskService(intent_service=intent_service)

    resp = ask_service.ask(db=seeded_db, text="DFS search in cpp", programming_language="python")

    # Must NOT return Word Search
    assert resp.problem is None or resp.problem.slug != "word-search"
    assert resp.status == "concept"
    assert resp.can_generate is True

    # Classifier MUST have been called
    assert spy_complete.called

    # Language in video_request must be cpp (extracted from text) rather than incoming python
    assert resp.video_request is not None
    assert resp.video_request.programming_language == "cpp"
    assert resp.video_payload is not None
    assert resp.video_payload["solution"]["programming_language"] == "cpp"


@pytest.mark.db
def test_fuzzy_match_dsa_problem_strict_threshold_rejection(seeded_db, monkeypatch, mock_llm_provider):
    """When fuzzy match triggers classifier and intent is dsa_problem with top score < 0.6, return concept."""
    test_settings = Settings(INTENT_PROVIDER="mock")
    monkeypatch.setattr("backend.app.services.ask_service.get_settings", lambda: test_settings)

    # Mock classifier returning dsa_problem for a nonexistent / weak matching problem
    mock_llm_provider.set_override(
        '{"intent": "dsa_problem", "clean_title": "Search In Grid Unmatched", "reply": "Searching for grid problem", "programming_language": "java"}'
    )

    intent_service = IntentService(provider=mock_llm_provider)
    ask_service = AskService(intent_service=intent_service)

    resp = ask_service.ask(db=seeded_db, text="search in grid with letters", programming_language="python")

    # Score < 0.6 so it is rejected and returned as concept with text from clean_title
    assert resp.status == "concept"
    assert resp.can_generate is True
    assert resp.video_request.text == "Search In Grid Unmatched"
    assert resp.video_request.programming_language == "java"


@pytest.mark.db
def test_fuzzy_match_chitchat_returns_friendly_reply(seeded_db, monkeypatch, mock_llm_provider):
    """When fuzzy match triggers classifier and intent is chitchat, return friendly reply with can_generate=False."""
    test_settings = Settings(INTENT_PROVIDER="mock")
    monkeypatch.setattr("backend.app.services.ask_service.get_settings", lambda: test_settings)

    mock_llm_provider.set_override(
        '{"intent": "chitchat", "clean_title": null, "reply": "Hey there! How can I help with DSA?", "programming_language": null}'
    )

    intent_service = IntentService(provider=mock_llm_provider)
    ask_service = AskService(intent_service=intent_service)

    resp = ask_service.ask(db=seeded_db, text="hey search friend", programming_language="python")

    assert resp.status == "chitchat"
    assert resp.can_generate is False
    assert "Hey there" in resp.message
