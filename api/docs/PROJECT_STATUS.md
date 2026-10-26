# Pebble Project Status & Read-Only Audit Report

**Date of Audit**: October 26, 2026  
**Auditor**: Antigravity Assistant  
**Status**: Read-only Architecture & Implementation Audit

---

## 1. File Map

### Project Tree (Two Levels Deep)
```
d:\Pebble
├── .env                       # Local environment variables and secrets (gitignored)
├── .env.example               # Template environment configuration with dummy placeholders
├── .gitignore                  # Git ignore rules for virtual environments, secrets, and caches
├── alembic.ini                # Alembic database migration configuration
├── README.md                  # Comprehensive setup, run, migration, and testing instructions
├── requirements.txt           # Python backend dependencies
├── backend/                   # Core application source code and migrations
│   ├── alembic/               # Database migration scripts and environment runner
│   │   ├── env.py             # Alembic migration execution harness connecting to DB
│   │   ├── script.py.mako     # Migration template
│   │   └── versions/          # Versioned schema migration files
│   ├── alembic.ini            # Redundant Alembic configuration copy
│   ├── requirements.txt       # Redundant requirements specification
│   └── app/                   # FastAPI backend implementation
│       ├── api/               # Thin HTTP controller route handlers
│       ├── code_execution/    # Placeholder package for future code execution/evaluation
│       ├── core/              # Cross-cutting middleware, logging, security, and rate limiting
│       ├── data/              # Static seed datasets (roadmaps.json)
│       ├── db/                # Database base class and session engine factory
│       ├── integrations/      # External service clients (teammate video engine)
│       ├── models/            # SQLAlchemy 2.0 ORM entity models
│       ├── rag/               # Placeholder package for future RAG pipelines
│       ├── repositories/      # Database abstraction and SQL query layer
│       ├── schemas/           # Pydantic validation and serialization models
│       ├── services/          # Core business logic and orchestration
│       ├── workers/           # Placeholder package for asynchronous task workers
│       ├── config.py          # Centralized configuration via Pydantic Settings
│       └── main.py            # FastAPI application factory and router mounting
├── data/                      # Local data storage and cloned source repos (gitignored)
├── docs/                      # Architectural contracts and API specifications
│   ├── api-contract.md        # API boundary decisions and endpoint specification
│   ├── openapi.json           # Exported OpenAPI 3.1 specification for backend
│   ├── project-overview.md    # Multi-phase architecture and technical roadmap
│   ├── THIRD_PARTY_NOTICES.md # Licensing notices for third-party libraries and datasets
│   └── video-contract.md      # Integration contract with teammate-owned Video Engine
├── frontend/                  # Frontend single-page application workspace
│   └── .gitkeep               # Directory placeholder
├── scripts/                   # CLI maintenance and data ingestion scripts
│   ├── .gitkeep               # Directory placeholder
│   └── ingest_solutions.py    # WalkCCC repository ingestion pipeline
├── tests/                     # Automated pytest test suite
│   ├── fixtures/              # Reusable mock datasets and sample repositories
│   │   └── fake_repo/         # Sample repository fixture for ingest tests
│   ├── conftest.py            # Pytest test client and DB session fixtures
│   ├── test_auth.py           # Registration, login, rate limit, and token tests
│   ├── test_chat.py           # Chat scope, problem resolution, and conversation tests
│   ├── test_config.py         # Configuration loading and CORS parsing tests
│   ├── test_exceptions.py     # Safe error handling and traceback suppression tests
│   ├── test_hardening.py      # Route hygiene, body size limit, and log scrubbing tests
│   ├── test_health.py         # Health check and database connectivity probe tests
│   ├── test_models.py         # ORM schema, constraint, and table count tests
│   ├── test_problems.py       # Ingest parsing, exact, and trigram search tests
│   ├── test_repositories.py   # Database repository integration tests
│   ├── test_roadmap.py        # Roadmap generation, status updates, and progress tests
│   ├── test_schemas.py        # Pydantic schema validation tests
│   ├── test_users.py          # Profile, preference, and onboarding tests
│   └── test_video.py          # Video payload, cache key, and job workflow tests
└── video-engine/              # Teammate-owned video rendering engine service
    └── README.md              # Instructions for external video engine setup
```

