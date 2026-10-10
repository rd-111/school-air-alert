"""Find contiguous lower- and higher-PM2.5 school-hour windows."""

from __future__ import annotations

from collections.abc import Sequence


def _window(hourly: Sequence[tuple[int, float]], length: int, choose_minimum: bool):
    if length < 1:
        raise ValueError("length must be at least 1")
    if len(hourly) < length:
        return None

    selected = None
    selected_average = None
    for start in range(len(hourly) - length + 1):
        window = hourly[start : start + length]
        if any(window[i][0] + 1 != window[i + 1][0] for i in range(len(window) - 1)):
            continue
        average = sum(value for _, value in window) / length
        better = selected_average is None or (
            average < selected_average if choose_minimum else average > selected_average
        )
        if better:
            selected = window
            selected_average = average

    if selected is None:
        return None
    return selected[0][0], selected[-1][0] + 1


def best_window(hourly: Sequence[tuple[int, float]], length: int = 1):
    """Return the earliest lowest-average contiguous interval, or ``None``."""
    return _window(hourly, length, choose_minimum=True)


def worst_window(hourly: Sequence[tuple[int, float]], length: int = 1):
    """Return the earliest highest-average contiguous interval, or ``None``."""
    return _window(hourly, length, choose_minimum=False)


def summary(hourly: Sequence[tuple[int, float]]) -> dict:
    """Return average, peak, best, and worst for valid readings."""
    if not hourly:
        return {"avg": None, "peak": None, "best": None, "worst": None}
    values = [value for _, value in hourly]
    return {
        "avg": sum(values) / len(values),
        "peak": max(values),
        "best": best_window(hourly),
        "worst": worst_window(hourly),
    }
