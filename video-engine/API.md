# Pebble API

Turns a coding question (plus an optional solution) into a narrated Manim explainer
video, stores it in Azure Blob Storage and returns a public URL.

Start the server:

```
python run_server.py                 # http://127.0.0.1:8000
PEBBLE_HOST=0.0.0.0 PEBBLE_PORT=9000 python run_server.py
```

Interactive docs: `/docs`.

## Authentication

Set `PEBBLE_API_KEY` on the server to require the header on every request:

```
X-API-Key: <PEBBLE_API_KEY>
```

Every endpoint except `GET /` and `GET /health` then needs it. A missing or wrong
key is `401`. If `PEBBLE_API_KEY` is unset the API is **open** (a startup warning
is printed) — fine on a laptop, never on the internet.

## Job lifecycle

`status`: `queued` → `processing` → `completed`, or `failed` (also `completed`
immediately on a cache hit, and `failed` with `cancelled by request` when a queued
job is cancelled).

`stage` is the pipeline step while `processing`, and is `null` otherwise:
`generating` → `narrating` → `rendering` → `assembling` → `uploading` → `done`.

A job takes about **2–4 minutes** (a repeat of an already-generated request returns
`completed` in under a second from the blob cache). **Poll every 5 seconds and give
up after 15 minutes.**

## Errors

All errors are JSON: `{"detail": "<message>"}`.

| Code | Meaning |
| --- | --- |
| 401 | missing or invalid `X-API-Key` |
| 404 | unknown `job_id` |
| 409 | job not finished / job already running or finished |
| 422 | invalid body, unknown status filter, unsupported style or language |
| 500/503 | server-side failure (for example blob storage not configured) |

---

## POST /generate-video

Query parameter `force=true` (optional, default `false`): skip the in-flight
dedupe **and** the blob cache, run the full pipeline and overwrite the stored
blobs for that request.

```bash
curl -X POST http://127.0.0.1:8000/generate-video \
  -H 'Content-Type: application/json' -H 'X-API-Key: KEY' \
  --data-binary @samples/two_sum_concise.json
```

Request body:

```json
{
  "question": {"id": 1, "slug": "two-sum", "title": "Two Sum"},
  "solution": {
    "code": "class Solution:\n    ...",
    "programming_language": "python",
    "validated": true
  },
  "preferences": {"explanation_language": "English", "explanation_style": "concise"}
}
```

`solution` may be omitted entirely (the algorithm is generated, and the code comes
back in the response). `preferences` may be omitted or empty: it defaults to
`English` / `beginner_friendly`. `explanation_language` is case-insensitive;
`explanation_style` is one of the values from `GET /options`. `solution.validated`
may be `false`/absent, in which case the code is checked and corrected when broken.

Response (200):

```json
{"job_id": "job_1a2b3c4d", "status": "queued"}
```

`status` is `completed` when the fingerprint was already generated (then no work is
queued at all).

## GET /video-status/{job_id}

```bash
curl http://127.0.0.1:8000/video-status/job_1a2b3c4d -H 'X-API-Key: KEY'
```

```json
{
  "job_id": "job_1a2b3c4d",
  "status": "completed",
  "stage": "done",
  "video_url": "https://<account>.blob.core.windows.net/<container>/videos/<fp>/final.mp4",
  "solution": {"code": "class Solution:\n ...", "programming_language": "python"},
  "error": null
}
```

`video_url` and `solution` are non-null only when `completed`; `error` is non-null
only when `failed`. The video URL is public — no key or SAS token is needed to
play or download it.

## GET /video-status/{job_id}/details

Teaching metadata for a finished job (never cost data). `409` while the job is
still queued or processing.

```json
{
  "job_id": "job_1a2b3c4d",
  "validation": {"performed": true, "is_correct": true, "issues": []},
  "solution_source": "corrected",
  "problem_summary": "Given an array of integers ...",
  "complexity": {"time": "O(n)", "space": "O(n)"},
  "duration_seconds": 194.54,
  "scene_count": 9
}
```

`solution_source` is one of `provided`, `corrected`, `generated`.

## POST /jobs/{job_id}/cancel

Cancels a job that has not started yet. It becomes `failed` with
`"error": "cancelled by request"` and never runs.

* queued → `200` with the failed job
* processing / completed / failed → `409 {"detail": "job already running or finished"}`
* unknown job → `404`

## GET /jobs?status=&limit=20

Newest first. `status` is optional (one of the four status values, empty means
all), `limit` is `1–100`. Returns a JSON array:

```json
[
  {
    "job_id": "job_1a2b3c4d",
    "status": "completed",
    "stage": "done",
    "title": "Two Sum",
    "created_at": "2026-10-27T09:12:03+00:00",
    "updated_at": "2026-10-27T09:14:37+00:00"
  }
]
```

## GET /options

The accepted preference values.

```json
{
  "explanation_styles": ["beginner_friendly", "interview_focused", "detailed", "concise"],
  "explanation_languages": ["English", "French", "German", "Hindi", "Spanish"]
}
```

If the server sets `AZURE_SPEECH_VOICE`, one voice is used for every language and
any `explanation_language` is accepted.

## GET /health

Open (no key). Cheap liveness probe.

```json
{"status": "ok", "queue_depth": 0, "processing": "job_1a2b3c4d"}
```

## GET /health/deep

Readiness of the local toolchain (no LLM or speech call is made). `status` is
`degraded` when any check is not `ok`.

```json
{
  "status": "ok",
  "checks": {"blob": "ok", "ffmpeg": "ok", "ffprobe": "ok", "manim": "ok", "env": "ok"}
}
```

`env` lists missing variable **names** only, never values.

## GET /

```json
{"service": "Pebble", "docs": "/docs", "health": "/health"}
```

---

## Full example

```bash
KEY=my-key
BASE=http://127.0.0.1:8000

JOB=$(curl -s -X POST "$BASE/generate-video" -H 'Content-Type: application/json' \
        -H "X-API-Key: $KEY" --data-binary @samples/two_sum_concise.json \
      | python -c 'import json,sys; print(json.load(sys.stdin)["job_id"])')

while true; do
  BODY=$(curl -s "$BASE/video-status/$JOB" -H "X-API-Key: $KEY")
  echo "$BODY"
  STATUS=$(echo "$BODY" | python -c 'import json,sys; print(json.load(sys.stdin)["status"])')
  [ "$STATUS" = "completed" -o "$STATUS" = "failed" ] && break
  sleep 5
done

URL=$(echo "$BODY" | python -c 'import json,sys; print(json.load(sys.stdin)["video_url"])')
curl -sI "$URL"        # 200, content-type: video/mp4, no credentials needed
```
