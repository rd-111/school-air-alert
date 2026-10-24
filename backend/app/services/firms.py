"""Bounded NASA FIRMS lookups for nearby satellite fire detections.

This module reports detections near a registered school. It does not infer
wind direction, smoke transport, or exposure at the school.
"""

from __future__ import annotations

import csv
import io
import math
import threading
import time
from collections import OrderedDict
from datetime import datetime, timedelta, timezone
from http.client import HTTPException as HttpClientError
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen

from app.config import Settings
from app.schemas.smoke import (
    FireCluster,
    FireDetection,
    SmokeHintResponse,
    SmokeHintSchool,
    WindSource,
)
from app.services.wind import (
    WindDataError,
    WindProviderError,
    WindSample,
    fetch_wind_samples,
    interpolate_wind,
    transport_points_toward_school,
)

FIRMS_AREA_API = "https://firms.modaps.eosdis.nasa.gov/api/area/csv"
FIRMS_SOURCE = "VIIRS_NOAA21_NRT"
REQUEST_TIMEOUT_SECONDS = 8
MAX_RESPONSE_BYTES = 1_000_000
MAX_DISPLAY_DETECTIONS = 20
_cache: OrderedDict[tuple[float, float, float], tuple[float, datetime, str]] = OrderedDict()
_wind_cache: OrderedDict[
    tuple[tuple[float, float, str], ...], tuple[float, datetime, list[list[WindSample]]]
] = OrderedDict()
_cache_lock = threading.Lock()


class FirmsProviderError(Exception):
    """FIRMS returned an unusable response or could not be reached."""


class FirmsProviderTimeout(FirmsProviderError):
    """FIRMS did not respond before the request timeout."""


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
        raise ValueError("school coordinates are invalid")


def _bounding_box(latitude: float, longitude: float, radius_km: float) -> tuple[float, float, float, float]:
    """Return a bounded FIRMS bounding box; exact radius is checked afterward."""
    if not math.isfinite(radius_km) or not 0 < radius_km <= 100:
        raise ValueError("search radius is outside its valid range")
    lat_delta = radius_km / 110.574
    cos_lat = max(abs(math.cos(math.radians(latitude))), 0.01)
    lon_delta = min(radius_km / (111.320 * cos_lat), 180)
    return (
        max(-180, longitude - lon_delta),
        max(-90, latitude - lat_delta),
        min(180, longitude + lon_delta),
        min(90, latitude + lat_delta),
    )


def _distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_km = 6371.0088
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)
    haversine = (
        math.sin(delta_phi / 2) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2) ** 2
    )
    return 2 * earth_radius_km * math.asin(min(1, math.sqrt(haversine)))


def _acquisition_time(row: dict[str, str]) -> datetime:
    raw_time = (row.get("acq_time") or "").strip()
    raw_date = (row.get("acq_date") or "").strip()
    if not raw_time.isdigit() or len(raw_time) > 4:
        raise ValueError("invalid acquisition time")
    return datetime.strptime(
        f"{raw_date} {raw_time.zfill(4)}", "%Y-%m-%d %H%M"
    ).replace(tzinfo=timezone.utc)


