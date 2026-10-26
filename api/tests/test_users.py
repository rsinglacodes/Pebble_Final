"""Tests for user profile, onboarding, and preference endpoints."""

import pytest
from fastapi import status


@pytest.mark.db
def test_register_login_then_get_me(client):
    """Register then login then GET /users/me works; /users/me never returns password_hash."""
    email = "me.tester@example.com"
    password = "StrongPassword123!"

    # 1. Register
    reg_resp = client.post(
        "/auth/register",
        json={"name": "Me Tester", "email": email, "password": password},
    )
    assert reg_resp.status_code == status.HTTP_201_CREATED

    # 2. Login
    login_resp = client.post(
        "/auth/login",
        json={"email": email, "password": password},
    )
    assert login_resp.status_code == status.HTTP_200_OK
    token = login_resp.json()["access_token"]
    assert token

    # 3. GET /users/me
    headers = {"Authorization": f"Bearer {token}"}
    me_resp = client.get("/users/me", headers=headers)
    assert me_resp.status_code == status.HTTP_200_OK
    me_data = me_resp.json()
    assert me_data["email"] == email
    assert me_data["name"] == "Me Tester"
    assert me_data["onboarding_completed"] is False
    assert "id" in me_data
    # /users/me never returns password_hash
    assert "password_hash" not in me_data


@pytest.mark.db
def test_update_user_name(client):
    """PATCH /users/me updates the user's name."""
    email = "updater@example.com"
    password = "Password123!"
    client.post("/auth/register", json={"name": "Initial Name", "email": email, "password": password})
    login_resp = client.post("/auth/login", json={"email": email, "password": password})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    patch_resp = client.patch("/users/me", json={"name": "Updated Name"}, headers=headers)
    assert patch_resp.status_code == status.HTTP_200_OK
    assert patch_resp.json()["name"] == "Updated Name"

    # Verify persisted via GET /users/me
    me_resp = client.get("/users/me", headers=headers)
    assert me_resp.json()["name"] == "Updated Name"



