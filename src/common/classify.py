"""Classify PM2.5 readings using prototype thresholds."""

# TODO verify against CPCB guidance. These placeholder thresholds apply to
# PM2.5 in ug/m3 averaged over school hours.
LEVELS = {
    "GREEN": 60,
    "YELLOW": 120,
}
LEVELS_SENSITIVE = {
    "GREEN": 40,
    "YELLOW": 90,
}

ADVICE = {
    "GREEN": "Normal outdoor activities are fine.",
    "YELLOW": (
        "Shorten outdoor play, move strenuous activity to the safest hours, "
        "and keep students with breathing problems indoors."
    ),
    "RED": "Move PE and assembly indoors, keep windows closed, and avoid outdoor activity.",
}


def classify(pm25, sensitive=False):
    """Return ``(status, advice)`` for a school-hours PM2.5 value in ug/m3."""
    levels = LEVELS_SENSITIVE if sensitive else LEVELS

    if pm25 <= levels["GREEN"]:
        status = "GREEN"
    elif pm25 <= levels["YELLOW"]:
        status = "YELLOW"
    else:
        status = "RED"

    return status, ADVICE[status]
