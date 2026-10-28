"""Tests for video_request and video_payload population in AskService.ask across all can_generate=True branches."""

import os
import uuid
import pytest
from backend.app.config import Settings
from backend.app.core.security import create_access_token, hash_password
from backend.app.repositories.user_repository import UserRepository
from backend.app.schemas.video import CreateVideoJobRequest
from backend.app.services.ask_service import AskService
from backend.app.services.ingest_service import IngestService

FAKE_REPO_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "fake_repo")


@pytest.fixture
def auth_headers(db_session):
    """Create a verified test user and return Bearer auth headers."""
    user = UserRepository.create(
        db=db_session,
        email=f"video_req_tester_{uuid.uuid4().hex[:8]}@example.com",
        name="Video Req Tester",
        password_hash=hash_password("StrongPassword123!"),
    )
    db_session.flush()
    token = create_access_token(str(user.id))
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def seeded_db(db_session):
    """Seed test database with fake_repo problems and solutions."""
    service = IngestService()
    service.ingest(db=db_session, repo_path=FAKE_REPO_DIR, commit_sha="test_commit_sha_123")
    return db_session


@pytest.fixture(autouse=True)
def disable_intent_provider(monkeypatch):
    """Ensure standard query branches are tested without external LLM calls."""
    test_settings = Settings(INTENT_PROVIDER="off")
    monkeypatch.setattr("backend.app.services.ask_service.get_settings", lambda: test_settings)


# ---------------------------------------------------------------------------
# Branch 1: status="found"
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_ask_found_branch_video_request_and_payload(seeded_db):
    """Problem resolved with available solution sets video_request and video_payload."""
    service = AskService()
    resp = service.ask(db=seeded_db, text="1", programming_language="python")

    assert resp.status == "found"
    assert resp.can_generate is True
    assert resp.problem is not None
    assert resp.problem.id == 1

    # video_request assertions
    assert isinstance(resp.video_request, CreateVideoJobRequest)
    assert resp.video_request.problem_id == 1
    assert resp.video_request.programming_language == "python"

    # video_payload assertions
    assert resp.video_payload is not None
    assert resp.video_payload["question"]["id"] == 1
    assert resp.video_payload["question"]["slug"] == "two-sum"
    assert resp.video_payload["solution"]["programming_language"] == "python"
    assert resp.video_payload["solution"]["validated"] is True
    assert "code" in resp.video_payload["solution"]
    assert resp.video_payload["preferences"]["explanation_language"] == "English"
    assert resp.video_payload["preferences"]["explanation_style"] == "beginner_friendly"


# ---------------------------------------------------------------------------
# Branch 2: status="no_solution"
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_ask_no_solution_branch_video_request_and_payload(seeded_db):
    """Problem resolved without available solution sets video_request and video_payload."""
    service = AskService()
    # Problem 2 (Add Two Numbers) only has cpp and python in fake_repo, no java
    resp = service.ask(db=seeded_db, text="2", programming_language="java")

    assert resp.status == "no_solution"
    assert resp.can_generate is True
    assert resp.problem is not None
    assert resp.problem.id == 2

    # video_request assertions
    assert isinstance(resp.video_request, CreateVideoJobRequest)
    assert resp.video_request.problem_id == 2
    assert resp.video_request.programming_language == "java"

    # video_payload assertions
    assert resp.video_payload is not None
    assert resp.video_payload["question"]["id"] == 2
    assert resp.video_payload["solution"]["programming_language"] == "java"
    assert "code" not in resp.video_payload["solution"]
    assert resp.video_payload["preferences"]["explanation_language"] == "English"
    assert resp.video_payload["preferences"]["explanation_style"] == "beginner_friendly"


