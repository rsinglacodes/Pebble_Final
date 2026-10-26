"""Tests for Groq LLM Provider and its integration with IntentService and AskService."""

import json
from unittest.mock import MagicMock, patch
import httpx
import pytest

from backend.app.config import Settings
from backend.app.db.base import Base
from backend.app.integrations.llm import get_llm_provider
from backend.app.integrations.llm.groq import GroqProvider
from backend.app.services.ask_service import AskService
from backend.app.services.intent_service import IntentService
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


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
def groq_provider():
    """GroqProvider instance with test credentials."""
    return GroqProvider(
        api_key="gsk_test_mock_key_12345",
        model="llama-3.1-8b-instant",
        timeout_seconds=5.0,
    )


def test_groq_provider_factory(monkeypatch):
    """When INTENT_PROVIDER='groq', get_llm_provider returns GroqProvider."""
    test_settings = Settings(
        INTENT_PROVIDER="groq",
        GROQ_API_KEY="gsk_factory_test_key",
        GROQ_MODEL="llama-3.1-8b-instant",
    )
    monkeypatch.setattr("backend.app.integrations.llm.get_settings", lambda: test_settings)

    provider = get_llm_provider()
    assert isinstance(provider, GroqProvider)
    assert provider.api_key == "gsk_factory_test_key"
    assert provider.model == "llama-3.1-8b-instant"


def test_groq_valid_json(groq_provider):
    """Valid completion response from Groq is parsed into IntentClassification."""
    expected_content = json.dumps({
        "intent": "algorithm_concept",
        "clean_title": "Binary Search",
        "reply": "Pebble can explain binary search.",
    })
    mock_response = httpx.Response(
        status_code=200,
        json={"choices": [{"message": {"content": expected_content}}]},
        request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
    )

    with patch("httpx.Client.post", return_value=mock_response) as mock_post:
        res = groq_provider.complete("System prompt", "<user_data>explain binary search</user_data>")
        assert res == expected_content

        # Verify call headers and payload
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        assert args[0] == "https://api.groq.com/openai/v1/chat/completions"
        assert kwargs["headers"]["Authorization"] == "Bearer gsk_test_mock_key_12345"
        assert kwargs["json"]["model"] == "llama-3.1-8b-instant"
        assert kwargs["json"]["response_format"] == {"type": "json_object"}

    # Verify integration with IntentService
    with patch("httpx.Client.post", return_value=mock_response):
        intent_service = IntentService(provider=groq_provider)
        classification = intent_service.classify("explain binary search")
        assert classification is not None
        assert classification.intent == "algorithm_concept"
        assert classification.clean_title == "Binary Search"


def test_groq_malformed_json(groq_provider):
    """Malformed or invalid JSON returned by Groq is handled safely returning None."""
    # 1. Groq returns non-JSON text content in the message
    mock_response_bad_content = httpx.Response(
        status_code=200,
        json={"choices": [{"message": {"content": "not a valid json string {{"}}]},
        request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
    )
    with patch("httpx.Client.post", return_value=mock_response_bad_content):
        intent_service = IntentService(provider=groq_provider)
        classification = intent_service.classify("some query")
        assert classification is None

    # 2. Groq returns response missing choices
    mock_response_no_choices = httpx.Response(
        status_code=200,
        json={"choices": []},
        request=httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions"),
    )
    with patch("httpx.Client.post", return_value=mock_response_no_choices):
        intent_service = IntentService(provider=groq_provider)
        classification = intent_service.classify("some query")
        assert classification is None


def test_groq_timeout(groq_provider):
    """Timeout during Groq HTTP call is caught and returns safe None default."""
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    with patch("httpx.Client.post", side_effect=httpx.TimeoutException("Connection timed out", request=req)):
        # Calling provider directly raises exception
        with pytest.raises(httpx.TimeoutException):
            groq_provider.complete("Sys", "User")

        # IntentService safely catches and returns None
        intent_service = IntentService(provider=groq_provider)
        classification = intent_service.classify("test query")
        assert classification is None


def test_groq_401_response(groq_provider):
    """401 Unauthorized from Groq is caught and returns safe None default."""
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    resp_401 = httpx.Response(
        status_code=401,
        json={"error": {"message": "Invalid API Key"}},
        request=req,
    )

    with patch("httpx.Client.post", return_value=resp_401):
        # Calling provider directly raises HTTPStatusError
        with pytest.raises(httpx.HTTPStatusError):
            groq_provider.complete("Sys", "User")

        # IntentService safely catches and returns None
        intent_service = IntentService(provider=groq_provider)
        classification = intent_service.classify("test query")
        assert classification is None


def test_groq_ask_service_fallback_on_error(monkeypatch, groq_provider, sqlite_session):
    """AskService falls back cleanly to keyword gate when Groq call fails."""
    test_settings = Settings(
        INTENT_PROVIDER="groq",
        GROQ_API_KEY="gsk_test",
    )
    monkeypatch.setattr("backend.app.services.ask_service.get_settings", lambda: test_settings)

    # Simulate 401 error from Groq
    req = httpx.Request("POST", "https://api.groq.com/openai/v1/chat/completions")
    resp_401 = httpx.Response(status_code=401, json={"error": "Unauthorized"}, request=req)

    with patch("httpx.Client.post", return_value=resp_401):
        intent_service = IntentService(provider=groq_provider)
        ask_service = AskService(intent_service=intent_service)

        # Query containing DSA keyword "binary search" -> passes keyword gate and returns concept
        resp = ask_service.ask(db=sqlite_session, text="binary search")
        assert resp.status == "concept"
        assert resp.can_generate is True
