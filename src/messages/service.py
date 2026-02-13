"""Message business logic: send messages, auto-title, fallback."""

import asyncio
import logging
import time
import uuid

from src.config.settings import get_settings
from src.db.client import get_supabase
from src.db.models import CONVERSATIONS, MESSAGES
from src.llm.client import get_llm_client
from src.llm.context import build_context
from src.llm.prompts import TITLE_GENERATION_PROMPT, build_system_prompt
from src.llm.token_counter import count_tokens

logger = logging.getLogger(__name__)


def _save_message(conversation_id: str, role: str, content: str, **extra) -> dict:
    db = get_supabase()
    row = {
        "conversation_id": conversation_id,
        "role": role,
        "content": content,
        **extra,
    }
    result = db.table(MESSAGES).insert(row).execute()
    return result.data[0]


def _get_conversation_messages(conversation_id: str) -> list[dict]:
    db = get_supabase()
    result = (
        db.table(MESSAGES)
        .select("role, content")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )
    return result.data


def _get_message_count(conversation_id: str) -> int:
    db = get_supabase()
    result = db.table(MESSAGES).select("id", count="exact").eq("conversation_id", conversation_id).execute()
    return result.count or 0


async def _generate_title(conversation_id: str, user_message: str) -> None:
    """Generate a conversation title from the first user message (fire-and-forget)."""
    try:
        settings = get_settings()
        client = get_llm_client("groq")
        messages = [
            {"role": "system", "content": TITLE_GENERATION_PROMPT},
            {"role": "user", "content": user_message[:500]},
        ]
        result = await client.generate(messages, settings.DEFAULT_MODEL)
        title = result["content"].strip().strip('"')[:500]
        if title:
            db = get_supabase()
            db.table(CONVERSATIONS).update({"title": title}).eq("id", conversation_id).execute()
    except Exception:
        logger.exception("Failed to generate title for conversation %s", conversation_id)


async def send_message(
    conversation_id: str,
    content: str,
    conversation: dict,
    model: str | None = None,
    thinking: bool = False,
) -> dict:
    """Save user message, call LLM, save assistant response, return assistant message."""
    settings = get_settings()
    model = model or conversation.get("model") or settings.DEFAULT_MODEL

    # Save user message
    user_msg = _save_message(
        conversation_id, "user", content,
        token_count=count_tokens(content),
    )

    # Auto-title on first message
    msg_count = _get_message_count(conversation_id)
    if msg_count == 1:
        asyncio.create_task(_generate_title(conversation_id, content))

    # Build context
    system_prompt = build_system_prompt(conversation.get("system_prompt"), thinking=thinking)
    history = _get_conversation_messages(conversation_id)
    context = build_context(history, system_prompt)

    # Call LLM with fallback
    start = time.time()
    try:
        client = get_llm_client("groq")
        result = await client.generate(context, model)
    except Exception:
        logger.warning("Primary LLM failed, falling back to Google AI")
        client = get_llm_client("google")
        model = settings.FALLBACK_MODEL
        result = await client.generate(context, model)

    latency_ms = int((time.time() - start) * 1000)

    # Save assistant message
    assistant_msg = _save_message(
        conversation_id, "assistant", result["content"],
        token_count=result.get("output_tokens", 0),
        model=model,
        finish_reason=result.get("finish_reason", "stop"),
        latency_ms=latency_ms,
        metadata={"input_tokens": result.get("input_tokens", 0)},
    )

    return assistant_msg
