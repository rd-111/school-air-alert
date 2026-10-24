from datetime import date
from types import SimpleNamespace

import pytest

from app.config import Settings
from app.main import app
from app.repositories.memory import MemoryRepositories
from app.schemas.schools import SchoolCreate, StatusResponse, SubscribeRequest
from app.services.schools import (
    SchoolNotFound,
    SchoolTopicsUnavailable,
    add_email_subscription,
    build_history,
    build_status,
    register_school,
)


def test_school_registration_memory_mode_avoids_sns_and_is_listable():
    repositories = MemoryRepositories.with_demo_school()
    created = register_school(
        repositories.schools,
        {
            "name": "New School",
            "latitude": 18.5,
            "longitude": 73.8,
            "language": "Marathi",
        },
        Settings(use_memory_db=True),
        topic_creator=lambda _school_id: pytest.fail("SNS must not run in memory mode"),
    )

    school = repositories.schools.get(created["school_id"])
    assert school["name"] == "New School"
    assert school["topic_arn"] == ""
    assert any(row["school_id"] == created["school_id"] for row in repositories.schools.list_all())


def test_school_list_returns_registered_coordinates_for_frontend_selection():
    from app.routers.schools import list_schools

    repositories = MemoryRepositories.with_demo_school()
    register_school(
        repositories.schools,
        {
            "name": "Demo School Pune",
            "latitude": 18.5204,
            "longitude": 73.8567,
            "language": "Marathi",
        },
        Settings(use_memory_db=True),
    )

    schools = list_schools(repositories={"schools": repositories.schools})
    pune = next(school for school in schools if school["name"] == "Demo School Pune")
    assert pune["latitude"] == 18.5204
    assert pune["longitude"] == 73.8567


def test_live_school_registration_saves_both_topics_from_injected_creator():
    repositories = MemoryRepositories()
    created_topics = []

    def create_topics(school_id):
        created_topics.append(school_id)
        return f"regular:{school_id}", f"sensitive:{school_id}"

    created = register_school(
        repositories.schools,
        {"name": "Sample School", "latitude": 1, "longitude": 2, "language": "English"},
        Settings(use_memory_db=False),
        topic_creator=create_topics,
    )
    saved = repositories.schools.get(created["school_id"])
    assert created_topics == [created["school_id"]]
    assert saved["topic_arn"] == f"regular:{created['school_id']}"
    assert saved["topic_arn_sensitive"] == f"sensitive:{created['school_id']}"


@pytest.mark.parametrize(
    "data",
    [
        {"name": "  ", "latitude": 1, "longitude": 2, "language": "English"},
        {"name": "Valid name", "latitude": 91, "longitude": 2, "language": "English"},
        {"name": "Valid name", "latitude": 1, "longitude": 2, "language": "French"},
    ],
)
def test_school_request_validation_rejects_bad_values(data):
    with pytest.raises(ValueError):
        SchoolCreate.model_validate(data)


def test_subscribe_request_rejects_invalid_email():
    with pytest.raises(ValueError):
        SubscribeRequest.model_validate(
            {"school_id": "s1", "email": "bad-email", "sensitive": False}
        )


def test_subscribe_uses_the_requested_audience_and_does_not_return_email():
    repositories = MemoryRepositories(
        schools=[
            {
                "school_id": "demo-school",
                "name": "Demo School",
                "topic_arn": "regular-topic",
                "topic_arn_sensitive": "sensitive-topic",
            }
        ]
    )
    calls = []

    result = add_email_subscription(
        repositories.schools,
        repositories.subscribers,
        {"school_id": "demo-school", "email": "parent@example.test", "sensitive": True},
        Settings(use_memory_db=False),
        email_subscriber=lambda topic, email: calls.append((topic, email)),
    )

    assert result == {"status": "pending_confirmation"}
    assert calls == [("sensitive-topic", "parent@example.test")]
    assert repositories._subscribers[("demo-school", "parent@example.test")]["sensitive"]


def test_subscribe_rejects_unknown_school_and_missing_production_topic():
    repositories = MemoryRepositories.with_demo_school()
    with pytest.raises(SchoolNotFound):
        add_email_subscription(
            repositories.schools,
            repositories.subscribers,
            {"school_id": "missing", "email": "parent@example.test", "sensitive": False},
            Settings(use_memory_db=True),
        )
    with pytest.raises(SchoolTopicsUnavailable):
        add_email_subscription(
            repositories.schools,
            repositories.subscribers,
            {"school_id": "demo-school", "email": "parent@example.test", "sensitive": False},
            Settings(use_memory_db=False),
        )


def test_history_counts_are_zero_for_empty_data_and_sort_oldest_first():
    repositories = MemoryRepositories.with_demo_school()
    school = repositories.schools.get("demo-school")
    assert build_history(school, repositories.history, 30, today=date(2026, 10, 9))["counts"] == {
        "green": 0,
        "yellow": 0,
        "red": 0,
    }
    repositories.history.put({"school_id": "demo-school", "date": "2026-10-09", "status": "RED"})
    repositories.history.put({"school_id": "demo-school", "date": "2026-10-08", "status": "GREEN"})
    report = build_history(school, repositories.history, 30, today=date(2026, 10, 9))
    assert report["counts"] == {"green": 1, "yellow": 0, "red": 1}
    assert [item["date"] for item in report["daily"]] == ["2026-10-08", "2026-10-09"]


def test_history_range_is_capped_at_ninety_days():
    repositories = MemoryRepositories.with_demo_school()
    school = repositories.schools.get("demo-school")
    report = build_history(school, repositories.history, 120, today=date(2026, 10, 9))
    assert report["days"] == 90


def test_status_prefers_saved_daily_values_but_uses_current_hourly_forecast():
    repositories = MemoryRepositories.with_demo_school()
    school = repositories.schools.get("demo-school")

    forecast = SimpleNamespace(
        school_hours_summary=SimpleNamespace(
            status="YELLOW", average_pm25=70, peak_pm25=100
        ),
        recommendations=SimpleNamespace(best_window=None, worst_window=None),
        hourly=[{"time": "2026-10-09T07:00:00+05:30", "pm25": 12, "status": "GREEN"}],
        source={
            "provider": "Open-Meteo", "model": "CAMS",
            "provider_url": "https://example.test/provider",
            "model_url": "https://example.test/model", "license": "CC BY 4.0",
            "attribution": "Forecast source", "model_resolution_note": "Model",
        },
        retrieved_at="2026-10-09T00:00:00Z",
    )

    result = build_status(
        school,
        {"date": "2026-10-09", "status": "RED", "avg_pm25": 121},
        forecast,
    )
    assert result["status"] == "RED"
    assert result["average_pm25"] == 121
    assert result["hourly"] == forecast.hourly
    assert StatusResponse.model_validate(result).status == "RED"


def test_openapi_lists_school_and_history_routes_with_response_models():
    paths = app.openapi()["paths"]
    assert {"get", "post"} <= paths["/api/v1/schools"].keys()
    assert "post" in paths["/api/v1/subscribe"]
    assert "get" in paths["/api/v1/status"]
    assert "get" in paths["/api/v1/history"]
