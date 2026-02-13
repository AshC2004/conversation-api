"""Tests for message endpoints."""


def test_send_message(client, auth_header):
    # Create a conversation
    conv = client.post("/api/v1/conversations", json={"title": "Msg Test"}, headers=auth_header)
    conv_id = conv.json()["data"]["id"]

    resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Say hello in one word."},
        headers=auth_header,
    )
    assert resp.status_code == 200
    data = resp.json()["data"]
    assert data["role"] == "assistant"
    assert len(data["content"]) > 0
    assert data["model"] is not None
    assert data["latency_ms"] > 0


def test_list_messages(client, auth_header):
    conv = client.post("/api/v1/conversations", json={"title": "List Msg"}, headers=auth_header)
    conv_id = conv.json()["data"]["id"]

    # Send a message to create some data
    client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Hello"},
        headers=auth_header,
    )

    resp = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=auth_header)
    assert resp.status_code == 200
    body = resp.json()
    assert body["total"] == 2  # user + assistant
    assert body["data"][0]["role"] == "user"
    assert body["data"][1]["role"] == "assistant"


def test_send_message_with_thinking(client, auth_header):
    conv = client.post("/api/v1/conversations", json={"title": "Thinking Test"}, headers=auth_header)
    conv_id = conv.json()["data"]["id"]

    resp = client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "What is 15 * 23?", "thinking": True},
        headers=auth_header,
    )
    assert resp.status_code == 200
    assert len(resp.json()["data"]["content"]) > 0


def test_token_counting(client, auth_header):
    conv = client.post("/api/v1/conversations", json={"title": "Token Test"}, headers=auth_header)
    conv_id = conv.json()["data"]["id"]

    client.post(
        f"/api/v1/conversations/{conv_id}/messages",
        json={"content": "Count test"},
        headers=auth_header,
    )

    msgs = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=auth_header)
    user_msg = msgs.json()["data"][0]
    assert user_msg["token_count"] is not None
    assert user_msg["token_count"] > 0
