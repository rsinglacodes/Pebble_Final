"""Tests for question history tracking, GET/DELETE /history, privacy, and resilience."""

import logging
import os
import uuid
import pytest
from unittest.mock import patch
from sqlalchemy import select

from backend.app.core.security import create_access_token, hash_password
from backend.app.models.ask_history import AskHistory
from backend.app.models.problem import Problem
from backend.app.repositories.user_repository import UserRepository
from backend.app.services.ingest_service import IngestService

FAKE_REPO_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "fake_repo")


@pytest.fixture
def auth_headers(db_session):
    """Create primary test user and return auth headers and user object."""
    user = UserRepository.create(
        db=db_session,
        email=f"hist_tester_{uuid.uuid4().hex[:8]}@example.com",
        name="History Tester",
        password_hash=hash_password("StrongPassword123!"),
    )
    db_session.flush()
    token = create_access_token(str(user.id))
    return {"headers": {"Authorization": f"Bearer {token}"}, "user": user}


@pytest.fixture
def other_user_headers(db_session):
    """Create second test user for privacy and authorization testing."""
    user = UserRepository.create(
        db=db_session,
        email=f"hist_other_{uuid.uuid4().hex[:8]}@example.com",
        name="Other User",
        password_hash=hash_password("StrongPassword123!"),
    )
    db_session.flush()
    token = create_access_token(str(user.id))
    return {"headers": {"Authorization": f"Bearer {token}"}, "user": user}


@pytest.fixture
def seeded_db(db_session):
    """Seed test database with fake_repo problems and solutions."""
    service = IngestService()
    service.ingest(db=db_session, repo_path=FAKE_REPO_DIR, commit_sha="test_commit_sha_123")
    return db_session


# ---------------------------------------------------------------------------
# 1. Row Creation for Statuses (found, no_solution, clarify, concept, out_of_scope)
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_history_creation_for_valid_statuses_and_none_for_out_of_scope(
    client, seeded_db, auth_headers, db_session
):
    """found, no_solution, clarify, concept each create 1 history row; out_of_scope creates none."""
    user = auth_headers["user"]
    headers = auth_headers["headers"]

    # Initial history count is 0
    init_count = db_session.query(AskHistory).filter(AskHistory.user_id == user.id).count()
    assert init_count == 0

    # 1. found -> creates 1 row with problem_id
    resp_found = client.post("/ask", json={"text": "1", "programming_language": "python"}, headers=headers)
    assert resp_found.status_code == 200
    assert resp_found.json()["status"] == "found"
    assert db_session.query(AskHistory).filter(AskHistory.user_id == user.id).count() == 1
    h_found = (
        db_session.query(AskHistory)
        .filter(AskHistory.user_id == user.id)
        .order_by(AskHistory.created_at.desc())
        .first()
    )
    assert h_found.status == "found"
    assert h_found.problem_id is not None
    assert h_found.programming_language == "python"

    # 2. no_solution -> creates 1 row with problem_id
    resp_no_sol = client.post("/ask", json={"text": "2", "programming_language": "java"}, headers=headers)
    assert resp_no_sol.status_code == 200
    assert resp_no_sol.json()["status"] == "no_solution"
    assert db_session.query(AskHistory).filter(AskHistory.user_id == user.id).count() == 2
    h_no_sol = (
        db_session.query(AskHistory)
        .filter(AskHistory.user_id == user.id)
        .order_by(AskHistory.created_at.desc())
        .first()
    )
    assert h_no_sol.status == "no_solution"
    assert h_no_sol.problem_id is not None
    assert h_no_sol.programming_language == "java"

    # 3. clarify -> creates 1 row with problem_id=None
    resp_clarify = client.post("/ask", json={"text": "two array", "programming_language": "python"}, headers=headers)
    assert resp_clarify.status_code == 200
    assert resp_clarify.json()["status"] == "clarify"
    assert db_session.query(AskHistory).filter(AskHistory.user_id == user.id).count() == 3
    h_clarify = (
        db_session.query(AskHistory)
        .filter(AskHistory.user_id == user.id)
        .order_by(AskHistory.created_at.desc())
        .first()
    )
    assert h_clarify.status == "clarify"
    assert h_clarify.problem_id is None

    # 4. concept -> creates 1 row with problem_id=None
    resp_concept = client.post(
        "/ask",
        json={"text": "explain how dynamic programming and memoization optimize recursive algorithms", "programming_language": "cpp"},
        headers=headers,
    )
    assert resp_concept.status_code == 200
    assert resp_concept.json()["status"] == "concept"
    assert db_session.query(AskHistory).filter(AskHistory.user_id == user.id).count() == 4
    h_concept = (
        db_session.query(AskHistory)
        .filter(AskHistory.user_id == user.id)
        .order_by(AskHistory.created_at.desc())
        .first()
    )
    assert h_concept.status == "concept"
    assert h_concept.problem_id is None
    assert h_concept.programming_language == "cpp"

    # 5. out_of_scope -> creates NOTHING
    resp_oos = client.post("/ask", json={"text": "make a video about my holiday"}, headers=headers)
    assert resp_oos.status_code == 200
    assert resp_oos.json()["status"] == "out_of_scope"
    # Row count must remain exactly 4
    assert db_session.query(AskHistory).filter(AskHistory.user_id == user.id).count() == 4


