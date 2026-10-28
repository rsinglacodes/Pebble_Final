"""Small HTTP API: submit a request, poll it, read the video URL.

The worker runs in a background thread, so a request returns immediately with a
job id. A job whose fingerprint is already in blob storage is answered from the
cache instead of spending LLM, speech and render time.

Set ``PEBBLE_API_KEY`` to require ``X-API-Key`` on every route except ``/`` and
``/health`` (which stay open for probes). Without it the API logs a warning and
accepts any caller — fine on a laptop, not on the internet.

Every error is JSON in the shape ``{"detail": "..."}``.
"""

from __future__ import annotations

import hmac
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from pebble.config import (
    AZURE_SPEECH_VOICE_KEY,
    Settings,
    is_supported_language,
    load_settings,
    supported_languages,
)
from pebble.environment import EnvInfo, detect
from pebble.errors import ConfigError
from pebble.jobs import (
    FORCE_PAYLOAD_KEY,
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUSES,
    JobStore,
)
from pebble.models import VideoRequest
from pebble.storage import BlobStorage, storage_configured
from pebble.styles import DEFAULT_STYLE, is_supported_style, supported_styles
from pebble.worker import Worker
from pebble.workspace import WORKSPACE_ROOT

logger = logging.getLogger(__name__)

API_KEY_ENV = "PEBBLE_API_KEY"
API_KEY_HEADER = "X-API-Key"

SERVICE_NAME = "Pebble"
LIST_LIMIT_DEFAULT = 20


@dataclass
class Runtime:
    """Everything the API needs, injectable for tests."""

    store: JobStore
    storage: BlobStorage
    worker: Worker
    settings: Settings
    env_info: EnvInfo


_runtime: Runtime | None = None


def build_runtime(store: JobStore | None = None, storage: BlobStorage | None = None) -> Runtime:
    settings = load_settings()
    job_store = store or JobStore()
    job_store.init()
    blob = storage or BlobStorage.from_env()
    worker = Worker(job_store, blob, settings=settings)
    return Runtime(
        store=job_store,
        storage=blob,
        worker=worker,
        settings=settings,
        env_info=detect(),
    )


def set_runtime(runtime: Runtime | None) -> None:
    """Install a runtime (tests) or clear it so the next call rebuilds it."""
    global _runtime
    _runtime = runtime


def get_runtime() -> Runtime:
    global _runtime
    if _runtime is None:
        _runtime = build_runtime()
    return _runtime


def configured_api_key() -> str | None:
    value = os.environ.get(API_KEY_ENV)
    return value.strip() if value and value.strip() else None


def require_api_key(x_api_key: str | None = Header(default=None, alias=API_KEY_HEADER)) -> None:
    """Reject callers without the configured key (constant-time compare)."""
    expected = configured_api_key()
    if expected is None:
        return
    provided = x_api_key or ""
    if not hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8")):
        raise HTTPException(status_code=401, detail="invalid or missing API key")


def _job_response(job: dict[str, Any]) -> dict[str, Any]:
    completed = job["status"] == STATUS_COMPLETED
    failed = job["status"] == STATUS_FAILED
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "stage": job["stage"],
        "video_url": job.get("video_url") if completed else None,
        "solution": job.get("solution") if completed else None,
        "error": job.get("error") if failed else None,
    }


def validate_preferences(request: VideoRequest) -> None:
    """Reject an unsupported language or style early, with the valid values.

    Empty or missing preferences are fine: they default to English and
    ``beginner_friendly``. When ``AZURE_SPEECH_VOICE`` is set the voice is fixed
    for every language, so any language is accepted.
    """
    preferences = request.preferences_or_default
    language = preferences.language
    if not is_supported_language(language):
        raise HTTPException(
            status_code=422,
            detail=(
                f"unsupported explanation_language {language!r}: valid values are "
                f"{', '.join(supported_languages())} "
                f"(or set {AZURE_SPEECH_VOICE_KEY} to accept any language)"
            ),
        )
    style = (preferences.explanation_style or "").strip() or DEFAULT_STYLE
    if not is_supported_style(style):
        raise HTTPException(
            status_code=422,
            detail=(
                f"unsupported explanation_style {preferences.explanation_style!r}: "
                f"valid values are {', '.join(supported_styles())}"
            ),
        )


def _workspace_root(runtime: "Runtime") -> Path:
    """Where job workspaces live (the worker's root, so tests can redirect it)."""
    return Path(getattr(runtime.worker, "workspace_root", None) or WORKSPACE_ROOT)


