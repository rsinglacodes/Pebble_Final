"""Tests for LLM Intent Classifier and its integration with AskService."""

import json
import logging
from unittest.mock import MagicMock
import uuid
import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from backend.app.config import Settings
from backend.app.db.base import Base
from backend.app.integrations.llm.mock import MockLLMProvider
from backend.app.models.problem import Problem
from backend.app.models.solution import Solution
from backend.app.models.user import User
from backend.app.schemas.ask import AskResponse
from backend.app.services.ask_service import AskService
from backend.app.services.intent_service import (
    INTENT_SYSTEM_PROMPT,
    IntentClassification,
    IntentService,
)
from backend.app.services.problem_service import ProblemService


@pytest.fixture
def sqlite_session():
    """Isolated in-memory SQLite session for tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


@pytest.fixture
def mock_llm():
    """Mock LLM provider fixture with clean state."""
    provider = MockLLMProvider()
    provider.reset()
    return provider


# ---------------------------------------------------------------------------
# 1. IntentClassification Schema Tests
# ---------------------------------------------------------------------------


def test_intent_classification_valid():
    """Valid JSON parses correctly into IntentClassification."""
    payload = {
        "intent": "chitchat",
        "clean_title": None,
        "reply": "Hello! How can I assist you with DSA today?",
    }
    model = IntentClassification.model_validate(payload)
    assert model.intent == "chitchat"
    assert model.clean_title is None
    assert "DSA" in model.reply


def test_intent_classification_invalid_intent():
    """Invalid intent string fails validation."""
    with pytest.raises(ValidationError):
        IntentClassification.model_validate({
            "intent": "unknown_intent",
            "clean_title": None,
            "reply": "Hello",
        })


def test_intent_classification_missing_reply():
    """Missing reply fails validation."""
    with pytest.raises(ValidationError):
        IntentClassification.model_validate({
            "intent": "algorithm_concept",
            "clean_title": "Binary Search",
        })


# ---------------------------------------------------------------------------
# 2. MockLLMProvider Unit Tests
# ---------------------------------------------------------------------------


def test_mock_llm_provider_chitchat(mock_llm):
    """Mock provider returns chitchat for greeting keywords."""
    res = mock_llm.complete(INTENT_SYSTEM_PROMPT, "<user_data>hello there</user_data>")
    data = json.loads(res)
    assert data["intent"] == "chitchat"
    assert data["clean_title"] is None


def test_mock_llm_provider_off_topic(mock_llm):
    """Mock provider returns off_topic for non-DSA queries."""
    res = mock_llm.complete(INTENT_SYSTEM_PROMPT, "<user_data>what is the weather today?</user_data>")
    data = json.loads(res)
    assert data["intent"] == "off_topic"


def test_mock_llm_provider_algorithm_concept(mock_llm):
    """Mock provider returns algorithm_concept for concept queries."""
    res = mock_llm.complete(INTENT_SYSTEM_PROMPT, "<user_data>explain binary search</user_data>")
    data = json.loads(res)
    assert data["intent"] == "algorithm_concept"
    assert data["clean_title"] == "Binary Search"


def test_mock_llm_provider_override(mock_llm):
    """Override response works as expected."""
    mock_llm.set_override(json.dumps({
        "intent": "chitchat",
        "clean_title": None,
        "reply": "Custom test reply",
    }))
    res = mock_llm.complete("", "")
    data = json.loads(res)
    assert data["reply"] == "Custom test reply"


# ---------------------------------------------------------------------------
# 3. IntentService Unit Tests
# ---------------------------------------------------------------------------


def test_intent_service_truncation_and_wrapping(mock_llm):
    """IntentService truncates prompt to 500 chars and wraps in <user_data> tags."""
    received_prompts = []

    def capture_prompt(system_prompt, user_prompt):
        received_prompts.append(user_prompt)
        return json.dumps({
            "intent": "chitchat",
            "clean_title": None,
            "reply": "Hi!",
        })

    mock_llm.set_handler(capture_prompt)
    service = IntentService(provider=mock_llm)

    long_input = "a" * 1000
    classification = service.classify(long_input)
    assert classification is not None
    assert len(received_prompts) == 1
    assert received_prompts[0].startswith("<user_data>\n")
    assert received_prompts[0].endswith("\n</user_data>")
    inner_text = received_prompts[0].replace("<user_data>\n", "").replace("\n</user_data>", "")
    assert len(inner_text) == 500


def test_intent_service_markdown_fence_cleaning(mock_llm):
    """IntentService cleans markdown ```json code blocks from response."""
    fenced = "```json\n{\"intent\": \"chitchat\", \"clean_title\": null, \"reply\": \"Hello!\"}\n```"
    mock_llm.set_override(fenced)
    service = IntentService(provider=mock_llm)
    res = service.classify("hi")
    assert res is not None
    assert res.intent == "chitchat"
    assert res.reply == "Hello!"


def test_intent_service_handles_failure_gracefully(mock_llm):
    """IntentService returns None if LLM raises an error without crashing."""
    mock_llm.set_failure(RuntimeError("API connection timeout"))
    service = IntentService(provider=mock_llm)
    res = service.classify("test query")
    assert res is None


# ---------------------------------------------------------------------------
# 4. AskService Integration Tests with Intent Classification
# ---------------------------------------------------------------------------


def test_ask_service_intent_provider_off(sqlite_session, monkeypatch):
    """When INTENT_PROVIDER='off', keyword gate is used and 'hello' is out_of_scope."""
    test_settings = Settings(INTENT_PROVIDER="off")
    monkeypatch.setattr("backend.app.services.ask_service.get_settings", lambda: test_settings)

    ask_service = AskService()
    resp = ask_service.ask(db=sqlite_session, text="hello")
    # 'hello' is not a DSA keyword, so without intent classifier it is rejected as out_of_scope
    assert resp.status == "out_of_scope"
    assert resp.can_generate is False


def test_ask_service_chitchat_flow(sqlite_session, monkeypatch, mock_llm):
    """With INTENT_PROVIDER='mock', 'hello' classified as chitchat returns status='chitchat'."""
    test_settings = Settings(INTENT_PROVIDER="mock")
    monkeypatch.setattr("backend.app.services.ask_service.get_settings", lambda: test_settings)

    intent_service = IntentService(provider=mock_llm)
    ask_service = AskService(intent_service=intent_service)

    resp = ask_service.ask(db=sqlite_session, text="hello friend")
    assert resp.status == "chitchat"
    assert resp.can_generate is False
    assert resp.video_request is None
    assert resp.video_payload is None
    assert "Hello" in resp.message


def test_ask_service_off_topic_flow(sqlite_session, monkeypatch, mock_llm):
    """With INTENT_PROVIDER='mock', recipe questions return status='out_of_scope'."""
    test_settings = Settings(INTENT_PROVIDER="mock")
    monkeypatch.setattr("backend.app.services.ask_service.get_settings", lambda: test_settings)

    intent_service = IntentService(provider=mock_llm)
    ask_service = AskService(intent_service=intent_service)

    resp = ask_service.ask(db=sqlite_session, text="give me a recipe for pizza")
    assert resp.status == "out_of_scope"
    assert resp.can_generate is False
    assert resp.video_request is None


def test_ask_service_algorithm_concept_flow(sqlite_session, monkeypatch, mock_llm):
    """Algorithm concept query returns status='concept', can_generate=True, and video payloads."""
    test_settings = Settings(INTENT_PROVIDER="mock")
    monkeypatch.setattr("backend.app.services.ask_service.get_settings", lambda: test_settings)

    intent_service = IntentService(provider=mock_llm)
    ask_service = AskService(intent_service=intent_service)

    resp = ask_service.ask(db=sqlite_session, text="can you explain binary search?", programming_language="python")
    assert resp.status == "concept"
    assert resp.can_generate is True
    assert resp.video_request is not None
    assert resp.video_request.text == "Binary Search"
    assert resp.video_request.programming_language == "python"
    assert resp.video_payload is not None
    assert resp.video_payload["question"]["title"] == "Binary Search"
    assert resp.video_payload["solution"]["programming_language"] == "python"


def test_ask_service_dsa_problem_resolved_flow(sqlite_session, monkeypatch, mock_llm):
    """dsa_problem intent that resolves in DB returns found with video_request and video_payload."""
    test_settings = Settings(INTENT_PROVIDER="mock")
    monkeypatch.setattr("backend.app.services.ask_service.get_settings", lambda: test_settings)

    # Seed a problem and solution in DB
    prob_id = uuid.uuid4()
    prob = Problem(
        id=prob_id,
        source="leetcode",
        external_problem_id="1",
        slug="two-sum",
        title="Two Sum",
        difficulty="Easy",
    )
    sol = Solution(
        id=uuid.uuid4(),
        problem_id=prob_id,
        language="python",
        code="class Solution:\n    def twoSum(self, nums, target):\n        return []\n",
        source_type="github",
        content_hash="dummy_hash_123",
        validated=True,
    )
    sqlite_session.add(prob)
    sqlite_session.add(sol)
    sqlite_session.commit()

    # Query with conversational prefix so initial lookup doesn't resolve by exact slug
    mock_llm.set_override(json.dumps({
        "intent": "dsa_problem",
        "clean_title": "Two Sum",
        "reply": "Found matching problem.",
    }))

    intent_service = IntentService(provider=mock_llm)
    ask_service = AskService(intent_service=intent_service)

    resp = ask_service.ask(db=sqlite_session, text="solve this for me: two sum problem", programming_language="python")
    assert resp.status == "found"
    assert resp.can_generate is True
    assert resp.problem is not None
    assert resp.problem.id == 1
    assert resp.video_request is not None
    assert resp.video_request.problem_id == 1
    assert resp.video_payload is not None
    assert resp.video_payload["question"]["id"] == 1
    assert resp.video_payload["solution"]["code"] == sol.code.strip()


def test_ask_service_llm_failure_falls_back_to_keyword_gate(sqlite_session, monkeypatch, mock_llm):
    """When LLM classifier call fails, execution falls back cleanly to keyword gate."""
    test_settings = Settings(INTENT_PROVIDER="mock")
    monkeypatch.setattr("backend.app.services.ask_service.get_settings", lambda: test_settings)

    mock_llm.set_failure(TimeoutError("Azure OpenAI timed out"))
    intent_service = IntentService(provider=mock_llm)
    ask_service = AskService(intent_service=intent_service)

    # "binary search" is a DSA keyword in dsa_keywords.py -> passes keyword gate and returns concept
    resp = ask_service.ask(db=sqlite_session, text="binary search")
    assert resp.status == "concept"
    assert resp.can_generate is True
