"""School creation, SNS subscription, and read-only status/report assembly."""

from datetime import date, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from app.config import Settings
from app.services.notify import create_school_topics, subscribe_email


class SchoolNotFound(Exception):
    pass


class SchoolTopicsUnavailable(Exception):
    pass


def register_school(
    school_repository,
    school_data: dict,
    settings: Settings,
    *,
    topic_creator=create_school_topics,
) -> dict:
    school_id = str(uuid4())
    if settings.use_memory_db:
        regular_topic, sensitive_topic = "", ""
    else:
        regular_topic, sensitive_topic = topic_creator(school_id)
    school = {
        "school_id": school_id,
        "name": school_data["name"],
        "lat": school_data["latitude"],
        "lon": school_data["longitude"],
        "language": school_data["language"],
        "topic_arn": regular_topic,
        "topic_arn_sensitive": sensitive_topic,
    }
    school_repository.put(school)
    return {"school_id": school_id, "name": school["name"], "status": "created"}


def add_email_subscription(
    school_repository,
    subscriber_repository,
    data: dict,
    settings: Settings,
    *,
    email_subscriber=subscribe_email,
) -> dict:
    school = school_repository.get(data["school_id"])
    if school is None:
        raise SchoolNotFound
    topic = school.get(
        "topic_arn_sensitive" if data["sensitive"] else "topic_arn", ""
    )
    if not topic and not settings.use_memory_db:
        raise SchoolTopicsUnavailable
    if topic:
        email_subscriber(topic, data["email"])
    subscriber_repository.put(
        {
            "school_id": data["school_id"],
            "contact": data["email"],
            "channel": "email",
            "sensitive": data["sensitive"],
        }
    )
    return {"status": "demo_only" if settings.use_memory_db else "pending_confirmation"}


def build_status(
    school: dict,
    latest_history: dict | None,
    forecast,
) -> dict:
    current = forecast.school_hours_summary
    return {
        "school": {"school_id": school["school_id"], "name": school["name"]},
        "date": latest_history.get("date") if latest_history else None,
        "status": latest_history.get("status", current.status) if latest_history else current.status,
        "average_pm25": latest_history.get("avg_pm25", current.average_pm25)
        if latest_history
        else current.average_pm25,
        "peak_pm25": latest_history.get("peak_pm25", current.peak_pm25)
        if latest_history
        else current.peak_pm25,
        "best_window": latest_history.get(
            "best_window", forecast.recommendations.best_window
        )
        if latest_history
        else forecast.recommendations.best_window,
        "worst_window": latest_history.get(
            "worst_window", forecast.recommendations.worst_window
        )
        if latest_history
        else forecast.recommendations.worst_window,
        "hourly": forecast.hourly,
        "source": forecast.source,
        "retrieved_at": forecast.retrieved_at,
    }


def build_history(
    school: dict,
    history_repository,
    days: int,
    *,
    today: date | None = None,
) -> dict:
    days = min(days, 90)
    end = today or datetime.now(ZoneInfo("Asia/Kolkata")).date()
    start = end - timedelta(days=days - 1)
    rows = history_repository.list_recent(
        school["school_id"], start.isoformat(), end.isoformat()
    )
    counts = {"green": 0, "yellow": 0, "red": 0}
    daily = []
    for row in sorted(rows, key=lambda item: item["date"]):
        status = row.get("status", "UNKNOWN")
        if status in {"GREEN", "YELLOW", "RED"}:
            counts[status.lower()] += 1
        daily.append(
            {
                "date": row["date"],
                "average_pm25": row.get("avg_pm25"),
                "peak_pm25": row.get("peak_pm25"),
                "status": status,
                "best_window": row.get("best_window"),
                "worst_window": row.get("worst_window"),
            }
        )
    return {
        "school": {"school_id": school["school_id"], "name": school["name"]},
        "days": days,
        "counts": counts,
        "daily": daily,
    }
