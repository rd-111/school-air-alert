"""Minimal Telegram webhook request/response schemas."""

from typing import Any

from pydantic import BaseModel, ConfigDict


class TelegramUpdate(BaseModel):
    model_config = ConfigDict(extra="ignore")

    update_id: int | None = None
    message: dict[str, Any] | None = None


class TelegramWebhookResponse(BaseModel):
    handled: bool