def parse_firms_csv(
    payload: str,
    *,
    latitude: float,
    longitude: float,
    radius_km: float,
    now: datetime,
) -> tuple[list[FireDetection], datetime | None]:
    """Parse, radius-filter, and time-filter FIRMS CSV rows.

    Returns current detections and the latest nearby observation older than
    the 24-hour window (the UI can then show a stale state).
    """
    _validate_coordinates(latitude, longitude)
    if not math.isfinite(radius_km) or not 0 < radius_km <= 100:
        raise ValueError("search radius is outside its valid range")
    if now.tzinfo is None:
        raise ValueError("current time must be timezone-aware")

    try:
        reader = csv.DictReader(io.StringIO(payload.lstrip("\ufeff")))
        fieldnames = reader.fieldnames
        rows = list(reader)
    except csv.Error:
        raise FirmsProviderError("FIRMS response has an invalid format") from None
    required = {"latitude", "longitude", "acq_date", "acq_time"}
    if fieldnames is None or not required.issubset(fieldnames):
        raise FirmsProviderError("FIRMS response has an invalid format")

    current = now.astimezone(timezone.utc)
    cutoff = current - timedelta(hours=24)
    detections: list[FireDetection] = []
    stale_latest: datetime | None = None
    row_count = 0
    valid_row_count = 0
    seen: set[tuple[str, datetime, float, float]] = set()
    for row in rows:
        if not row or not any(value for value in row.values() if value):
            continue
        row_count += 1
        try:
            detected_lat = float(row["latitude"])
            detected_lon = float(row["longitude"])
            if (
                not math.isfinite(detected_lat)
                or not math.isfinite(detected_lon)
                or not -90 <= detected_lat <= 90
                or not -180 <= detected_lon <= 180
            ):
                raise ValueError("invalid coordinate")
            observed_at = _acquisition_time(row)
        except (KeyError, TypeError, ValueError) as exc:
            del exc
            continue
        valid_row_count += 1
        satellite = (row.get("satellite") or "").strip()
        duplicate_key = (satellite, observed_at, detected_lat, detected_lon)
        if duplicate_key in seen:
            continue
        seen.add(duplicate_key)
        distance = _distance_km(latitude, longitude, detected_lat, detected_lon)
        if distance > radius_km or observed_at > current:
            continue
        if observed_at < cutoff:
            stale_latest = max(stale_latest, observed_at) if stale_latest else observed_at
            continue
        scan_km = _optional_positive_float(row.get("scan"))
        track_km = _optional_positive_float(row.get("track"))
        detections.append(
            FireDetection(
                observed_at=observed_at,
                latitude=detected_lat,
                longitude=detected_lon,
                distance_km=round(distance, 2),
                satellite=satellite or None,
                confidence=(row.get("confidence") or "").strip() or None,
                pixel_scan_km=scan_km,
                pixel_track_km=track_km,
            )
        )
    if row_count and not valid_row_count:
        raise FirmsProviderError("FIRMS response has no valid detection rows")
    detections.sort(key=lambda detection: detection.observed_at, reverse=True)
    return detections, stale_latest


def _optional_positive_float(value: str | None) -> float | None:
    try:
        parsed = float(value) if value is not None else None
    except (TypeError, ValueError):
        return None
    return parsed if parsed is not None and math.isfinite(parsed) and parsed > 0 else None


def cluster_detections(detections: list[FireDetection]) -> list[dict]:
    """Group overlapping pixel-footprint disks, only within the same platform/pass.

    FIRMS scan/track values describe actual pixel dimensions in kilometres.
    Their orientation is not included here, so each pixel is represented by a
    conservative circumscribed disk. Missing dimensions remain singleton
    clusters. A connected component is one cluster, not a count of fires.
    """
    groups: dict[tuple[str, datetime, int | None], list[FireDetection]] = {}
    for index, detection in enumerate(detections):
        unknown_platform_nonce = index if detection.satellite is None else None
        groups.setdefault(
            (detection.satellite or "", detection.observed_at, unknown_platform_nonce), []
        ).append(detection)

    clusters: list[dict] = []
    for (satellite, observed_at, _unknown_nonce), group in sorted(
        groups.items(), key=lambda item: (item[0][1], item[0][0], item[0][2] or -1)
    ):
        satellite = satellite or None
        remaining = set(range(len(group)))
        components: list[list[int]] = []
        while remaining:
            first = min(remaining)
            remaining.remove(first)
            component = [first]
            pending = [component[0]]
            while pending:
                current = pending.pop()
                detection = group[current]
                if detection.pixel_scan_km is None or detection.pixel_track_km is None:
                    continue
                radius = math.hypot(detection.pixel_scan_km, detection.pixel_track_km) / 2
                neighbors = []
                for candidate in sorted(remaining):
                    other = group[candidate]
                    if other.pixel_scan_km is None or other.pixel_track_km is None:
                        continue
                    other_radius = math.hypot(other.pixel_scan_km, other.pixel_track_km) / 2
                    if _distance_km(
                        detection.latitude,
                        detection.longitude,
                        other.latitude,
                        other.longitude,
                    ) <= radius + other_radius:
                        neighbors.append(candidate)
                for neighbor in neighbors:
                    remaining.remove(neighbor)
                    component.append(neighbor)
                    pending.append(neighbor)
            components.append(component)

        for component in components:
            pixels = [group[index] for index in component]
            clusters.append(
                {
                    "observed_at": observed_at,
                    "latitude": sum(item.latitude for item in pixels) / len(pixels),
                    "longitude": sum(item.longitude for item in pixels) / len(pixels),
                    "satellite": satellite,
                    "pixels": pixels,
                    "wind_status": "indeterminate",
                    "wind_speed_mps": None,
                    "wind_direction_from_degrees": None,
                }
            )
    return clusters


