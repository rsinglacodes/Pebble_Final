"""Mock video provider simulating teammate's real Video Engine API."""

import time
import uuid
from typing import Any, Dict, Optional
from backend.app.integrations.video.base import VideoProvider

SAMPLE_VIDEO_URL = "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4"
SAMPLE_BLOB_NAME = "BigBuckBunny.mp4"


class MockVideoProvider(VideoProvider):
    """Mock video generation provider mimicking teammate's exact response shapes and timing."""

    def __init__(self, stage_duration_scale: float = 1.0):
        """Args:
            stage_duration_scale: Multiplier for stage durations.
        """
        self.stage_duration_scale = stage_duration_scale
        self.jobs: Dict[str, Dict[str, Any]] = {}

    def submit(self, payload: Dict[str, Any]) -> str:
        """Submit a payload and initialize mock job."""
        provider_job_id = f"job_{uuid.uuid4().hex[:12]}"
        sol_data = payload.get("solution", {})
        self.jobs[provider_job_id] = {
            "created_at": time.time(),
            "payload": payload,
            "status": "queued",
            "forced_status": None,
            "sent_code": sol_data.get("code"),
            "sent_lang": sol_data.get("programming_language", "python"),
            "sent_validated": sol_data.get("validated", False),
        }
        return provider_job_id

    def force_status(
        self,
        provider_job_id: str,
        status: str,
        error: Optional[str] = None,
        returned_code: Optional[str] = None,
        returned_language: Optional[str] = None,
        video_url: Optional[str] = None,
    ) -> None:
        """Helper to force a specific status (queued, processing, completed, failed)."""
        if provider_job_id not in self.jobs:
            self.jobs[provider_job_id] = {
                "created_at": time.time(),
                "payload": {},
                "status": "queued",
                "forced_status": None,
                "sent_code": None,
                "sent_lang": "python",
                "sent_validated": False,
            }
        self.jobs[provider_job_id]["forced_status"] = {
            "status": status,
            "error": error,
            "returned_code": returned_code,
            "returned_language": returned_language,
            "video_url": video_url,
        }

    def get_raw_status(self, provider_job_id: str) -> Dict[str, Any]:
        """Return teammate's exact response shape:
        {job_id, status: queued|processing|completed|failed, video_url, solution:{code, programming_language}, error}
        """
        job = self.jobs.get(provider_job_id)
        if not job:
            return {
                "job_id": provider_job_id,
                "status": "failed",
                "video_url": None,
                "solution": None,
                "error": "job not found on video service",
            }

        # Check forced status
        if job["forced_status"]:
            forced = job["forced_status"]
            raw_st = forced["status"]
            if raw_st == "completed":
                code = forced["returned_code"] if forced["returned_code"] is not None else (job["sent_code"] or "class Solution: pass")
                lang = forced["returned_language"] or job["sent_lang"]
                v_url = forced["video_url"] or SAMPLE_VIDEO_URL
                return {
                    "job_id": provider_job_id,
                    "status": "completed",
                    "video_url": v_url,
                    "solution": {"code": code, "programming_language": lang},
                    "error": None,
                }
            elif raw_st == "failed":
                return {
                    "job_id": provider_job_id,
                    "status": "failed",
                    "video_url": None,
                    "solution": None,
                    "error": forced.get("error") or "render_failed",
                }
            elif raw_st in ("queued", "processing"):
                return {
                    "job_id": provider_job_id,
                    "status": raw_st,
                    "video_url": None,
                    "solution": None,
                    "error": None,
                }
            else:
                return {
                    "job_id": provider_job_id,
                    "status": raw_st,
                    "video_url": None,
                    "solution": None,
                    "error": None,
                }

        elapsed = (time.time() - job["created_at"]) / self.stage_duration_scale

        if elapsed < 3.0:
            return {
                "job_id": provider_job_id,
                "status": "queued",
                "video_url": None,
                "solution": None,
                "error": None,
            }
        elif elapsed < 8.0:
            return {
                "job_id": provider_job_id,
                "status": "processing",
                "video_url": None,
                "solution": None,
                "error": None,
            }
        else:
            code = job["sent_code"] or "class Solution:\n    def twoSum(self, nums, target):\n        return []"
            return {
                "job_id": provider_job_id,
                "status": "completed",
                "video_url": SAMPLE_VIDEO_URL,
                "solution": {
                    "code": code,
                    "programming_language": job["sent_lang"],
                },
                "error": None,
            }

    def get_status(self, provider_job_id: str) -> Dict[str, Any]:
        """Fetch current status mapped to Pebble internal format."""
        raw = self.get_raw_status(provider_job_id)
        raw_status = raw.get("status")
        video_url = raw.get("video_url")
        solution = raw.get("solution")
        error = raw.get("error")

        blob_name = None
        if video_url:
            blob_name = video_url.rsplit("/", 1)[-1] if "/" in video_url else video_url

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
