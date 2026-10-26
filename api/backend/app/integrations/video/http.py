"""HTTP client integration for teammate-owned Video Engine service."""

import logging
from typing import Any, Dict
import httpx
from fastapi import HTTPException, status
from backend.app.integrations.video.base import VideoProvider

logger = logging.getLogger(__name__)


class HttpVideoProvider(VideoProvider):
    """Client communicating with external Video Engine API over HTTP."""

    def __init__(self, base_url: str, api_key: str = "", timeout_seconds: float = 10.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout_seconds

    def _headers(self) -> Dict[str, str]:
        headers = {"Content-Type": "application/json"}
        if self.api_key and self.api_key.strip():
            headers["X-API-Key"] = self.api_key.strip()
        return headers

    def submit(self, payload: Dict[str, Any]) -> str:
        """Call POST {VIDEO_ENGINE_URL}/generate-video.

        Returns:
            job_id (str)
        """
        url = f"{self.base_url}/generate-video"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.post(url, json=payload, headers=self._headers())
                if response.status_code != 200:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=f"Video engine generate-video request failed with status {response.status_code}: {response.text}",
                    )
                data = response.json()
                job_id = data.get("job_id")
                if not job_id:
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail="Video engine response did not include 'job_id'",
                    )
                return str(job_id)
        except httpx.RequestError as exc:
            raise HTTPException(
                status_code=status.HTTP_504_GATEWAY_TIMEOUT,
                detail=f"Failed to communicate with video engine: {exc}",
            )

    def get_status(self, provider_job_id: str) -> Dict[str, Any]:
        """Call GET {VIDEO_ENGINE_URL}/video-status/{job_id}.

        Returns mapped status dictionary with stage, blob_name, and solution.
        """
        url = f"{self.base_url}/video-status/{provider_job_id}"
        try:
            with httpx.Client(timeout=self.timeout) as client:
                response = client.get(url, headers=self._headers())

                # 404 marks the job failed with 'job not found on video service'
                if response.status_code == 404:
                    return {
                        "status": "failed",
                        "stage": "failed",
                        "video_url": None,
                        "blob_name": None,
                        "solution": None,
                        "error": "job not found on video service",
                    }

                # 5xx responses are retried and never fail the job from a single poll error
                if 500 <= response.status_code < 600:
                    logger.warning("Video engine poll returned %s, retrying...", response.status_code)
                    return {
                        "status": "retry",
                        "stage": None,
                        "video_url": None,
                        "blob_name": None,
                        "solution": None,
                        "error": None,
                        "retryable": True,
                    }

                if response.status_code != 200:
                    return {
                        "status": "failed",
                        "stage": "failed",
                        "video_url": None,
                        "blob_name": None,
                        "solution": None,
                        "error": f"Video service error {response.status_code}: {response.text}",
                    }

                data = response.json()
                raw_status = data.get("status")
                video_url = data.get("video_url")
                solution = data.get("solution")
                error = data.get("error")

                # blob_name is the last path segment of video_url or null
                blob_name = None
                if video_url:
                    blob_name = video_url.rsplit("/", 1)[-1] if "/" in video_url else video_url

                # Map status:
                # - 'queued' -> 'queued'
                # - 'processing' -> 'running'
                # - 'completed' -> 'completed'
                # - 'failed' -> 'failed'
                # - unknown statuses count as 'running'
                if raw_status == "queued":
                    mapped_status = "queued"
                elif raw_status == "processing":
                    mapped_status = "running"
                elif raw_status == "completed":
                    mapped_status = "completed"
                elif raw_status == "failed":
                    mapped_status = "failed"
                else:
                    mapped_status = "running"

                stage = raw_status if raw_status is not None else mapped_status

                return {
                    "status": mapped_status,
                    "stage": stage,
                    "video_url": video_url,
                    "blob_name": blob_name,
                    "solution": solution,
                    "error": error,
                }

        except (httpx.TimeoutException, httpx.RequestError) as exc:
            # Timeouts and network errors on a poll are retried and never fail the job
            logger.warning("Video engine poll network/timeout error: %s, retrying...", exc)
            return {
                "status": "retry",
                "stage": None,
                "video_url": None,
                "blob_name": None,
                "solution": None,
                "error": None,
                "retryable": True,
            }
