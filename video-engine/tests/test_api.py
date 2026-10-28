"""API: submission, polling, cache hits, auth and error mapping (no network)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from pebble import api
from pebble.config import Settings
from pebble.environment import EnvInfo
from pebble.jobs import FORCE_PAYLOAD_KEY, STATUS_COMPLETED, STATUS_FAILED, JobStore
from pebble.styles import STYLES
from tests.conftest import load_sample
from tests.test_worker import FakePipelineResult, FakeStorage, _workspace

ENV = EnvInfo(
    manim_version="0.22.0",
    latex_available=False,
    ffmpeg_available=True,
    ffprobe_available=True,
    code_font="Menlo",
)


REQUIRED_ENV_NAMES = (
    "AZURE_OPENAI_ENDPOINT",
    "AZURE_API_KEY",
    "AZURE_OPENAI_API_KEY",
    "AZURE_OPENAI_DEPLOYMENT",
    "AZURE_OPENAI_API_VERSION",
    "AZURE_SPEECH_KEY",
    "AZURE_SPEECH_REGION",
)


class FakeWorker:
    def __init__(self) -> None:
        self.notified = 0
        self.started = False

    def notify(self) -> None:
        self.notified += 1

    def start(self) -> None:
        self.started = True

    def stop(self, timeout: float = 10.0) -> None:
        self.started = False


@pytest.fixture
def runtime(tmp_path, monkeypatch):
    monkeypatch.delenv("PEBBLE_API_KEY", raising=False)
    store = JobStore(tmp_path / "jobs.db")
    store.init()
    storage = FakeStorage()
    rt = api.Runtime(
        store=store,
        storage=storage,
        worker=FakeWorker(),
        settings=Settings(),
        env_info=ENV,
    )
    api.set_runtime(rt)
    yield rt
    api.set_runtime(None)


@pytest.fixture
def client(runtime) -> TestClient:
    return TestClient(api.app)


def _payload(**changes) -> dict:
    payload = json.loads(
        (Path(__file__).resolve().parent.parent / "samples" / "two_sum_concise.json").read_text(
            encoding="utf-8"
        )
    )
    payload.update(changes)
    return payload


def test_post_creates_a_queued_job_and_wakes_the_worker(client, runtime):
    response = client.post("/generate-video", json=_payload())

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "queued"
    assert body["job_id"].startswith("job_")
    assert runtime.worker.notified == 1
    assert runtime.store.queue_depth() == 1


def test_post_returns_422_for_an_invalid_body(client):
    response = client.post("/generate-video", json={"question": "not an object"})
    assert response.status_code == 422

    response = client.post("/generate-video", json={"preferences": {"explanation_language": 5}})
    assert response.status_code == 422


def test_post_dedupes_an_active_job(client, runtime):
    first = client.post("/generate-video", json=_payload()).json()
    second = client.post("/generate-video", json=_payload()).json()

    assert second["job_id"] == first["job_id"]
    assert second["status"] == "queued"
    assert runtime.store.queue_depth() == 1


def test_post_completes_immediately_on_a_cache_hit(client, runtime):
    request = load_sample("two_sum_concise.json")
    runtime.storage.cached = {
        "video_url": "https://acct.blob.core.windows.net/videos/videos/fp/final.mp4",
        "solution": {"code": "print(1)", "programming_language": "python"},
    }

    body = client.post("/generate-video", json=_payload()).json()

    assert body["status"] == STATUS_COMPLETED
    assert runtime.worker.notified == 0, "a cache hit must not queue pipeline work"
    stored = runtime.store.get(body["job_id"])
    assert stored["video_url"].endswith("/final.mp4")
    assert stored["solution"]["code"] == "print(1)"
    assert stored["stage"] == "done"
    assert runtime.store.queue_depth() == 0
    assert request.request_fingerprint() in runtime.storage.cache_lookups

    # A second identical POST reuses the finished job instead of piling up rows.
    again = client.post("/generate-video", json=_payload()).json()
    assert again == {"job_id": body["job_id"], "status": STATUS_COMPLETED}


def test_status_polls_from_queued_to_completed(client, runtime):
    job_id = client.post("/generate-video", json=_payload()).json()["job_id"]

    first = client.get(f"/video-status/{job_id}").json()
    assert first["status"] == "queued"
    assert first["stage"] is None
    assert first["video_url"] is None
    assert first["solution"] is None
    assert first["error"] is None

    runtime.store.set_stage(job_id, "rendering")
    assert client.get(f"/video-status/{job_id}").json()["stage"] == "rendering"

    runtime.store.set_status(
        job_id,
        STATUS_COMPLETED,
        stage="done",
        video_url="https://acct.blob.core.windows.net/videos/videos/fp/final.mp4",
        solution={"code": "print(1)", "programming_language": "python"},
    )
    done = client.get(f"/video-status/{job_id}").json()
    assert done["status"] == STATUS_COMPLETED
    assert done["video_url"].endswith("/final.mp4")
    assert done["solution"]["code"] == "print(1)"

    # A completed job never exposes an error, even if one was stored earlier.
    runtime.store.set_status(job_id, STATUS_COMPLETED, stage="done", error="stale")
    assert client.get(f"/video-status/{job_id}").json()["error"] is None


def test_status_reports_a_sanitized_failure(client, runtime):
    job_id = client.post("/generate-video", json=_payload()).json()["job_id"]
    runtime.store.set_status(job_id, STATUS_FAILED, stage=None, error="RenderError: scene 2")

    body = client.get(f"/video-status/{job_id}").json()
    assert body["status"] == STATUS_FAILED
    assert body["error"] == "RenderError: scene 2"
    assert body["video_url"] is None and body["solution"] is None


def test_unknown_job_is_404(client):
    response = client.get("/video-status/job_deadbeef")
    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}


def test_health_is_open_and_counts_the_queue(client, runtime):
    health = client.get("/health").json()
    assert health == {"status": "ok", "queue_depth": 0, "processing": None}

    job_id = client.post("/generate-video", json=_payload()).json()["job_id"]
    assert client.get("/health").json()["queue_depth"] == 1

    runtime.store.set_status(job_id, "processing", stage="generating")
    health = client.get("/health").json()
    assert health["processing"] == job_id
    assert health["queue_depth"] == 0


def test_api_key_protects_everything_but_health(runtime, monkeypatch):
    monkeypatch.setenv("PEBBLE_API_KEY", "s3cret-key")
    client = TestClient(api.app)

    assert client.get("/health").status_code == 200
    assert client.post("/generate-video", json=_payload()).status_code == 401
    assert client.get("/video-status/job_x").status_code == 401

    headers = {"X-API-Key": "s3cret-key"}
    assert client.post("/generate-video", json=_payload(), headers=headers).status_code == 200
    assert client.get("/video-status/job_x", headers=headers).status_code == 404

    wrong = {"X-API-Key": "s3cret-kez"}
    assert client.post("/generate-video", json=_payload(), headers=wrong).status_code == 401


def test_startup_warnings_mention_open_auth_and_storage(monkeypatch):
    monkeypatch.delenv("PEBBLE_API_KEY", raising=False)
    notes = api.startup_warnings()
    assert any("PEBBLE_API_KEY" in note for note in notes)


def test_cache_lookup_failure_still_queues_the_job(client, runtime):
    def explode(fingerprint):
        raise OSError("blob unavailable")

    runtime.storage.get_cached_result = explode  # type: ignore[assignment]
    body = client.post("/generate-video", json=_payload()).json()

    assert body["status"] == "queued"
    assert runtime.worker.notified == 1


def test_worker_finish_flow_through_the_api(tmp_path, runtime, monkeypatch):
    """A queued job completed by a real Worker surfaces through /video-status."""
    from pebble.worker import Worker

    runtime.storage = FakeStorage()
    runtime.worker = Worker(
        runtime.store,
        runtime.storage,
        runner=lambda *args, **kwargs: None,
        workspace_root=tmp_path / "workspace",
        poll_interval=0.01,
    )
    client = TestClient(api.app)
    job_id = client.post("/generate-video", json=_payload()).json()["job_id"]

    workspace = _workspace(tmp_path / "workspace", job_id)

    def runner(payload, job_id=None, on_status=None, settings=None, env_info=None):
        on_status("generating")
        workspace.mkdir(parents=True, exist_ok=True)
        (workspace / "metadata.json").write_text("{}\n", encoding="utf-8")
        (workspace / "final.mp4").write_bytes(b"\x00" * 8)
        return FakePipelineResult(job_id, workspace, workspace / "final.mp4", 30.0)

    runtime.worker._runner = runner
    runtime.worker.process(job_id)

    body = client.get(f"/video-status/{job_id}").json()
    assert body["status"] == STATUS_COMPLETED
    assert body["video_url"].endswith("/final.mp4")
    assert body["solution"]["code"].startswith("class Solution")


# ---------------------------------------------------------------------------
# Early validation (422) and force=true
# ---------------------------------------------------------------------------


def test_unsupported_language_is_rejected_before_any_work(client, runtime):
    response = client.post(
        "/generate-video",
        json=_payload(preferences={"explanation_language": "Klingon"}),
    )

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "Klingon" in detail
    assert "English" in detail and "Hindi" in detail
    assert runtime.store.queue_depth() == 0
    assert runtime.worker.notified == 0


def test_unsupported_style_is_rejected_before_any_work(client, runtime):
    response = client.post(
        "/generate-video",
        json=_payload(preferences={"explanation_style": "interpretive_dance"}),
    )

    assert response.status_code == 422
    assert "beginner_friendly" in response.json()["detail"]
    assert runtime.store.queue_depth() == 0


def test_preferences_are_case_insensitive_and_empty_defaults_are_accepted(client):
    assert (
        client.post(
            "/generate-video",
            json=_payload(preferences={"explanation_language": "english", "explanation_style": "Concise"}),
        ).status_code
        == 200
    )
    assert client.post("/generate-video", json=_payload(preferences={})).status_code == 200
    assert client.post("/generate-video", json=_payload(preferences=None)).status_code == 200


def test_a_fixed_speech_voice_accepts_any_language(client, monkeypatch):
    monkeypatch.setenv("AZURE_SPEECH_VOICE", "en-US-JennyNeural")

    response = client.post(
        "/generate-video",
        json=_payload(preferences={"explanation_language": "Klingon"}),
    )

    assert response.status_code == 200


def test_force_skips_dedupe_and_the_cache(client, runtime):
    runtime.storage.cached = {
        "video_url": "https://acct.blob.core.windows.net/videos/videos/fp/final.mp4",
        "solution": {"code": "old", "programming_language": "python"},
    }

    cached_hit = client.post("/generate-video", json=_payload()).json()
    assert cached_hit["status"] == STATUS_COMPLETED

    forced = client.post("/generate-video?force=true", json=_payload())
    assert forced.status_code == 200
    body = forced.json()
    assert body["status"] == "queued"
    assert body["job_id"] != cached_hit["job_id"]
    assert runtime.worker.notified == 1, "the pipeline must run again"
    assert runtime.store.get(body["job_id"])["status"] == "queued"

    # A forced job does not dedupe against the in-flight one either.
    second = client.post("/generate-video?force=true", json=_payload()).json()
    assert second["job_id"] != body["job_id"]
    assert runtime.store.queue_depth() == 2
    assert (
        runtime.store.get(body["job_id"])["payload"][FORCE_PAYLOAD_KEY] is True
    ), "the worker has to know the job is forced"


def test_force_false_is_the_default(client, runtime):
    first = client.post("/generate-video", json=_payload()).json()
    second = client.post("/generate-video?force=false", json=_payload()).json()
    assert second["job_id"] == first["job_id"]
    assert runtime.store.queue_depth() == 1


# ---------------------------------------------------------------------------
# Options, root and deep health
# ---------------------------------------------------------------------------


def test_root_points_at_the_docs(client):
    assert client.get("/").json() == {"service": "Pebble", "docs": "/docs", "health": "/health"}


def test_options_lists_the_supported_values(client):
    body = client.get("/options").json()

    assert body["explanation_styles"] == list(STYLES)
    assert body["explanation_languages"] == ["English", "French", "German", "Hindi", "Spanish"]


def test_health_deep_reports_every_check(client, monkeypatch):
    for name in REQUIRED_ENV_NAMES:
        monkeypatch.setenv(name, "placeholder")

    body = client.get("/health/deep").json()

    assert body["status"] == "ok"
    assert set(body["checks"]) == {"blob", "ffmpeg", "ffprobe", "manim", "env"}
    assert all(value == "ok" for value in body["checks"].values())


def test_health_deep_is_degraded_with_a_reason(client, runtime, monkeypatch):
    runtime.storage.ready_result = (False, "container 'videos' is not reachable")
    for name in REQUIRED_ENV_NAMES:
        monkeypatch.delenv(name, raising=False)

    body = client.get("/health/deep").json()

    assert body["status"] == "degraded"
    assert body["checks"]["blob"] == "container 'videos' is not reachable"
    assert body["checks"]["env"].startswith("missing: ")
    assert "AZURE_SPEECH_KEY" in body["checks"]["env"]


def test_health_deep_never_leaks_a_secret_value(client, monkeypatch):
    monkeypatch.setenv("AZURE_API_KEY", "super-secret-value-123")

    assert "super-secret-value-123" not in json.dumps(client.get("/health/deep").json())


# ---------------------------------------------------------------------------
# Job listing
# ---------------------------------------------------------------------------


def test_jobs_list_is_newest_first(client, runtime):
    first = client.post("/generate-video", json=_payload()).json()["job_id"]
    second = client.post(
        "/generate-video", json=_payload(question={"id": 2, "title": "Dijkstra"})
    ).json()["job_id"]

    entries = client.get("/jobs").json()

    assert [entry["job_id"] for entry in entries] == [second, first]
    assert entries[1]["title"] == "Two Sum"
    assert entries[1]["status"] == "queued"
    assert entries[1]["stage"] is None
    assert entries[1]["created_at"] and entries[1]["updated_at"]
    assert set(entries[1]) == {
        "job_id",
        "status",
        "stage",
        "title",
        "created_at",
        "updated_at",
    }


def test_jobs_list_filters_by_status_and_caps_the_limit(client, runtime):
    job_id = client.post("/generate-video", json=_payload()).json()["job_id"]
    runtime.store.set_status(job_id, STATUS_COMPLETED, stage="done", video_url="u")

    assert [e["job_id"] for e in client.get("/jobs?status=completed").json()] == [job_id]
    assert client.get("/jobs?status=queued").json() == []
    assert client.get("/jobs?status=&limit=1").json()[0]["job_id"] == job_id
    assert client.get("/jobs?status=nonsense").status_code == 422
    assert client.get("/jobs?limit=0").status_code == 422
    assert client.get("/jobs?limit=101").status_code == 422


# ---------------------------------------------------------------------------
# Cancel
# ---------------------------------------------------------------------------


def test_cancel_a_queued_job_keeps_it_from_running(client, runtime):
    job_id = client.post("/generate-video", json=_payload()).json()["job_id"]

    body = client.post(f"/jobs/{job_id}/cancel").json()

    assert body["status"] == STATUS_FAILED
    assert body["error"] == "cancelled by request"
    assert body["video_url"] is None
    assert runtime.store.queue_depth() == 0


def test_cancel_conflicts_with_a_running_or_finished_job(client, runtime):
    job_id = client.post("/generate-video", json=_payload()).json()["job_id"]
    runtime.store.set_status(job_id, "processing", stage="rendering")

    response = client.post(f"/jobs/{job_id}/cancel")
    assert response.status_code == 409
    assert response.json() == {"detail": "job already running or finished"}

    runtime.store.set_status(job_id, STATUS_COMPLETED, stage="done", video_url="u")
    assert client.post(f"/jobs/{job_id}/cancel").status_code == 409


def test_cancel_an_unknown_job_is_404(client):
    response = client.post("/jobs/job_deadbeef/cancel")
    assert response.status_code == 404
    assert response.json() == {"detail": "job not found"}


# ---------------------------------------------------------------------------
# Details
# ---------------------------------------------------------------------------


def test_details_of_an_unfinished_job_is_409(client):
    job_id = client.post("/generate-video", json=_payload()).json()["job_id"]

    response = client.get(f"/video-status/{job_id}/details")

    assert response.status_code == 409
    assert response.json() == {"detail": "job not finished"}


def test_details_of_an_unknown_job_is_404(client):
    assert client.get("/video-status/job_deadbeef/details").status_code == 404


def test_details_read_the_metadata_blob(client, runtime):
    runtime.storage = FakeStorage(
        cached={
            "video_url": "https://acct.blob.core.windows.net/videos/videos/fp/final.mp4",
            "duration_seconds": 194.54,
        },
        metadata={
            "problem_summary": "Find two numbers that add up to the target.",
            "validation": {"performed": True, "is_correct": False, "issues": ["off-by-one"]},
            "solution_source": "corrected",
            "complexity": {"time": "O(n)", "space": "O(n)"},
            "scenes": [{"class_name": "Scene1_Intro"}, {"class_name": "Scene2_Trace"}],
            "cost": {"total_usd": 0.42},
        },
    )
    job_id = client.post("/generate-video", json=_payload()).json()["job_id"]
    runtime.store.set_status(job_id, STATUS_COMPLETED, stage="done", video_url="u")

    body = client.get(f"/video-status/{job_id}/details").json()

    assert body == {
        "job_id": job_id,
        "validation": {"performed": True, "is_correct": False, "issues": ["off-by-one"]},
        "solution_source": "corrected",
        "problem_summary": "Find two numbers that add up to the target.",
        "complexity": {"time": "O(n)", "space": "O(n)"},
        "duration_seconds": 194.54,
        "scene_count": 2,
    }
    assert "cost" not in json.dumps(body)


def test_details_prefer_the_local_workspace_copy(client, runtime, tmp_path):
    runtime.worker.workspace_root = tmp_path
    runtime.storage = FakeStorage(metadata={"problem_summary": "stale blob copy"})
    job_id = client.post("/generate-video", json=_payload()).json()["job_id"]
    runtime.store.set_status(job_id, STATUS_COMPLETED, stage="done", video_url="u")

    workspace = tmp_path / job_id
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "metadata.json").write_text(
        json.dumps(
            {
                "problem_summary": "fresh local copy",
                "validation": {"performed": True, "is_correct": True},
                "solution_source": "provided",
                "complexity": {"time": "O(n)", "space": "O(1)"},
                "scenes": [{"class_name": "Scene1_Intro"}],
            }
        ),
        encoding="utf-8",
    )
    (workspace / "result.json").write_text(
        json.dumps({"duration_seconds": 31.2}), encoding="utf-8"
    )

    body = client.get(f"/video-status/{job_id}/details").json()

    assert body["problem_summary"] == "fresh local copy"
    assert body["solution_source"] == "provided"
    assert body["duration_seconds"] == 31.2
    assert body["scene_count"] == 1
    assert body["validation"]["issues"] == []


def test_details_without_any_metadata_are_all_null(client, runtime):
    runtime.storage = FakeStorage()
    job_id = client.post("/generate-video", json=_payload()).json()["job_id"]
    runtime.store.set_status(job_id, STATUS_COMPLETED, stage="done", video_url="u")

    body = client.get(f"/video-status/{job_id}/details").json()

    assert body["validation"] == {"performed": None, "is_correct": None, "issues": []}
    assert body["solution_source"] is None
    assert body["duration_seconds"] is None
    assert body["scene_count"] is None


# ---------------------------------------------------------------------------
# Errors and auth for the new endpoints
# ---------------------------------------------------------------------------


def test_an_invalid_body_detail_is_one_string(client):
    body = client.post("/generate-video", json={"question": "not an object"}).json()
    assert isinstance(body["detail"], str) and body["detail"]


def test_the_api_key_protects_the_new_endpoints(runtime, monkeypatch):
    monkeypatch.setenv("PEBBLE_API_KEY", "s3cret-key")
    client = TestClient(api.app)
    protected = [
        ("get", "/options"),
        ("get", "/jobs"),
        ("get", "/health/deep"),
        ("get", "/video-status/job_x/details"),
        ("post", "/jobs/job_x/cancel"),
    ]

    assert client.get("/").status_code == 200
    for method, path in protected:
        assert getattr(client, method)(path).status_code == 401, path
        assert (
            getattr(client, method)(path, headers={"X-API-Key": "s3cret-key"}).status_code
            != 401
        ), path
