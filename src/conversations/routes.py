"""Conversation CRUD endpoints."""

from fastapi import APIRouter, Depends, Query

from src.auth.dependencies import CurrentUser, get_current_user
from src.conversations.schemas import (
    ConversationListResponse,
    ConversationResponse,
    CreateConversationRequest,
    UpdateConversationRequest,
)
from src.conversations.service import (
    create_conversation,
    delete_conversation,
    get_conversation,
    list_conversations,
    update_conversation,
)

router = APIRouter(prefix="/api/v1/conversations", tags=["Conversations"])


@router.post("", status_code=201)
async def create(body: CreateConversationRequest, user: CurrentUser = Depends(get_current_user)):
    data = body.model_dump(exclude_none=True)
    conv = create_conversation(user.id, data)
    return {"status": "success", "data": conv}


@router.get("")
async def list_all(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    user: CurrentUser = Depends(get_current_user),
):
    conversations, total = list_conversations(user.id, page, per_page)
    return ConversationListResponse(data=conversations, page=page, per_page=per_page, total=total)


@router.get("/{conversation_id}")
async def get(conversation_id: str, user: CurrentUser = Depends(get_current_user)):
    conv, messages = get_conversation(conversation_id, user.id)
    return {"status": "success", "data": {**conv, "messages": messages}}


@router.patch("/{conversation_id}")
async def patch(conversation_id: str, body: UpdateConversationRequest, user: CurrentUser = Depends(get_current_user)):
    updated = update_conversation(conversation_id, user.id, body.model_dump())
    return {"status": "success", "data": updated}


@router.delete("/{conversation_id}", status_code=204)
async def delete(conversation_id: str, user: CurrentUser = Depends(get_current_user)):
    delete_conversation(conversation_id, user.id)
