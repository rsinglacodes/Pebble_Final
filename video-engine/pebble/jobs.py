"""SQLite job store for the small HTTP API (thread-safe, single file).

One table, one row per job. ``processing`` rows are requeued on startup so a
crash never leaves a job stuck forever.
"""

from __future__ import annotations

import json
import logging
import secrets
import sqlite3
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pebble.workspace import WORKSPACE_ROOT

logger = logging.getLogger(__name__)

DEFAULT_DB_PATH = WORKSPACE_ROOT / "jobs.db"

STATUS_QUEUED = "queued"
STATUS_PROCESSING = "processing"
STATUS_COMPLETED = "completed"
STATUS_FAILED = "failed"
ACTIVE_STATUSES = (STATUS_QUEUED, STATUS_PROCESSING)
STATUSES = (STATUS_QUEUED, STATUS_PROCESSING, STATUS_COMPLETED, STATUS_FAILED)

# ``POST /generate-video?force=true`` skips the dedupe and the blob cache, so the
# flag travels with the payload: a forced job must run the pipeline even when its
# fingerprint is already stored. The worker strips it before the pipeline runs.
FORCE_PAYLOAD_KEY = "_pebble_force"
CANCELLED_ERROR = "cancelled by request"

MAX_LIST_LIMIT = 100

STAGE_NULL = None
STAGES = ("generating", "narrating", "rendering", "assembling", "uploading", "done")

SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    job_id        TEXT PRIMARY KEY,
    fingerprint   TEXT NOT NULL,
    status        TEXT NOT NULL,
    stage         TEXT,
    payload_json  TEXT NOT NULL,
    video_url     TEXT,
    solution_json TEXT,
    error         TEXT,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS jobs_fingerprint ON jobs (fingerprint, status);
