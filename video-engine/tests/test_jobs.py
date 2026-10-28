"""Job store: persistence, restart requeue, dedupe and status transitions."""

from __future__ import annotations

import json

from pebble.jobs import (
    STATUS_COMPLETED,
    STATUS_FAILED,
    STATUS_PROCESSING,
    STATUS_QUEUED,
    JobStore,
)


def _store(tmp_path) -> JobStore:
    store = JobStore(tmp_path / "jobs.db")
    store.init()
    return store


def test_new_job_id_shape():
    from pebble.jobs import new_job_id

    job_id = new_job_id()
    assert job_id.startswith("job_")
    assert len(job_id) == 12
    assert int(job_id[4:], 16) >= 0


def test_create_get_and_payload_round_trip(tmp_path):
    store = _store(tmp_path)
    payload = {"question": {"id": 1, "title": "Two Sum"}}
    job = store.create("fp1", payload)

    assert job["job_id"].startswith("job_")
    assert job["status"] == STATUS_QUEUED
    assert job["stage"] is None
    assert job["error"] is None

    fetched = store.get(job["job_id"])
    assert fetched["payload"] == payload
    assert fetched["fingerprint"] == "fp1"
    assert fetched["created_at"] and fetched["updated_at"]


def test_unknown_job_is_none(tmp_path):
    assert _store(tmp_path).get("job_nope") is None


def test_status_and_solution_round_trip(tmp_path):
    store = _store(tmp_path)
    job = store.create("fp", {})
    store.set_status(
        job["job_id"],
        STATUS_COMPLETED,
        stage="done",
        video_url="https://x/final.mp4",
        solution={"code": "print(1)", "programming_language": "python"},
    )

    stored = store.get(job["job_id"])
    assert stored["status"] == STATUS_COMPLETED
    assert stored["video_url"] == "https://x/final.mp4"
    assert stored["solution"]["programming_language"] == "python"
    assert stored["stage"] == "done"


def test_failure_records_the_error(tmp_path):
    store = _store(tmp_path)
    job = store.create("fp", {})
    store.set_status(job["job_id"], STATUS_FAILED, stage=None, error="boom")

    stored = store.get(job["job_id"])
    assert stored["status"] == STATUS_FAILED
    assert stored["error"] == "boom"
    assert stored["stage"] is None


def test_unknown_column_is_refused(tmp_path):
    store = _store(tmp_path)
    job = store.create("fp", {})
    try:
        store.update(job["job_id"], nonsense=1)
    except ValueError as exc:
        assert "unknown job column" in str(exc)
    else:  # pragma: no cover - the guard must fire
        raise AssertionError("update accepted an unknown column")


def test_queue_is_fifo_and_depth_counts_queued_only(tmp_path):
    store = _store(tmp_path)
    first = store.create("fp1", {})
    second = store.create("fp2", {})
    assert store.queue_depth() == 2
    assert store.next_queued()["job_id"] == first["job_id"]

    store.set_status(second["job_id"], STATUS_PROCESSING, stage="generating")
    assert store.queue_depth() == 1
    assert store.processing_job() == second["job_id"]
    assert store.next_queued()["job_id"] == first["job_id"]


def test_processing_jobs_are_requeued_on_restart(tmp_path):
    path = tmp_path / "jobs.db"
    store = JobStore(path)
    store.init()
    job = store.create("fp", {})
    store.set_status(job["job_id"], STATUS_PROCESSING, stage="rendering")
    store.close()

    reopened = JobStore(path)
    depth = reopened.init()

    assert depth == 1
    restored = reopened.get(job["job_id"])
    assert restored["status"] == STATUS_QUEUED
    assert restored["stage"] is None
    reopened.close()


def test_find_active_dedupes_the_same_fingerprint(tmp_path):
    store = _store(tmp_path)
    job = store.create("fp", {})

    active = store.find_active("fp")
    assert active["job_id"] == job["job_id"]

    store.set_status(job["job_id"], STATUS_PROCESSING, stage="generating")
    assert store.find_active("fp")["job_id"] == job["job_id"]

    store.set_status(job["job_id"], STATUS_COMPLETED, stage="done", video_url="u")
    assert store.find_active("fp") is None
    assert store.find_active("other") is None