### Purpose of Every Folder & File under `backend/app`, `scripts`, `tests`, and `docs`

#### Under `backend/app`:
- `config.py`: Application configuration and environment variable loading using Pydantic Settings.
- `main.py`: FastAPI application factory, middleware registration, and API router assembly.
- `__init__.py`: Package initialization for the backend application.
- `api/auth.py`: Authentication route handlers for user registration and login.
- `api/conversations.py`: Chat and conversation route handlers for multi-turn DSA interaction.
- `api/health.py`: Health check and database connectivity probe endpoint.
- `api/problems.py`: LeetCode problem search, resolution, and solution endpoints.
- `api/roadmap.py`: User roadmap retrieval, problem status mutation, and progress aggregation.
- `api/users.py`: User profile, learning preferences, and onboarding endpoints.
- `api/video.py`: Video generation job creation, polling, result retrieval, and retry endpoints.
- `api/__init__.py`: API router package initialization.
- `code_execution/__init__.py`: Package placeholder reserved for future code execution/evaluation logic.
- `core/dependencies.py`: FastAPI dependency injection helpers for authentication and database sessions.
- `core/dsa_keywords.py`: Curated list of ~100 DSA keywords used for rule-based chat scope verification.
- `core/exceptions.py`: Global exception handlers ensuring masked, safe JSON error responses without stack traces.
- `core/logging.py`: Security logging filter redacting JWTs, passwords, secrets, credentials, and full user code.
- `core/middleware.py`: ASGI middleware enforcing a strict 200 KB request body size ceiling.
- `core/rate_limit.py`: SlowAPI rate limiter setup with per-authenticated-user key extraction.
- `core/security.py`: Password hashing (bcrypt) and JWT access token creation/validation routines.
- `core/__init__.py`: Core utilities and cross-cutting security module initialization.
- `data/roadmaps.json`: Curated starter problem lists (15 problems each) for beginner, intermediate, and advanced levels.
- `db/base.py`: SQLAlchemy DeclarativeBase base class for all ORM models.
- `db/session.py`: PostgreSQL engine creation and session factory handling psycopg 3 connections.
- `db/__init__.py`: Database session and engine package initialization.
- `integrations/__init__.py`: External service integrations package initialization.
- `integrations/video/base.py`: Abstract VideoProvider interface defining submit and get_status methods.
- `integrations/video/http.py`: Concrete HttpVideoProvider communicating with teammate's Azure Video Engine API over HTTP.
- `integrations/video/mock.py`: MockVideoProvider simulating asynchronous rendering lifecycle over ~10 seconds.
- `integrations/video/README.md`: Architectural documentation for the video integration layer and contract.
- `integrations/video/__init__.py`: Video integration factory and package initialization.
- `models/conversation.py`: SQLAlchemy ORM models for Conversation and Message entities.
- `models/problem.py`: SQLAlchemy ORM models for Problem entity.
- `models/progress.py`: SQLAlchemy ORM models for Roadmap, RoadmapProblem, and UserProgress entities.
- `models/solution.py`: SQLAlchemy ORM models for Solution, SolutionTest, and ExecutionTrace entities.
- `models/user.py`: SQLAlchemy ORM models for User, AuthIdentity, and UserPreference entities.
- `models/video.py`: SQLAlchemy ORM models for VideoJob and GeneratedVideo entities.
- `models/__init__.py`: Package initialization importing all ORM models for Alembic metadata tracking.
- `rag/__init__.py`: Package placeholder reserved for future retrieval-augmented generation modules.
- `repositories/conversation_repository.py`: Database queries for creating, listing, and retrieving user conversations.
- `repositories/health_repository.py`: Database ping query executing `SELECT 1` for health probes.
- `repositories/message_repository.py`: Database operations for persisting and loading conversation messages.
- `repositories/preferences_repository.py`: Database operations for reading and updating user learning preferences.
- `repositories/problem_repository.py`: Problem resolution queries with exact and pg_trgm fuzzy matching.
- `repositories/progress_repository.py`: Queries for tracking and querying user problem solve statuses.
- `repositories/roadmap_repository.py`: Database operations for provisioning and updating user roadmaps.
- `repositories/solution_repository.py`: Database queries for fetching and upserting multi-language solutions.
- `repositories/user_repository.py`: Database operations for user registration, authentication, and profile lookup.
- `repositories/video_repository.py`: Queries for video job state transitions and cached video deduplication.
- `schemas/auth.py`: Pydantic request and response schemas for user registration, login, and JWT tokens.
- `schemas/contracts.py`: Contract definitions aligning backend payloads with external video engine expectations.
- `schemas/conversation.py`: Pydantic models for chat messages, conversation payloads, and assistant responses.
- `schemas/problem.py`: Pydantic models for problem metadata, search results, and code solutions.
- `schemas/roadmap.py`: Pydantic schemas for roadmap problem items, status updates, and progress counts.
- `schemas/video.py`: Pydantic models for video render requests, job polling responses, and results.
- `schemas/__init__.py`: Schema package initialization.
- `services/auth_service.py`: Business logic for credential validation, password verification, and JWT generation.
- `services/cache_service.py`: Deterministic SHA256 cache key computation for video generation deduplication.
- `services/chat_service.py`: Scope validation, problem resolution, solution selection, and progress updating for chat.
- `services/health_service.py`: Health assessment aggregating database connectivity and system status.
- `services/ingest_service.py`: Ingestion pipeline cloning WalkCCC repository, extracting solutions, and upserting problems.
- `services/onboarding_service.py`: Onboarding workflow saving user background and initializing personalized roadmap.
- `services/payload_builder.py`: Constructs exact JSON payloads for external video engine across four distinct cases.
- `services/problem_service.py`: Business logic coordinating problem search, slug resolution, and language availability.
- `services/roadmap_service.py`: Roadmap initialization from level presets, status updates, and progress counters.
- `services/video_service.py`: Video job orchestration, duplicate job prevention, cache reuse, and polling.
- `workers/__init__.py`: Package placeholder reserved for background job workers.

