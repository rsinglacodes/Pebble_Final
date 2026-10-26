# API Contract

## Architecture & System Boundary
- **Single LLM Engine**: There is ONE LLM, owned by teammate (hosted on Azure). The Pebble backend never generates or validates code.
- **No Local Code Sandbox**: There is no sandbox, code execution engine, repair loop, trace engine, or scene planner in this backend.
- **Single-Page DSA Core**: The user flow consists of authentication and one page featuring a query text input and programming language dropdown (`python`, `java`, `cpp`).

---

## TypeScript Interfaces

```typescript
type ProgrammingLanguage = 'python' | 'java' | 'cpp';

interface AskRequest {
  text: string; // 1-5000 characters
  programming_language?: ProgrammingLanguage; // default: 'python'
}

interface ProblemInfo {
  id: number;
  slug: string;
  title: string;
  source_url?: string;
}

interface SolutionInfo {
  language: string;
  code: string;
  validated: boolean;
}

interface CandidateInfo {
  id: number;
  slug: string;
  title: string;
}

interface AskResponse {
  status: 'found' | 'no_solution' | 'clarify' | 'concept' | 'out_of_scope';
  message: string;
  problem?: ProblemInfo;
  solution?: SolutionInfo;
  available_languages: string[];
  candidates?: CandidateInfo[];
  can_generate: boolean;
}

interface HistoryProblemInfo {
  id: number;
  slug: string;
  title: string;
}

interface HistoryItemResponse {
  id: string; // UUID
  text: string;
  status: 'found' | 'no_solution' | 'clarify' | 'concept';
  problem: HistoryProblemInfo | null;
  programming_language: string;
  created_at: string; // ISO 8601 timestamp
}

interface VideoJob {
  id: string;
  status: 'queued' | 'running' | 'completed' | 'failed';
  stage: string;
  video_url?: string;
  error?: string;
}

interface HealthResponse {
  status: 'ok';
  db: boolean;
}
```

---

## Endpoints

### 1. Authentication & Users
- `POST /auth/register`: Register with `email`, `password`, `name`. Returns JWT access token.
- `POST /auth/login`: Authenticate with `email` and `password`. Returns JWT access token.
- `GET /users/me`: Return current user profile (`id`, `email`, `name`, `onboarding_completed`).
- `PATCH /users/me`: Update user `name`.

### 2. Query & DSA Resolution
- `POST /ask`: Primary problem resolution and concept entry point.
  - **Auth**: Required (`Bearer <token>`).
  - **Rate Limit**: 30 requests/minute per authenticated user.
  - **Payload**: `AskRequest` (`text`, `programming_language`).
  - **Statuses**:
    - `found`: Problem resolved and stored solution exists for requested language (`validated: true`). If pasted code, `validated: false`. Stores 1 `ask_history` row.
    - `no_solution`: Problem resolved but solution missing for requested language. Message: `"No stored <Language> solution for this problem. Pebble will generate one with the video."`. Stores 1 `ask_history` row.
    - `clarify`: Multiple weak matches returned as up to 3 candidates in `candidates`. Stores 1 `ask_history` row.
    - `concept`: Text resolves to no problem but passes DSA keyword scope gate. Message: `"Pebble will generate the explanation from your description."`. Stores 1 `ask_history` row.
    - `out_of_scope`: Non-DSA query or prompt injection attempt. Message: `"Sorry, I can only help with data structures and algorithms. Try a LeetCode number, a problem name, or a topic like arrays, trees or graphs."`. Stores nothing.
  - **Privacy**: Request `text` is never logged in application logs and redacted in the log filter. History insertion errors never fail `/ask`.

### 3. Question History
- `GET /history`: Retrieve current user's question history ordered newest first (`limit` query param defaults to 20, max 50).
- `DELETE /history/{id}`: Delete a single history entry owned by current user. Another user's row returns 404.
- `DELETE /history`: Delete all history entries owned by current user.

### 4. Problems Catalog
- `GET /problems`: List catalog problems with pagination.
- `GET /problems/{id}`: Retrieve problem details by external ID, UUID, or slug.
- `GET /problems/{id}/solutions`: Retrieve problem solutions filtered by language.
- `GET /problems/resolve`: Resolve query `q` using exact match or trigram similarity.

### 5. Video Jobs
- `POST /video-jobs`: Enqueue a video generation job for a problem or concept.
- `GET /video-jobs/{job_id}`: Poll video job status.
- `GET /video-jobs/{job_id}/stream`: Stream real-time video generation updates via SSE.

### 6. System Health
- `GET /health`: Health probe returning API status and database connectivity.