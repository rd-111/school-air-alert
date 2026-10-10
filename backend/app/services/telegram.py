"""Telegram Bot API transport and command handling."""

from __future__ import annotations

import json
import logging
from urllib.error import URLError
from urllib.request import Request, urlopen

from app.config import Settings
from app.services.classify import classify
from app.services.messages import localized_advice, template_message

logger = logging.getLogger(__name__)
TELEGRAM_TIMEOUT_SECONDS = 10


class TelegramProviderError(Exception):
    """Telegram returned an error or did not respond."""


def send_telegram_message(
    chat_id: str | int, text: str, token: str, *, school_id: str | None = None
) -> bool:
    """Send one Bot API message without including credentials in logs/errors."""
    if not token:
        return False
    request = Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=json.dumps({"chat_id": chat_id, "text": text}).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urlopen(request, timeout=TELEGRAM_TIMEOUT_SECONDS) as response:
            result = json.loads(response.read().decode("utf-8"))
        if not isinstance(result, dict) or result.get("ok") is not True:
            raise TelegramProviderError("Telegram rejected the message")
        return True
    except (TimeoutError, URLError, OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        logger.warning(
            json.dumps(
                {
                    "event": "telegram_send_failed",
                    "school_id": school_id,
                    "reason": type(exc).__name__,
                }
            )
        )
        return False
    except TelegramProviderError:
        logger.warning(
            json.dumps(
                {"event": "telegram_send_failed", "school_id": school_id, "reason": "provider_error"}
            )
        )
        return False


def process_update(
    update: dict,
    schools_repository,
    subscribers_repository,
    settings: Settings,
    *,
    sender=send_telegram_message,
    forecast_loader=None,
) -> bool:
    """Handle the project's supported bot commands; return whether it replied."""
    message = update.get("message") or {}
    chat_id = (message.get("chat") or {}).get("id")
    text = message.get("text")
    if chat_id is None or not isinstance(text, str):
        return False

    contact = str(chat_id)
    parts = text.strip().split()
    if not parts:
        return False
    command = parts[0].split("@", maxsplit=1)[0].lower()
    reply = ""

    if command == "/start":
        reply = "School Air Alert bot. Commands: /schools, /subscribe <school_id>, /sensitive on|off, /today, /stop."
    elif command == "/schools":
        schools = schools_repository.list_all()
        reply = "\n".join(f"{row['school_id']}: {row['name']}" for row in schools)
        if not reply:
            reply = "No schools are registered yet."
    elif command == "/subscribe":
        if len(parts) != 2:
            reply = "Use /subscribe <school_id>."
        else:
            school_id = parts[1]
            school = schools_repository.get(school_id)
            if school is None:
                reply = "School was not found. Use /schools to see available schools."
            else:
                subscribers_repository.put(
                    {
                        "school_id": school_id,
                        "contact": contact,
                        "channel": "telegram",
                        "sensitive": False,
                    }
                )
                reply = f"Subscribed to {school['name']}. Use /sensitive on|off to change alert level."
    elif command == "/sensitive":
        if len(parts) != 2 or parts[1].lower() not in {"on", "off"}:
            reply = "Use /sensitive on or /sensitive off."
        else:
            rows = [
                row
                for row in subscribers_repository.find_by_contact(contact)
                if row.get("channel") == "telegram"
            ]
            if not rows:
                reply = "Subscribe to a school first with /subscribe <school_id>."
            else:
                enabled = parts[1].lower() == "on"
                for row in rows:
                    row["sensitive"] = enabled
                    subscribers_repository.put(row)
                reply = "Stricter alerts enabled." if enabled else "Regular alerts enabled."
    elif command == "/stop":
        rows = [
            row
            for row in subscribers_repository.find_by_contact(contact)
            if row.get("channel") == "telegram"
        ]
        for row in rows:
            subscribers_repository.delete(row["school_id"], contact)
        reply = "Telegram alerts stopped." if rows else "You have no Telegram school subscriptions."
    elif command == "/today":
        rows = [
            row
            for row in subscribers_repository.find_by_contact(contact)
            if row.get("channel") == "telegram"
        ]
        if not rows:
            reply = "Subscribe to a school first with /subscribe <school_id>."
        elif forecast_loader is None:
            reply = "Today's forecast is unavailable right now."
        else:
            replies = []
            for row in rows:
                school = schools_repository.get(row["school_id"])
                if school is None:
                    continue
                try:
                    forecast = forecast_loader(school["lat"], school["lon"], settings)
                    summary = forecast.school_hours_summary
                    sensitive = bool(row.get("sensitive"))
                    average = summary.average_pm25
                    peak = summary.peak_pm25
                    status = summary.status
                    if sensitive:
                        values = [
                            point.pm25
                            for point in forecast.hourly
                            if point.pm25 is not None and 7 <= point.time.hour < 15
                        ]
                        average = sum(values) / len(values) if values else None
                        peak = max(values) if values else None
                        status, _ = classify(
                            average,
                            sensitive=True,
                            levels={
                                "GREEN": settings.pm25_sensitive_green_max,
                                "YELLOW": settings.pm25_sensitive_yellow_max,
                            },
                        )
                    replies.append(
                        template_message(
                            school["name"],
                            status,
                            average,
                            peak,
                            forecast.recommendations.best_window.model_dump()
                            if forecast.recommendations.best_window
                            else None,
                            forecast.recommendations.worst_window.model_dump()
                            if forecast.recommendations.worst_window
                            else None,
                            language=school.get("language", "English"),
                            advice=localized_advice(status, school.get("language", "English")),
                            sensitive=sensitive,
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - one school's provider error is isolated
                    logger.warning(
                        json.dumps(
                            {
                                "event": "telegram_today_failed",
                                "school_id": row["school_id"],
                                "reason": type(exc).__name__,
                            }
                        )
                    )
            reply = "\n\n".join(replies) or "Today's forecast is unavailable right now."
    else:
        reply = "Use /start to see available commands."

    sender(chat_id, reply, settings.telegram_token)
    return True
