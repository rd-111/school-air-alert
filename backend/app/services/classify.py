"""Classify PM2.5 with the app's configurable school policy, not official AQI."""

from collections.abc import Mapping
from math import isfinite

# TODO verify against CPCB guidance. Values are placeholders for PM2.5 in
# ug/m3 averaged over school hours.
LEVELS = {
    "GREEN": 60,
    "YELLOW": 120,
}

# TODO verify against CPCB guidance.
LEVELS_SENSITIVE = {
    "GREEN": 40,
    "YELLOW": 90,
}

# TODO verify the intended purpose and value against project specifications
# and CPCB guidance. None means undefined; it is not used by classification.
ACTIVITY_FACTOR = None

ADVICE = {
    "GREEN": "Normal outdoor activities are fine.",
    "YELLOW": (
        "Shorten outdoor play, move strenuous activity to the safest hours, "
        "and keep students with breathing problems indoors."
    ),
    "RED": "Move PE and assembly indoors, keep windows closed, and avoid outdoor activity.",
}

UNKNOWN_ADVICE = "There is not enough forecast data to classify this period."


def classify(pm25, sensitive=False, levels: Mapping[str, float] | None = None):
    """Return status and advice; return UNKNOWN for absent or invalid readings.

    ``levels`` optionally supplies the two configurable boundaries. The existing
    module constants remain the defaults and the original two-argument interface
    remains valid.
    """
    if pm25 is None or isinstance(pm25, bool) or not isinstance(pm25, (int, float)):
        return "UNKNOWN", UNKNOWN_ADVICE
    if not isfinite(pm25) or pm25 < 0:
        return "UNKNOWN", UNKNOWN_ADVICE

    selected_levels = (
        levels if levels is not None else LEVELS_SENSITIVE if sensitive else LEVELS
    )
    green_max = selected_levels.get("GREEN")
    yellow_max = selected_levels.get("YELLOW")
    if (
        green_max is None
        or yellow_max is None
        or green_max < 0
        or yellow_max <= green_max
    ):
        raise ValueError("classification thresholds must satisfy 0 <= GREEN < YELLOW")

    if pm25 <= green_max:
        status = "GREEN"
    elif pm25 <= yellow_max:
        status = "YELLOW"
    else:
        status = "RED"

    return status, ADVICE[status]
