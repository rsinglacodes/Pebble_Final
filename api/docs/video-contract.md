# Video Service Contract

## 1. Architecture & Boundaries
- **Single LLM Engine**: There is ONE LLM, owned by teammate (hosted on Azure). The Pebble backend never generates or validates code.
- **No Local Sandbox / Trace**: There is no sandbox, repair loop, trace engine, or scene planner in the backend.
- Teammate's code lives only in `video-engine/` with its own `requirements.txt` and `README.md`. It runs as a dedicated API on port 8001 (uvicorn).
- Teammate owns: Manim, Azure Speech, FFmpeg, Azure Blob Storage upload. Backend owns: cache key, duplicate-job prevention, database records, rate limits, and user authorization.
- Teammate's server processes ONE job at a time, so jobs can sit in 'queued' for a long time.

## 2. Video Render Request
The backend initiates video rendering via `POST {VIDEO_ENGINE_URL}/generate-video`.
An `X-API-Key` header is sent **ONLY** if `VIDEO_ENGINE_API_KEY` is non-empty (default is empty).

### Payload Format
Preferences are always fixed:
```json
{
  "preferences": {
    "explanation_language": "English",
    "explanation_style": "beginner_friendly"
  }
}
```

### Four Payload Cases
1. **Stored Repo Code**:
   - `question`: `{"id": <id>, "slug": "<slug>", "title": "<title>"}`
   - `solution`: `{"code": "...", "programming_language": "<lang>", "validated": true}`
2. **User Code**:
   - `question`: `{"id": <id>, "slug": "<slug>", "title": "<title>"}` (or `{"id": null, "slug": null, "title": "<text>"}` if unmatched)
   - `solution`: `{"code": "...", "programming_language": "<lang>", "validated": false}`
3. **Problem Known but No Code in that Language**:
   - `question`: `{"id": <id>, "slug": "<slug>", "title": "<title>"}`
   - `solution`: `{"programming_language": "<lang>"}` (no `code` key)
4. **Unmatched Text**:
   - `question`: `{"id": null, "slug": null, "title": "<text>"}`
   - `solution`: `{"programming_language": "<lang>"}` (or with user code: `{"code": "...", "programming_language": "<lang>", "validated": false}`)

## 3. Video Render Job Polling
- `POST {VIDEO_ENGINE_URL}/generate-video` returns:
  ```json
  {
    "job_id": "job_12345",
    "status": "queued"
  }
  ```
- Backend polls `GET {VIDEO_ENGINE_URL}/video-status/{job_id}` which returns:
  ```json
  {
    "job_id": "job_12345",
    "status": "queued | processing | completed | failed",
    "video_url": "https://<account>.blob.core.windows.net/videos/two-sum-python.mp4",
    "solution": {
      "code": "...",
      "programming_language": "python"
    },
    "error": null
  }
  ```
- `video_url` and `solution` are null until completed; `error` is null unless failed.
- Status Mapping & Polling Rules:
  - `'processing'` is mapped to our internal status `'running'`.
  - `stage` = the raw status string from her API.
  - `blob_name` = last path segment of `video_url` or null.
  - Unknown statuses count as `'running'`.
  - A 404 on a poll marks the job failed with `'job not found on video service'`.
  - Timeouts and 5xx responses on a poll are retried and never fail the job from a single poll error.
  - Request timeout is 10 seconds.
  - Polling runs every 5 seconds, giving up after `VIDEO_JOB_TIMEOUT_MINUTES` (default 30) and marking the job failed with `'timed out'`.
  - On app startup, resume polling for video_jobs in queued or running state that have a `provider_job_id`; mark those without one as failed.

## 4. Returned Solution Storage & Provenance
Returned solution is stored in `generated_videos.solution_json` (jsonb):
```json
{
  "code": "...",
  "programming_language": "python",
  "validated": true,
  "origin": "repo | user_code | ai_generated"
}
```
Provenance logic:
- `validated = true` and `origin = 'repo'` ONLY if the returned code equals the code we sent AND we sent `validated = true`.
- `origin = 'user_code'` and `validated = false` if it equals user-submitted code.
- Otherwise `validated = false` and `origin = 'ai_generated'`.
- Returned as `solution` in `GET /video-jobs/{id}/result`.

## 5. Cache Key Computation
The cache key is computed **only inside the backend** (never sent to the video engine):
- `sha256(problem_identifier + ":" + programming_language + ":" + user_code_hash)`
- Where `problem_identifier` = problem number, or normalized lowercase text for unmatched.
- Where `user_code_hash` = sha256 of user code when code is user-submitted (empty string otherwise).
- Explanation language and style are removed from the cache key.

## 6. Limits & Rate Limiting
- **Per-User Concurrency**: At most 1 queued or running job per user (submitting another returns the existing job instead of creating a new one).
- **Unmatched-Text Limit**: At most 5 unmatched-text video jobs per hour per user (HTTP 429).
- **Global Queue Capacity**: If 10 jobs are already queued or running across all users, returns HTTP 503 `{"error": "busy", "message": "Video queue is full, try again later"}`.
