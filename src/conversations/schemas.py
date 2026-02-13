"""Pydantic schemas for conversation requests and responses."""

from typing import Any

from pydantic import BaseModel, Field


# --- Requests ---

class CreateConversationRequest(BaseModel):
    title: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateConversationRequest(BaseModel):
    title: str | None = None
    system_prompt: str | None = None
    is_archived: bool | None = None


# --- Responses ---

class ConversationResponse(BaseModel):
    id: str
    user_id: str
    title: str | None
    model: str | None
    system_prompt: str | None
    metadata: dict[str, Any]
    is_archived: bool
    created_at: str
    updated_at: str

    model_config = {"from_attributes": True}


class ConversationListResponse(BaseModel):
    status: str = "success"
    data: list[ConversationResponse]
    page: int
    per_page: int
    total: int
