"""Usage stats and models listing endpoints."""

from fastapi import APIRouter, Depends

from src.auth.dependencies import CurrentUser, get_current_user
from src.config.settings import get_settings
from src.db.client import get_supabase
from src.db.models import CONVERSATIONS, MESSAGES
from src.utils.cost_tracker import MODEL_PRICING, estimate_cost

router = APIRouter(prefix="/api/v1", tags=["Usage"])


@router.get("/usage/stats", summary="Get usage statistics for the authenticated user")
async def usage_stats(user: CurrentUser = Depends(get_current_user)):
    db = get_supabase()

    # Conversation count
    conv_result = db.table(CONVERSATIONS).select("id", count="exact").eq("user_id", user.id).execute()
    conversation_count = conv_result.count or 0

    # Message count and token sums via messages in user's conversations
    # First get user's conversation IDs
    conv_ids_result = db.table(CONVERSATIONS).select("id").eq("user_id", user.id).execute()
    conv_ids = [c["id"] for c in conv_ids_result.data]

    total_tokens = 0
    total_input_tokens = 0
    message_count = 0
    total_cost = 0.0

    if conv_ids:
        for conv_id in conv_ids:
            msgs = (
                db.table(MESSAGES)
                .select("token_count, metadata, model, role")
                .eq("conversation_id", conv_id)
                .execute()
            )
            for msg in msgs.data:
                message_count += 1
                tokens = msg.get("token_count") or 0
                total_tokens += tokens
                meta = msg.get("metadata") or {}
                input_t = meta.get("input_tokens", 0)
                total_input_tokens += input_t
                if msg.get("role") == "assistant" and msg.get("model"):
                    cost_from_meta = meta.get("cost_usd")
                    if cost_from_meta is not None:
                        total_cost += cost_from_meta
                    else:
                        total_cost += estimate_cost(input_t, tokens, msg["model"])

    return {
        "status": "success",
        "data": {
            "conversation_count": conversation_count,
            "message_count": message_count,
            "total_output_tokens": total_tokens,
            "total_input_tokens": total_input_tokens,
            "estimated_cost_usd": round(total_cost, 6),
        },
    }


@router.get("/models", summary="List supported LLM models")
async def list_models():
    settings = get_settings()

    models = [
        {
            "id": "llama-3.1-8b-instant",
            "provider": "groq",
            "name": "Llama 3.1 8B Instant",
            "max_context_tokens": 8192,
            "cost_per_1k_input": MODEL_PRICING["llama-3.1-8b-instant"]["input"],
            "cost_per_1k_output": MODEL_PRICING["llama-3.1-8b-instant"]["output"],
            "is_default": settings.DEFAULT_MODEL == "llama-3.1-8b-instant",
        },
        {
            "id": "llama-3.1-70b-versatile",
            "provider": "groq",
            "name": "Llama 3.1 70B Versatile",
            "max_context_tokens": 32768,
            "cost_per_1k_input": MODEL_PRICING["llama-3.1-70b-versatile"]["input"],
            "cost_per_1k_output": MODEL_PRICING["llama-3.1-70b-versatile"]["output"],
            "is_default": False,
        },
        {
            "id": "llama-3.3-70b-versatile",
            "provider": "groq",
            "name": "Llama 3.3 70B Versatile",
            "max_context_tokens": 32768,
            "cost_per_1k_input": MODEL_PRICING["llama-3.3-70b-versatile"]["input"],
            "cost_per_1k_output": MODEL_PRICING["llama-3.3-70b-versatile"]["output"],
            "is_default": False,
        },
        {
            "id": "mixtral-8x7b-32768",
            "provider": "groq",
            "name": "Mixtral 8x7B",
            "max_context_tokens": 32768,
            "cost_per_1k_input": MODEL_PRICING["mixtral-8x7b-32768"]["input"],
            "cost_per_1k_output": MODEL_PRICING["mixtral-8x7b-32768"]["output"],
            "is_default": False,
        },
        {
            "id": "gemini-1.5-flash",
            "provider": "google",
            "name": "Gemini 1.5 Flash",
            "max_context_tokens": 1048576,
            "cost_per_1k_input": MODEL_PRICING["gemini-1.5-flash"]["input"],
            "cost_per_1k_output": MODEL_PRICING["gemini-1.5-flash"]["output"],
            "is_default": False,
            "is_fallback": settings.FALLBACK_MODEL == "gemini-1.5-flash",
        },
        {
            "id": "gemini-1.5-pro",
            "provider": "google",
            "name": "Gemini 1.5 Pro",
            "max_context_tokens": 2097152,
            "cost_per_1k_input": MODEL_PRICING["gemini-1.5-pro"]["input"],
            "cost_per_1k_output": MODEL_PRICING["gemini-1.5-pro"]["output"],
            "is_default": False,
        },
    ]

    return {"status": "success", "data": models}