# ---------------------------------------------------------------------------
# 2. GET /history (Privacy, Ordering, Pagination)
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_get_history_private_and_ordered_newest_first(
    client, seeded_db, auth_headers, other_user_headers
):
    """GET /history is private per user, ordered newest first, and supports ?limit."""
    headers_a = auth_headers["headers"]
    headers_b = other_user_headers["headers"]

    # User A creates queries
    client.post("/ask", json={"text": "1", "programming_language": "python"}, headers=headers_a)
    client.post("/ask", json={"text": "2", "programming_language": "java"}, headers=headers_a)
    client.post("/ask", json={"text": "explain dynamic programming", "programming_language": "cpp"}, headers=headers_a)

    # User B creates 1 query
    client.post("/ask", json={"text": "1", "programming_language": "cpp"}, headers=headers_b)

    # 1. User A sees only their 3 queries
    resp_a = client.get("/history", headers=headers_a)
    assert resp_a.status_code == 200
    data_a = resp_a.json()
    assert len(data_a) == 3

    # Ordered newest first
    assert data_a[0]["status"] == "concept"
    assert data_a[0]["problem"] is None
    assert data_a[0]["programming_language"] == "cpp"

    assert data_a[1]["status"] == "no_solution"
    assert data_a[1]["problem"]["id"] == 2
    assert data_a[1]["problem"]["slug"] == "add-two-numbers"
    assert data_a[1]["programming_language"] == "java"

    assert data_a[2]["status"] == "found"
    assert data_a[2]["problem"]["id"] == 1
    assert data_a[2]["problem"]["slug"] == "two-sum"
    assert data_a[2]["programming_language"] == "python"

    # Verify timestamps strictly descending
    assert data_a[0]["created_at"] >= data_a[1]["created_at"]
    assert data_a[1]["created_at"] >= data_a[2]["created_at"]

    # 2. User B sees only their 1 query
    resp_b = client.get("/history", headers=headers_b)
    assert resp_b.status_code == 200
    data_b = resp_b.json()
    assert len(data_b) == 1
    assert data_b[0]["programming_language"] == "cpp"

    # 3. Optional ?limit parameter up to 50
    resp_limit = client.get("/history?limit=2", headers=headers_a)
    assert resp_limit.status_code == 200
    assert len(resp_limit.json()) == 2

    # 4. Unauthenticated returns 401
    assert client.get("/history").status_code == 401


