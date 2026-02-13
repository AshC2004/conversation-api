"""Tests for auth endpoints."""

import uuid


def test_health(client):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_register(client):
    email = f"reg_{uuid.uuid4().hex[:8]}@example.com"
    resp = client.post("/api/v1/auth/register", json={"email": email, "password": "TestPass123"})
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


def test_register_duplicate(client, test_email, auth_tokens):
    resp = client.post("/api/v1/auth/register", json={"email": test_email, "password": "TestPass123"})
    assert resp.status_code == 409


def test_login_success(client, test_email, test_password):
    resp = client.post("/api/v1/auth/login", json={"email": test_email, "password": test_password})
    assert resp.status_code == 200
    assert "access_token" in resp.json()["data"]


def test_login_wrong_password(client, test_email):
    resp = client.post("/api/v1/auth/login", json={"email": test_email, "password": "WrongPass"})
    assert resp.status_code == 401


def test_login_nonexistent_user(client):
    resp = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "x"})
    assert resp.status_code == 401


def test_refresh_token(client, test_email, test_password):
    login = client.post("/api/v1/auth/login", json={"email": test_email, "password": test_password})
    refresh = login.json()["data"]["refresh_token"]

    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh})
    assert resp.status_code == 200
    assert "access_token" in resp.json()["data"]


def test_refresh_revoked_token(client, test_email, test_password):
    login = client.post("/api/v1/auth/login", json={"email": test_email, "password": test_password})
    tokens = login.json()["data"]

    # Use refresh once
    client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})

    # Try again — should be revoked
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 401


def test_logout(client, test_email, test_password):
    login = client.post("/api/v1/auth/login", json={"email": test_email, "password": test_password})
    tokens = login.json()["data"]

    resp = client.post(
        "/api/v1/auth/logout",
        json={"refresh_token": tokens["refresh_token"]},
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert resp.status_code == 200

    # Refresh should now fail
    resp = client.post("/api/v1/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert resp.status_code == 401


def test_missing_auth(client):
    resp = client.post("/api/v1/auth/logout", json={"refresh_token": "x"})
    assert resp.status_code == 401
    assert resp.json()["error"]["type"] == "authentication_error"