#### Under `scripts/`:
- `scripts/ingest_solutions.py`: CLI script to clone WalkCCC repository and ingest problems and multi-language solutions into PostgreSQL.
- `scripts/.gitkeep`: Preserves scripts directory in version control.

#### Under `tests/`:
- `tests/conftest.py`: Shared pytest fixtures for FastAPI test client, database sessions, and auth headers.
- `tests/test_auth.py`: Unit and integration tests for user registration, login, rate limiting, and token verification.
- `tests/test_chat.py`: Tests for chat scope validation, problem resolution, code handling, and conversation privacy.
- `tests/test_config.py`: Unit tests for application settings loading, CORS origin parsing, and environment variables.
- `tests/test_exceptions.py`: Tests verifying masked 500 error responses and suppression of stack traces.
- `tests/test_hardening.py`: Tests for plain route mounting, 200 KB request body limit, and log credential sanitization.
- `tests/test_health.py`: Tests for `/health` endpoint under database connected and disconnected states and CORS headers.
- `tests/test_models.py`: Database schema and model tests validating table counts, foreign keys, and unique constraints.
- `tests/test_problems.py`: Tests for problem ingestion, directory parsing, exact and trigram similarity search resolution.
- `tests/test_repositories.py`: Database integration tests for user and problem repository operations.
- `tests/test_roadmap.py`: Tests for onboarding roadmap provisioning, deduplication, status transitions, and progress aggregation.
- `tests/test_schemas.py`: Schema validation tests for auth, preferences, problems, chat, and video job Pydantic models.
- `tests/test_users.py`: Tests for user profile updates, learning preferences persistence, and onboarding completion.
- `tests/test_video.py`: Tests for payload builder, cache key hashing, video job deduplication, cache hits, and retries.
- `tests/__init__.py`: Test package initialization.