# ---------------------------------------------------------------------------
# 3. DELETE /history/{id} and DELETE /history
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_delete_single_and_delete_all_history(
    client, seeded_db, auth_headers, other_user_headers
):
    """DELETE /history/{id} deletes one; DELETE /history deletes all; another user's id returns 404."""
    headers_a = auth_headers["headers"]
    headers_b = other_user_headers["headers"]

    # User A creates 2 queries
    client.post("/ask", json={"text": "1", "programming_language": "python"}, headers=headers_a)
    client.post("/ask", json={"text": "2", "programming_language": "python"}, headers=headers_a)

    items_a = client.get("/history", headers=headers_a).json()
    assert len(items_a) == 2
    item_to_delete = items_a[0]["id"]
    item_to_keep = items_a[1]["id"]

    # User B cannot delete User A's item -> returns 404
    resp_unauth_delete = client.delete(f"/history/{item_to_delete}", headers=headers_b)
    assert resp_unauth_delete.status_code == 404

    # Non-existent ID returns 404
    resp_404 = client.delete(f"/history/{uuid.uuid4()}", headers=headers_a)
    assert resp_404.status_code == 404

    # User A deletes their own single item
    resp_del_one = client.delete(f"/history/{item_to_delete}", headers=headers_a)
    assert resp_del_one.status_code == 200
    assert resp_del_one.json()["status"] == "deleted"

    # Verify only 1 item remains for User A
    remaining_a = client.get("/history", headers=headers_a).json()
    assert len(remaining_a) == 1
    assert remaining_a[0]["id"] == item_to_keep

    # DELETE /history deletes all remaining rows for User A
    resp_del_all = client.delete("/history", headers=headers_a)
    assert resp_del_all.status_code == 200
    assert resp_del_all.json()["status"] == "deleted"

    # Verify User A's history is now completely empty
    empty_a = client.get("/history", headers=headers_a).json()
    assert empty_a == []


# ---------------------------------------------------------------------------
# 4. Resilience: Insert Failure Does Not Break /ask
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_insert_failure_does_not_break_ask(client, seeded_db, auth_headers, caplog):
    """If writing history errors, /ask logs error type only and still returns the answer."""
    from backend.app.services.ask_service import AskService
    from sqlalchemy.exc import SQLAlchemyError

    headers = auth_headers["headers"]

    # Simulate an unexpected database error inside _save_history
    def broken_save_history(*args, **kwargs):
        raise SQLAlchemyError("Simulated database failure")

    with patch.object(AskService, "_save_history", side_effect=broken_save_history):
        with caplog.at_level(logging.ERROR):
            resp = client.post("/ask", json={"text": "1", "programming_language": "python"}, headers=headers)

    # /ask still succeeds and returns found answer
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "found"
    assert data["problem"]["id"] == 1
    assert data["solution"]["language"] == "python"


@pytest.mark.db
def test_internal_save_history_catches_exception_and_logs_error_type(client, db_session, auth_headers, caplog):
    """Directly test _save_history exception handling and error type logging."""
    from backend.app.services.ask_service import AskService
    from sqlalchemy.exc import OperationalError

    service = AskService()
    user = auth_headers["user"]

    canary_text = "secret_canary_not_logged_12345"

    with patch.object(db_session, "commit", side_effect=OperationalError("db error", {}, Exception())):
        with patch("backend.app.services.ask_service.logger.error") as mock_log_error:
            service._save_history(
                db=db_session,
                user=user,
                text=canary_text,
                status="found",
                problem_id_int=1,
                programming_language="python",
            )

    # Error type must be logged
    mock_log_error.assert_called_with("Failed to record ask history: %s", "OperationalError")
    # Canary text must never be logged in error message or args
    for call_args in mock_log_error.call_args_list:
        msg, *args = call_args[0]
        assert canary_text not in str(msg)
        assert not any(canary_text in str(arg) for arg in args)


# ---------------------------------------------------------------------------
# 5. Privacy: Captured Logs Contain None of Sent Text
# ---------------------------------------------------------------------------


@pytest.mark.db
def test_history_logs_contain_none_of_sent_text(client, seeded_db, auth_headers, caplog):
    """Captured application logs must not contain user query text from /ask or /history."""
    headers = auth_headers["headers"]
    canary = "super_private_canary_history_test_text_777"

    with caplog.at_level(logging.DEBUG):
        # 1. Ask question with canary text
        resp_ask = client.post("/ask", json={"text": canary, "programming_language": "python"}, headers=headers)
        assert resp_ask.status_code == 200

        # 2. Get history
        resp_hist = client.get("/history", headers=headers)
        assert resp_hist.status_code == 200

    # Ensure sensitive canary is scrubbed/absent from log records
    assert canary not in caplog.text, "User query text was detected in captured application logs!"
