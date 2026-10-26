"""Tests for LeetCode solution ingestion, directory parsing, and problem search/resolve endpoints."""

import os
import shutil
import uuid
import pytest
from fastapi import status
from fastapi.testclient import TestClient
from backend.app.core.security import create_access_token, hash_password
from backend.app.repositories.user_repository import UserRepository
from backend.app.services.ingest_service import IngestService

FAKE_REPO_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "fake_repo")


# ---------------------------------------------------------------------------
# Unit Tests (No Database Required)
# ---------------------------------------------------------------------------


def test_parse_problem_dir_valid_names():
    """Verify parse_problem_dir extracts number, title, and slug correctly."""
    assert IngestService.parse_problem_dir("1. Two Sum") == (1, "Two Sum", "two-sum")
    assert IngestService.parse_problem_dir("2. Add Two Numbers") == (
        2,
        "Add Two Numbers",
        "add-two-numbers",
    )
    assert IngestService.parse_problem_dir("15. 3Sum") == (15, "3Sum", "3sum")
    assert IngestService.parse_problem_dir(
        "3. Longest Substring Without Repeating Characters"
    ) == (
        3,
        "Longest Substring Without Repeating Characters",
        "longest-substring-without-repeating-characters",
    )
    assert IngestService.parse_problem_dir(
        "1576. Replace All ?'s to Avoid Consecutive Repeating Characters"
    ) == (
        1576,
        "Replace All ?'s to Avoid Consecutive Repeating Characters",
        "replace-all-s-to-avoid-consecutive-repeating-characters",
    )


def test_parse_problem_dir_invalid_names():
    """Verify parse_problem_dir returns None for non-conforming folder names."""
    assert IngestService.parse_problem_dir("solutions") is None
    assert IngestService.parse_problem_dir("README.md") is None
    assert IngestService.parse_problem_dir(".git") is None
    assert IngestService.parse_problem_dir("Two Sum") is None
    assert IngestService.parse_problem_dir("123") is None


# ---------------------------------------------------------------------------
# Fixtures for DB-backed problem tests
# ---------------------------------------------------------------------------


