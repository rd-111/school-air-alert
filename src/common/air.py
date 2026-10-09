"""Fetch and parse hourly PM2.5 forecasts from Open-Meteo."""

import json
from urllib.error import URLError
from urllib.parse import urlencode
from urllib.request import urlopen


API_URL = "https://air-quality-api.open-meteo.com/v1/air-quality"
REQUEST_TIMEOUT_SECONDS = 10


def fetch_hourly_pm25(lat, lon):
    """Return the Open-Meteo JSON response, retrying once after a URL error."""
    query = urlencode(
        {
            "latitude": lat,
            "longitude": lon,
            "hourly": "pm2_5",
            "forecast_days": 1,
            "timezone": "Asia/Kolkata",
        }
    )
    url = f"{API_URL}?{query}"

    for attempt in range(2):
        try:
            with urlopen(url, timeout=REQUEST_TIMEOUT_SECONDS) as response:
                return json.loads(response.read().decode("utf-8"))
        except URLError:
            if attempt == 1:
                raise


def parse_school_hours(data, hours=range(7, 15)):
    """Return ``(hour, PM2.5)`` pairs for requested hours, skipping missing data."""
    if not isinstance(data, dict):
        return []

    hourly = data.get("hourly")
    if not isinstance(hourly, dict):
        return []

    times = hourly.get("time")
    values = hourly.get("pm2_5")
    if not isinstance(times, list) or not isinstance(values, list):
        return []

    result = []
    for timestamp, pm25 in zip(times, values):
        if not isinstance(timestamp, str) or len(timestamp) < 13:
            continue
        try:
            hour = int(timestamp[11:13])
        except ValueError:
            continue
        if hour in hours and pm25 is not None:
            result.append((hour, pm25))
    return result
