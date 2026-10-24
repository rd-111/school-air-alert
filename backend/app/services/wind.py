"""Modeled historical wind lookup and geometric transport comparison."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from http.client import HTTPException as HttpClientError
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

HISTORICAL_FORECAST_API = "https://historical-forecast-api.open-meteo.com/v1/forecast"
WIND_SOURCE_URL = "https://open-meteo.com/en/docs/historical-forecast-api"
WIND_REQUEST_TIMEOUT_SECONDS = 8
MAX_WIND_RESPONSE_BYTES = 1_000_000
MAX_WIND_LOCATIONS = 20
MAX_INTERPOLATION_GAP = timedelta(hours=1)


class WindProviderError(Exception):
    """The modeled wind provider returned unusable data or could not be reached."""


class WindDataError(Exception):
    """The request completed but records were malformed or insufficient."""


@dataclass(frozen=True)
class WindSample:
    time: datetime
    speed_mps: float | None
    direction_from_degrees: float | None


@dataclass(frozen=True)
class WindVector:
    east_mps: float
    north_mps: float

    @property
    def speed_mps(self) -> float:
        return math.hypot(self.east_mps, self.north_mps)

    @property
    def direction_from_degrees(self) -> float:
        """Meteorological direction: the direction wind comes from."""
        direction = math.degrees(math.atan2(-self.east_mps, -self.north_mps)) % 360
        return 0.0 if math.isclose(direction, 360.0, abs_tol=1e-10) else direction


def wind_from_to_vector(speed_mps: float, direction_from_degrees: float) -> WindVector:
    """Convert meteorological wind-from degrees to an east/north transport vector."""
    if (
        not math.isfinite(speed_mps)
        or speed_mps < 0
        or not math.isfinite(direction_from_degrees)
        or not 0 <= direction_from_degrees <= 360
    ):
        raise ValueError("wind values are invalid")
    radians = math.radians(direction_from_degrees % 360)
    return WindVector(
        east_mps=-speed_mps * math.sin(radians),
        north_mps=-speed_mps * math.cos(radians),
    )


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        raise ValueError("wind timestamps must be timezone-aware")
    return value.astimezone(timezone.utc)


def interpolate_wind(samples: list[WindSample], target: datetime) -> WindVector | None:
    """Interpolate hourly wind components at target; incomplete records return None."""
    target = _as_utc(target)
    ordered = sorted(samples, key=lambda sample: _as_utc(sample.time))
    if not ordered:
        return None
    before = [sample for sample in ordered if _as_utc(sample.time) <= target]
    after = [sample for sample in ordered if _as_utc(sample.time) >= target]
    if not before or not after:
        return None
    left, right = before[-1], after[0]
    left_time, right_time = _as_utc(left.time), _as_utc(right.time)

    def components(sample: WindSample) -> WindVector | None:
        if sample.speed_mps is None or sample.direction_from_degrees is None:
            return None
        try:
            return wind_from_to_vector(sample.speed_mps, sample.direction_from_degrees)
        except (TypeError, ValueError):
            return None

    left_vector = components(left)
    if left_time == target:
        return left_vector if left_vector and left_vector.speed_mps > 0 else None
    right_vector = components(right)
    if (
        left_vector is None
        or right_vector is None
        or right_time <= left_time
        or right_time - left_time > MAX_INTERPOLATION_GAP
    ):
        return None
    fraction = (target - left_time).total_seconds() / (right_time - left_time).total_seconds()
    vector = WindVector(
        east_mps=left_vector.east_mps
        + fraction * (right_vector.east_mps - left_vector.east_mps),
        north_mps=left_vector.north_mps
        + fraction * (right_vector.north_mps - left_vector.north_mps),
    )
    return vector if vector.speed_mps > 0 else None


def transport_points_toward_school(
    vector: WindVector,
    *,
    source_latitude: float,
    source_longitude: float,
    school_latitude: float,
    school_longitude: float,
) -> bool | None:
    """Return whether the downwind vector has a positive projection to the school.

    This is a geometric half-plane check, not a plume-width or exposure model.
    A zero-distance source or calm vector has no determinable direction.
    """
    values = (source_latitude, source_longitude, school_latitude, school_longitude)
    if not all(math.isfinite(value) for value in values):
        return None
    mean_latitude = math.radians((source_latitude + school_latitude) / 2)
    east_km = (
        math.radians(school_longitude - source_longitude)
        * 6371.0088
        * math.cos(mean_latitude)
    )
    north_km = math.radians(school_latitude - source_latitude) * 6371.0088
    if vector.speed_mps <= 0 or math.hypot(east_km, north_km) == 0:
        return None
    return vector.east_mps * east_km + vector.north_mps * north_km > 0


def _parse_hourly_location(payload: dict) -> list[WindSample]:
    hourly = payload.get("hourly")
    if not isinstance(hourly, dict):
        raise WindDataError("wind response has no hourly data")
    times = hourly.get("time")
    speeds = hourly.get("wind_speed_10m")
    directions = hourly.get("wind_direction_10m")
    if not all(isinstance(items, list) for items in (times, speeds, directions)):
        raise WindDataError("wind response is missing required variables")
    if not (len(times) == len(speeds) == len(directions)):
        raise WindDataError("wind response arrays have different lengths")
    samples: list[WindSample] = []
    try:
        for time_value, speed, direction in zip(times, speeds, directions, strict=True):
            parsed = datetime.fromisoformat(time_value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            speed_value = None if speed is None else float(speed)
            direction_value = None if direction is None else float(direction)
            if speed_value is not None and not math.isfinite(speed_value):
                speed_value = None
            if direction_value is not None and not math.isfinite(direction_value):
                direction_value = None
            samples.append(WindSample(parsed, speed_value, direction_value))
    except (AttributeError, TypeError, ValueError):
        raise WindDataError("wind response contains invalid hourly values") from None
    return samples


def _build_wind_url(clusters: list[dict]) -> str:
    if not clusters or len(clusters) > MAX_WIND_LOCATIONS:
        raise WindDataError("wind request has an unsupported number of locations")
    observations = [cluster["observed_at"].astimezone(timezone.utc) for cluster in clusters]
    start_date = min(observations).date()
    end_date = max(observations).date()
    query = urlencode(
        {
            "latitude": ",".join(f"{cluster['latitude']:.5f}" for cluster in clusters),
            "longitude": ",".join(f"{cluster['longitude']:.5f}" for cluster in clusters),
            "hourly": "wind_speed_10m,wind_direction_10m",
            "wind_speed_unit": "ms",
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "timezone": "GMT",
        }
    )
    return f"{HISTORICAL_FORECAST_API}?{query}"


def fetch_wind_samples(clusters: list[dict]) -> list[list[WindSample]]:
    """Fetch one bounded, batched modeled-wind request for detection clusters."""
    url = _build_wind_url(clusters)
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "SchoolAirAlert/1.0"})
    try:
        with urlopen(request, timeout=WIND_REQUEST_TIMEOUT_SECONDS) as response:
            payload = response.read(MAX_WIND_RESPONSE_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError, HttpClientError):
        raise WindProviderError("modeled wind provider request failed") from None
    if len(payload) > MAX_WIND_RESPONSE_BYTES:
        raise WindDataError("modeled wind response exceeded the size limit")
    try:
        decoded = json.loads(payload)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise WindDataError("modeled wind response was invalid JSON") from None
    locations = decoded if isinstance(decoded, list) else [decoded]
    if len(locations) != len(clusters) or not all(isinstance(item, dict) for item in locations):
        raise WindDataError("modeled wind response did not match requested locations")
    return [_parse_hourly_location(item) for item in locations]


