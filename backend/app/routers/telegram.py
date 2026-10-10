"""Secret-header-protected Telegram webhook."""

import hmac
from typing import Annotated

from fastapi import APIRouter, Depends, Header, HTTPException

from app.config import Settings
from app.deps import get_repositories, get_settings
from app.schemas.forecast import ErrorResponse
from app.schemas.telegram import TelegramUpdate, TelegramWebhookResponse
from app.services.forecast import build_forecast
from app.services.telegram import process_update

router = APIRouter(tags=["telegram"])


@router.post(
    "/telegram",
    response_model=TelegramWebhookResponse,
    responses={403: {"model": ErrorResponse}},
)
def telegram_webhook(
    update: TelegramUpdate,
    repositories: Annotated[dict, Depends(get_repositories)],
    settings: Annotated[Settings, Depends(get_settings)],
    secret_token: Annotated[
        str | None, Header(alias="X-Telegram-Bot-Api-Secret-Token")
    ] = None,
) -> TelegramWebhookResponse:
    if not settings.telegram_secret or not secret_token or not hmac.compare_digest(
        settings.telegram_secret, secret_token
    ):
        raise HTTPException(
            status_code=403,
            detail={"code": "WEBHOOK_FORBIDDEN", "message": "Webhook secret is invalid."},
        )
    if not settings.telegram_token:
        raise HTTPException(
            status_code=503,
            detail={"code": "TELEGRAM_UNAVAILABLE", "message": "Telegram bot is not configured."},
        )
    handled = process_update(
        update.model_dump(exclude_none=True),
        repositories["schools"],
        repositories["subscribers"],
        settings,
        forecast_loader=build_forecast,
    )
    return TelegramWebhookResponse(handled=handled)
