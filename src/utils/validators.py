"""Shared validators and utility schemas."""

from pydantic import BaseModel


class SuccessResponse(BaseModel):
    status: str = "success"
    data: dict
