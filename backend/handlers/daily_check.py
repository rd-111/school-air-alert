"""AWS Lambda entry point for the daily school forecast run."""

from datetime import datetime

from app.deps import get_repositories, get_settings
from app.services.daily import run_daily_check


def handler(event, _context):
    repositories = get_repositories()
    event = event if isinstance(event, dict) else {}
    forecast_target = event.get("forecast_target", "today")
    scheduled_time = event.get("scheduled_time")
    now = (
        datetime.fromisoformat(scheduled_time.replace("Z", "+00:00"))
        if isinstance(scheduled_time, str)
        else None
    )
    return run_daily_check(
        repositories["schools"],
        repositories["history"],
        get_settings(),
        subscribers_repository=repositories["subscribers"],
        notification_repository=repositories["notifications"],
        forecast_target=forecast_target,
        now=now,
    )
