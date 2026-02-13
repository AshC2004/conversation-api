"""Business logic for conversations with ownership verification."""

from fastapi import HTTPException

from src.conversations import repository


def verify_ownership(conversation: dict, user_id: str) -> None:
    if conversation["user_id"] != user_id:
        raise HTTPException(status_code=403, detail="You do not have access to this conversation")


def create_conversation(user_id: str, data: dict) -> dict:
    return repository.create(user_id, data)


def list_conversations(user_id: str, page: int, per_page: int) -> tuple[list[dict], int]:
    return repository.list_by_user(user_id, page, per_page)


def get_conversation(conversation_id: str, user_id: str) -> tuple[dict, list[dict]]:
    conv, messages = repository.get_with_messages(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    verify_ownership(conv, user_id)
    return conv, messages


def update_conversation(conversation_id: str, user_id: str, data: dict) -> dict:
    conv = repository.get_by_id(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    verify_ownership(conv, user_id)
    # Filter out None values
    update_data = {k: v for k, v in data.items() if v is not None}
    if not update_data:
        return conv
    return repository.update(conversation_id, update_data)


def delete_conversation(conversation_id: str, user_id: str) -> None:
    conv = repository.get_by_id(conversation_id)
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    verify_ownership(conv, user_id)
    repository.delete(conversation_id)
