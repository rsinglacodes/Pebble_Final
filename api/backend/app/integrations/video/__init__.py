"""Video provider integrations package."""

from typing import Optional
from backend.app.config import get_settings
from backend.app.integrations.video.base import VideoProvider
from backend.app.integrations.video.http import HttpVideoProvider
from backend.app.integrations.video.mock import MockVideoProvider

_mock_provider_instance: Optional[MockVideoProvider] = None


def get_video_provider() -> VideoProvider:
    """Factory selecting provider based on VIDEO_PROVIDER config ('mock' or 'http')."""
    global _mock_provider_instance
    settings = get_settings()
    provider_type = settings.VIDEO_PROVIDER.lower() if settings.VIDEO_PROVIDER else "mock"

    if provider_type == "http":
        return HttpVideoProvider(
            base_url=settings.VIDEO_ENGINE_URL,
            api_key=settings.VIDEO_ENGINE_API_KEY,
        )

    if _mock_provider_instance is None:
        _mock_provider_instance = MockVideoProvider()
    return _mock_provider_instance


def reset_mock_provider() -> MockVideoProvider:
    """Helper for testing to reset mock provider state."""
    global _mock_provider_instance
    _mock_provider_instance = MockVideoProvider()
    return _mock_provider_instance


__all__ = [
    "VideoProvider",
    "MockVideoProvider",
    "HttpVideoProvider",
    "get_video_provider",
    "reset_mock_provider",
]
