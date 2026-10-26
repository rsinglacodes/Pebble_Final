# Video Integration Layer

This directory houses the backend integration adapter for the video generation engine.
Contract reference: `docs/video-contract.md`.

- Talks to the teammate-owned engine at `POST {VIDEO_ENGINE_URL}/render` and `GET {VIDEO_ENGINE_URL}/jobs/{provider_job_id}`.
- Provider implementation (including `MockVideoProvider` for local testing) will be added in Phase B11.
