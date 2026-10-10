"""Open-Meteo Air Quality API client and bounded in-process response cache."""

from __future__ import annotations

import copy
import json
import math
import threading
import time
from collections import OrderedDict
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
REQUEST_TIMEOUT_SECONDS = 10
MAX_CACHE_ENTRIES = 128
MAX_ATTEMPTS = 2


class AirProviderError(Exception):
    """An upstream provider returned an unusable response or failed."""


class AirProviderTimeout(AirProviderError):
    """The upstream provider did not respond before the request timeout."""


_cache: OrderedDict[tuple[float, float, int], tuple[float, dict]] = OrderedDict()
_cache_lock = threading.Lock()


def _validate_coordinates(latitude: float, longitude: float) -> None:
    if (
        isinstance(latitude, bool)
        or isinstance(longitude, bool)
        or not isinstance(latitude, (int, float))
        or not isinstance(longitude, (int, float))
        or not math.isfinite(latitude)
        or not math.isfinite(longitude)
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        raise ValueError("latitude or longitude is outside its valid range")


def clear_cache() -> None:
    """Clear cached forecasts; intended for tests and explicit maintenance."""
    with _cache_lock:
        _cache.clear()


def fetch_hourly_pm25(
    latitude: float,
    longitude: float,
    *,
    forecast_days: int = 1,
    cache_ttl_seconds: int = 300,
) -> dict:
    """Fetch and normalize hourly PM2.5 forecasts for WGS84 coordinates.

    The public Open-Meteo API needs no key for non-commercial use. Results are
    cached briefly and network failures receive one retry.
    """
    _validate_coordinates(latitude, longitude)
    if forecast_days not in {1, 2}:
        raise ValueError("forecast_days must be 1 or 2")
    cache_key = (
        round(float(latitude), 6),
        round(float(longitude), 6),
        forecast_days,
    )
    now = time.monotonic()
    if cache_ttl_seconds > 0:
        with _cache_lock:
            cached = _cache.get(cache_key)
            if cached and cached[0] > now:
                _cache.move_to_end(cache_key)
                return copy.deepcopy(cached[1])
            if cached:
                del _cache[cache_key]

    query = urlencode(
        {
            "latitude": latitude,
            "longitude": longitude,
            "hourly": "pm2_5",
            "forecast_days": forecast_days,
            "timezone": "Asia/Kolkata",
            "domains": "cams_global",
        }
    )
    url = f"{API_URL}?{query}"
    payload = _request_json(url)
    normalized = _normalize_response(payload)
    normalized["retrieved_at"] = datetime.now(timezone.utc).isoformat()

    if cache_ttl_seconds > 0:
        with _cache_lock:
            _cache[cache_key] = (time.monotonic() + cache_ttl_seconds, normalized)
            _cache.move_to_end(cache_key)
            while len(_cache) > MAX_CACHE_ENTRIES:
                _cache.popitem(last=False)

    return copy.deepcopy(normalized)


def parse_school_hours(data: dict, hours=range(7, 15)) -> list[tuple[int, float]]:
    """Extract valid local school-hour PM2.5 values from provider-shaped data."""
    if not isinstance(data, dict):
        return []
    hourly = data.get("hourly")
    if isinstance(hourly, list):
        points = ((item.get("time"), item.get("pm25")) for item in hourly if isinstance(item, dict))
    elif isinstance(hourly, dict):
        times = hourly.get("time")
        values = hourly.get("pm2_5")
        if not isinstance(times, list) or not isinstance(values, list) or len(times) != len(values):
            return []
        points = zip(times, values)
    else:
        return []

    allowed = set(hours)
    result = []
    for timestamp, value in points:
        if not isinstance(timestamp, str) or value is None:
            continue
        try:
            hour = datetime.fromisoformat(timestamp.replace("Z", "+00:00")).hour
        except ValueError:
            continue
        try:
            numeric_value = float(value)
        except (OverflowError, TypeError, ValueError):
            continue
        if (
            hour in allowed
            and not isinstance(value, bool)
            and isinstance(value, (int, float))
            and math.isfinite(numeric_value)
            and numeric_value >= 0
        ):
            result.append((hour, numeric_value))
    return result


def _request_json(url: str) -> dict:
    last_error: Exception | None = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            with urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                payload = json.loads(response.read().decode("utf-8"))
            if not isinstance(payload, dict):
                raise AirProviderError("provider returned an invalid response")
            return payload
        except TimeoutError as exc:
            last_error = exc
        except HTTPError as exc:
            if exc.code < 500 and exc.code != 429:
                raise AirProviderError("provider rejected the forecast request") from None
            last_error = exc
        except URLError as exc:
            last_error = exc
            if isinstance(exc.reason, TimeoutError):
                last_error = TimeoutError()
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise AirProviderError("provider returned malformed JSON") from exc
        except OSError as exc:
            last_error = exc

        if attempt == MAX_ATTEMPTS - 1:
            if isinstance(last_error, TimeoutError):
                raise AirProviderTimeout("provider request timed out") from None
            if isinstance(last_error, URLError) and isinstance(
                last_error.reason, TimeoutError
            ):
                raise AirProviderTimeout("provider request timed out") from None
            raise AirProviderError("provider request failed") from None

    raise AirProviderError("provider request failed") from last_error


def _normalize_response(payload: dict) -> dict:
    if payload.get("error"):
        raise AirProviderError("provider returned an error response")

    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise AirProviderError("provider response has no hourly forecast")
    times = hourly.get("time")
    values = hourly.get("pm2_5")
    if (
        not isinstance(times, list)
        or not isinstance(values, list)
        or not times
        or len(times) != len(values)
    ):
        raise AirProviderError("provider response has malformed hourly values")

    normalized_hours = []
    for timestamp, value in zip(times, values, strict=True):
        if not isinstance(timestamp, str):
            raise AirProviderError("provider response has an invalid timestamp")
        if value is not None and (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
            or value < 0
        ):
            raise AirProviderError("provider response has an invalid PM2.5 value")
        normalized_hours.append({"time": timestamp, "pm25": value})

    return {
        "latitude": payload.get("latitude"),
        "longitude": payload.get("longitude"),
        "timezone": payload.get("timezone", "Asia/Kolkata"),
        "hourly": normalized_hours,
    }
