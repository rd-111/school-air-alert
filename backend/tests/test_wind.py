"""Modeled-wind parsing, interpolation, and source-to-school geometry tests."""

import json
from datetime import datetime, timedelta, timezone
from io import BytesIO
from pathlib import Path

import pytest

from app.services import wind
from app.services.wind import WindDataError, WindProviderError, WindSample

FIXTURE = Path(__file__).parent / "fixtures/open_meteo_wind_sample.json"
T0 = datetime(2026, 10, 23, 10, tzinfo=timezone.utc)


@pytest.mark.parametrize(
    ("wind_from", "east_sign", "north_sign"),
    [(0, 0, -1), (90, -1, 0), (180, 0, 1), (270, 1, 0), (360, 0, -1)],
)
def test_wind_from_direction_becomes_opposite_transport_vector(wind_from, east_sign, north_sign):
    vector = wind.wind_from_to_vector(1, wind_from)
    assert vector.east_mps == pytest.approx(east_sign, abs=1e-12)
    assert vector.north_mps == pytest.approx(north_sign, abs=1e-12)


def test_interpolation_uses_vectors_across_zero_degree_wraparound():
    vector = wind.interpolate_wind(
        [WindSample(T0, 2, 350), WindSample(T0 + timedelta(hours=1), 2, 10)],
        T0 + timedelta(minutes=30),
    )
    assert vector is not None
    assert vector.direction_from_degrees == pytest.approx(0, abs=1e-8)
    assert vector.speed_mps > 0


def test_interpolation_returns_exact_hour_without_neighbor():
    vector = wind.interpolate_wind([WindSample(T0, 3, 180)], T0)
    assert vector is not None
    assert vector.north_mps == pytest.approx(3)


@pytest.mark.parametrize(
    "samples",
    [
        [],
        [WindSample(T0, None, 180), WindSample(T0 + timedelta(hours=1), 2, 180)],
        [WindSample(T0, 2, 180), WindSample(T0 + timedelta(hours=2), 2, 180)],
        [WindSample(T0 + timedelta(hours=1), 2, 180)],
        [WindSample(T0, -1, 361)],
    ],
)
def test_missing_stale_incomplete_or_unbracketed_wind_is_indeterminate(samples):
    assert wind.interpolate_wind(samples, T0 + timedelta(minutes=30)) is None


def test_transport_uses_cluster_location_and_wind_direction_from():
    northbound = wind.wind_from_to_vector(2, 180)
    assert wind.transport_points_toward_school(
        northbound,
        source_latitude=19,
        source_longitude=72,
        school_latitude=20,
        school_longitude=72,
    ) is True
    assert wind.transport_points_toward_school(
        northbound,
        source_latitude=20,
        source_longitude=72,
        school_latitude=19,
        school_longitude=72,
    ) is False


def test_zero_distance_or_calm_wind_has_no_directional_result():
    calm = wind.wind_from_to_vector(0, 0)
    assert wind.transport_points_toward_school(
        calm,
        source_latitude=19,
        source_longitude=72,
        school_latitude=20,
        school_longitude=72,
    ) is None
    northbound = wind.wind_from_to_vector(2, 180)
    assert wind.transport_points_toward_school(
        northbound,
        source_latitude=19,
        source_longitude=72,
        school_latitude=19,
        school_longitude=72,
    ) is None


def test_batched_provider_request_uses_cluster_time_location_and_documented_variables(monkeypatch):
    captured = {}

    class FakeResponse(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

    def respond(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeResponse(FIXTURE.read_bytes())

    monkeypatch.setattr(wind, "urlopen", respond)
    clusters = [{"latitude": 19.1, "longitude": 72.9, "observed_at": T0 + timedelta(minutes=30)}]
    result = wind.fetch_wind_samples(clusters)
    assert "wind_speed_10m%2Cwind_direction_10m" in captured["url"]
    assert "2026-10-23" in captured["url"]
    assert "19.10000" in captured["url"] and "72.90000" in captured["url"]
    assert captured["timeout"] == wind.WIND_REQUEST_TIMEOUT_SECONDS
    assert len(result) == 1 and len(result[0]) == 3


@pytest.mark.parametrize("payload", [b"not json", b"{}", json.dumps([{}]).encode()])
def test_provider_rejects_invalid_or_incomplete_responses(monkeypatch, payload):
    class FakeResponse(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

    monkeypatch.setattr(wind, "urlopen", lambda *_args, **_kwargs: FakeResponse(payload))
    with pytest.raises(WindDataError):
        wind.fetch_wind_samples(
            [{"latitude": 19, "longitude": 72, "observed_at": T0}]
        )


def test_provider_timeout_and_wind_data_absence_are_errors_or_indeterminate(monkeypatch):
    monkeypatch.setattr(
        wind,
        "urlopen",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError()),
    )
    with pytest.raises(WindProviderError):
        wind.fetch_wind_samples(
            [{"latitude": 19, "longitude": 72, "observed_at": T0}]
        )
