"""Forecast assembly and endpoint tests; all provider calls are mocked."""

import json
from datetime import date, datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.services import forecast
from app.services.air import AirProviderError, AirProviderTimeout

FIXTURE = Path(__file__).resolve().parents[2] / "tests/fixtures/open_meteo_sample.json"


def test_build_forecast_skips_missing_values_and_reports_source(monkeypatch):
    payload = json.loads(FIXTURE.read_text())
    monkeypatch.setattr(forecast, "fetch_hourly_pm25", lambda *_args, **_kwargs: {
        "latitude": payload["latitude"],
        "longitude": payload["longitude"],
        "timezone": payload["timezone"],
        "hourly": [
            {"time": timestamp, "pm25": value}
            for timestamp, value in zip(
                payload["hourly"]["time"], payload["hourly"]["pm2_5"], strict=True
            )
        ],
    })

    result = forecast.build_forecast(
        19,
        72,
        Settings(),
        target_date=date.fromisoformat(payload["hourly"]["time"][0][:10]),
    )

    assert result.data_type == "forecast"
    assert result.source.provider == "Open-Meteo Air Quality API"
    assert result.school_hours_summary.valid_reading_count == 7
    assert result.school_hours_summary.missing_school_hour_count == 1
    assert result.hourly[2].status == "UNKNOWN"
    assert result.school_hours_summary.status == "UNKNOWN"
    assert result.recommendations.no_suitable_window is True
    assert result.stale is False
    assert result.recommendations.activity_guidance[0].guidance_code == "INCOMPLETE_FORECAST"
    assert result.school_hours_summary.policy_note.startswith("GREEN/YELLOW/RED")
    assert result.recommendations.best_window is not None


def test_two_day_response_selects_only_requested_local_school_date(monkeypatch):
    start = "2026-10-09T"
    tomorrow = "2026-10-10T"
    hourly = [
        {"time": f"{start}{hour:02d}:00", "pm25": 200}
        for hour in range(7, 15)
    ] + [
        {"time": f"{tomorrow}{hour:02d}:00", "pm25": 30}
        for hour in range(7, 15)
    ]
    calls = []
    retrieved_at = datetime.now(timezone.utc).replace(microsecond=0)

    def fetch(_latitude, _longitude, **options):
        calls.append(options["forecast_days"])
        return {
            "timezone": "Asia/Kolkata",
            "hourly": hourly,
            "retrieved_at": retrieved_at.isoformat(),
        }

    monkeypatch.setattr(forecast, "fetch_hourly_pm25", fetch)
    result = forecast.build_forecast(
        19,
        72,
        Settings(),
        target_date=date(2026, 10, 10),
        forecast_days=2,
    )

    assert calls == [2]
    assert result.school_hours_summary.status == "GREEN"
    assert result.school_hours_summary.average_pm25 == 30
    assert all(point.time.date().isoformat() == "2026-10-10" for point in result.hourly)
    assert result.retrieved_at == retrieved_at


def test_two_day_forecast_with_missing_tomorrow_reading_is_unknown(monkeypatch):
    hourly = [
        {"time": f"2026-10-10T{hour:02d}:00", "pm25": None if hour == 8 else 30}
        for hour in range(7, 15)
    ]
    monkeypatch.setattr(
        forecast,
        "fetch_hourly_pm25",
        lambda *_args, **_kwargs: {
            "timezone": "Asia/Kolkata",
            "hourly": hourly,
            "retrieved_at": datetime.now(timezone.utc).isoformat(),
        },
    )

    result = forecast.build_forecast(
        19, 72, Settings(), target_date=date(2026, 10, 10), forecast_days=2
    )

    assert result.school_hours_summary.status == "UNKNOWN"
    assert result.school_hours_summary.missing_school_hour_count == 1
    assert result.recommendations.no_suitable_window is True
    assert not any(point.status == "GREEN" for point in result.hourly if point.pm25 is None)


def test_stale_data_is_unknown_and_not_recommended(monkeypatch):
    payload = json.loads(FIXTURE.read_text())
    monkeypatch.setattr(forecast, "fetch_hourly_pm25", lambda *_args, **_kwargs: {
        "timezone": payload["timezone"],
        "hourly": [
            {"time": timestamp, "pm25": value}
            for timestamp, value in zip(
                payload["hourly"]["time"], payload["hourly"]["pm2_5"], strict=True
            )
        ],
        "retrieved_at": "2026-10-07T00:00:00+00:00",
    })

    result = forecast.build_forecast(
        19,
        72,
        Settings(),
        target_date=date.fromisoformat(payload["hourly"]["time"][0][:10]),
    )

    assert result.stale is True
    assert result.school_hours_summary.status == "UNKNOWN"
    assert result.recommendations.no_suitable_window is True
    assert result.recommendations.best_window.outdoor_activity_recommended is False


def test_forecast_endpoint_validates_coordinates_and_returns_structured_error():
    client = TestClient(create_app(Settings()))
    response = client.get("/api/v1/forecast?latitude=91&longitude=72")
    assert response.status_code == 422
    assert response.json() == {
        "error": {"code": "VALIDATION_ERROR", "message": "Request parameters are invalid."}
    }


def test_forecast_endpoint_provider_failure_is_generic(monkeypatch):
    monkeypatch.setattr(forecast, "fetch_hourly_pm25", lambda *_args, **_kwargs: (_ for _ in ()).throw(AirProviderError("secret")))
    client = TestClient(create_app(Settings()))
    response = client.get("/api/v1/forecast?latitude=19&longitude=72")
    assert response.status_code == 502
    assert response.json() == {
        "error": {"code": "UPSTREAM_FAILURE", "message": "Forecast provider is unavailable."}
    }


def test_forecast_endpoint_timeout_preserves_gateway_timeout_status(monkeypatch):
    monkeypatch.setattr(forecast, "fetch_hourly_pm25", lambda *_args, **_kwargs: (_ for _ in ()).throw(AirProviderTimeout("secret")))
    client = TestClient(create_app(Settings()))
    response = client.get("/api/v1/forecast?latitude=19&longitude=72")
    assert response.status_code == 504
    assert response.json() == {
        "error": {"code": "UPSTREAM_TIMEOUT", "message": "Forecast provider timed out."}
    }