@pytest.fixture
def auth_headers(db_session):
    """Create a verified test user and return Bearer auth headers."""
    user = UserRepository.create(
        db=db_session,
        email=f"prob_tester_{uuid.uuid4().hex[:8]}@example.com",
        name="Problem Tester",
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


# ---------------------------------------------------------------------------
# Integration Tests (Requires Database)
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_ingest_idempotency_and_hash_diff(db_session, tmp_path):
    """Test first ingest, idempotent re-run (0 new problems/solutions), and update on content_hash diff."""
    service = IngestService()

    # Copy fake_repo to tmp_path so we can safely edit files
    test_repo = tmp_path / "test_repo"
    shutil.copytree(FAKE_REPO_DIR, test_repo)

    # 1. First run: creates problems and solutions
    stats1 = service.ingest(db=db_session, repo_path=str(test_repo), commit_sha="sha_v1")
    assert stats1.problems_created == 4  # 4 problem directories detected (solutions for 3 and 4 skipped)
    assert stats1.problems_updated == 0
    assert stats1.solutions_created["python"] == 2
    assert stats1.solutions_created["cpp"] == 2
    assert stats1.solutions_created["java"] == 1
    # Check that skipped files were recorded
    assert any("TypeScript" in reason for reason in stats1.skipped_files)
    assert any("MySQL" in reason for reason in stats1.skipped_files)

    # 2. Second run: identical files -> 0 created, 0 updated, all unchanged
    stats2 = service.ingest(db=db_session, repo_path=str(test_repo), commit_sha="sha_v1")
    assert stats2.problems_created == 0
    assert stats2.problems_updated == 0
    assert stats2.problems_unchanged == 4
    assert stats2.solutions_created["python"] == 0
    assert stats2.solutions_updated["python"] == 0
    assert stats2.solutions_unchanged["python"] == 2
    assert stats2.solutions_created["cpp"] == 0
    assert stats2.solutions_updated["cpp"] == 0
    assert stats2.solutions_created["java"] == 0
    assert stats2.solutions_updated["java"] == 0

    # 3. Modify one python solution file and re-run -> 0 new problems, 1 updated solution
    two_sum_py = test_repo / "solutions" / "1. Two Sum" / "1.py"
    with open(two_sum_py, "a", encoding="utf-8") as f:
        f.write("\n# Optimized with single-pass hash map\n")

    stats3 = service.ingest(db=db_session, repo_path=str(test_repo), commit_sha="sha_v2")
    assert stats3.problems_created == 0
    assert stats3.problems_updated == 0
    assert stats3.problems_unchanged == 4
    assert stats3.solutions_created["python"] == 0
    assert stats3.solutions_updated["python"] == 1
    assert stats3.solutions_unchanged["python"] == 1  # 2.py remained unchanged


@pytest.mark.db
def test_resolve_by_number(client, seeded_db, auth_headers):
    """GET /problems/resolve?q=1&language=python resolves by exact problem number."""
    resp = client.get("/problems/resolve?q=1&language=python", headers=auth_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["resolved"] is True
    assert data["problem"]["id"] == 1
    assert data["problem"]["slug"] == "two-sum"
    assert data["problem"]["title"] == "Two Sum"
    assert data["solution"] is not None
    assert data["solution"]["language"] == "python"
    assert data["solution"]["validated"] is True
    assert "twoSum" in data["solution"]["code"]
    assert set(data["available_languages"]) == {"cpp", "java", "python"}


@pytest.mark.db
def test_resolve_by_slug(client, seeded_db, auth_headers):
    """GET /problems/resolve?q=two-sum&language=java resolves by exact slug."""
    resp = client.get("/problems/resolve?q=two-sum&language=java", headers=auth_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["resolved"] is True
    assert data["problem"]["id"] == 1
    assert data["problem"]["slug"] == "two-sum"
    assert data["solution"]["language"] == "java"
    assert data["solution"]["validated"] is True


@pytest.mark.db
def test_resolve_by_url(client, seeded_db, auth_headers):
    """GET /problems/resolve resolves by full LeetCode problem URL."""
    resp = client.get(
        "/problems/resolve?q=https://leetcode.com/problems/two-sum/&language=cpp",
        headers=auth_headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["resolved"] is True
    assert data["problem"]["slug"] == "two-sum"
    assert data["solution"]["language"] == "cpp"

    # Also test URL with trailing /description
    resp2 = client.get(
        "/problems/resolve?q=https://leetcode.com/problems/add-two-numbers/description",
        headers=auth_headers,
    )
    assert resp2.status_code == status.HTTP_200_OK
    data2 = resp2.json()
    assert data2["resolved"] is True
    assert data2["problem"]["slug"] == "add-two-numbers"


@pytest.mark.db
def test_resolve_by_typo_trgm(client, seeded_db, auth_headers):
    """GET /problems/resolve?q=twosum fuzzy matches 'Two Sum' via pg_trgm similarity."""
    resp = client.get("/problems/resolve?q=twosum", headers=auth_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["resolved"] is True
    assert data["problem"]["slug"] == "two-sum"
    assert data["candidates"] is not None
    assert len(data["candidates"]) >= 1
    assert data["candidates"][0]["score"] >= 0.4


@pytest.mark.db
def test_resolve_unknown_problem(client, seeded_db, auth_headers):
    """GET /problems/resolve?q=unknown returns resolved=false with candidates list."""
    resp = client.get(
        "/problems/resolve?q=completely-unknown-nonexistent-problem-xyz",
        headers=auth_headers,
    )
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["resolved"] is False
    assert data["problem"] is None
    assert data["solution"] is None
    assert isinstance(data["candidates"], list)


@pytest.mark.db
def test_resolve_missing_language_and_solutions_endpoint(client, seeded_db, auth_headers):
    """Test resolution with missing language, and GET /problems/{id}/solutions behavior."""
    # 1. Resolve with unsupported language -> solution=null, available_languages intact
    resp = client.get("/problems/resolve?q=1&language=rust", headers=auth_headers)
    assert resp.status_code == status.HTTP_200_OK
    data = resp.json()
    assert data["resolved"] is True
    assert data["solution"] is None
    assert set(data["available_languages"]) == {"cpp", "java", "python"}

    # 2. GET /problems/{id}/solutions without language parameter returns empty list
    resp_empty = client.get("/problems/1/solutions", headers=auth_headers)
    assert resp_empty.status_code == status.HTTP_200_OK
    assert resp_empty.json() == []

    # 3. GET /problems/{id}/solutions with empty language query string returns empty list
    resp_empty_q = client.get("/problems/1/solutions?language=", headers=auth_headers)
    assert resp_empty_q.status_code == status.HTTP_200_OK
    assert resp_empty_q.json() == []

    # 4. GET /problems/{id}/solutions with unrepresented language returns empty list
    resp_rust = client.get("/problems/1/solutions?language=rust", headers=auth_headers)
    assert resp_rust.status_code == status.HTTP_200_OK
    assert resp_rust.json() == []

    # 5. GET /problems/{id}/solutions with matching language returns solution list
    resp_py = client.get("/problems/1/solutions?language=python", headers=auth_headers)
    assert resp_py.status_code == status.HTTP_200_OK
    py_sols = resp_py.json()
    assert len(py_sols) == 1
    assert py_sols[0]["language"] == "python"
    assert py_sols[0]["validated"] is True
    assert "twoSum" in py_sols[0]["code"]


@pytest.mark.db
def test_get_problem_by_id_and_slug(client, seeded_db, auth_headers):
    """GET /problems/{id} returns problem details or 404."""
    # Lookup by number
    resp_num = client.get("/problems/1", headers=auth_headers)
    assert resp_num.status_code == status.HTTP_200_OK
    data = resp_num.json()
    assert data["id"] == 1
    assert data["slug"] == "two-sum"
    assert data["title"] == "Two Sum"
    assert set(data["available_languages"]) == {"cpp", "java", "python"}

    # Lookup by slug
    resp_slug = client.get("/problems/add-two-numbers", headers=auth_headers)
    assert resp_slug.status_code == status.HTTP_200_OK
    assert resp_slug.json()["id"] == 2

    # Nonexistent problem returns 404
    resp_404 = client.get("/problems/99999", headers=auth_headers)
    assert resp_404.status_code == status.HTTP_404_NOT_FOUND


def test_problems_endpoints_require_authentication(client):
    """Unauthenticated calls to /problems endpoints return 401 Unauthorized."""
    assert client.get("/problems/resolve?q=1").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/problems/1").status_code == status.HTTP_401_UNAUTHORIZED
    assert client.get("/problems/1/solutions?language=python").status_code == status.HTTP_401_UNAUTHORIZED


# ---------------------------------------------------------------------------
# Ingestion Optimization, Batching, Resuming, Limit, and No-.git Tests
# ---------------------------------------------------------------------------


def test_get_commit_sha_no_git(tmp_path):
    """Verify get_commit_sha returns 'zip-download' when .git folder is absent."""
    service = IngestService()
    repo_dir = tmp_path / "repo_no_git"
    repo_dir.mkdir()
    assert service.get_commit_sha(str(repo_dir)) == "zip-download"


def test_clone_repository_skip_clone_and_existing_solutions(tmp_path, monkeypatch):
    """Verify clone_repository skips git clone when --skip-clone is set or solutions exists."""
    from scripts.ingest_solutions import clone_repository
    import subprocess

    called = []

    def fake_run(*args, **kwargs):
        called.append(args)

    monkeypatch.setattr(subprocess, "run", fake_run)

    # 1. --skip-clone flag skips clone
    empty_dir = tmp_path / "empty_dir"
    clone_repository("https://example.com/repo", str(empty_dir), skip_clone=True)
    assert len(called) == 0

    # 2. Existing solutions directory skips clone
    existing_solutions_dir = tmp_path / "repo_with_solutions"
    (existing_solutions_dir / "solutions").mkdir(parents=True)
    clone_repository("https://example.com/repo", str(existing_solutions_dir), skip_clone=False)
    assert len(called) == 0


@pytest.mark.db
def test_ingest_no_git_sets_zip_download(db_session, tmp_path):
    """Ingest without .git directory sets commit_sha to 'zip-download' without failing."""
    service = IngestService()
    test_repo = tmp_path / "test_repo_no_git"
    shutil.copytree(FAKE_REPO_DIR, test_repo)
    git_dir = test_repo / ".git"
    if git_dir.exists():
        shutil.rmtree(git_dir)

    stats = service.ingest(db=db_session, repo_path=str(test_repo), commit_sha=None)
    assert stats.problems_created == 4
    assert stats.solutions_created["python"] == 2

    from sqlalchemy import select
    from backend.app.models.solution import Solution
    sols = db_session.scalars(select(Solution)).all()
    assert len(sols) > 0
    for s in sols:
        assert s.commit_sha == "zip-download"
        assert "zip-download" in s.source_url


@pytest.mark.db
def test_ingest_limit_flag(db_session, tmp_path):
    """Test --limit N flag to ingest only the first N problems."""
    service = IngestService()
    test_repo = tmp_path / "test_repo_limit"
    shutil.copytree(FAKE_REPO_DIR, test_repo)

    # Ingest only first 1 problem
    stats_limit1 = service.ingest(
        db=db_session, repo_path=str(test_repo), commit_sha="limit_sha", limit=1
    )
    assert stats_limit1.problems_created == 1
    assert stats_limit1.problems_unchanged == 0
    assert stats_limit1.solutions_created["python"] == 1

    # Ingest with limit 2: problem 1 is unchanged, problem 2 is created
    stats_limit2 = service.ingest(
        db=db_session, repo_path=str(test_repo), commit_sha="limit_sha", limit=2
    )
    assert stats_limit2.problems_created == 1
    assert stats_limit2.problems_unchanged == 1
    assert stats_limit2.solutions_created["python"] == 1
    assert stats_limit2.solutions_unchanged["python"] == 1


@pytest.mark.db
def test_ingest_batching_resuming_and_idempotency(db_session, tmp_path):
    """Verify batching commits (batch_size=2), resuming on rerun, and updating only changed hashes."""
    service = IngestService()
    test_repo = tmp_path / "test_repo_batch"
    shutil.copytree(FAKE_REPO_DIR, test_repo)

    # 1. Initial ingestion with small batch_size=2 to test multi-batch commits
    stats1 = service.ingest(
        db=db_session, repo_path=str(test_repo), commit_sha="batch_v1", batch_size=2
    )
    assert stats1.problems_created == 4
    assert stats1.solutions_created["python"] == 2
    assert stats1.solutions_created["cpp"] == 2
    assert stats1.solutions_created["java"] == 1

    from sqlalchemy import select, func
    from backend.app.models.problem import Problem
    from backend.app.models.solution import Solution

    total_probs = db_session.scalar(select(func.count(Problem.id)))
    total_sols = db_session.scalar(select(func.count(Solution.id)))
    assert total_probs == 4
    assert total_sols == 5

    # 2. Resuming / Re-run with batch_size=2: all problems and solutions are unchanged, no duplicates
    stats2 = service.ingest(
        db=db_session, repo_path=str(test_repo), commit_sha="batch_v1", batch_size=2
    )
    assert stats2.problems_created == 0
    assert stats2.problems_updated == 0
    assert stats2.problems_unchanged == 4
    assert stats2.solutions_created["python"] == 0
    assert stats2.solutions_updated["python"] == 0
    assert stats2.solutions_unchanged["python"] == 2
    assert stats2.solutions_created["cpp"] == 0
    assert stats2.solutions_unchanged["cpp"] == 2
    assert stats2.solutions_created["java"] == 0
    assert stats2.solutions_unchanged["java"] == 1

    assert db_session.scalar(select(func.count(Problem.id))) == 4
    assert db_session.scalar(select(func.count(Solution.id))) == 5

    # 3. Modify 1 solution file and add a new solution file: only changed/new update, no duplicates
    p1_py = test_repo / "solutions" / "1. Two Sum" / "1.py"
    with open(p1_py, "a", encoding="utf-8") as f:
        f.write("\n# Modified code for hash diff test\n")

    p2_java = test_repo / "solutions" / "2. Add Two Numbers" / "2.java"
    with open(p2_java, "w", encoding="utf-8") as f:
        f.write("class Solution { /* java implementation */ }\n")

    stats3 = service.ingest(
        db=db_session, repo_path=str(test_repo), commit_sha="batch_v2", batch_size=2
    )
    assert stats3.problems_created == 0
    assert stats3.problems_updated == 0
    assert stats3.problems_unchanged == 4
    assert stats3.solutions_created["python"] == 0
    assert stats3.solutions_updated["python"] == 1  # 1.py was updated
    assert stats3.solutions_unchanged["python"] == 1  # 2.py was unchanged
    assert stats3.solutions_created["java"] == 1  # 2.java was newly created
    assert stats3.solutions_unchanged["java"] == 1  # 1.java was unchanged
    assert stats3.solutions_unchanged["cpp"] == 2  # all cpp unchanged

    assert db_session.scalar(select(func.count(Problem.id))) == 4
    assert db_session.scalar(select(func.count(Solution.id))) == 6
