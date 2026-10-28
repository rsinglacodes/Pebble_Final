"""Background worker: one thread, one job at a time, oldest job first.

A job is answered from the blob cache when the fingerprint is already stored,
otherwise the full pipeline runs, the video is uploaded and only then is the job
marked completed. Any failure marks the job failed with a short, sanitized
message; the traceback stays in the job's ``pipeline.log`` and the workspace is
kept so the work can be inspected or re-uploaded.
"""

from __future__ import annotations

import json
import logging
import os
import shutil
import threading
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from pebble import pipeline as pipeline_module
from pebble.config import Settings, load_settings
from pebble.environment import EnvInfo, detect
from pebble.jobs import FORCE_PAYLOAD_KEY, STATUS_COMPLETED, STATUS_FAILED, JobStore
from pebble.logging_setup import secret_values
from pebble.storage import BlobStorage
from pebble.workspace import WORKSPACE_ROOT

logger = logging.getLogger(__name__)

KEEP_WORKSPACE_ENV = "PEBBLE_KEEP_WORKSPACE"
SCRATCH_FOLDERS = ("media", "scenes", "audio", "muxed", "frames", "render_logs")
KEPT_FILES = (
    "animation.py",
    "generation.json",
    "result.json",
    "metadata.json",
    "pipeline.log",
)
MAX_ERROR_CHARS = 300
MAX_PIPELINE_LOG_BYTES = 512 * 1024


def sanitize_error(message: str) -> str:
    """Strip secret values and trim a failure message for the API."""
    cleaned = " ".join((message or "").split())
    for secret in secret_values():
        if secret:
            cleaned = cleaned.replace(secret, "***")
    if len(cleaned) > MAX_ERROR_CHARS:
        cleaned = cleaned[: MAX_ERROR_CHARS - 3] + "..."
    return cleaned or "job failed"


