"""Normalize provider data into the public forecast response."""

from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from app.config import Settings
from app.schemas.forecast import ForecastResponse
from app.services.activities import activity_guidance
from app.services.air import AirProviderError, fetch_hourly_pm25
from app.services.classify import classify
from app.services.planner import best_window, summary, worst_window

PROVIDER_URL = "https://open-meteo.com/en/docs/air-quality-api"
MODEL_URL = "https://ads.atmosphere.copernicus.eu/"
POLICY_NOTE = (
    "GREEN/YELLOW/RED are configurable school decision-support bands for hourly "
    "PM2.5. They are not official CPCB AQI categories."
)
API_DISCLAIMER = "Informational only, not medical advice."
ACTIVITY_NOTE = (
    "Forecast windows are decision support only; they do not guarantee that "
    "outdoor activity is safe."
)
MAX_FORECAST_AGE_SECONDS = 24 * 60 * 60


def _as_local_datetime(value: str, timezone_name: str) -> datetime:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (TypeError, ValueError) as exc:
        raise AirProviderError("provider response has an invalid timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=ZoneInfo(timezone_name))
    return parsed


def _configured_levels(settings: Settings, *, sensitive: bool = False) -> dict[str, float]:
    if sensitive:
        return {
            "GREEN": settings.pm25_sensitive_green_max,
            "YELLOW": settings.pm25_sensitive_yellow_max,
        }
    return {"GREEN": settings.pm25_green_max, "YELLOW": settings.pm25_yellow_max}


def _window_object(
    readings: list[tuple[datetime, float]],
    hours: tuple[int, int] | None,
    settings: Settings,
    *,
    lowest: bool,
    allow_outdoor_recommendation: bool,
) -> dict | None:
    if hours is None:
        return None
    start_hour, end_hour = hours
    window = [
        (timestamp, value)
        for timestamp, value in readings
        if start_hour <= timestamp.hour < end_hour
    ]
    if not window or len(window) != end_hour - start_hour:
        return None

    average = sum(value for _, value in window) / len(window)
    status, _ = classify(average, levels=_configured_levels(settings))
    return {
        "start": window[0][0],
        "end": window[0][0] + timedelta(hours=len(window)),
        "average_pm25": average,
        "status": status,
        "outdoor_activity_recommended": allow_outdoor_recommendation
        and status in {"GREEN", "YELLOW"},
        "reason_code": (
            "LOWEST_PM25_WINDOW_BUT_RED"
            if lowest and status == "RED"
            else "LOWEST_PM25_WINDOW"
            if lowest
            else "HIGHEST_PM25_WINDOW"
        ),
    }


def build_forecast(
    latitude: float,
    longitude: float,
    settings: Settings,
    *,
    target_date: date | None = None,
    forecast_days: int = 1,
) -> ForecastResponse:
    """Fetch provider data and assemble status and outdoor-window guidance."""
    provider_data = fetch_hourly_pm25(
        latitude,
        longitude,
        forecast_days=forecast_days,
        cache_ttl_seconds=settings.forecast_cache_ttl_seconds,
    )
    timezone_name = provider_data.get("timezone") or "Asia/Kolkata"
    try:
        ZoneInfo(timezone_name)
    except (KeyError, TypeError) as exc:
        raise AirProviderError("provider returned an invalid timezone") from exc

    requested_date = target_date or datetime.now(ZoneInfo(timezone_name)).date()
    retrieved_at = provider_data.get("retrieved_at")
    if retrieved_at:
        try:
            retrieved_at = datetime.fromisoformat(retrieved_at.replace("Z", "+00:00"))
        except (AttributeError, ValueError) as exc:
            raise AirProviderError("provider returned an invalid retrieval timestamp") from exc
        if retrieved_at.tzinfo is None:
            retrieved_at = retrieved_at.replace(tzinfo=timezone.utc)
    else:
        retrieved_at = datetime.now(timezone.utc)
    stale = (
        datetime.now(timezone.utc) - retrieved_at.astimezone(timezone.utc)
    ).total_seconds() > MAX_FORECAST_AGE_SECONDS
    hours = []
    for point in provider_data["hourly"]:
        timestamp = _as_local_datetime(point["time"], timezone_name)
        if timestamp.astimezone(ZoneInfo(timezone_name)).date() != requested_date:
            continue
        pm25 = point["pm25"]
        if stale or pm25 is None:
            status = "UNKNOWN"
        else:
            status, _ = classify(pm25, levels=_configured_levels(settings))
        hours.append({"time": timestamp, "pm25": pm25, "status": status})

    school_points = [
        (point["time"], point["pm25"])
        for point in hours
        if 7 <= point["time"].hour < 15 and point["pm25"] is not None
    ]
    school_points.sort(key=lambda point: point[0])
    numeric_by_hour = [(timestamp.hour, value) for timestamp, value in school_points]
    statistics = summary(numeric_by_hour)
    average = statistics["avg"]
    peak = statistics["peak"]
    expected_school_hours = 8
    valid_count = len(school_points)
    valid_hours = {timestamp.hour for timestamp, _ in school_points}
    complete_school_hours = valid_hours == set(range(7, 15))
    if average is None or not complete_school_hours or stale:
        status, advice = classify(None)
    else:
        status, advice = classify(average, levels=_configured_levels(settings))
    advice = f"{advice} {API_DISCLAIMER}"

    best = best_window(numeric_by_hour)
    worst = worst_window(numeric_by_hour)
    best_object = _window_object(
        school_points,
        best,
        settings,
        lowest=True,
        allow_outdoor_recommendation=complete_school_hours and not stale,
    )
    worst_object = _window_object(
        school_points,
        worst,
        settings,
        lowest=False,
        allow_outdoor_recommendation=complete_school_hours and not stale,
    )
    recommendations = {
        "best_window": best_object,
        "worst_window": worst_object,
        "no_suitable_window": stale
        or not complete_school_hours
        or best is None
        or best_object is None
        or best_object["status"] in {"RED", "UNKNOWN"},
        "note": ACTIVITY_NOTE,
        "activity_guidance": activity_guidance(
            status, complete_school_hours=complete_school_hours and not stale
        ),
    }
    return ForecastResponse(
        location={
            "latitude": (
                provider_data["latitude"]
                if provider_data.get("latitude") is not None
                else latitude
            ),
            "longitude": (
                provider_data["longitude"]
                if provider_data.get("longitude") is not None
                else longitude
            ),
        },
        timezone=timezone_name,
        retrieved_at=retrieved_at,
        stale=stale,
        source={
            "provider": "Open-Meteo Air Quality API",
            "model": "CAMS Global Atmospheric Composition Forecasts",
            "provider_url": PROVIDER_URL,
            "model_url": MODEL_URL,
            "license": "CC BY 4.0",
            "attribution": "Air-quality data by Open-Meteo, based on CAMS Global forecasts.",
            "model_resolution_note": (
                "The global model is about 45 km and has native 3-hourly updates; "
                "the API returns an hourly time series."
            ),
        },
        hourly=hours,
        school_hours_summary={
            "average_pm25": average,
            "peak_pm25": peak,
            "status": status,
            "valid_reading_count": valid_count,
            "missing_school_hour_count": max(0, expected_school_hours - len(valid_hours)),
            "policy_note": POLICY_NOTE,
            "advice": advice,
        },
        recommendations=recommendations,
    )
