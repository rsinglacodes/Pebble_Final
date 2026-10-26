"""Base interface for video generation providers."""

from abc import ABC, abstractmethod
from typing import Any, Dict


class VideoProvider(ABC):
    """Abstract interface for video generation providers."""

    @abstractmethod
    def submit(self, payload: Dict[str, Any]) -> str:
        """Submit video rendering payload to provider.
        
        Returns:
            provider_job_id (str)
        """
        pass

    @abstractmethod
    def get_status(self, provider_job_id: str) -> Dict[str, Any]:
        """Poll the provider for current job status.
        
        Returns:
            dict containing:
            - status (str): queued | running | completed | failed
            - stage (str): queued | rendering | narration | assembling | uploading | completed
            - video_url (Optional[str])
            - blob_name (Optional[str])
            - error (Optional[str])
        """
        pass