#### Under `docs/`:
- `docs/api-contract.md`: Specification of backend API boundaries, external LLM architecture, and video rendering endpoints.
- `docs/openapi.json`: Exported OpenAPI 3.1 specification containing all 19 plain API route definitions.
- `docs/project-overview.md`: Architectural specification and phase-by-phase implementation plan for Pebble.
- `docs/THIRD_PARTY_NOTICES.md`: Third-party open-source licensing notices and attribution.
- `docs/video-contract.md`: Definite contract between Pebble backend and teammate-owned Azure Video Engine.

---

## 2. Routes Table

Extracted directly from `app.openapi()` and source inspection:

| Method | Path | Login Required | Rate Limit | Handler File |
|---|---|---|---|---|
| `POST` | `/auth/login` | No | 5/minute | `backend/app/api/auth.py` |
| `POST` | `/auth/register` | No | None | `backend/app/api/auth.py` |
| `GET` | `/conversations` | Yes | None | `backend/app/api/conversations.py` |
| `POST` | `/conversations` | Yes | None | `backend/app/api/conversations.py` |
| `GET` | `/conversations/{id}` | Yes | None | `backend/app/api/conversations.py` |
| `POST` | `/conversations/{id}/messages` | Yes | 30/minute | `backend/app/api/conversations.py` |
| `GET` | `/health` | No | None | `backend/app/api/health.py` |
| `GET` | `/problems/resolve` | Yes | None | `backend/app/api/problems.py` |
| `GET` | `/problems/{id}` | Yes | None | `backend/app/api/problems.py` |
| `GET` | `/problems/{id}/solutions` | Yes | None | `backend/app/api/problems.py` |
| `GET` | `/progress` | Yes | None | `backend/app/api/roadmap.py` |
| `GET` | `/roadmap` | Yes | None | `backend/app/api/roadmap.py` |
| `PATCH` | `/roadmap/problems/{problem_id}` | Yes | None | `backend/app/api/roadmap.py` |
| `GET` | `/users/me` | Yes | None | `backend/app/api/users.py` |
| `PATCH` | `/users/me` | Yes | None | `backend/app/api/users.py` |
| `POST` | `/users/me/onboarding` | Yes | None | `backend/app/api/users.py` |
| `GET` | `/users/me/preferences` | Yes | None | `backend/app/api/users.py` |
| `PUT` | `/users/me/preferences` | Yes | None | `backend/app/api/users.py` |
| `POST` | `/video-jobs` | Yes | 30/minute | `backend/app/api/video.py` |
| `GET` | `/video-jobs/{id}` | Yes | None | `backend/app/api/video.py` |
| `GET` | `/video-jobs/{id}/result` | Yes | None | `backend/app/api/video.py` |
| `POST` | `/video-jobs/{id}/retry` | Yes | None | `backend/app/api/video.py` |

*(Note: Built-in documentation endpoints `/docs`, `/redoc`, and `/openapi.json` are public and served internally by FastAPI).*

---

## 3. Database Status

### 1. Model Tables Registered (15 Tables)
- `auth_identities`
- `conversations`
- `execution_traces`
- `generated_videos`
- `messages`
- `problem_tests`
- `problems`
- `roadmap_problems`
- `roadmaps`
- `solution_tests`
- `solutions`
- `user_preferences`
- `user_progress`
- `users`
- `video_jobs`

### 2. Alembic Revision History
- `adda3ced4de0`: `initial_schema` (down_revision: None)
- `dec6626353f0`: `add_password_hash_to_users` (down_revision: `adda3ced4de0`)
- `e4a2c1f09b40`: `add_solutions_validated_commit_sha_and_trgm_indexes` (down_revision: `dec6626353f0`)
- `f1b8c2d3e4a5`: `update_video_jobs_and_generated_videos_schema` (down_revision: `e4a2c1f09b40`) — **HEAD**

