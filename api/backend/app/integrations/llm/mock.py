"""Mock LLM provider for unit and integration testing."""

import json
from typing import Callable, Optional

from backend.app.integrations.llm.base import LLMProvider


class MockLLMProvider(LLMProvider):
    """Deterministic mock LLM provider for testing without external API calls."""

    def __init__(self) -> None:
        self._override_response: Optional[str] = None
        self._raise_error: Optional[Exception] = None
        self._custom_handler: Optional[Callable[[str, str], str]] = None

    def set_override(self, response_json_str: Optional[str]) -> None:
        """Force a specific JSON string response."""
        self._override_response = response_json_str

    def set_failure(self, error: Optional[Exception]) -> None:
        """Force a failure/exception on complete()."""
        self._raise_error = error

    def set_handler(self, handler: Optional[Callable[[str, str], str]]) -> None:
        """Set a dynamic handler function."""
        self._custom_handler = handler

    def reset(self) -> None:
        """Reset mock state."""
        self._override_response = None
        self._raise_error = None
        self._custom_handler = None

    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Return deterministic JSON response based on user_prompt."""
        if self._raise_error is not None:
            raise self._raise_error

        if self._override_response is not None:
            return self._override_response

        if self._custom_handler is not None:
            return self._custom_handler(system_prompt, user_prompt)

        lower_prompt = user_prompt.lower()

        # Check for greetings / chitchat
        if any(w in lower_prompt for w in ("hello", "hi", "hey", "good morning", "how are you")):
            return json.dumps({
                "intent": "chitchat",
                "clean_title": None,
                "reply": "Hello! How can I help you with data structures and algorithms?",
            })

        # Check for off-topic queries
        if any(w in lower_prompt for w in ("weather", "recipe", "cook", "pizza", "movie", "politics", "football")):
            return json.dumps({
                "intent": "off_topic",
                "clean_title": None,
                "reply": "I specialize in data structures and algorithms. Please ask a DSA-related question.",
            })

        # Check for specific problems
        if "two sum" in lower_prompt or "problem 1" in lower_prompt:
            return json.dumps({
                "intent": "dsa_problem",
                "clean_title": "Two Sum",
                "reply": "Found matching DSA problem.",
            })

        if "reverse linked list" in lower_prompt:
            return json.dumps({
                "intent": "dsa_problem",
                "clean_title": "Reverse Linked List",
                "reply": "Found matching DSA problem.",
            })

        if "unknown problem" in lower_prompt:
            return json.dumps({
                "intent": "dsa_problem",
                "clean_title": "Nonexistent Problem 9999",
                "reply": "Looking for DSA problem.",
            })

        # Check for algorithm concepts
        if "binary search" in lower_prompt:
            return json.dumps({
                "intent": "algorithm_concept",
                "clean_title": "Binary Search",
                "reply": "Pebble will generate an explanation for binary search.",
            })

        if "dijkstra" in lower_prompt:
            return json.dumps({
                "intent": "algorithm_concept",
                "clean_title": "Dijkstra's Algorithm",
                "reply": "Pebble will generate an explanation for Dijkstra's algorithm.",
            })

        # Default fallback: concept
        return json.dumps({
            "intent": "algorithm_concept",
            "clean_title": None,
            "reply": "Pebble will generate an explanation for this algorithm concept.",
        })
