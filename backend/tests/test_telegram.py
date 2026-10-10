import json
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException

from app.config import Settings
from app.repositories.memory import MemoryRepositories
from app.routers.telegram import telegram_webhook
from app.schemas.forecast import (
    ActivityRecommendations,
    AirQualitySummary,
    ForecastResponse,
    ForecastSource,
    HourlyForecast,
)
from app.schemas.telegram import TelegramUpdate
from app.services.telegram import process_update, send_telegram_message


def sample_forecast(value=50):
    start = datetime.fromisoformat("2026-10-09T07:00:00+05:30")
    return ForecastResponse(
        location={"latitude": 19, "longitude": 72},
        timezone="Asia/Kolkata",
        retrieved_at=start,
        source=ForecastSource(
            provider="Open-Meteo", model="CAMS", provider_url="https://example.test/p",
            model_url="https://example.test/m", license="CC BY 4.0",
            attribution="Source", model_resolution_note="Forecast model",
        ),
        hourly=[
            HourlyForecast(time=start + timedelta(hours=offset), pm25=value, status="GREEN")
            for offset in range(8)
        ],
        school_hours_summary=AirQualitySummary(
            average_pm25=value, peak_pm25=value, status="GREEN",
            valid_reading_count=8, missing_school_hour_count=0,
            policy_note="Policy", advice="Advice",
        ),
        recommendations=ActivityRecommendations(
            best_window=None, worst_window=None, no_suitable_window=True,
            note="Decision support only",
        ),
    )


def test_supported_commands_subscribe_toggle_sensitive_today_and_stop():
    repositories = MemoryRepositories.with_demo_school()
    sent = []
    sender = lambda chat_id, text, _token: sent.append((chat_id, text)) or True
    settings = Settings(use_memory_db=True, telegram_token="test-token")

    def handle(text):
        return process_update(
            {"message": {"chat": {"id": 123}, "text": text}},
            repositories.schools,
            repositories.subscribers,
            settings,
            sender=sender,
            forecast_loader=lambda *_args: sample_forecast(),
        )

    assert handle("/start")
    assert "/schools" in sent[-1][1]
    assert handle("/schools")
    assert "demo-school: Demo School" in sent[-1][1]
    assert handle("/subscribe demo-school")
    assert repositories.subscribers.find_by_contact("123")[0]["sensitive"] is False
    assert handle("/sensitive on")
    assert repositories.subscribers.find_by_contact("123")[0]["sensitive"] is True
    assert handle("/sensitive off")
    assert repositories.subscribers.find_by_contact("123")[0]["sensitive"] is False
    assert handle("/sensitive on")
    assert handle("/today")
    assert "YELLOW" in sent[-1][1]
    assert "Informational only, not medical advice." in sent[-1][1]
    assert handle("/stop")
    assert repositories.subscribers.find_by_contact("123") == []


def test_invalid_telegram_webhook_secret_is_rejected():
    repositories = MemoryRepositories.with_demo_school()
    with pytest.raises(HTTPException) as error:
        telegram_webhook(
            TelegramUpdate(message={"chat": {"id": 123}, "text": "/start"}),
            {"schools": repositories.schools, "subscribers": repositories.subscribers},
            Settings(telegram_secret="expected-secret"),
            "wrong-secret",
        )
    assert error.value.status_code == 403


def test_telegram_transport_uses_timeout_and_parses_success(monkeypatch):
    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return None

        def read(self):
            return json.dumps({"ok": True}).encode()

    seen = {}

    def fake_urlopen(request, timeout):
        seen["request"] = request
        seen["timeout"] = timeout
        return Response()

    monkeypatch.setattr("app.services.telegram.urlopen", fake_urlopen)
    assert send_telegram_message(123, "hello", "token-placeholder")
    assert seen["timeout"] == 10
    assert seen["request"].method == "POST"


def test_telegram_transport_falls_back_without_logging_token(monkeypatch, caplog):
    monkeypatch.setattr(
        "app.services.telegram.urlopen", lambda *_args, **_kwargs: (_ for _ in ()).throw(TimeoutError())
    )
    assert not send_telegram_message(123, "hello", "secret-placeholder")
    assert "secret-placeholder" not in caplog.text