CREATE INDEX IF NOT EXISTS jobs_status ON jobs (status, created_at);
"""

COLUMNS = (
    "job_id",
    "fingerprint",
    "status",
    "stage",
    "payload_json",
    "video_url",
    "solution_json",
    "error",
    "created_at",
    "updated_at",
)


def new_job_id() -> str:
    return f"job_{secrets.token_hex(4)}"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class JobStore:
    """Thread-safe access to the jobs table."""

    def __init__(self, path: Path | str | None = None) -> None:
        self.path = Path(path) if path is not None else DEFAULT_DB_PATH
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(str(self.path), check_same_thread=False)
        self._connection.row_factory = sqlite3.Row

    # -- lifecycle -------------------------------------------------------

    def init(self) -> int:
        """Create the schema and requeue interrupted jobs; returns the depth."""
        with self._lock:
            self._connection.executescript(SCHEMA)
            cursor = self._connection.execute(
                "UPDATE jobs SET status = ?, stage = NULL, updated_at = ? WHERE status = ?",
                (STATUS_QUEUED, _now(), STATUS_PROCESSING),
            )
            self._connection.commit()
            requeued = cursor.rowcount if cursor.rowcount and cursor.rowcount > 0 else 0
        if requeued:
            logger.info("requeued %d interrupted job(s) on startup", requeued)
        return self.queue_depth()

    def close(self) -> None:
        with self._lock:
            self._connection.close()

    # -- writes ----------------------------------------------------------

    def create(
        self,
        fingerprint: str,
        payload: dict[str, Any],
        status: str = STATUS_QUEUED,
        stage: str | None = None,
        video_url: str | None = None,
        solution: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        job_id = new_job_id()
        now = _now()
        with self._lock:
            self._connection.execute(
                "INSERT INTO jobs (job_id, fingerprint, status, stage, payload_json,"
                " video_url, solution_json, error, created_at, updated_at)"
                " VALUES (?, ?, ?, ?, ?, ?, ?, NULL, ?, ?)",
                (
                    job_id,
                    fingerprint,
                    status,
                    stage,
                    json.dumps(payload, ensure_ascii=False),
                    video_url,
                    json.dumps(solution, ensure_ascii=False) if solution else None,
                    now,
                    now,
                ),
            )
            self._connection.commit()
        return self.get(job_id) or {}

    def find_completed(self, fingerprint: str) -> dict[str, Any] | None:
        """The most recent finished job for this request, if any."""
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM jobs WHERE fingerprint = ? AND status = ?"
                " ORDER BY created_at DESC LIMIT 1",
                (fingerprint, STATUS_COMPLETED),
            ).fetchone()
        return dict(row) if row else None

    def find_active(self, fingerprint: str) -> dict[str, Any] | None:
        """An already queued/processing job for the same request, if any."""
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM jobs WHERE fingerprint = ? AND status IN (?, ?)"
                " ORDER BY created_at LIMIT 1",
                (fingerprint, STATUS_QUEUED, STATUS_PROCESSING),
            ).fetchone()
        return dict(row) if row else None

    def next_queued(self) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM jobs WHERE status = ? ORDER BY created_at LIMIT 1",
                (STATUS_QUEUED,),
            ).fetchone()
        return dict(row) if row else None

    def update(self, job_id: str, **fields: Any) -> dict[str, Any] | None:
        if not fields:
            return self.get(job_id)
        unknown = set(fields) - set(COLUMNS) - {"solution"}
        if unknown:
            raise ValueError(f"unknown job column(s): {sorted(unknown)}")
        if "solution" in fields:
            fields["solution_json"] = (
                json.dumps(fields.pop("solution"), ensure_ascii=False)
                if fields["solution"] is not None
                else None
            )
        fields["updated_at"] = _now()
        assignments = ", ".join(f"{name} = ?" for name in fields)
        values = [*fields.values(), job_id]
        with self._lock:
            self._connection.execute(
                f"UPDATE jobs SET {assignments} WHERE job_id = ?", values
            )
            self._connection.commit()
        return self.get(job_id)

    def set_status(
        self,
        job_id: str,
        status: str,
        stage: str | None = None,
        video_url: str | None = None,
        solution: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> dict[str, Any] | None:
        fields: dict[str, Any] = {"status": status, "stage": stage}
        if video_url is not None:
            fields["video_url"] = video_url
        if solution is not None:
            fields["solution"] = solution
        fields["error"] = error
        return self.update(job_id, **fields)

    def set_stage(self, job_id: str, stage: str | None) -> None:
        self.update(job_id, stage=stage)

    def claim(self, job_id: str, stage: str = "generating") -> dict[str, Any] | None:
        """Move a queued job to processing in one statement.

        Returns the updated row, or None when the job could not be claimed (it
        was cancelled in between, or it is already finished). Doing the
        transition in SQL is what makes "cancel a queued job" race-free: a job
        can never start after it has been cancelled.
        """
        with self._lock:
            cursor = self._connection.execute(
                "UPDATE jobs SET status = ?, stage = ?, updated_at = ?"
                " WHERE job_id = ? AND status IN (?, ?)",
                (STATUS_PROCESSING, stage, _now(), job_id, STATUS_QUEUED, STATUS_PROCESSING),
            )
            self._connection.commit()
            claimed = cursor.rowcount
        return self.get(job_id) if claimed else None

    def cancel(self, job_id: str) -> dict[str, Any] | None:
        """Fail a *queued* job so it never runs; None when it could not be cancelled."""
        with self._lock:
            cursor = self._connection.execute(
                "UPDATE jobs SET status = ?, stage = NULL, error = ?, updated_at = ?"
                " WHERE job_id = ? AND status = ?",
                (STATUS_FAILED, CANCELLED_ERROR, _now(), job_id, STATUS_QUEUED),
            )
            self._connection.commit()
            cancelled = cursor.rowcount
        return self.get(job_id) if cancelled else None

    # -- reads -----------------------------------------------------------

    def get(self, job_id: str) -> dict[str, Any] | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT * FROM jobs WHERE job_id = ?", (job_id,)
            ).fetchone()
        return _decode(dict(row)) if row else None

    def queue_depth(self) -> int:
        with self._lock:
            row = self._connection.execute(
                "SELECT COUNT(*) AS n FROM jobs WHERE status = ?", (STATUS_QUEUED,)
            ).fetchone()
        return int(row["n"]) if row else 0

    def list_jobs(self, status: str | None = None, limit: int = 20) -> list[dict[str, Any]]:
        """Newest first; optionally filtered by status and capped at MAX_LIST_LIMIT."""
        capped = max(1, min(int(limit), MAX_LIST_LIMIT))
        query = "SELECT * FROM jobs"
        params: list[Any] = []
        if status:
            query += " WHERE status = ?"
            params.append(status)
        # created_at has second resolution, so the rowid breaks ties in favour of
        # the job that was inserted last.
        query += " ORDER BY created_at DESC, rowid DESC LIMIT ?"
        params.append(capped)
        with self._lock:
            rows = self._connection.execute(query, params).fetchall()
        return [_decode(dict(row)) for row in rows]

    def processing_job(self) -> str | None:
        with self._lock:
            row = self._connection.execute(
                "SELECT job_id FROM jobs WHERE status = ? ORDER BY updated_at LIMIT 1",
                (STATUS_PROCESSING,),
            ).fetchone()
        return row["job_id"] if row else None


def _decode(row: dict[str, Any]) -> dict[str, Any]:
    """Turn the JSON columns back into Python values."""
    decoded = dict(row)
    for source, key in (("payload_json", "payload"), ("solution_json", "solution")):
        raw = decoded.pop(source, None)
        decoded[key] = json.loads(raw) if raw else None
    return decoded