def fetch_firms_csv(
    map_key: str,
    *,
    latitude: float,
    longitude: float,
    radius_km: float,
) -> str:
    """Fetch two bounded UTC date ranges; the parsed window remains 24 hours."""
    _validate_coordinates(latitude, longitude)
    if not map_key.strip():
        raise ValueError("FIRMS MAP_KEY is not configured")
    west, south, east, north = _bounding_box(latitude, longitude, radius_km)
    area = ",".join(f"{value:.5f}" for value in (west, south, east, north))
    url = "/".join(
        (
            FIRMS_AREA_API,
            quote(map_key.strip(), safe=""),
            FIRMS_SOURCE,
            quote(area, safe=","),
            "2",
        )
    )
    request = Request(url, headers={"Accept": "text/csv", "User-Agent": "SchoolAirAlert/1.0"})
    try:
        with urlopen(request, timeout=REQUEST_TIMEOUT_SECONDS) as response:
            payload = response.read(MAX_RESPONSE_BYTES + 1)
    except HTTPError as exc:
        if exc.code == 429:
            raise FirmsProviderError("FIRMS rate limit was reached") from None
        raise FirmsProviderError("FIRMS request failed") from None
    except HttpClientError:
        raise FirmsProviderError("FIRMS response was incomplete") from None
    except TimeoutError as exc:
        del exc
        raise FirmsProviderTimeout("FIRMS request timed out") from None
    except (URLError, OSError) as exc:
        if isinstance(exc, URLError) and isinstance(exc.reason, TimeoutError):
            raise FirmsProviderTimeout("FIRMS request timed out") from None
        raise FirmsProviderError("FIRMS request failed") from None
    if len(payload) > MAX_RESPONSE_BYTES:
        raise FirmsProviderError("FIRMS response exceeded the size limit")
    try:
        return payload.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise FirmsProviderError("FIRMS response was not valid text") from None


def _empty_response(school: SmokeHintSchool, radius_km: float, status: str) -> SmokeHintResponse:
    return SmokeHintResponse(
        status=status,
        school=school,
        retrieved_at=None,
        search_radius_km=radius_km,
        detections=[],
    )


def clear_cache() -> None:
    """Clear cached FIRMS responses for tests and local development."""
    with _cache_lock:
        _cache.clear()
        _wind_cache.clear()


def _wind_cache_key(clusters: list[dict]) -> tuple[tuple[float, float, str], ...]:
    return tuple(
        (
            round(cluster["latitude"], 5),
            round(cluster["longitude"], 5),
            cluster["observed_at"].isoformat(),
        )
        for cluster in clusters
    )


