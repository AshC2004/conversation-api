"""Tests for conversation CRUD endpoints."""

import uuid


def test_create_conversation(client, auth_header):
    resp = client.post(
        "/api/v1/conversations",
        json={"title": "Test Conv", "model": "llama-3.1-8b-instant"},
        headers=auth_header,
    )
    assert resp.status_code == 201
    data = resp.json()["data"]
    assert data["title"] == "Test Conv"
    assert data["model"] == "llama-3.1-8b-instant"
    assert data["is_archived"] is False


def test_create_conversation_no_auth(client):
    resp = client.post("/api/v1/conversations", json={"title": "No Auth"})
    assert resp.status_code == 401


def test_list_conversations(client, auth_header):
    # Create one to ensure list is non-empty
    client.post("/api/v1/conversations", json={"title": "List Test"}, headers=auth_header)

    resp = client.get("/api/v1/conversations", headers=auth_header)
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "success"
    assert len(body["data"]) >= 1
    assert "page" in body
    assert "total" in body


def test_list_pagination(client, auth_header):
    resp = client.get("/api/v1/conversations?page=1&per_page=2", headers=auth_header)
    assert resp.status_code == 200
    assert resp.json()["per_page"] == 2


def test_get_conversation(client, auth_header):
    create = client.post("/api/v1/conversations", json={"title": "Get Test"}, headers=auth_header)
    conv_id = create.json()["data"]["id"]

    resp = client.get(f"/api/v1/conversations/{conv_id}", headers=auth_header)
    assert resp.status_code == 200
    assert resp.json()["data"]["id"] == conv_id
    assert "messages" in resp.json()["data"]


def test_get_conversation_not_found(client, auth_header):
    fake_id = str(uuid.uuid4())
    resp = client.get(f"/api/v1/conversations/{fake_id}", headers=auth_header)
    assert resp.status_code == 404


def test_update_conversation(client, auth_header):
    create = client.post("/api/v1/conversations", json={"title": "Original"}, headers=auth_header)
    conv_id = create.json()["data"]["id"]

    resp = client.patch(f"/api/v1/conversations/{conv_id}", json={"title": "Updated"}, headers=auth_header)
    assert resp.status_code == 200
    assert resp.json()["data"]["title"] == "Updated"


def test_delete_conversation(client, auth_header):
    create = client.post("/api/v1/conversations", json={"title": "Delete Me"}, headers=auth_header)
    conv_id = create.json()["data"]["id"]

    resp = client.delete(f"/api/v1/conversations/{conv_id}", headers=auth_header)
    assert resp.status_code == 204

    # Verify it's gone
    resp = client.get(f"/api/v1/conversations/{conv_id}", headers=auth_header)
    assert resp.status_code == 404


def test_ownership_check(client, auth_header):
    """Another user shouldn't access this user's conversations."""
    create = client.post("/api/v1/conversations", json={"title": "Private"}, headers=auth_header)
    conv_id = create.json()["data"]["id"]

    # Register a second user
    email2 = f"other_{uuid.uuid4().hex[:8]}@example.com"
    reg = client.post("/api/v1/auth/register", json={"email": email2, "password": "OtherPass123"})
    token2 = reg.json()["data"]["access_token"]

    resp = client.get(f"/api/v1/conversations/{conv_id}", headers={"Authorization": f"Bearer {token2}"})
    assert resp.status_code == 403