### 3. Primary Database Head Status
- Primary Database Revision: `f1b8c2d3e4a5`
- Is Primary Database at Head: **Yes**

### 4. Primary Database Row Counts
- `problems`: **0**
- `solutions` (grouped by language): **{} (0)**
- `users`: **4**
- `generated_videos`: **1**
- `user_progress`: **0**

---

## 4. Feature Status Table

| Feature | Status | Implementation File | Test Evidence |
|---|---|---|---|
| Auth | **Done** | `backend/app/api/auth.py`, `backend/app/services/auth_service.py` | `tests/test_auth.py::test_register_ok`, `test_login_wrong_password_and_unknown_email_same_message` |
| Preferences | **Done** | `backend/app/api/users.py`, `backend/app/repositories/preferences_repository.py` | `tests/test_users.py::test_preferences_save_and_reload` |
| Onboarding | **Done** | `backend/app/api/users.py`, `backend/app/services/onboarding_service.py` | `tests/test_users.py::test_onboarding_sets_onboarding_completed`, `tests/test_roadmap.py::test_roadmap_created_after_onboarding_and_not_duplicated` |
| Problem Ingestion & Search | **Done** | `scripts/ingest_solutions.py`, `backend/app/services/ingest_service.py`, `backend/app/api/problems.py` | `tests/test_problems.py::test_ingest_idempotency_and_hash_diff`, `tests/test_problems.py::test_resolve_by_typo_trgm` |
| /conversations Chat | **Done** | `backend/app/api/conversations.py`, `backend/app/services/chat_service.py` | `tests/test_chat.py::test_solve_problem_1_in_python_returns_solution_and_updates_progress`, `test_out_of_scope_message` |
| POST /ask | **Missing** | N/A (Chat is structured as multi-turn `/conversations/{id}/messages`) | None |
| Video Jobs & Cache | **Done** | `backend/app/api/video.py`, `backend/app/services/video_service.py`, `backend/app/services/cache_service.py` | `tests/test_video.py::test_first_request_creates_job_and_completes_with_stored_url`, `test_identical_second_request_returns_stored_url_without_provider_call` |
| Roadmap | **Done** | `backend/app/api/roadmap.py`, `backend/app/services/roadmap_service.py`, `backend/app/data/roadmaps.json` | `tests/test_roadmap.py::test_roadmap_status_updates`, `test_intermediate_and_advanced_roadmaps_created_from_level` |
| Progress or History | **Done** | `backend/app/api/roadmap.py`, `backend/app/repositories/progress_repository.py` | `tests/test_roadmap.py::test_roadmap_status_updates`, `tests/test_chat.py::test_solve_problem_1_in_python_returns_solution_and_updates_progress` |
| Hardening | **Done** | `backend/app/core/middleware.py`, `backend/app/core/logging.py`, `backend/app/core/exceptions.py`, `backend/app/core/rate_limit.py` | `tests/test_hardening.py::test_plain_routes_only`, `test_request_body_size_limit`, `test_sensitive_data_logging_filter` |

---

## 5. Test Suite Metrics & Warnings

### Tests per File (Total: 68 Tests across 13 Files)
- `tests/test_auth.py`: **7** tests
- `tests/test_chat.py`: **7** tests
- `tests/test_config.py`: **3** tests
- `tests/test_exceptions.py`: **2** tests
- `tests/test_hardening.py`: **3** tests
- `tests/test_health.py`: **5** tests
- `tests/test_models.py`: **3** tests
- `tests/test_problems.py`: **11** tests
- `tests/test_repositories.py`: **2** tests
- `tests/test_roadmap.py`: **5** tests
- `tests/test_schemas.py`: **8** tests
- `tests/test_users.py`: **4** tests
- `tests/test_video.py`: **8** tests

