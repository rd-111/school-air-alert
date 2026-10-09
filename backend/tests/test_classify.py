import pytest

from app.services.classify import ACTIVITY_FACTOR, ADVICE, classify


@pytest.mark.parametrize(
    ("pm25", "expected_status"),
    ((60, "GREEN"), (61, "YELLOW"), (120, "YELLOW"), (121, "RED")),
)
def test_normal_threshold_boundaries(pm25, expected_status):
    status, advice = classify(pm25)

    assert status == expected_status
    assert advice == ADVICE[expected_status]


@pytest.mark.parametrize(
    ("pm25", "expected_status"),
    ((40, "GREEN"), (41, "YELLOW"), (90, "YELLOW"), (91, "RED")),
)
def test_sensitive_threshold_boundaries(pm25, expected_status):
    status, advice = classify(pm25, sensitive=True)

    assert status == expected_status
    assert advice == ADVICE[expected_status]


@pytest.mark.parametrize(
    ("pm25", "expected_status", "expected_advice"),
    (
        (0, "GREEN", "Normal outdoor activities are fine."),
        (
            61,
            "YELLOW",
            (
                "Shorten outdoor play, move strenuous activity to the safest hours, "
                "and keep students with breathing problems indoors."
            ),
        ),
        (
            121,
            "RED",
            "Move PE and assembly indoors, keep windows closed, and avoid outdoor activity.",
        ),
    ),
)
def test_existing_advice_text_is_preserved(pm25, expected_status, expected_advice):
    assert classify(pm25) == (expected_status, expected_advice)


def test_activity_factor_remains_undefined_and_unused():
    assert ACTIVITY_FACTOR is None
    assert classify(60) == ("GREEN", ADVICE["GREEN"])
