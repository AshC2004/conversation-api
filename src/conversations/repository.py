"""Data access layer for conversations."""

from typing import Any

from src.db.client import get_supabase
from src.db.models import CONVERSATIONS, MESSAGES


def create(user_id: str, data: dict[str, Any]) -> dict:
    db = get_supabase()
    row = {"user_id": user_id, **data}
    result = db.table(CONVERSATIONS).insert(row).execute()
    return result.data[0]


def list_by_user(user_id: str, page: int = 1, per_page: int = 20) -> tuple[list[dict], int]:
    db = get_supabase()
    offset = (page - 1) * per_page

    # Get total count
    count_result = db.table(CONVERSATIONS).select("id", count="exact").eq("user_id", user_id).eq("is_archived", False).execute()
    total = count_result.count or 0

    # Get page
    result = (
        db.table(CONVERSATIONS)
        .select("*")
        .eq("user_id", user_id)
        .eq("is_archived", False)
        .order("updated_at", desc=True)
        .range(offset, offset + per_page - 1)
        .execute()
    )
    return result.data, total


def get_by_id(conversation_id: str) -> dict | None:
    db = get_supabase()
    result = db.table(CONVERSATIONS).select("*").eq("id", conversation_id).execute()
    return result.data[0] if result.data else None


def get_with_messages(conversation_id: str) -> tuple[dict | None, list[dict]]:
    conv = get_by_id(conversation_id)
    if not conv:
        return None, []
    db = get_supabase()
    msgs = (
        db.table(MESSAGES)
        .select("*")
        .eq("conversation_id", conversation_id)
        .order("created_at")
        .execute()
    )
    return conv, msgs.data


def update(conversation_id: str, data: dict[str, Any]) -> dict | None:
    db = get_supabase()
    result = db.table(CONVERSATIONS).update(data).eq("id", conversation_id).execute()
    return result.data[0] if result.data else None


def delete(conversation_id: str) -> bool:
    db = get_supabase()
    result = db.table(CONVERSATIONS).delete().eq("id", conversation_id).execute()
    return bool(result.data)