### Deprecation Warnings Summary (6 Warnings)
1. `starlette/testclient.py:45`: `DeprecationWarning: The anyio.abc.BlockingPortal alias is deprecated, use anyio.from_thread.BlockingPortal instead.`  
   *Source*: Starlette's `TestClient` initialization with upstream AnyIO 4.x.
2. `tests/test_hardening.py::test_request_body_size_limit`: `DeprecationWarning: 'HTTP_413_REQUEST_ENTITY_TOO_LARGE' is deprecated. Use 'HTTP_413_CONTENT_TOO_LARGE' instead.`  
   *Source*: Starlette `BaseHTTPMiddleware` internal handling during client request exception wrapping.
3-6. `tests/test_roadmap.py::test_invalid_status_returns_422` (x4 occurrences): `DeprecationWarning: 'HTTP_422_UNPROCESSABLE_ENTITY' is deprecated. Use 'HTTP_422_UNPROCESSABLE_CONTENT' instead.`  
   *Source*: Direct references to `status.HTTP_422_UNPROCESSABLE_ENTITY` in assertions in `tests/test_roadmap.py` lines 122, 126, 130, 134.

---

## 6. Configuration Audit

### Environment Variables in `config.py`
| Environment Variable | Required in Schema | Has Default |
|---|---|---|
| `APP_ENV` | No | Yes (`"development"`) |
| `APP_NAME` | No | Yes (`"Pebble"`) |
| `API_PREFIX` | No | Yes (`"/api/v1"`) |
| `DEBUG` | No | Yes (`True`) |
| `DATABASE_URL` | No* | Yes (`""`) |
| `TEST_DATABASE_URL` | No | Yes (`None`) |
| `SECRET_KEY` | No | Yes (`"dev-secret-key-change-in-production-min-32-chars"`) |
| `JWT_SECRET` | No | Yes (`"dev-jwt-secret-key-change-in-production-min-32-chars"`) |
| `JWT_ALGORITHM` | No | Yes (`"HS256"`) |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Yes (`60`) |
| `CORS_ORIGINS` | No | Yes (`["http://localhost:5173"]`) |
| `VIDEO_PROVIDER` | No | Yes (`"mock"`) |
| `VIDEO_ENGINE_URL` | No | Yes (`"http://localhost:8001"`) |
| `VIDEO_ENGINE_API_KEY` | No | Yes (`"dev-video-engine-api-key-secret"`) |

*\*Note: While all schema fields define defaults to allow instantiation in isolated tests, `DATABASE_URL` is required functionally at runtime for database connections.*

- **Current Value of `VIDEO_PROVIDER`**: `mock`
- **JWT_SECRET is not a default or placeholder and is at least 32 characters**: **No**  
  *(Currently set to the default placeholder: `"dev-jwt-secret-key-change-in-production-min-32-chars"`).*

---

## 7. Security Check

| Check Item | Result | Evidence |
|---|---|---|
| Every route except register, login, and health uses `get_current_user` | **Yes** | Inspected `app.routes` and AST; all business endpoints require `Depends(get_current_user)`. Only `/auth/register`, `/auth/login`, `/health`, and Swagger UI/OpenAPI docs are public. |
| Rate limits on messages and video jobs (30/min) are keyed per user, not per IP | **Yes** | `backend/app/core/rate_limit.py` line 9 (`get_user_or_ip`) parses `Authorization: Bearer <token>`, decodes JWT claims, and returns `user:<sub_id>`. |
| A test proves they return 429 | **No** | Login rate limit has a test (`tests/test_auth.py::test_login_rate_limit_429`), but there is no test verifying that 31 requests to `/conversations/{id}/messages` or `/video-jobs` return 429. |
| The 200 KB body limit stops requests without a Content-Length header (chunked) | **Yes** | `backend/app/core/middleware.py` lines 44-67 (`limited_receive`) accumulates byte chunks into `total_bytes` and raises `BodySizeExceededError` if `total_bytes > 204,800`. |
| `.env` is not tracked (`git ls-files`) | **Yes** | `.gitignore` specifies `.env`, `.env.local`, `*.secret` (line 31). Git is not currently tracking `.env`. |
| Nothing prints secrets, tokens, or full user code in logs | **Yes** | `SensitiveDataFilter` installed on root, `backend`, and `uvicorn` loggers in `backend/app/core/logging.py`; redacts JWTs, Bearer headers, passwords, connection string passwords, and full user code. Verified in `tests/test_hardening.py::test_sensitive_data_logging_filter`. |

