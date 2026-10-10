"""Offline tests for the Open-Meteo client."""

import json
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest

from app.services import air

FIXTURE = Path(__file__).resolve().parents[2] / "tests/fixtures/open_meteo_sample.json"


class FakeResponse:
    def __init__(self, content):
        self.content = content

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return None

    def read(self):
        return self.content


def test_fetch_normalizes_fixture_and_sends_documented_parameters(monkeypatch):
    payload = FIXTURE.read_bytes()
    seen = []

    def fake_urlopen(url, timeout):
        seen.append((url, timeout))
        return FakeResponse(payload)

    monkeypatch.setattr(air, "urlopen", fake_urlopen)
    air.clear_cache()

    result = air.fetch_hourly_pm25(19.076, 72.8777, cache_ttl_seconds=0)

    assert result["hourly"][2] == {"time": "2026-10-09T08:00", "pm25": None}
    params = parse_qs(urlparse(seen[0][0]).query)
    assert params["hourly"] == ["pm2_5"]
    assert params["forecast_days"] == ["1"]
    assert params["timezone"] == ["Asia/Kolkata"]
    assert params["latitude"] == ["19.076"]
    assert params["longitude"] == ["72.8777"]
    assert seen[0][1] == 10
    assert "retrieved_at" in result


def test_forecast_days_two_uses_distinct_cache_entry_and_request_parameter(monkeypatch):
    calls = []
    monkeypatch.setattr(
        air,
        "urlopen",
        lambda url, timeout: calls.append((url, timeout))
        or FakeResponse(FIXTURE.read_bytes()),
    )
    air.clear_cache()

    air.fetch_hourly_pm25(19, 72, forecast_days=1)
    air.fetch_hourly_pm25(19, 72, forecast_days=2)

    assert len(calls) == 2
    assert parse_qs(urlparse(calls[0][0]).query)["forecast_days"] == ["1"]
    assert parse_qs(urlparse(calls[1][0]).query)["forecast_days"] == ["2"]


def test_parse_school_hours_uses_fixture_and_skips_missing_readings():
    payload = json.loads(FIXTURE.read_text())
    assert air.parse_school_hours(payload) == [
        (7, 13.4), (9, 16.2), (10, 17.5), (11, 18.1),
        (12, 17.3), (13, 15.8), (14, 14.2),
    ]


@pytest.mark.parametrize("payload", [{}, {"hourly": {}}, {"hourly": {"time": ["bad"], "pm2_5": []}}, None])
def test_parse_school_hours_returns_empty_for_empty_or_malformed_data(payload):
    assert air.parse_school_hours(payload) == []


def test_retries_one_failed_request_then_succeeds(monkeypatch):
    payload = FIXTURE.read_bytes()
    calls = 0

    def fake_urlopen(_url, timeout):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise TimeoutError
        return FakeResponse(payload)

    monkeypatch.setattr(air, "urlopen", fake_urlopen)
    air.clear_cache()
    assert air.fetch_hourly_pm25(1, 2, cache_ttl_seconds=0)["hourly"]
    assert calls == 2


@pytest.mark.parametrize("payload", [b"not json", b"[]", b'{"hourly": {}}'])
def test_malformed_provider_data_raises_safe_error(monkeypatch, payload):
    monkeypatch.setattr(air, "urlopen", lambda *_args, **_kwargs: FakeResponse(payload))
    air.clear_cache()
    with pytest.raises(air.AirProviderError):
        air.fetch_hourly_pm25(1, 2, cache_ttl_seconds=0)


@pytest.mark.parametrize("latitude,longitude", [(91, 0), (0, 181), (float("nan"), 0)])
def test_invalid_coordinates_never_call_network(monkeypatch, latitude, longitude):
    monkeypatch.setattr(air, "urlopen", lambda *_args, **_kwargs: pytest.fail("network called"))
    with pytest.raises(ValueError):
        air.fetch_hourly_pm25(latitude, longitude)


def test_cache_returns_independent_copy(monkeypatch):
    monkeypatch.setattr(
        air,
        "urlopen",
        lambda *_args, **_kwargs: FakeResponse(FIXTURE.read_bytes()),
    )
    air.clear_cache()
    first = air.fetch_hourly_pm25(3, 4)
    first["hourly"].clear()
    second = air.fetch_hourly_pm25(3, 4)
    assert len(second["hourly"]) == 10
