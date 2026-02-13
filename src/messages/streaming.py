"""SSE event formatting utilities for streaming responses."""

import json


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def format_message_start(message_id: str, model: str) -> str:
    return _sse("message_start", {"type": "message_start", "message": {"id": message_id, "model": model}})


def format_content_block_start(index: int = 0) -> str:
    return _sse("content_block_start", {"type": "content_block_start", "index": index, "content_block": {"type": "text", "text": ""}})


def format_content_block_delta(text: str, index: int = 0) -> str:
    return _sse("content_block_delta", {"type": "content_block_delta", "index": index, "delta": {"type": "text_delta", "text": text}})


def format_content_block_stop(index: int = 0) -> str:
    return _sse("content_block_stop", {"type": "content_block_stop", "index": index})


def format_message_delta(stop_reason: str, output_tokens: int = 0) -> str:
    return _sse("message_delta", {"type": "message_delta", "delta": {"stop_reason": stop_reason}, "usage": {"output_tokens": output_tokens}})


def format_message_stop() -> str:
    return _sse("message_stop", {"type": "message_stop"})


def format_error(error_type: str, message: str) -> str:
    return _sse("error", {"type": "error", "error": {"type": error_type, "message": message}})
