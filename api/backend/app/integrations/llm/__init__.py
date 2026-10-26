"""LLM integrations package."""

from typing import Optional

from backend.app.config import get_settings
from backend.app.integrations.llm.azure_openai import AzureOpenAIProvider
from backend.app.integrations.llm.base import LLMProvider
from backend.app.integrations.llm.groq import GroqProvider
from backend.app.integrations.llm.mock import MockLLMProvider

_mock_instance: Optional[MockLLMProvider] = None


def get_mock_llm_provider() -> MockLLMProvider:
    """Get or create singleton mock provider instance for tests."""
    global _mock_instance
    if _mock_instance is None:
        _mock_instance = MockLLMProvider()
    return _mock_instance


def get_llm_provider() -> Optional[LLMProvider]:
    """Factory function returning the configured LLMProvider based on settings.

    Returns:
        LLMProvider instance, or None if INTENT_PROVIDER is 'off' or unknown.
    """
    settings = get_settings()
    provider_name = (settings.INTENT_PROVIDER or "off").strip().lower()

    if provider_name == "off":
        return None
    elif provider_name == "mock":
        return get_mock_llm_provider()
    elif provider_name == "azure":
        return AzureOpenAIProvider(
            endpoint=settings.AZURE_OPENAI_ENDPOINT,
            api_key=settings.AZURE_OPENAI_API_KEY,
            deployment=settings.AZURE_OPENAI_DEPLOYMENT,
            api_version=settings.AZURE_OPENAI_API_VERSION,
            timeout_seconds=settings.INTENT_TIMEOUT_SECONDS,
        )
    elif provider_name == "groq":
        return GroqProvider(
            api_key=settings.GROQ_API_KEY,
            model=settings.GROQ_MODEL,
            timeout_seconds=settings.INTENT_TIMEOUT_SECONDS,
        )
    return None


__all__ = [
    "LLMProvider",
    "AzureOpenAIProvider",
    "GroqProvider",
    "MockLLMProvider",
    "get_llm_provider",
    "get_mock_llm_provider",
]
