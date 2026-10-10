"""Daily forecast, alert, and history orchestration."""

from __future__ import annotations

import hashlib
import json
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from app.config import Settings
from app.services.classify import classify
from app.services.forecast import build_forecast
from app.services.messages import ai_message, localized_advice, template_message
from app.services.notify import publish_alert
from app.services.telegram import send_telegram_message

logger = logging.getLogger(__name__)
IST = ZoneInfo("Asia/Kolkata")


def _sensitive_readings(forecast, forecast_date) -> list[tuple[datetime, float]]:
    return [
        (point.time.astimezone(IST), float(point.pm25))
        for point in forecast.hourly
        if point.pm25 is not None
        and point.time.astimezone(IST).date() == forecast_date
        and 7 <= point.time.astimezone(IST).hour < 15
    ]


def _window_dict(window):
    return window.model_dump() if window is not None else None


def _alert_message(
    name,
    status,
    average,
    peak,
    best,
    worst,
    language,
    settings,
    *,
    sensitive,
    forecast_target,
):
    advice = localized_advice(status, language)
    summary = {
        "average_pm25": average,
        "peak_pm25": peak,
        "best_window": best,
        "worst_window": worst,
        "sensitive": sensitive,
        "forecast_target": forecast_target,
    }
    if settings.bedrock_model:
        return ai_message(
            name,
            status,
            advice,
            summary,
            language,
            settings.bedrock_model,
            forecast_target=forecast_target,
        )
    return template_message(
        name,
        status,
        average,
        peak,
        best,
        worst,
        language=language,
        advice=advice,
        sensitive=sensitive,
        forecast_target=forecast_target,
    )


def _notify(notifier, topic, school_id, name, status, message):
    try:
        return bool(notifier(topic, school_id, name, status, message))
    except Exception as exc:  # noqa: BLE001 - isolate publisher failures per school
        logger.warning(
            json.dumps(
                {
                    "event": "notification_failed",
                    "school_id": school_id,
                    "reason": type(exc).__name__,
                }
            )
        )
        return False


def _notify_once(repository, key, notifier, topic, school_id, name, status, message, now):
    if repository is None:
        return _notify(notifier, topic, school_id, name, status, message)
    try:
        claimed = repository.claim(key, int(now.timestamp()) + 7 * 24 * 60 * 60)
    except Exception as exc:  # noqa: BLE001 - failed claims must not risk duplicate sends
        logger.warning(
            json.dumps(
                {
                    "event": "notification_claim_failed",
                    "school_id": school_id,
                    "reason": type(exc).__name__,
                }
            )
        )
        return False
    if not claimed:
        logger.info(json.dumps({"event": "notification_duplicate_skipped", "school_id": school_id}))
        return False
    delivered = _notify(notifier, topic, school_id, name, status, message)
    if not delivered:
        try:
            repository.release(key)
        except Exception as exc:  # noqa: BLE001 - TTL will expire an unreleased failed claim
            logger.warning(
                json.dumps(
                    {
                        "event": "notification_claim_release_failed",
                        "school_id": school_id,
                        "reason": type(exc).__name__,
                    }
                )
            )
    return delivered


def _delivery_key(school_id, forecast_date, forecast_target, audience):
    raw = f"{school_id}|{forecast_date.isoformat()}|{forecast_target}|{audience}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def _local_time(value: datetime | None) -> datetime:
    current = value or datetime.now(IST)
    return current.replace(tzinfo=IST) if current.tzinfo is None else current.astimezone(IST)


