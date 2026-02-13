"""Message endpoints: list, send, stream, events."""

import asyncio
import logging
import time
import uuid

from fastapi import APIRouter, Depends, Query, Request
from starlette.responses import StreamingResponse

from src.auth.dependencies import CurrentUser, get_current_user
from src.config.settings import get_settings
from src.conversations.service import get_conversation
from src.db.client import get_supabase
from src.db.models import MESSAGES
from src.llm.client import get_llm_client
from src.llm.context import build_context
from src.llm.prompts import build_system_prompt
from src.llm.token_counter import count_tokens
from src.messages.schemas import MessageListResponse, SendMessageRequest
from src.messages.service import _get_conversation_messages, _get_message_count, _generate_title, _save_message, send_message
from src.messages.streaming import (
    format_content_block_delta,
    format_content_block_start,
    format_content_block_stop,
    format_error,
    format_message_delta,
    format_message_start,
    format_message_stop,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/conversations/{conversation_id}", tags=["Messages"])


@router.get("/messages")
async def list_messages(
    conversation_id: str,
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=200),
    user: CurrentUser = Depends(get_current_user),
):
    get_conversation(conversation_id, user.id)

    db = get_supabase()
    offset = (page - 1) * per_page

    count_result = db.table(MESSAGES).select("id", count="exact").eq("conversation_id", conversation_id).execute()
    total = count_result.count or 0

    result = (
        db.table(MESSAGES)
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .range(offset, offset + per_page - 1)
        .execute()
    )

    return MessageListResponse(data=result.data, page=page, per_page=per_page, total=total)


@router.post("/messages")
async def send(
    conversation_id: str,
    body: SendMessageRequest,
    user: CurrentUser = Depends(get_current_user),
):
    conv, _ = get_conversation(conversation_id, user.id)
    assistant_msg = await send_message(
        conversation_id, body.content, conv,
        model=body.model, thinking=body.thinking,
    )
    return {"status": "success", "data": assistant_msg}


@router.post("/messages/stream")
async def stream(
    conversation_id: str,
    body: SendMessageRequest,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    conv, _ = get_conversation(conversation_id, user.id)
    settings = get_settings()
    model = body.model or conv.get("model") or settings.DEFAULT_MODEL

    # Save user message
    user_msg = _save_message(
        conversation_id, "user", body.content,
        token_count=count_tokens(body.content),
    )

    # Auto-title on first message
    if _get_message_count(conversation_id) == 1:
        asyncio.create_task(_generate_title(conversation_id, body.content))

    # Build context
    system_prompt = build_system_prompt(conv.get("system_prompt"), thinking=body.thinking)
    history = _get_conversation_messages(conversation_id)
    context = build_context(history, system_prompt)

    message_id = str(uuid.uuid4())

    async def event_generator():
        full_content = ""
        output_tokens = 0
        finish_reason = "stop"
        start = time.time()

        yield format_message_start(message_id, model)
        yield format_content_block_start()

        active_model = model
        try:
            try:
                client = get_llm_client("groq")
                stream = client.generate_stream(context, model)
            except Exception:
                logger.warning("Primary LLM failed, falling back")
                client = get_llm_client("google")
                active_model = settings.FALLBACK_MODEL
                stream = client.generate_stream(context, active_model)

            async for chunk in stream:
                if await request.is_disconnected():
                    logger.info("Client disconnected during stream")
                    break

                if chunk["type"] == "delta":
                    full_content += chunk["content"]
                    yield format_content_block_delta(chunk["content"])
                elif chunk["type"] == "finish":
                    finish_reason = chunk.get("finish_reason", "stop")
                    usage = chunk.get("usage", {})
                    output_tokens = usage.get("output_tokens", 0)

        except Exception as e:
            logger.exception("Error during streaming")
            yield format_error("stream_error", str(e))
            return

        yield format_content_block_stop()
        yield format_message_delta(finish_reason, output_tokens)
        yield format_message_stop()

        # Save assistant message after stream completes
        latency_ms = int((time.time() - start) * 1000)
        if full_content:
            _save_message(
                conversation_id, "assistant", full_content,
                token_count=output_tokens or count_tokens(full_content),
                model=active_model,
                finish_reason=finish_reason,
                latency_ms=latency_ms,
            )

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive", "X-Accel-Buffering": "no"},
    )


@router.get("/events")
async def events(
    conversation_id: str,
    request: Request,
    user: CurrentUser = Depends(get_current_user),
):
    """SSE stream for real-time conversation events (new messages)."""
    get_conversation(conversation_id, user.id)

    async def event_stream():
        last_count = _get_message_count(conversation_id)
        while True:
            if await request.is_disconnected():
                break
            current_count = _get_message_count(conversation_id)
            if current_count > last_count:
                db = get_supabase()
                new_msgs = (
                    db.table(MESSAGES)
                    .select("*")
                    .eq("conversation_id", conversation_id)
                    .order("created_at", desc=True)
                    .limit(current_count - last_count)
                    .execute()
                )
                import json
                for msg in reversed(new_msgs.data):
                    yield f"event: new_message\ndata: {json.dumps(msg, default=str)}\n\n"
                last_count = current_count
            await asyncio.sleep(1)

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
