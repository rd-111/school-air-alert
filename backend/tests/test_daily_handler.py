from datetime import datetime

from handlers import daily_check


def test_evening_schedule_event_passes_fixed_scheduled_time(monkeypatch):
    repositories = {
        "schools": object(),
        "history": object(),
        "subscribers": object(),
        "notifications": object(),
    }
    captured = {}
    monkeypatch.setattr(daily_check, "get_repositories", lambda: repositories)
    monkeypatch.setattr(daily_check, "get_settings", lambda: "settings")

    def run(_schools, _history, _settings, **kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(daily_check, "run_daily_check", run)

    assert daily_check.handler(
        {
            "forecast_target": "tomorrow",
            "scheduled_time": "2026-10-09T13:30:00Z",
        },
        None,
    ) == {"ok": True}
    assert captured["forecast_target"] == "tomorrow"
    assert captured["now"] == datetime.fromisoformat("2026-10-09T13:30:00+00:00")
    assert captured["notification_repository"] is repositories["notifications"]
