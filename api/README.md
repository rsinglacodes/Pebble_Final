# Pebble — AI-Based DSA Learning Platform

Pebble is an AI-powered DSA learning companion that helps students understand coding problems and algorithms through personalized explanations, execution-based visualizations, and narrated educational videos.

---

## Architecture Overview

- **Backend**: FastAPI with a strict layered architecture:
  `backend/app/{api,core,db,models,schemas,repositories,services,integrations,rag,code_execution,workers}`
  - **Routes**: Thin HTTP controllers mounted on plain base paths (`/auth`, `/users`, `/problems`, `/conversations`, `/video-jobs`, `/roadmap`, `/progress`, `/health`).
  - **Services**: Business logic, chat scope verification, roadmap progression, video job coordination.
  - **Repositories**: SQL / database operations (SQLAlchemy 2.0 + psycopg 3).
  - **Core & Hardening**:
    - Request body size limit enforced at 200 KB (`BodySizeLimitMiddleware`).
    - Sensitive data scrubbing in all logs (`SensitiveDataFilter` masks tokens, passwords, secrets, connection strings, and full user code).
    - Global safe error responses (returns `{ "error": ... }` and suppresses internal stack traces).
    - Rate limiting via SlowAPI (30 requests/minute on `POST /conversations/{id}/messages` and `POST /video-jobs`).
- **Database**: Neon PostgreSQL with `pg_trgm` extension for trigram similarity search on LeetCode problems.
- **Video Engine**: Standalone service (`video-engine/`) owned by teammate, communicating via `backend/app/integrations/video/` per `docs/video-contract.md`.
- **API Spec**: Exported OpenAPI 3.1 specification available at `docs/openapi.json`.

---

## Getting Started (Windows PowerShell)

Follow these steps in Windows PowerShell to set up and run the backend:

### 1. Create and Activate Virtual Environment

```powershell
# Navigate to the project root
cd d:\Pebble

# Create virtual environment
python -m venv venv

# Activate virtual environment
.\venv\Scripts\Activate.ps1
```

> **Note**: If script execution is restricted on Windows, run:
> `Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser`

### 2. Configure Environment Variables

```powershell
# Copy template to .env
Copy-Item .env.example .env
```

Configure your `.env` file (which is gitignored):
```env
APP_ENV=development
APP_NAME=Pebble
DEBUG=true

# Neon PostgreSQL connection string (psycopg 3 driver)
DATABASE_URL=postgresql+psycopg://neondb_owner:YOUR_PASSWORD@ep-sample-pooler.us-east-2.aws.neon.tech/neondb?sslmode=require
TEST_DATABASE_URL=postgresql+psycopg://neondb_owner:YOUR_TEST_PASSWORD@ep-sample-test.us-east-2.aws.neon.tech/neondb?sslmode=require

SECRET_KEY=dev-secret-key-change-in-production-min-32-chars
JWT_SECRET=dev-jwt-secret-key-change-in-production-min-32-chars
CORS_ORIGINS=["http://localhost:5173"]

# Teammate Video Engine integration
VIDEO_PROVIDER=mock
VIDEO_ENGINE_URL=http://localhost:8001
VIDEO_ENGINE_API_KEY=dev-video-engine-api-key-secret
```

### 3. Install Dependencies

```powershell
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Database Migrations (Alembic)

Apply database schema migrations to Neon PostgreSQL:

```powershell
# Run all pending migrations
alembic upgrade head

# Or specify custom config path if running from another directory:
alembic -c alembic.ini upgrade head

# Revert the last migration:
alembic downgrade -1
```

### 5. Ingest LeetCode Problems & Solutions

Ingest curated solutions from `walkccc/LeetCode` into PostgreSQL with `pg_trgm` indexing:

```powershell
# Default: Clones walkccc/LeetCode into data/source_repo (gitignored) and ingests Python, Java, and C++ solutions
python scripts/ingest_solutions.py

# Optional: Specify custom repository directory or clone URL
python scripts/ingest_solutions.py --repo-path data/source_repo --repo-url https://github.com/walkccc/LeetCode
```

### 6. Run Development Server

```powershell
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
```

- API Health Check: [http://127.0.0.1:8000/health](http://127.0.0.1:8000/health)
- Interactive Swagger UI: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Interactive ReDoc: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)
- Static OpenAPI Spec: `docs/openapi.json`

### 7. Run Test Suite

Run the full pytest suite:

```powershell
pytest -v
```

---

## API Endpoints Summary

| Endpoint | Method | Description | Rate Limit |
|---|---|---|---|
| `/health` | GET | System health & status check | None |
| `/auth/register` | POST | Register a new user | None |
| `/auth/login` | POST | Authenticate user & retrieve JWT | None |
| `/users/me` | GET | Current user profile | None |
| `/users/me/preferences` | PATCH | Update user learning preferences | None |
| `/users/me/onboarding` | POST | Complete user onboarding & auto-provision roadmap | None |
| `/roadmap` | GET | Fetch user's personalized DSA problem roadmap | None |
| `/roadmap/problems/{problem_id}` | PATCH | Update problem progress (`not_started`, `in_progress`, `solved`) | None |
| `/progress` | GET | Aggregated completion counts for user roadmap | None |
| `/problems/resolve` | GET | Search problems by title or slug similarity (`pg_trgm`) | None |
| `/problems/{id}` | GET | Retrieve problem details | None |
| `/problems/{id}/solutions` | GET | Retrieve multi-language solutions for problem | None |
| `/conversations` | POST | Create a new chat conversation | None |
| `/conversations` | GET | List user's conversations | None |
| `/conversations/{id}` | GET | Retrieve conversation messages and metadata | None |
| `/conversations/{id}/messages` | POST | Send DSA message / question | 30 / min |
| `/video-jobs` | POST | Create video explanation generation job | 30 / min |
| `/video-jobs` | GET | List user's video jobs | None |
| `/video-jobs/{id}` | GET | Check video job status | None |
| `/video-jobs/{id}/result` | GET | Retrieve completed video render result | None |
| `/video-jobs/{id}/retry` | POST | Retry a failed video job | None |