# ---------------------------------------------------------------------------
# Branch 3: status="concept"
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_ask_concept_branch_video_request_and_payload(seeded_db):
    """Concept query passing DSA keyword gate sets video_request and video_payload."""
    service = AskService()
    query = "explain how dynamic programming and memoization optimize recursive algorithms"
    resp = service.ask(db=seeded_db, text=query, programming_language="cpp")

    assert resp.status == "concept"
    assert resp.can_generate is True

    # video_request assertions
    assert isinstance(resp.video_request, CreateVideoJobRequest)
    assert resp.video_request.problem_id is None
    assert resp.video_request.text == query[:300]
    assert resp.video_request.programming_language == "cpp"

    # video_payload assertions
    assert resp.video_payload is not None
    assert resp.video_payload["question"]["id"] is None
    assert resp.video_payload["question"]["title"] == query[:300]
    assert resp.video_payload["solution"]["programming_language"] == "cpp"
    assert "code" not in resp.video_payload["solution"]
    assert resp.video_payload["preferences"]["explanation_language"] == "English"
    assert resp.video_payload["preferences"]["explanation_style"] == "beginner_friendly"


# ---------------------------------------------------------------------------
# Branch 4: pasted-code branch
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_ask_pasted_code_without_problem_video_request_and_payload(seeded_db):
    """Pasted code without a problem sets user_code, video_request, and video_payload."""
    code_text = (
        "```python\n"
        "def custom_algorithm(x):\n"
        "    return x * 2\n"
        "```"
    )
    service = AskService()
    resp = service.ask(db=seeded_db, text=code_text, programming_language="python")

    assert resp.status == "concept"
    assert resp.can_generate is True

    # video_request assertions
    assert isinstance(resp.video_request, CreateVideoJobRequest)
    assert resp.video_request.user_code == "def custom_algorithm(x):\n    return x * 2"
    assert resp.video_request.programming_language == "python"

    # video_payload assertions
    assert resp.video_payload is not None
    assert resp.video_payload["solution"]["code"] == "def custom_algorithm(x):\n    return x * 2"
    assert resp.video_payload["solution"]["programming_language"] == "python"
    assert resp.video_payload["solution"]["validated"] is False
    assert resp.video_payload["preferences"]["explanation_language"] == "English"
    assert resp.video_payload["preferences"]["explanation_style"] == "beginner_friendly"


@pytest.mark.db
def test_ask_pasted_code_with_problem_video_request_and_payload(seeded_db):
    """Pasted code with resolved problem sets problem_id, user_code, video_request, and video_payload."""
    code_text = (
        "1. Two Sum\n"
        "```python\n"
        "def twoSum(nums, target):\n"
        "    return []\n"
        "```"
    )
    service = AskService()
    resp = service.ask(db=seeded_db, text=code_text, programming_language="python")

    assert resp.status == "found"
    assert resp.can_generate is True
    assert resp.problem is not None
    assert resp.problem.id == 1

    # video_request assertions
    assert isinstance(resp.video_request, CreateVideoJobRequest)
    assert resp.video_request.problem_id == 1
    assert resp.video_request.user_code == "def twoSum(nums, target):\n    return []"
    assert resp.video_request.programming_language == "python"

    # video_payload assertions
    assert resp.video_payload is not None
    assert resp.video_payload["question"]["id"] == 1
    assert resp.video_payload["solution"]["code"] == "def twoSum(nums, target):\n    return []"
    assert resp.video_payload["solution"]["programming_language"] == "python"
    assert resp.video_payload["solution"]["validated"] is False
    assert resp.video_payload["preferences"]["explanation_language"] == "English"
    assert resp.video_payload["preferences"]["explanation_style"] == "beginner_friendly"


@pytest.mark.db
def test_ask_api_endpoint_returns_video_request_and_payload(client, seeded_db, auth_headers):
    """POST /ask returns video_request and video_payload in response JSON."""
    payload = {"text": "1", "programming_language": "python"}
    resp = client.post("/ask", json=payload, headers=auth_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "found"
    assert data["can_generate"] is True
    assert data["video_request"] is not None
    assert data["video_request"]["problem_id"] == 1
    assert data["video_request"]["programming_language"] == "python"
    assert data["video_payload"] is not None
    assert data["video_payload"]["question"]["id"] == 1