def test_database_survives_a_reopen(tmp_path):
    path = tmp_path / "jobs.db"
    store = JobStore(path)
    store.init()
    job = store.create("fp", {"question": {"id": 7}})
    store.close()

    reopened = JobStore(path)
    reopened.init()
    assert reopened.get(job["job_id"])["payload"] == {"question": {"id": 7}}
    reopened.close()


def test_row_decoding_is_json_safe(tmp_path):
    store = _store(tmp_path)
    job = store.create("fp", {"a": [1, 2]}, status=STATUS_COMPLETED, solution={"code": "x"})
    raw = json.loads(json.dumps(store.get(job["job_id"]), default=str))
    assert raw["payload"] == {"a": [1, 2]}
    assert raw["solution"] == {"code": "x"}


def test_find_completed_returns_the_latest_finished_job(tmp_path):
    store = _store(tmp_path)
    first = store.create("fp", {})
    store.set_status(first["job_id"], STATUS_COMPLETED, stage="done", video_url="u1")
    second = store.create("fp", {})
    assert store.find_completed("fp")["job_id"] == first["job_id"]

    store.set_status(second["job_id"], STATUS_COMPLETED, stage="done", video_url="u2")
    assert store.find_completed("fp")["video_url"] == "u2"
    assert store.find_completed("other") is None


def test_a_cached_job_can_be_created_completed(tmp_path):
    store = _store(tmp_path)
    job = store.create(
        "fp",
        {},
        status=STATUS_COMPLETED,
        stage="done",
        video_url="u",
        solution={"code": "x"},
    )
    assert job["status"] == STATUS_COMPLETED
    assert job["stage"] == "done"
    assert job["video_url"] == "u"
    assert store.queue_depth() == 0


# ---------------------------------------------------------------------------
# claim / cancel / list (API support)
# ---------------------------------------------------------------------------


def test_claim_moves_a_queued_job_to_processing(tmp_path):
    store = _store(tmp_path)
    job = store.create("fp", {})

    claimed = store.claim(job["job_id"])

    assert claimed["status"] == STATUS_PROCESSING
    assert claimed["stage"] == "generating"
    assert store.queue_depth() == 0


def test_claim_refuses_a_cancelled_job(tmp_path):
    store = _store(tmp_path)
    job = store.create("fp", {})
    store.cancel(job["job_id"])

    assert store.claim(job["job_id"]) is None
    assert store.get(job["job_id"])["error"] == "cancelled by request"


def test_cancel_only_touches_a_queued_job(tmp_path):
    store = _store(tmp_path)
    queued = store.create("fp", {})
    running = store.create("fp2", {})
    store.set_status(running["job_id"], STATUS_PROCESSING, stage="rendering")
    finished = store.create("fp3", {})
    store.set_status(finished["job_id"], STATUS_COMPLETED, stage="done", video_url="u")

    assert store.cancel(queued["job_id"])["status"] == STATUS_FAILED
    assert store.cancel(running["job_id"]) is None
    assert store.cancel(finished["job_id"]) is None
    assert store.get(running["job_id"])["status"] == STATUS_PROCESSING
    assert store.get(finished["job_id"])["status"] == STATUS_COMPLETED
    assert store.cancel("job_nope") is None


def test_list_jobs_is_newest_first_with_a_status_filter_and_a_cap(tmp_path):
    store = _store(tmp_path)
    first = store.create("fp1", {"question": {"title": "Two Sum"}})
    second = store.create("fp2", {"question": {"title": "Dijkstra"}})
    store.set_status(first["job_id"], STATUS_COMPLETED, stage="done", video_url="u")

    newest = store.list_jobs()
    assert [job["job_id"] for job in newest] == [second["job_id"], first["job_id"]]

    completed = store.list_jobs(status=STATUS_COMPLETED)
    assert [job["job_id"] for job in completed] == [first["job_id"]]

    assert [job["job_id"] for job in store.list_jobs(limit=1)] == [second["job_id"]]
    assert len(store.list_jobs(limit=10_000)) == 2
    assert store.list_jobs(limit=0)[0]["job_id"] == second["job_id"]
    assert store.list_jobs(status="failed") == []
