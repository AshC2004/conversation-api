"""Tests for SSE streaming endpoints."""


def test_streaming_endpoint(client, auth_header):
    conv = client.post("/api/v1/conversations", json={"title": "Stream Test"}, headers=auth_header)
    conv_id = conv.json()["data"]["id"]

    with client.stream(
        "POST",
        f"/api/v1/conversations/{conv_id}/messages/stream",
        json={"content": "Say hi in one word."},
        headers=auth_header,
    ) as resp:
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "text/event-stream; charset=utf-8"

        events = []
        for line in resp.iter_lines():
            if line.startswith("event: "):
                events.append(line[7:])

    # Verify SSE event sequence
    assert events[0] == "message_start"
    assert events[1] == "content_block_start"
    assert "content_block_delta" in events
    assert "content_block_stop" in events
    assert "message_delta" in events
    assert events[-1] == "message_stop"


def test_streaming_saves_message(client, auth_header):
    conv = client.post("/api/v1/conversations", json={"title": "Stream Save"}, headers=auth_header)
    conv_id = conv.json()["data"]["id"]

    # Consume the stream
    with client.stream(
        "POST",
        f"/api/v1/conversations/{conv_id}/messages/stream",
        json={"content": "Say OK."},
        headers=auth_header,
    ) as resp:
        for _ in resp.iter_lines():
            pass

    # Verify messages were saved
    msgs = client.get(f"/api/v1/conversations/{conv_id}/messages", headers=auth_header)
    assert msgs.json()["total"] == 2
    assert msgs.json()["data"][0]["role"] == "user"
    assert msgs.json()["data"][1]["role"] == "assistant"


def test_sse_event_format(client, auth_header):
    conv = client.post("/api/v1/conversations", json={"title": "SSE Format"}, headers=auth_header)
    conv_id = conv.json()["data"]["id"]

    with client.stream(
        "POST",
        f"/api/v1/conversations/{conv_id}/messages/stream",
        json={"content": "Say yes."},
        headers=auth_header,
    ) as resp:
        raw_lines = list(resp.iter_lines())

    # Every event should have "event:" and "data:" lines
    has_event = any(line.startswith("event: ") for line in raw_lines)
    has_data = any(line.startswith("data: ") for line in raw_lines)
    assert has_event
    assert has_data
