"""Tests for Conversation and Message repository and API endpoints."""

import uuid
from datetime import datetime, timezone
import pytest
from fastapi import status
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from backend.app.core.security import create_access_token
from backend.app.db.base import Base
from backend.app.models.conversation import Conversation, Message
from backend.app.models.user import User
from backend.app.repositories.conversation_repository import ConversationRepository


@pytest.fixture
def sqlite_session():
    """In-memory SQLite session for isolated database tests."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        engine.dispose()


def test_repository_crud_and_auto_title(sqlite_session: Session):
    """Test conversation creation, auto-titling on first user message, rename, and messages."""
    user = User(name="Test User", email="test@example.com")
    sqlite_session.add(user)
    sqlite_session.commit()
    sqlite_session.refresh(user)

    repo = ConversationRepository()

    # 1. Create conversation with default title
    conv = repo.create(sqlite_session, user.id)
    assert conv.title == "New conversation"
    assert conv.user_id == user.id

    # 2. Add first user message - auto-title triggered (max 40 chars)
    long_prompt = "How can I implement a binary search tree in Python with deletion?"
    msg1 = repo.add_message(
        sqlite_session,
        conversation_id=conv.id,
        user_id=user.id,
        role="user",
        content=long_prompt,
    )
    assert msg1 is not None
    assert msg1.content == long_prompt
    assert len(conv.title) <= 40
    assert conv.title == long_prompt[:40].rstrip()

    # 3. Add second user message - title remains unchanged
    title_after_first = conv.title
    repo.add_message(
        sqlite_session,
        conversation_id=conv.id,
        user_id=user.id,
        role="user",
        content="Another question that should not change title",
    )
    assert conv.title == title_after_first

    # 4. Rename
    renamed = repo.rename(sqlite_session, conv.id, user.id, "Custom BST Title")
    assert renamed is not None
    assert renamed.title == "Custom BST Title"


def test_repository_meta_roundtrip_and_cascade(sqlite_session: Session):
    """Test structured meta round-trip and cascade delete of messages."""
    user = User(name="Meta User", email="meta@example.com")
    sqlite_session.add(user)
    sqlite_session.commit()
    sqlite_session.refresh(user)

    repo = ConversationRepository()
    conv = repo.create(sqlite_session, user.id, title="Algorithm Discussion")

    meta_payload = {
        "status": "ready",
        "problem": "Two Sum",
        "solution": {"complexity": "O(n)", "code": "def two_sum(): pass"},
        "video_request": {"prompt": "two sum visualization"},
        "video_payload": {"fps": 30},
        "video_job_id": "job-abc-123",
        "video_url": "https://storage.googleapis.com/videos/twosum.mp4",
    }

    # Add message with meta
    msg = repo.add_message(
        sqlite_session,
        conversation_id=conv.id,
        user_id=user.id,
        role="assistant",
        content="Here is the explanation and generated video solution.",
        meta=meta_payload,
    )
    assert msg is not None
    assert msg.meta == meta_payload

    # Fetch with messages
    fetched = repo.get_by_id(sqlite_session, conv.id, user.id)
    assert fetched is not None
    assert len(fetched.messages) == 1
    assert fetched.messages[0].meta["video_url"] == meta_payload["video_url"]
    assert fetched.messages[0].meta["solution"]["complexity"] == "O(n)"

    # Delete conversation - messages should cascade delete
    deleted = repo.delete(sqlite_session, conv.id, user.id)
    assert deleted is True

    # Verify conversation is gone
    assert repo.get_by_id(sqlite_session, conv.id, user.id) is None
    remaining_messages = sqlite_session.scalars(
        select(Message).where(Message.conversation_id == conv.id)
    ).all()
    assert len(remaining_messages) == 0


def test_repository_ownership_isolation(sqlite_session: Session):
    """Verify User A cannot access, modify, add messages to, or delete User B's conversations."""
    user_a = User(name="User A", email="usera@example.com")
    user_b = User(name="User B", email="userb@example.com")
    sqlite_session.add_all([user_a, user_b])
    sqlite_session.commit()
    sqlite_session.refresh(user_a)
    sqlite_session.refresh(user_b)

    repo = ConversationRepository()
    conv_a = repo.create(sqlite_session, user_a.id, title="User A Secret Chat")

    # User B cannot get User A's conversation
    assert repo.get_by_id(sqlite_session, conv_a.id, user_b.id) is None

    # User B cannot add message to User A's conversation
    assert (
        repo.add_message(sqlite_session, conv_a.id, user_b.id, role="user", content="Sneaky message")
        is None
    )

    # User B cannot rename User A's conversation
    assert repo.rename(sqlite_session, conv_a.id, user_b.id, "Hacked Title") is None
    assert conv_a.title == "User A Secret Chat"

    # User B cannot delete User A's conversation
    assert repo.delete(sqlite_session, conv_a.id, user_b.id) is False
    assert repo.get_by_id(sqlite_session, conv_a.id, user_a.id) is not None

    # User B's list does not include User A's conversation
    user_b_list = repo.list_by_user(sqlite_session, user_b.id)
    assert len(user_b_list) == 0


def test_repository_ordering_and_pagination(sqlite_session: Session):
    """Verify conversations are listed newest updated first and paginated."""
    user = User(name="Order User", email="order@example.com")
    sqlite_session.add(user)
    sqlite_session.commit()
    sqlite_session.refresh(user)

    repo = ConversationRepository()
    c1 = repo.create(sqlite_session, user.id, title="Conversation 1")
    c2 = repo.create(sqlite_session, user.id, title="Conversation 2")
    c3 = repo.create(sqlite_session, user.id, title="Conversation 3")

    # Update C1 by adding a message
    repo.add_message(sqlite_session, c1.id, user.id, role="user", content="Reviving C1")

    # List conversations - C1 should now be first because it was most recently updated
    convs = repo.list_by_user(sqlite_session, user.id)
    assert convs[0].id == c1.id

    # Test pagination
    page1 = repo.list_by_user(sqlite_session, user.id, limit=2, offset=0)
    assert len(page1) == 2
    page2 = repo.list_by_user(sqlite_session, user.id, limit=2, offset=2)
    assert len(page2) == 1


