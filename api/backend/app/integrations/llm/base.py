"""Base interface for LLM completion providers."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    """Abstract interface for LLM completions."""

    @abstractmethod
    def complete(self, system_prompt: str, user_prompt: str) -> str:
        """Execute chat completion and return the response string.

        Args:
            system_prompt: System prompt with persona and output instructions.
            user_prompt: User data content to process.

        Returns:
            Raw completion text (typically a JSON string).
        """
        pass
