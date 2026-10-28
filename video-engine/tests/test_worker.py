"""Worker: cache hits, uploads, cleanup and failure handling (no network)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from pebble.jobs import FORCE_PAYLOAD_KEY, STATUS_COMPLETED, STATUS_FAILED, JobStore
from pebble.worker import Worker, sanitize_error


@dataclass
class FakePipelineResult:
    job_id: str
    workspace: Path
    final_video: Path
    duration_seconds: float
    solution_code: str = "class Solution:\n    pass\n"
    programming_language: str = "python"

    @property
    def scene_count(self) -> int:
        return 2


class FakeStorage:
    """In-memory stand-in for BlobStorage."""

    def __init__(self, cached: dict | None = None, metadata: dict | None = None) -> None:
        self.cached = cached
        self.metadata = metadata
        self.uploads: list[tuple[str, Path, dict | None, dict]] = []
        self.cache_lookups: list[str] = []
        self.downloads: list[str] = []
        self.fail_upload = False
        self.ready_result: tuple[bool, str] = (True, "container 'videos' reachable")

    def get_cached_result(self, fingerprint: str):
        self.cache_lookups.append(fingerprint)
        return self.cached

    def video_key(self, fingerprint: str) -> str:
        return f"videos/{fingerprint}/final.mp4"

    def metadata_key(self, fingerprint: str) -> str:
        return f"videos/{fingerprint}/metadata.json"

    def download_text(self, key: str) -> str | None:
        self.downloads.append(key)
        return json.dumps(self.metadata) if self.metadata is not None else None

    def ready(self) -> tuple[bool, str]:
        return self.ready_result

    def public_url(self, key: str) -> str:
        return f"https://acct.blob.core.windows.net/videos/{key}"

    def upload_job_bundle(self, fingerprint, video_path, metadata, result):
        if self.fail_upload:
            raise OSError("upload exploded")
        self.uploads.append((fingerprint, Path(video_path), metadata, result))
        return result["video_url"]


def _store(tmp_path) -> JobStore:
    store = JobStore(tmp_path / "jobs.db")
    store.init()
    return store


def _workspace(root: Path, job_id: str) -> Path:
    """A finished job workspace with the heavy scratch folders in place."""
    path = root / job_id
    for name in ("media", "scenes", "audio", "muxed", "frames", "render_logs"):
        (path / name).mkdir(parents=True, exist_ok=True)
        (path / name / "junk.bin").write_bytes(b"x" * 32)
    for name in ("animation.py", "generation.json", "result.json", "metadata.json"):
        (path / name).write_text("{}" if name.endswith(".json") else "pass\n", encoding="utf-8")
    (path / "final.mp4").write_bytes(b"\x00" * 64)
    (path / "pipeline.log").write_text("log\n", encoding="utf-8")
    (path / "metadata.json").write_text(json.dumps({"scenes": []}), encoding="utf-8")
    return path


def _worker(tmp_path, store, storage, runner, keep=None, monkeypatch=None):
    if monkeypatch is not None:
        if keep is None:
            monkeypatch.delenv("PEBBLE_KEEP_WORKSPACE", raising=False)
        else:
            monkeypatch.setenv("PEBBLE_KEEP_WORKSPACE", keep)
    return Worker(
        store,
        storage,
        runner=runner,
        workspace_root=tmp_path / "workspace",
        poll_interval=0.01,
    )


def test_cache_hit_completes_without_running_the_pipeline(tmp_path, monkeypatch):
    store = _store(tmp_path)
    job = store.create("fp-cached", {})
    storage = FakeStorage(
        cached={
            "video_url": "https://acct.blob.core.windows.net/videos/videos/fp-cached/final.mp4",
            "solution": {"code": "print(1)", "programming_language": "python"},
        }
    )

    def runner(*args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("the pipeline must not run on a cache hit")

    worker = _worker(tmp_path, store, storage, runner, monkeypatch=monkeypatch)
    worker.process("job_missing")
    result = worker.process(job["job_id"])

    assert result["status"] == STATUS_COMPLETED
    assert result["stage"] == "done"
    assert result["solution"]["code"] == "print(1)"
    assert storage.cache_lookups == ["fp-cached"]


def test_successful_run_uploads_and_cleans_up(tmp_path, monkeypatch):
    store = _store(tmp_path)
    job = store.create("fp1", {"question": {"id": 1}})
    storage = FakeStorage()
    workspace = _workspace(tmp_path / "workspace", job["job_id"])
    stages: list[str] = []

    def runner(payload, job_id=None, on_status=None, settings=None, env_info=None):
        assert payload == {"question": {"id": 1}}
        for stage in ("generating", "narrating", "rendering", "assembling", "done"):
            stages.append(stage)
            on_status(stage)
        return FakePipelineResult(
            job_id=job_id,
            workspace=workspace,
            final_video=workspace / "final.mp4",
            duration_seconds=42.5,
        )

    worker = _worker(tmp_path, store, storage, runner, monkeypatch=monkeypatch)
    updated = worker.process(job["job_id"])

    assert stages == ["generating", "narrating", "rendering", "assembling", "done"]
    assert updated["status"] == STATUS_COMPLETED
    assert updated["stage"] == "done"
    assert updated["video_url"].endswith("/videos/fp1/final.mp4")
    assert updated["solution"]["programming_language"] == "python"

    fingerprint, video, metadata, result_doc = storage.uploads[0]
    assert fingerprint == "fp1"
    assert video.name == "final.mp4"
    assert metadata == {"scenes": []}
    assert result_doc["duration_seconds"] == 42.5
    assert result_doc["solution"]["code"].startswith("class Solution")

    # Heavy scratch folders are gone; the small artefacts and log remain.
    for name in ("media", "scenes", "audio", "muxed", "frames", "render_logs"):
        assert not (workspace / name).exists(), name
    for name in ("animation.py", "generation.json", "result.json", "metadata.json"):
        assert (workspace / name).exists(), name
    assert (workspace / "pipeline.log").exists()
    assert (workspace / "final.mp4").exists()


def test_keep_workspace_env_disables_cleanup(tmp_path, monkeypatch):
    store = _store(tmp_path)
    job = store.create("fp1", {})
    storage = FakeStorage()
    workspace = _workspace(tmp_path / "workspace", job["job_id"])

    def runner(payload, job_id=None, on_status=None, settings=None, env_info=None):
        return FakePipelineResult(job_id, workspace, workspace / "final.mp4", 10.0)

    worker = _worker(tmp_path, store, storage, runner, keep="1", monkeypatch=monkeypatch)
    worker.process(job["job_id"])

    assert (workspace / "media").exists()
    assert (workspace / "render_logs").exists()


def test_upload_failure_keeps_the_video_and_fails_the_job(tmp_path, monkeypatch):
    store = _store(tmp_path)
    job = store.create("fp1", {})
    storage = FakeStorage()
    storage.fail_upload = True
    workspace = _workspace(tmp_path / "workspace", job["job_id"])

    def runner(payload, job_id=None, on_status=None, settings=None, env_info=None):
        return FakePipelineResult(job_id, workspace, workspace / "final.mp4", 12.0)

    worker = _worker(tmp_path, store, storage, runner, monkeypatch=monkeypatch)
    updated = worker.process(job["job_id"])

    assert updated["status"] == STATUS_FAILED
    assert "upload exploded" in updated["error"]
    assert updated["video_url"] is None
    assert (workspace / "final.mp4").exists()
    assert (workspace / "media").exists(), "a failed upload must not clean up"
    log = (workspace / "pipeline.log").read_text(encoding="utf-8")
    assert "worker traceback" in log


def test_pipeline_failure_is_sanitized(tmp_path, monkeypatch):
    monkeypatch.setenv("AZURE_SPEECH_KEY", "super-secret-value-123")
    store = _store(tmp_path)
    job = store.create("fp1", {})

    def runner(payload, job_id=None, on_status=None, settings=None, env_info=None):
        on_status("rendering")
        raise RuntimeError("boom with super-secret-value-123 inside")

    worker = _worker(tmp_path, store, FakeStorage(), runner, monkeypatch=monkeypatch)
    updated = worker.process(job["job_id"])

    assert updated["status"] == STATUS_FAILED
    assert "super-secret-value-123" not in updated["error"]
    assert "***" in updated["error"]
    assert updated["stage"] is None


def test_sanitize_error_trims_long_messages(monkeypatch):
    monkeypatch.delenv("AZURE_API_KEY", raising=False)
    long = "x" * 900
    cleaned = sanitize_error(long)
    assert len(cleaned) <= 300
    assert cleaned.endswith("...")
    assert sanitize_error("") == "job failed"


def test_completed_jobs_are_not_rerun(tmp_path, monkeypatch):
    store = _store(tmp_path)
    job = store.create("fp1", {})
    store.set_status(job["job_id"], STATUS_COMPLETED, stage="done", video_url="u")

    def runner(*args, **kwargs):  # pragma: no cover
        raise AssertionError("a completed job must not run again")

    worker = _worker(tmp_path, store, FakeStorage(), runner, monkeypatch=monkeypatch)
    assert worker.process(job["job_id"])["status"] == STATUS_COMPLETED


def test_a_forced_job_ignores_the_blob_cache(tmp_path, monkeypatch):
    store = _store(tmp_path)
    job = store.create("fp1", {FORCE_PAYLOAD_KEY: True, "question": {"id": 1}})
    storage = FakeStorage(
        cached={"video_url": "https://acct/stale.mp4", "solution": {"code": "old"}}
    )
    workspace = _workspace(tmp_path / "workspace", job["job_id"])
    seen: list[dict] = []

    def runner(payload, job_id=None, on_status=None, settings=None, env_info=None):
        seen.append(payload)
        return FakePipelineResult(job_id, workspace, workspace / "final.mp4", 20.0)

    worker = _worker(tmp_path, store, storage, runner, monkeypatch=monkeypatch)
    updated = worker.process(job["job_id"])

    assert storage.cache_lookups == [], "force=true must not consult the cache"
    assert seen == [{"question": {"id": 1}}], "the force marker is stripped"
    assert updated["status"] == STATUS_COMPLETED
    assert updated["video_url"].endswith("/videos/fp1/final.mp4")


def test_a_cancelled_job_never_runs(tmp_path, monkeypatch):
    store = _store(tmp_path)
    job = store.create("fp1", {})
    assert store.cancel(job["job_id"])["error"] == "cancelled by request"

    def runner(*args, **kwargs):  # pragma: no cover - must not run
        raise AssertionError("a cancelled job must never run")

    worker = _worker(tmp_path, store, FakeStorage(), runner, monkeypatch=monkeypatch)
    result = worker.process(job["job_id"])

    assert result["status"] == STATUS_FAILED
    assert result["error"] == "cancelled by request"
    assert result["video_url"] is None


def test_the_thread_drains_a_queued_job(tmp_path, monkeypatch):
    store = _store(tmp_path)
    job = store.create("fp1", {})
    storage = FakeStorage()
    workspace = _workspace(tmp_path / "workspace", job["job_id"])
    seen: list[str] = []

    def runner(payload, job_id=None, on_status=None, settings=None, env_info=None):
        seen.append(job_id)
        return FakePipelineResult(job_id, workspace, workspace / "final.mp4", 5.0)

    worker = _worker(tmp_path, store, storage, runner, monkeypatch=monkeypatch)
    worker.start()
    try:
        worker.notify()
        for _ in range(200):
            if store.get(job["job_id"])["status"] == STATUS_COMPLETED:
                break
            import time

            time.sleep(0.05)
    finally:
        worker.stop()

    assert seen == [job["job_id"]]
    assert store.get(job["job_id"])["status"] == STATUS_COMPLETED
    assert not worker.running