@pytest.mark.db
def test_api_conversations_flow_and_isolation(client):
    """Integration test via HTTP: create, auto-title, meta round-trip, ownership 404, delete cascade."""
    # Register User 1
    reg1 = client.post(
        "/auth/register",
        json={"name": "Chat User 1", "email": "chat1@example.com", "password": "Password123!"},
    )
    assert reg1.status_code == status.HTTP_201_CREATED
    login1 = client.post("/auth/login", json={"email": "chat1@example.com", "password": "Password123!"})
    token1 = login1.json()["access_token"]
    headers1 = {"Authorization": f"Bearer {token1}"}

    # Register User 2
    reg2 = client.post(
        "/auth/register",
        json={"name": "Chat User 2", "email": "chat2@example.com", "password": "Password123!"},
    )
    assert reg2.status_code == status.HTTP_201_CREATED
    login2 = client.post("/auth/login", json={"email": "chat2@example.com", "password": "Password123!"})
    token2 = login2.json()["access_token"]
    headers2 = {"Authorization": f"Bearer {token2}"}

    # 1. User 1 creates conversation
    create_resp = client.post("/conversations", json={"title": "New conversation"}, headers=headers1)
    assert create_resp.status_code == status.HTTP_201_CREATED
    conv_id = create_resp.json()["id"]
    assert create_resp.json()["title"] == "New conversation"

    # 2. User 1 adds first message -> auto-title
    prompt = "How does merge sort work and what is its complexity?"
    msg_resp = client.post(
        f"/conversations/{conv_id}/messages",
        json={"role": "user", "content": prompt},
        headers=headers1,
    )
    assert msg_resp.status_code == status.HTTP_201_CREATED

    # Verify auto-title updated on GET
    detail_resp = client.get(f"/conversations/{conv_id}", headers=headers1)
    assert detail_resp.status_code == status.HTTP_200_OK
    assert detail_resp.json()["title"] == prompt[:40].rstrip()
    assert len(detail_resp.json()["messages"]) == 1

    # 3. User 1 adds assistant message with meta
    meta = {
        "status": "ready",
        "problem": "Merge Sort",
        "solution": {"complexity": "O(n log n)"},
        "video_url": "https://storage.example.com/mergesort.mp4",
    }
    msg2_resp = client.post(
        f"/conversations/{conv_id}/messages",
        json={"role": "assistant", "content": "Here is merge sort explained.", "meta": meta},
        headers=headers1,
    )
    assert msg2_resp.status_code == status.HTTP_201_CREATED
    assert msg2_resp.json()["meta"] == meta

    # 4. User 2 attempts to access User 1's conversation -> 404
    u2_get = client.get(f"/conversations/{conv_id}", headers=headers2)
    assert u2_get.status_code == status.HTTP_404_NOT_FOUND

    u2_msg = client.post(
        f"/conversations/{conv_id}/messages",
        json={"role": "user", "content": "Attack attempt"},
        headers=headers2,
    )
    assert u2_msg.status_code == status.HTTP_404_NOT_FOUND

    u2_patch = client.patch(
        f"/conversations/{conv_id}",
        json={"title": "Hacked Title"},
        headers=headers2,
    )
    assert u2_patch.status_code == status.HTTP_404_NOT_FOUND

    u2_delete = client.delete(f"/conversations/{conv_id}", headers=headers2)
    assert u2_delete.status_code == status.HTTP_404_NOT_FOUND

    # 5. User 1 renames conversation
    patch_resp = client.patch(f"/conversations/{conv_id}", json={"title": "Merge Sort Guide"}, headers=headers1)
    assert patch_resp.status_code == status.HTTP_200_OK
    assert patch_resp.json()["title"] == "Merge Sort Guide"

    # 5b. User 1 patches message meta (e.g. saves video_job_id and video_url)
    msg2_id = msg2_resp.json()["id"]
    meta_patch_resp = client.patch(
        f"/conversations/{conv_id}/messages/{msg2_id}",
        json={"meta": {"video_job_id": "job-saved-123", "video_url": "https://storage.example.com/updated.mp4"}},
        headers=headers1,
    )
    assert meta_patch_resp.status_code == status.HTTP_200_OK
    assert meta_patch_resp.json()["meta"]["video_job_id"] == "job-saved-123"
    assert meta_patch_resp.json()["meta"]["video_url"] == "https://storage.example.com/updated.mp4"
    assert meta_patch_resp.json()["meta"]["problem"] == "Merge Sort"

    # User 2 cannot patch User 1's message meta -> 404
    u2_patch_meta = client.patch(
        f"/conversations/{conv_id}/messages/{msg2_id}",
        json={"meta": {"video_job_id": "hacked"}},
        headers=headers2,
    )
    assert u2_patch_meta.status_code == status.HTTP_404_NOT_FOUND

    # 6. User 1 deletes conversation -> 204
    del_resp = client.delete(f"/conversations/{conv_id}", headers=headers1)
    assert del_resp.status_code == status.HTTP_204_NO_CONTENT

    # Verify 404 after deletion
    get_after_del = client.get(f"/conversations/{conv_id}", headers=headers1)
    assert get_after_del.status_code == status.HTTP_404_NOT_FOUND
