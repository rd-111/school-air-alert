from datetime import date, datetime, timedelta

from app.config import Settings
from app.repositories.dynamodb import _from_dynamo, _to_dynamo
from app.repositories.memory import MemoryRepositories
from app.schemas.forecast import ForecastResponse
from app.services.daily import run_daily_check
from app.services.messages import alert_subject, localized_advice, template_message
from app.services.notify import publish_alert


def make_forecast(value=50.0, forecast_day=date(2026, 10, 9)):
    start = datetime.combine(forecast_day, datetime.min.time()).replace(
        hour=7, tzinfo=datetime.fromisoformat("2026-10-09T07:00:00+05:30").tzinfo
    )
    hourly = [
        {"time": start + timedelta(hours=index), "pm25": value, "status": "GREEN"}
        for index in range(8)
    ]
    return ForecastResponse(
        location={"latitude": 19, "longitude": 72},
        timezone="Asia/Kolkata",
        retrieved_at=datetime.fromisoformat("2026-10-09T06:00:00+05:30"),
        source={
            "provider": "Open-Meteo",
            "model": "CAMS",
            "provider_url": "https://example.test/provider",
            "model_url": "https://example.test/model",
            "license": "CC BY 4.0",
            "attribution": "Forecast source",
            "model_resolution_note": "Forecast model",
        },
        hourly=hourly,
        school_hours_summary={
            "average_pm25": value,
            "peak_pm25": value,
            "status": "GREEN",
            "valid_reading_count": 8,
            "missing_school_hour_count": 0,
            "policy_note": "Project policy",
            "advice": "Current advice",
        },
        recommendations={
            "best_window": {
                "start": start,
                "end": start + timedelta(hours=1),
                "average_pm25": value,
                "status": "GREEN",
                "outdoor_activity_recommended": True,
                "reason_code": "LOWEST_PM25_WINDOW",
            },
            "worst_window": {
                "start": start + timedelta(hours=7),
                "end": start + timedelta(hours=8),
                "average_pm25": value,
                "status": "GREEN",
                "outdoor_activity_recommended": True,
                "reason_code": "HIGHEST_PM25_WINDOW",
            },
            "no_suitable_window": False,
            "note": "Decision support only",
        },
    )


def test_daily_job_isolates_school_failures_and_publishes_distinct_audiences():
    memory = MemoryRepositories(
        schools=[
            {"school_id": "bad", "name": "Bad", "lat": 1, "lon": 2},
            {
                "school_id": "school-1",
                "name": "Sample School",
                "lat": 19,
                "lon": 72,
                "language": "English",
                "topic_arn": "regular-topic",
                "topic_arn_sensitive": "sensitive-topic",
            },
        ]
    )
    schools = memory.schools
    history = memory.history
    memory.subscribers.put(
        {
            "school_id": "school-1",
            "contact": "12345",
            "channel": "telegram",
            "sensitive": True,
        }
    )
    sent = []
    telegram_sent = []

    def forecast_loader(latitude, longitude, _settings, **_options):
        if latitude == 1:
            raise RuntimeError("provider issue")
        return make_forecast()

    def notifier(topic, school_id, name, status, message):
        sent.append((topic, school_id, name, status, message))
        return True

    result = run_daily_check(
        schools,
        history,
        Settings(use_memory_db=True, telegram_token="test-token"),
        forecast_loader=forecast_loader,
        notifier=notifier,
        subscribers_repository=memory.subscribers,
        telegram_sender=lambda chat_id, message, _token, **_kwargs: telegram_sent.append(
            (chat_id, message)
        ) or True,
        now=datetime.fromisoformat("2026-10-09T06:00:00+05:30"),
    )

    assert result["processed"] == 1
    assert result["failed"] == 1
    assert result["schools"][1]["history_saved"] is True
    assert [message[0] for message in sent] == ["regular-topic", "sensitive-topic"]
    assert [message[3] for message in sent] == ["GREEN", "YELLOW"]
    assert "consider indoor options" in sent[1][4]
    assert result["schools"][1]["telegram_delivered"] == 1
    assert telegram_sent[0][0] == "12345"
    assert "YELLOW" in telegram_sent[0][1]
    stored = history.get("school-1", "2026-10-09")
    assert stored["avg_pm25"] == 50
    assert stored["best_window"]["start"].hour == 7