def get_smoke_hint(
    school: dict,
    settings: Settings,
    *,
    now: datetime | None = None,
) -> SmokeHintResponse:
    """Return a nearby-detection hint without inferring smoke exposure."""
    latitude = school.get("lat", school.get("latitude"))
    longitude = school.get("lon", school.get("longitude"))
    _validate_coordinates(latitude, longitude)
    radius = settings.firms_search_radius_km
    school_model = SmokeHintSchool(
        school_id=school["school_id"],
        name=school["name"],
        latitude=latitude,
        longitude=longitude,
    )
    if not settings.firms_map_key.strip():
        return _empty_response(school_model, radius, "unconfigured")

    current = now or datetime.now(timezone.utc)
    key = (round(latitude, 5), round(longitude, 5), float(radius))
    cache_ttl = settings.firms_cache_ttl_seconds
    monotonic_now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(key)
        if cached and cache_ttl and monotonic_now - cached[0] < cache_ttl:
            _cache.move_to_end(key)
        elif cached:
            del _cache[key]

    if cached and cache_ttl and monotonic_now - cached[0] < cache_ttl:
        fetched_at, payload = cached[1], cached[2]
    else:
        fetched_at, payload = None, None

    try:
        if payload is None:
            payload = fetch_firms_csv(
                settings.firms_map_key,
                latitude=latitude,
                longitude=longitude,
                radius_km=radius,
            )
            fetched_at = datetime.now(timezone.utc) if now is None else current
            if cache_ttl:
                with _cache_lock:
                    _cache[key] = (monotonic_now, fetched_at, payload)
                    _cache.move_to_end(key)
                    while len(_cache) > 128:
                        _cache.popitem(last=False)
        detections, stale_latest = parse_firms_csv(
            payload,
            latitude=latitude,
            longitude=longitude,
            radius_km=radius,
            now=current,
        )
    except FirmsProviderError as exc:
        del exc
        return _empty_response(school_model, radius, "unavailable")

    if not detections:
        status = "stale" if stale_latest else "no_detections"
        return SmokeHintResponse(
            status=status,
            school=school_model,
            retrieved_at=fetched_at,
            latest_observation_at=stale_latest,
            search_radius_km=radius,
            detections=[],
        )

    clusters = cluster_detections(detections)
    wind_retrieved_at = None
    wind_key = _wind_cache_key(clusters)
    cache_ttl = settings.firms_cache_ttl_seconds
    with _cache_lock:
        cached_wind = _wind_cache.get(wind_key)
        if cached_wind and cache_ttl and time.monotonic() - cached_wind[0] < cache_ttl:
            _wind_cache.move_to_end(wind_key)
        elif cached_wind:
            del _wind_cache[wind_key]
    if cached_wind and cache_ttl and time.monotonic() - cached_wind[0] < cache_ttl:
        wind_samples = cached_wind[2]
        wind_retrieved_at = cached_wind[1]
        wind_was_cached = True
    else:
        wind_samples = []
        wind_was_cached = False
    try:
        if not wind_was_cached:
            wind_samples = fetch_wind_samples(clusters)
            wind_retrieved_at = datetime.now(timezone.utc)
            if cache_ttl:
                with _cache_lock:
                    _wind_cache[wind_key] = (time.monotonic(), wind_retrieved_at, wind_samples)
                    _wind_cache.move_to_end(wind_key)
                    while len(_wind_cache) > 128:
                        _wind_cache.popitem(last=False)
    except WindProviderError:
        wind_samples = []
        status = "wind_unavailable"
    except WindDataError:
        wind_samples = []
        status = "wind_indeterminate"
    else:
        for cluster, samples in zip(clusters, wind_samples, strict=True):
            vector = interpolate_wind(samples, cluster["observed_at"])
            if vector is None:
                continue
            toward = transport_points_toward_school(
                vector,
                source_latitude=cluster["latitude"],
                source_longitude=cluster["longitude"],
                school_latitude=latitude,
                school_longitude=longitude,
            )
            cluster["wind_status"] = (
                "indeterminate" if toward is None else "transport_toward" if toward else "not_toward"
            )
            cluster["wind_speed_mps"] = round(vector.speed_mps, 3)
            cluster["wind_direction_from_degrees"] = round(vector.direction_from_degrees, 1)
        if any(cluster["wind_status"] == "transport_toward" for cluster in clusters):
            status = "transport_possible"
        elif any(cluster["wind_status"] == "indeterminate" for cluster in clusters):
            status = "wind_indeterminate"
        else:
            status = "no_upwind_clusters"

    result_clusters = [
        FireCluster(
            cluster_id=f"{index + 1}",
            observed_at=cluster["observed_at"],
            latitude=cluster["latitude"],
            longitude=cluster["longitude"],
            pixel_count=len(cluster["pixels"]),
            wind_status=cluster["wind_status"],
            wind_speed_mps=cluster["wind_speed_mps"],
            wind_direction_from_degrees=cluster["wind_direction_from_degrees"],
        )
        for index, cluster in enumerate(clusters)
    ]
    result = SmokeHintResponse(
        status=status,
        school=school_model,
        retrieved_at=fetched_at,
        latest_observation_at=detections[0].observed_at,
        search_radius_km=radius,
        detections=detections[:MAX_DISPLAY_DETECTIONS],
        clusters=result_clusters,
        wind_source=WindSource(retrieved_at=wind_retrieved_at),
    )
    return result