---

## 8. Video Contract Audit

### Generated Payloads for the Four Contract Cases

#### Case 1: Curated Repo Solution
```json
{
  "question": {
    "id": 1,
    "slug": "two-sum",
    "title": "Two Sum"
  },
  "solution": {
    "code": "class Solution:\n    def twoSum(self, nums, target):\n        return []",
    "programming_language": "python",
    "validated": true
  },
  "preferences": {
    "explanation_language": "English",
    "explanation_style": "beginner_friendly"
  }
}
```

#### Case 2: User Code
```json
{
  "question": {
    "id": 1,
    "slug": "two-sum",
    "title": "Two Sum"
  },
  "solution": {
    "code": "def my_two_sum(nums):\n    pass",
    "programming_language": "python",
    "validated": false
  },
  "preferences": {
    "explanation_language": "English",
    "explanation_style": "technical"
  }
}
```

#### Case 3: No Solution
```json
{
  "question": {
    "id": 1,
    "slug": "two-sum",
    "title": "Two Sum"
  },
  "solution": {},
  "preferences": {
    "explanation_language": "Hindi",
    "explanation_style": "both"
  }
}
```

#### Case 4: Unknown Problem (Problem not in database)
```json
{
  "question": {
    "id": null,
    "slug": null,
    "title": "What is binary search?"
  },
  "solution": {},
  "preferences": {
    "explanation_language": "English",
    "explanation_style": "beginner_friendly"
  }
}
```

### Differences from `docs/video-contract.md`
- **Differences Found**: **None (0 differences)**.
- All four cases align identically with `docs/video-contract.md` section 2.
- Language mappings (`en` -> `"English"`, `hi` -> `"Hindi"`) and style mappings (`beginner` -> `"beginner_friendly"`, `technical` -> `"technical"`, `both` -> `"both"`) match exactly.
- All prohibited fields (`fingerprint`, `source`, `include_narration`, `description`, `examples`, `constraints`, `notes`) are omitted.

### `HttpVideoProvider` Transport Specification
- **Submit**:
  - Request: `POST {VIDEO_ENGINE_URL}/render`
  - Headers: `{"X-API-Key": "<VIDEO_ENGINE_API_KEY>", "Content-Type": "application/json"}`
  - Body: JSON rendered above from `PayloadBuilder`
  - Timeout: 10.0 seconds
  - Expected Response: HTTP 200 with `{"job_id": "<job_id_string>"}`
- **Get Status**:
  - Request: `GET {VIDEO_ENGINE_URL}/jobs/{job_id}`
  - Headers: `{"X-API-Key": "<VIDEO_ENGINE_API_KEY>", "Content-Type": "application/json"}`
  - Body: None
  - Timeout: 10.0 seconds
  - Expected Response: HTTP 200 with `{"status": "queued|running|completed|failed", "stage": "rendering|narration|assembling|uploading", "video_url": "...", "blob_name": "...", "error": null}`
- **Test Coverage**:
  - Does a test cover `HttpVideoProvider`? **No** (all tests use `MockVideoProvider`).
  - Does a test cover the HEAD-check regeneration rule (`_verify_video_url_live`)? **No** (mock mode skips the HEAD check, and no unit test exercises it).

---

## 9. Dead or Unused Code Analysis (If Dropping Onboarding & Roadmap, Keeping Login + Single `POST /ask`)

If onboarding and roadmap are dropped in favor of authentication plus a single stateless `POST /ask` endpoint, the following components would become unused:

