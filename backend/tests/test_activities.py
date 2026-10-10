import pytest

from app.services.activities import ACTIVITIES, activity_guidance


def test_guidance_is_general_and_never_calls_incomplete_data_green():
    incomplete = activity_guidance("UNKNOWN", complete_school_hours=False)
    assert tuple(item["activity"] for item in incomplete) == ACTIVITIES
    assert {item["guidance_code"] for item in incomplete} == {"INCOMPLETE_FORECAST"}


def test_red_status_points_to_general_red_policy_without_activity_thresholds():
    recommendations = activity_guidance("RED", complete_school_hours=True)
    assert {item["guidance_code"] for item in recommendations} == {"RED_POLICY_REVIEW"}


def test_non_red_complete_forecast_uses_only_general_policy_guidance():
    recommendations = activity_guidance("YELLOW", complete_school_hours=True)
    assert {item["guidance_code"] for item in recommendations} == {"GENERAL_POLICY"}


def test_invalid_status_is_rejected():
    with pytest.raises(ValueError, match="supported forecast status"):
        activity_guidance("PURPLE", complete_school_hours=True)
