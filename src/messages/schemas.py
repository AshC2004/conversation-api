"""Pydantic schemas for message requests and responses."""

from typing import Any

from pydantic import BaseModel, Field


class SendMessageRequest(BaseModel):
    content: str
    model: str | None = None
    thinking: bool = False


class MessageResponse(BaseModel):
    id: str
    conversation_id: str
    role: str
    content: str
    token_count: int | None = None
    model: str | None = None
    finish_reason: str | None = None
    latency_ms: int | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: str

    model_config = {"from_attributes": True}


class MessageListResponse(BaseModel):
    status: str = "success"
    data: list[MessageResponse]
    page: int
    per_page: int
    total: int