class Worker:
    """Drains the job store in a single background thread."""

    def __init__(
        self,
        store: JobStore,
        storage: BlobStorage,
        settings: Settings | None = None,
        env_info: EnvInfo | None = None,
        poll_interval: float = 1.0,
        runner: Callable[..., Any] | None = None,
        workspace_root: Path | None = None,
    ) -> None:
        self.store = store
        self.storage = storage
        self._settings = settings
        self._env_info = env_info
        self.poll_interval = poll_interval
        self._runner = runner or pipeline_module.run_pipeline
        self.workspace_root = Path(workspace_root or WORKSPACE_ROOT)
        self._thread: threading.Thread | None = None
        self._stop = threading.Event()
        self._wake = threading.Event()

    # -- lifecycle -------------------------------------------------------

    @property
    def settings(self) -> Settings:
        if self._settings is None:
            self._settings = load_settings()
        return self._settings

    @property
    def env_info(self) -> EnvInfo:
        if self._env_info is None:
            self._env_info = detect()
        return self._env_info

    @property
    def running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def start(self) -> None:
        if self.running:
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="pebble-worker", daemon=True)
        self._thread.start()
        logger.info("worker started")

    def stop(self, timeout: float = 10.0) -> None:
        self._stop.set()
        self._wake.set()
        thread = self._thread
        if thread is not None and thread.is_alive():
            thread.join(timeout=timeout)
        self._thread = None
        logger.info("worker stopped")

    def notify(self) -> None:
        """Wake the loop early after a new job is queued."""
        self._wake.set()

    def _loop(self) -> None:
        while not self._stop.is_set():
            job = None
            try:
                job = self.store.next_queued()
            except Exception as exc:  # pragma: no cover - defensive
                logger.error("could not read the job queue: %s", sanitize_error(str(exc)))
            if job is None:
                self._wake.wait(self.poll_interval)
                self._wake.clear()
                continue
            try:
                self.process(job["job_id"])
            except Exception as exc:  # pragma: no cover - process handles its own errors
                logger.error("worker crashed on %s: %s", job["job_id"], sanitize_error(str(exc)))

    # -- one job ---------------------------------------------------------

    def process(self, job_id: str) -> dict[str, Any] | None:
        """Run one job to completion or failure; never raises."""
        job = self.store.get(job_id)
        if job is None or job["status"] in (STATUS_COMPLETED, STATUS_FAILED):
            return job

        # Claiming in one statement means a job cancelled a moment ago can never
        # start, and two runs of the worker can never take the same job.
        claimed = self.store.claim(job_id)
        if claimed is None:
            logger.info("[%s] not claimed: cancelled or already finished", job_id)
            return self.store.get(job_id)
        job = claimed

        fingerprint = job["fingerprint"]
        payload = dict(job.get("payload") or {})
        # A forced job runs the pipeline even when its fingerprint is stored.
        forced = bool(payload.pop(FORCE_PAYLOAD_KEY, False))
        logger.info(
            "[%s] processing (fingerprint %s%s)",
            job_id,
            fingerprint[:12],
            ", forced" if forced else "",
        )

        try:
            cached = None if forced else self.storage.get_cached_result(fingerprint)
            if cached is not None:
                logger.info("[%s] cache hit: no pipeline run needed", job_id)
                return self.store.set_status(
                    job_id,
                    STATUS_COMPLETED,
                    stage="done",
                    video_url=cached.get("video_url"),
                    solution=cached.get("solution"),
                )

            result = self._runner(
                payload,
                job_id=job_id,
                on_status=lambda stage: self.store.set_stage(job_id, stage),
                settings=self.settings,
                env_info=self.env_info,
            )
            return self._finish(job, fingerprint, result)
        except Exception as exc:  # noqa: BLE001 - every failure is reported, not raised
            return self._fail(job, exc)

    def _finish(self, job: dict[str, Any], fingerprint: str, result: Any) -> dict[str, Any]:
        job_id = job["job_id"]
        self.store.set_stage(job_id, "uploading")

        root = Path(getattr(result, "workspace", self.workspace_root / job_id))
        solution = {
            "code": result.solution_code,
            "programming_language": result.programming_language,
        }
        metadata = _read_json(root / "metadata.json")
        video_path = Path(result.final_video)
        video_url = self.storage.public_url(self.storage.video_key(fingerprint))
        result_doc = {
            "video_url": video_url,
            "solution": solution,
            "created_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "duration_seconds": round(float(result.duration_seconds), 2),
        }

        self.storage.upload_job_bundle(fingerprint, video_path, metadata, result_doc)
        logger.info("[%s] uploaded: %s", job_id, video_url)

        updated = self.store.set_status(
            job_id, STATUS_COMPLETED, stage="done", video_url=video_url, solution=solution
        )
        logger.info(
            "[%s] completed in %.1fs of video", job_id, float(result.duration_seconds)
        )
        self.cleanup(job_id)
        return updated

    def _fail(self, job: dict[str, Any], exc: Exception) -> dict[str, Any]:
        job_id = job["job_id"]
        message = sanitize_error(f"{type(exc).__name__}: {exc}")
        self._append_pipeline_log(job_id, traceback.format_exc())
        logger.error("[%s] failed: %s", job_id, message)
        logger.info("workspace kept for debugging: %s", self.workspace_root / job_id)
        return self.store.set_status(
            job_id, STATUS_FAILED, stage=None, error=message
        )

    def _append_pipeline_log(self, job_id: str, text: str) -> None:
        path = self.workspace_root / job_id / "pipeline.log"
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with path.open("a", encoding="utf-8") as handle:
                handle.write("\n--- worker traceback ---\n" + (text or "") + "\n")
        except OSError:  # pragma: no cover - logging must never break a job
            logger.debug("could not append the traceback to %s", path)

    # -- cleanup ---------------------------------------------------------

    def cleanup(self, job_id: str) -> list[str]:
        """Delete the heavy scratch folders after a successful upload."""
        if _keep_workspace():
            logger.info("keeping the full workspace for %s (%s)", job_id, KEEP_WORKSPACE_ENV)
            return []
        root = self.workspace_root / job_id
        removed: list[str] = []
        for name in SCRATCH_FOLDERS:
            folder = root / name
            if not folder.exists():
                continue
            shutil.rmtree(folder, ignore_errors=True)
            removed.append(name)
        if removed:
            logger.info("cleaned scratch folders for %s: %s", job_id, ", ".join(removed))
        return removed


TRUE_VALUES = {"1", "true", "yes", "on"}


def _keep_workspace() -> bool:
    return (os.environ.get(KEEP_WORKSPACE_ENV) or "").strip().lower() in TRUE_VALUES


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