def test_subscriber_lookup_failure_does_not_stop_later_schools():
    memory = MemoryRepositories(
        schools=[
            {"school_id": "school-1", "name": "One", "lat": 19, "lon": 72},
            {"school_id": "school-2", "name": "Two", "lat": 19, "lon": 72},
        ]
    )

    class FailingSubscribers:
        def list_by_school(self, school_id):
            if school_id == "school-1":
                raise RuntimeError("subscriber store unavailable")
            return []

    result = run_daily_check(
        memory.schools,
        memory.history,
        Settings(use_memory_db=True),
        forecast_loader=lambda *_args, **_kwargs: make_forecast(),
        notifier=lambda *_args: True,
        subscribers_repository=FailingSubscribers(),
        now=datetime.fromisoformat("2026-10-09T06:00:00+05:30"),
    )

    assert result["processed"] == 2
    assert result["failed"] == 0
    assert [item["school_id"] for item in result["schools"]] == ["school-1", "school-2"]


def test_evening_run_selects_tomorrow_and_skips_history_writes():
    memory = MemoryRepositories(
        schools=[
            {"school_id": "school-1", "name": "Sample School", "lat": 19, "lon": 72,
             "language": "English", "topic_arn": "regular", "topic_arn_sensitive": "sensitive"}
        ]
    )
    calls = []

    def loader(latitude, longitude, _settings, *, target_date, forecast_days):
        calls.append((target_date, forecast_days))
        return make_forecast(forecast_day=target_date)

    sent = []
    result = run_daily_check(
        memory.schools,
        memory.history,
        Settings(use_memory_db=True),
        forecast_loader=loader,
        notifier=lambda topic, _school_id, _name, _status, message: sent.append(
            (topic, message)
        ) or True,
        notification_repository=memory.notifications,
        forecast_target="tomorrow",
        now=datetime.fromisoformat("2026-10-09T19:00:00+05:30"),
    )

    assert calls == [(date(2026, 10, 10), 2)]
    assert result["date"] == "2026-10-09"
    assert result["forecast_date"] == "2026-10-10"
    assert result["schools"][0]["history_saved"] is False
    assert memory.history.get("school-1", "2026-10-10") is None
    assert [topic for topic, _message in sent] == ["regular", "sensitive"]
    assert all(message.startswith("Tomorrow's forecast:") for _topic, message in sent)


def test_evening_target_date_uses_india_date_at_utc_midnight_boundary():
    memory = MemoryRepositories(
        schools=[{"school_id": "school-1", "name": "School", "lat": 19, "lon": 72}]
    )
    requested = []

    def loader(_latitude, _longitude, _settings, *, target_date, forecast_days):
        requested.append((target_date, forecast_days))
        return make_forecast(forecast_day=target_date)

    result = run_daily_check(
        memory.schools,
        memory.history,
        Settings(use_memory_db=True),
        forecast_loader=loader,
        forecast_target="tomorrow",
        # 00:00 in India is still the previous UTC calendar date.
        now=datetime.fromisoformat("2026-10-09T18:30:00+00:00"),
    )

    assert result["date"] == "2026-10-10"
    assert result["forecast_date"] == "2026-10-11"
    assert requested == [(date(2026, 10, 11), 2)]


def test_evening_forecast_failure_sends_nothing_and_writes_no_history():
    memory = MemoryRepositories(
        schools=[
            {
                "school_id": "school-1",
                "name": "School",
                "lat": 19,
                "lon": 72,
                "topic_arn": "regular",
                "topic_arn_sensitive": "sensitive",
            }
        ]
    )
    sent = []
    result = run_daily_check(
        memory.schools,
        memory.history,
        Settings(use_memory_db=True),
        forecast_loader=lambda *_args, **_kwargs: (_ for _ in ()).throw(
            RuntimeError("forecast unavailable")
        ),
        notifier=lambda *args: sent.append(args) or True,
        notification_repository=memory.notifications,
        forecast_target="tomorrow",
        now=datetime.fromisoformat("2026-10-09T19:00:00+05:30"),
    )

    assert result["processed"] == 0
    assert result["failed"] == 1
    assert sent == []
    assert memory.history.get("school-1", "2026-10-10") is None


