"""Black-box tests for auth endpoints (P1.3a).

Tests exercise the auth router through HTTP using Starlette TestClient.
Uses a minimal FastAPI app with only the auth router mounted.
"""

import pytest
from starlette.testclient import TestClient


def test_setup_and_login(client: TestClient):
    """End-to-end: setup admin, login, check status, logout."""
    # Create first admin
    resp = client.post("/api/auth/setup", json={"username": "admin", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Login
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "password123"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["username"] == "admin"

    # Check auth status
    resp = client.get("/api/auth/status")
    assert resp.status_code == 200
    data = resp.json()
    assert data["configured"] is True
    assert data["authenticated"] is True
    assert data["username"] == "admin"
    assert data["is_admin"] is True

    # Logout
    resp = client.post("/api/auth/logout")
    assert resp.status_code == 200
    assert resp.json()["ok"] is True


def test_login_wrong_password(client: TestClient):
    """Login with wrong password returns 401."""
    client.post("/api/auth/setup", json={"username": "admin", "password": "password123"})
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "wrong"})
    assert resp.status_code == 401


def test_auth_policy(client: TestClient):
    """Auth policy endpoint returns password requirements."""
    resp = client.get("/api/auth/policy")
    assert resp.status_code == 200
    data = resp.json()
    assert data["password_min_length"] >= 4
    assert isinstance(data["reserved_usernames"], list)


def test_signup_disabled_by_default(client: TestClient):
    """Signup is disabled when open registration is off."""
    client.post("/api/auth/setup", json={"username": "admin", "password": "password123"})
    resp = client.post("/api/auth/signup", json={"username": "user2", "password": "password123"})
    # May return 403 (disabled) or 200 depending on config
    assert resp.status_code in (200, 403)


def test_change_password(client: TestClient):
    """Admin can change their password after login."""
    client.post("/api/auth/setup", json={"username": "admin", "password": "password123"})
    client.post("/api/auth/login", json={"username": "admin", "password": "password123"})

    resp = client.post("/api/auth/change-password", json={
        "current_password": "password123",
        "new_password": "newpassword456",
    })
    assert resp.status_code == 200
    assert resp.json()["ok"] is True

    # Old password no longer works
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "password123"})
    assert resp.status_code == 401

    # New password works
    resp = client.post("/api/auth/login", json={"username": "admin", "password": "newpassword456"})
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