### 1. Routes (16 Routes)
- `/users/me/onboarding` (`POST`)
- `/users/me/preferences` (`GET`, `PUT`)
- `/users/me` (`GET`, `PATCH`)
- `/roadmap` (`GET`)
- `/roadmap/problems/{problem_id}` (`PATCH`)
- `/progress` (`GET`)
- `/conversations` (`GET`, `POST`)
- `/conversations/{id}` (`GET`)
- `/conversations/{id}/messages` (`POST`)
- `/video-jobs` (`POST`)
- `/video-jobs/{id}` (`GET`)
- `/video-jobs/{id}/result` (`GET`)
- `/video-jobs/{id}/retry` (`POST`)
- `/problems/resolve` (`GET`), `/problems/{id}` (`GET`), `/problems/{id}/solutions` (`GET`) *(if internal to `/ask`)*

### 2. Files
- `backend/app/data/roadmaps.json`
- `backend/app/api/roadmap.py`
- `backend/app/api/conversations.py`
- `backend/app/api/users.py`
- `backend/app/services/roadmap_service.py`
- `backend/app/services/onboarding_service.py`
- `backend/app/repositories/roadmap_repository.py`
- `backend/app/repositories/progress_repository.py`
- `backend/app/repositories/preferences_repository.py`
- `backend/app/repositories/conversation_repository.py`
- `backend/app/repositories/message_repository.py`
- `backend/app/schemas/roadmap.py`
- `backend/app/schemas/conversation.py`

### 3. Tests
- `tests/test_roadmap.py` (all 5 tests)
- `tests/test_chat.py` (all 7 tests)
- In `tests/test_users.py`: `test_onboarding_sets_onboarding_completed`, `test_preferences_save_and_reload`
- In `tests/test_schemas.py`: `test_chat_result_schema`, `test_chat_response_schema`, `test_preferences_schema_valid`, `test_preferences_schema_invalid`

### 4. Database Tables (6 Tables)
- `roadmaps`
- `roadmap_problems`
- `user_progress`
- `conversations`
- `messages`
- `user_preferences`

---

## 10. Top 10 Risks or Gaps

1. **Placeholder Secrets in Production Config**: `JWT_SECRET` and `SECRET_KEY` currently use development default placeholders and must be rotated to cryptographically random secrets in production.
2. **Zero Ingested Problems in Primary DB**: The primary database has 0 problems and 0 solutions, meaning problem resolution and solution lookups will fail until `scripts/ingest_solutions.py` is executed against it.
3. **Untested HTTP Video Provider**: `HttpVideoProvider` has zero unit or mock tests, leaving real HTTP integration with the teammate's Azure Video Engine unverified in CI.
4. **Untested Blob Live Verification**: The video URL HEAD-check regeneration rule (`_verify_video_url_live`) is bypassed in mock mode and has no automated test coverage.
5. **Missing 429 Test Coverage for New Limits**: While rate limiting is implemented on `/conversations/{id}/messages` and `/video-jobs`, no test currently validates that 31+ requests trigger an HTTP 429.
6. **In-Memory Background Worker State**: Video generation polling and job completion runs via FastAPI `BackgroundTasks`, which can lose progress if the uvicorn process restarts while jobs are rendering.
7. **Missing Git Repository Tracking**: The local workspace root is not initialized as a git repository (`fatal: not a git repository`), which impairs automated revision auditing and CI/CD secret scanning.
8. **Stateless `POST /ask` Vision Gap**: There is no `/ask` endpoint implemented in the backend; requests currently rely on a stateful `/conversations/{id}/messages` flow.
9. **No Code Validation on Ingested Solutions**: Solutions ingested from WalkCCC are marked `validated=true` without running AST linting or compile checks.
10. **Starlette and Pytest Deprecation Warnings**: Six deprecation warnings are emitted during test runs (`HTTP_422_UNPROCESSABLE_ENTITY`, `HTTP_413_REQUEST_ENTITY_TOO_LARGE`, and AnyIO `BlockingPortal`).
