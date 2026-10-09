"""Prototype PM2.5 alert classification.

Thresholds below are illustrative prototype values in micrograms per cubic
meter (µg/m³). They are not official health guidance. Readings must use a
matching averaging period before classification.
"""


# Illustrative thresholds only; verify authoritative guidance before use.
YELLOW_THRESHOLD_UG_M3 = 15.0
RED_THRESHOLD_UG_M3 = 35.0


def classify_pm25(pm25_ug_m3: float) -> str:
    """Return a Green, Yellow, or Red alert for a PM2.5 reading in µg/m³."""
    if isinstance(pm25_ug_m3, bool) or not isinstance(pm25_ug_m3, (int, float)):
        raise TypeError("PM2.5 reading must be a number")
    if pm25_ug_m3 < 0:
        raise ValueError("PM2.5 reading cannot be negative")

    if pm25_ug_m3 >= RED_THRESHOLD_UG_M3:
        return "Red"
    if pm25_ug_m3 >= YELLOW_THRESHOLD_UG_M3:
        return "Yellow"
    return "Green"