def test_failed_evening_notification_can_retry_without_duplicating_success():
    memory = MemoryRepositories(
        schools=[
            {
                "school_id": "school-1",
                "name": "School",
                "lat": 19,
                "lon": 72,
                "topic_arn": "regular",
                "topic_arn_sensitive": "sensitive",
            }
        ]
    )
    regular_results = iter([False, True])
    sent = []

    def notifier(topic, *_args):
        sent.append(topic)
        return next(regular_results) if topic == "regular" else True

    options = {
        "forecast_loader": lambda _lat, _lon, _settings, *, target_date, **_kwargs: make_forecast(
            forecast_day=target_date
        ),
        "notifier": notifier,
        "notification_repository": memory.notifications,
        "forecast_target": "tomorrow",
        "now": datetime.fromisoformat("2026-10-09T19:00:00+05:30"),
    }
    first = run_daily_check(
        memory.schools, memory.history, Settings(use_memory_db=True), **options
    )
    retry = run_daily_check(
        memory.schools, memory.history, Settings(use_memory_db=True), **options
    )

    assert first["schools"][0]["notifications"]["regular"] is False
    assert retry["schools"][0]["notifications"]["regular"] is True
    assert sent == ["regular", "sensitive", "regular"]
    assert memory.history.get("school-1", "2026-10-10") is None


def test_scheduled_retry_does_not_publish_duplicate_messages():
    memory = MemoryRepositories(
        schools=[
            {"school_id": "school-1", "name": "Sample School", "lat": 19, "lon": 72,
             "language": "English", "topic_arn": "regular", "topic_arn_sensitive": "sensitive"}
        ]
    )
    sent = []
    options = {
        "forecast_loader": lambda *_args, **_kwargs: make_forecast(),
        "notifier": lambda topic, *_args: sent.append(topic) or True,
        "notification_repository": memory.notifications,
        "forecast_target": "tomorrow",
        "now": datetime.fromisoformat("2026-10-09T19:00:00+05:30"),
    }
    run_daily_check(memory.schools, memory.history, Settings(use_memory_db=True), **options)
    run_daily_check(memory.schools, memory.history, Settings(use_memory_db=True), **options)

    assert sent == ["regular", "sensitive"]
    assert memory.history.get("school-1", "2026-10-10") is None


def test_memory_history_overwrites_the_same_school_and_date():
    repository = MemoryRepositories().history
    repository.put({"school_id": "s1", "date": "2026-10-09", "avg_pm25": 50})
    repository.put({"school_id": "s1", "date": "2026-10-09", "avg_pm25": 60})
    assert repository.get("s1", "2026-10-09")["avg_pm25"] == 60


def test_dynamodb_numeric_conversion_is_recursive_and_round_trips():
    encoded = _to_dynamo({"average": 32.5, "window": {"pm25": 40.25}})
    assert str(encoded["average"]) == "32.5"
    assert _from_dynamo(encoded) == {"average": 32.5, "window": {"pm25": 40.25}}


def test_alert_subject_is_capped_at_100_characters():
    subject = alert_subject("GREEN", "A" * 200)
    assert len(subject) <= 100
    assert subject.startswith("Air Alert GREEN:")


def test_message_contains_forecast_windows_and_localized_advice():
    forecast = make_forecast()
    summary = forecast.school_hours_summary
    message = template_message(
        "School",
        summary.status,
        summary.average_pm25,
        summary.peak_pm25,
        forecast.recommendations.best_window.model_dump(),
        forecast.recommendations.worst_window.model_dump(),
        language="Hindi",
        advice=localized_advice("GREEN", "Hindi"),
    )
    assert "07:00-08:00" in message
    assert "केवल जानकारी" in message


def test_sns_publish_uses_limited_subject_and_handles_failures():
    class Client:
        def __init__(self, fail=False):
            self.fail = fail
            self.call = None

        def publish(self, **kwargs):
            if self.fail:
                raise RuntimeError("private detail")
            self.call = kwargs

    client = Client()
    assert publish_alert(
        "topic", "school-1", "S" * 200, "GREEN", "alert", sns_client=client
    )
    assert len(client.call["Subject"]) <= 100
    assert client.call["TopicArn"] == "topic"
    assert not publish_alert(
        "topic", "school-1", "School", "RED", "alert", sns_client=Client(fail=True)
    )