def _read_json_file(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return data if isinstance(data, dict) else None


def _job_metadata(runtime: "Runtime", job: dict[str, Any]) -> dict[str, Any]:
    """The job's metadata.json: the local workspace copy first, then the blob."""
    local = _read_json_file(_workspace_root(runtime) / job["job_id"] / "metadata.json")
    if local is not None:
        return local
    key_for = getattr(runtime.storage, "metadata_key", None)
    download = getattr(runtime.storage, "download_text", None)
    if key_for is None or download is None:  # pragma: no cover - fakes without blobs
        return {}
    try:
        text = download(key_for(job["fingerprint"]))
    except Exception as exc:  # noqa: BLE001 - details are best effort
        logger.warning("could not read the metadata blob (%s)", type(exc).__name__)
        return {}
    if not text:
        return {}
    try:
        document = json.loads(text)
    except ValueError:
        return {}
    return document if isinstance(document, dict) else {}


def _job_result(runtime: "Runtime", job: dict[str, Any]) -> dict[str, Any]:
    """The job's result.json (local first): it carries the finished duration."""
    local = _read_json_file(_workspace_root(runtime) / job["job_id"] / "result.json")
    if local is not None:
        return local
    try:
        return runtime.storage.get_cached_result(job["fingerprint"]) or {}
    except Exception as exc:  # noqa: BLE001 - details are best effort
        logger.warning("could not read the result blob (%s)", type(exc).__name__)
        return {}


def details_document(runtime: "Runtime", job: dict[str, Any]) -> dict[str, Any]:
    """The teaching metadata of a finished job. Never cost data, never secrets."""
    meta = _job_metadata(runtime, job)
    result = _job_result(runtime, job)
    validation = meta.get("validation") or {}
    complexity = meta.get("complexity") or {}
    scenes = meta.get("scenes") or []
    duration = result.get("duration_seconds")
    return {
        "job_id": job["job_id"],
        "validation": {
            "performed": validation.get("performed"),
            "is_correct": validation.get("is_correct"),
            "issues": [str(item) for item in (validation.get("issues") or [])],
        },
        "solution_source": meta.get("solution_source") or None,
        "problem_summary": meta.get("problem_summary") or None,
        "complexity": {
            "time": complexity.get("time") or None,
            "space": complexity.get("space") or None,
        },
        "duration_seconds": (
            round(float(duration), 2) if isinstance(duration, (int, float)) else None
        ),
        "scene_count": len(scenes) if scenes else None,
    }


def job_title(job: dict[str, Any]) -> str:
    """A short human label for a job list: the question title, else its slug."""
    payload = job.get("payload") or {}
    question = payload.get("question") or {}
    return str(question.get("title") or question.get("slug") or "").strip()


def _list_entry(job: dict[str, Any]) -> dict[str, Any]:
    return {
        "job_id": job["job_id"],
        "status": job["status"],
        "stage": job["stage"],
        "title": job_title(job),
        "created_at": job["created_at"],
        "updated_at": job["updated_at"],
    }


def _blob_check(storage: Any) -> str:
    """Container reachable? Never uploads anything."""
    ready = getattr(storage, "ready", None)
    if ready is None:  # pragma: no cover - fakes without a container
        return "ok"
    try:
        ok, detail = ready()
    except ConfigError as exc:
        return str(exc)
    except Exception as exc:  # noqa: BLE001 - a short reason is the whole point
        return f"container check failed ({type(exc).__name__})"
    return "ok" if ok else str(detail)


def deep_checks(runtime: "Runtime") -> dict[str, str]:
    """Local readiness only: no LLM call, no speech call."""
    env = runtime.env_info
    settings = runtime.settings
    missing = settings.missing_required_names
    return {
        "blob": _blob_check(runtime.storage),
        "ffmpeg": "ok" if env.ffmpeg_available else "ffmpeg is not on PATH",
        "ffprobe": "ok" if env.ffprobe_available else "ffprobe is not on PATH",
        "manim": "ok" if env.manim_available else f"manim import failed ({env.manim_version})",
        "env": "ok" if not missing else "missing: " + ", ".join(missing),
    }


def create_app() -> FastAPI:
    app = FastAPI(title=SERVICE_NAME, version="1.0", docs_url="/docs")

    @app.exception_handler(RequestValidationError)
    def invalid_body(request: Request, exc: RequestValidationError) -> JSONResponse:
        """One readable ``detail`` string instead of pydantic's error list."""
        problems: list[str] = []
        for error in exc.errors():
            parts = [str(part) for part in error.get("loc", ()) if part != "body"]
            where = ".".join(parts)
            message = str(error.get("msg") or "invalid value")
            problems.append(f"{where}: {message}" if where else message)
        return JSONResponse(
            status_code=422,
            content={"detail": "; ".join(problems) or "invalid request body"},
        )

    @app.get("/")
    def root() -> dict[str, Any]:
        return {"service": SERVICE_NAME, "docs": "/docs", "health": "/health"}

    @app.get("/health")
    def health() -> dict[str, Any]:
        runtime = get_runtime()
        return {
            "status": "ok",
            "queue_depth": runtime.store.queue_depth(),
            "processing": runtime.store.processing_job(),
        }

    @app.get("/health/deep", dependencies=[Depends(require_api_key)])
    def health_deep() -> dict[str, Any]:
        runtime = get_runtime()
        checks = deep_checks(runtime)
        failing = [name for name, value in checks.items() if value != "ok"]
        return {"status": "degraded" if failing else "ok", "checks": checks}

    @app.get("/options", dependencies=[Depends(require_api_key)])
    def options() -> dict[str, Any]:
        return {
            "explanation_styles": supported_styles(),
            "explanation_languages": supported_languages(),
        }

    @app.post("/generate-video", dependencies=[Depends(require_api_key)])
    def generate_video(
        request: VideoRequest, force: bool = Query(default=False)
    ) -> dict[str, Any]:
        validate_preferences(request)
        try:
            runtime = get_runtime()
        except ConfigError as exc:
            raise HTTPException(status_code=503, detail=str(exc)) from exc

        fingerprint = request.request_fingerprint()
        payload = request.model_dump()

        if force:
            # Skip both the in-flight dedupe and the blob cache and run the
            # whole pipeline again, overwriting the stored blobs.
            payload[FORCE_PAYLOAD_KEY] = True
            job = runtime.store.create(fingerprint, payload)
            logger.info(
                "queued %s for %s with force=true: dedupe and cache skipped",
                job["job_id"],
                fingerprint[:12],
            )
            runtime.worker.notify()
            return {"job_id": job["job_id"], "status": job["status"]}

        active = runtime.store.find_active(fingerprint)
        if active is not None:
            logger.info(
                "request for %s already %s as %s",
                fingerprint[:12],
                active["status"],
                active["job_id"],
            )
            return {"job_id": active["job_id"], "status": active["status"]}

        cached = _cached_result(runtime, fingerprint)
        if cached is not None:
            logger.info("cache hit for %s: no pipeline run", fingerprint[:12])
            existing = runtime.store.find_completed(fingerprint)
            if existing is not None and existing.get("video_url"):
                # Same request answered before: reuse the job row, no new one.
                return {"job_id": existing["job_id"], "status": existing["status"]}
            job = runtime.store.create(
                fingerprint,
                payload,
                status=STATUS_COMPLETED,
                stage="done",
                video_url=cached.get("video_url"),
                solution=cached.get("solution"),
            )
            return {"job_id": job["job_id"], "status": job["status"]}

        job = runtime.store.create(fingerprint, payload)
        logger.info("queued %s (fingerprint %s)", job["job_id"], fingerprint[:12])
        runtime.worker.notify()
        return {"job_id": job["job_id"], "status": job["status"]}

    @app.get("/video-status/{job_id}", dependencies=[Depends(require_api_key)])
    def video_status(job_id: str) -> dict[str, Any]:
        runtime = get_runtime()
        job = runtime.store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        return _job_response(job)

    @app.get("/video-status/{job_id}/details", dependencies=[Depends(require_api_key)])
    def video_details(job_id: str) -> dict[str, Any]:
        runtime = get_runtime()
        job = runtime.store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        if job["status"] != STATUS_COMPLETED:
            raise HTTPException(status_code=409, detail="job not finished")
        return details_document(runtime, job)

    @app.post("/jobs/{job_id}/cancel", dependencies=[Depends(require_api_key)])
    def cancel_job(job_id: str) -> dict[str, Any]:
        runtime = get_runtime()
        job = runtime.store.get(job_id)
        if job is None:
            raise HTTPException(status_code=404, detail="job not found")
        cancelled = runtime.store.cancel(job_id)
        if cancelled is None:
            raise HTTPException(
                status_code=409, detail="job already running or finished"
            )
        logger.info("cancelled %s before it started", job_id)
        return _job_response(cancelled)

    @app.get("/jobs", dependencies=[Depends(require_api_key)])
    def list_jobs(
        status: str | None = Query(default=None),
        limit: int = Query(default=LIST_LIMIT_DEFAULT, ge=1, le=100),
    ) -> list[dict[str, Any]]:
        runtime = get_runtime()
        wanted = (status or "").strip()
        if wanted and wanted not in STATUSES:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"unknown status {wanted!r}: valid values are "
                    f"{', '.join(STATUSES)}"
                ),
            )
        return [
            _list_entry(job)
            for job in runtime.store.list_jobs(status=wanted or None, limit=limit)
        ]

    return app


def _cached_result(runtime: Runtime, fingerprint: str) -> dict[str, Any] | None:
    """Cache lookups must never take the API down if blob storage hiccups."""
    try:
        return runtime.storage.get_cached_result(fingerprint)
    except Exception as exc:  # noqa: BLE001 - a cache miss is not an error
        logger.warning("blob cache lookup failed (%s); running the pipeline", type(exc).__name__)
        return None


def startup_warnings() -> list[str]:
    """Human-readable notes printed by run_server.py at startup."""
    notes: list[str] = []
    if configured_api_key() is None:
        notes.append(
            f"{API_KEY_ENV} is not set: every endpoint is open (local development only)"
        )
    if not storage_configured():
        notes.append("blob storage is not configured: uploads will fail")
    return notes


app = create_app()


def _json_error(message: str) -> JSONResponse:  # pragma: no cover - helper for scripts
    return JSONResponse(status_code=503, content={"detail": message})