def run_daily_check(
    schools_repository,
    history_repository,
    settings: Settings,
    *,
    forecast_loader=build_forecast,
    notifier=publish_alert,
    telegram_sender=send_telegram_message,
    subscribers_repository=None,
    notification_repository=None,
    forecast_target: str = "today",
    now: datetime | None = None,
) -> dict:
    """Run all schools independently and return a JSON-compatible summary."""
    if forecast_target not in {"today", "tomorrow"}:
        raise ValueError("forecast_target must be 'today' or 'tomorrow'")
    local_now = _local_time(now)
    run_date = local_now.date()
    forecast_date = run_date + timedelta(days=forecast_target == "tomorrow")
    forecast_days = 2 if forecast_target == "tomorrow" else 1
    outcomes = []
    for school in schools_repository.list_all():
        school_id = str(school.get("school_id", "unknown"))
        name = str(school.get("name", "School"))
        try:
            latitude = school.get("lat", school.get("latitude"))
            longitude = school.get("lon", school.get("longitude"))
            forecast = forecast_loader(
                latitude,
                longitude,
                settings,
                target_date=forecast_date,
                forecast_days=forecast_days,
            )
        except Exception as exc:  # noqa: BLE001 - one provider failure must not stop the run
            logger.warning(
                json.dumps(
                    {
                        "event": "school_forecast_failed",
                        "school_id": school_id,
                        "reason": type(exc).__name__,
                    }
                )
            )
            outcomes.append({"school_id": school_id, "status": "failed"})
            continue

        summary = forecast.school_hours_summary
        best = _window_dict(forecast.recommendations.best_window)
        worst = _window_dict(forecast.recommendations.worst_window)
        history_record = {
            "school_id": school_id,
            "date": forecast_date.isoformat(),
            "avg_pm25": summary.average_pm25,
            "peak_pm25": summary.peak_pm25,
            "status": summary.status,
            "best_window": best,
            "worst_window": worst,
        }
        history_saved = False
        if forecast_target == "today":
            try:
                history_repository.put(history_record)
                history_saved = True
            except Exception as exc:  # noqa: BLE001 - preserve notifications if history is unavailable
                logger.warning(
                    json.dumps(
                        {
                            "event": "history_write_failed",
                            "school_id": school_id,
                            "reason": type(exc).__name__,
                        }
                    )
                )

        language = school.get("language", "English")
        regular_message = _alert_message(
            name,
            summary.status,
            summary.average_pm25,
            summary.peak_pm25,
            best,
            worst,
            language,
            settings,
            sensitive=False,
            forecast_target=forecast_target,
        )
        notifications = {
            "regular": _notify_once(
                notification_repository,
                _delivery_key(school_id, forecast_date, forecast_target, "sns-regular"),
                notifier,
                school.get("topic_arn", ""),
                school_id,
                name,
                summary.status,
                regular_message,
                local_now,
            )
        }

        sensitive_points = _sensitive_readings(forecast, forecast_date)
        sensitive_values = [value for _timestamp, value in sensitive_points]
        sensitive_hours = {timestamp.hour for timestamp, _value in sensitive_points}
        sensitive_average = (
            sum(sensitive_values) / len(sensitive_values) if sensitive_values else None
        )
        sensitive_peak = max(sensitive_values) if sensitive_values else None
        if sensitive_average is None or sensitive_hours != set(range(7, 15)):
            sensitive_status, _ = classify(None)
        else:
            sensitive_levels = {
                "GREEN": settings.pm25_sensitive_green_max,
                "YELLOW": settings.pm25_sensitive_yellow_max,
            }
            sensitive_status, _ = classify(
                sensitive_average, sensitive=True, levels=sensitive_levels
            )
        sensitive_message = _alert_message(
            name,
            sensitive_status,
            sensitive_average,
            sensitive_peak,
            best,
            worst,
            language,
            settings,
            sensitive=True,
            forecast_target=forecast_target,
        )
        notifications["sensitive"] = _notify_once(
            notification_repository,
            _delivery_key(school_id, forecast_date, forecast_target, "sns-sensitive"),
            notifier,
            school.get("topic_arn_sensitive", ""),
            school_id,
            name,
            sensitive_status,
            sensitive_message,
            local_now,
        )
        telegram_delivered = 0
        if subscribers_repository is not None:
            try:
                subscribers = subscribers_repository.list_by_school(school_id)
            except Exception as exc:  # noqa: BLE001 - subscriber storage must not stop other schools
                logger.warning(
                    json.dumps(
                        {
                            "event": "subscriber_lookup_failed",
                            "school_id": school_id,
                            "reason": type(exc).__name__,
                        }
                    )
                )
                subscribers = []
            for subscriber in subscribers:
                if subscriber.get("channel") != "telegram":
                    continue
                recipient_sensitive = bool(subscriber.get("sensitive"))
                recipient_message = (
                    sensitive_message if recipient_sensitive else regular_message
                )
                recipient_status = (
                    sensitive_status if recipient_sensitive else summary.status
                )

                def send_to_recipient(
                    _topic,
                    _school_id,
                    _name,
                    _status,
                    body,
                    recipient=subscriber,
                    current_school_id=school_id,
                ):
                    return telegram_sender(
                        recipient["contact"],
                        body,
                        settings.telegram_token,
                        school_id=current_school_id,
                    )

                delivery_id = hashlib.sha256(
                    subscriber.get("contact", "").encode("utf-8")
                ).hexdigest()
                if _notify_once(
                    notification_repository,
                    _delivery_key(
                        school_id,
                        forecast_date,
                        forecast_target,
                        f"telegram-{delivery_id}",
                    ),
                    send_to_recipient,
                    "telegram",
                    school_id,
                    name,
                    recipient_status,
                    recipient_message,
                    local_now,
                ):
                    telegram_delivered += 1
        outcomes.append(
            {
                "school_id": school_id,
                "status": summary.status,
                "history_saved": history_saved,
                "notifications": notifications,
                "telegram_delivered": telegram_delivered,
            }
        )

    return {
        "date": run_date.isoformat(),
        "forecast_date": forecast_date.isoformat(),
        "forecast_target": forecast_target,
        "processed": sum(result["status"] != "failed" for result in outcomes),
        "failed": sum(result["status"] == "failed" for result in outcomes),
        "schools": outcomes,
    }
