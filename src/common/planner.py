"""Find lower- and higher-PM2.5 windows in hourly readings."""


def _window(hourly, length, choose_minimum):
    if length < 1:
        raise ValueError("length must be at least 1")
    if len(hourly) < length:
        return None

    best_window = None
    best_average = None
    for start in range(len(hourly) - length + 1):
        window = hourly[start : start + length]
        if any(window[index][0] + 1 != window[index + 1][0] for index in range(len(window) - 1)):
            continue
        average = sum(reading for _, reading in window) / length
        is_better = (
            best_average is None
            or (average < best_average if choose_minimum else average > best_average)
        )
        if is_better:
            best_window = window
            best_average = average

    if best_window is None:
        return None
    return (best_window[0][0], best_window[-1][0] + 1)


def best_window(hourly, length=1):
    """Return ``(start_hour, end_hour)`` for the lowest-average contiguous window."""
    return _window(hourly, length, choose_minimum=True)


def worst_window(hourly, length=1):
    """Return ``(start_hour, end_hour)`` for the highest-average contiguous window."""
    return _window(hourly, length, choose_minimum=False)


def summary(hourly):
    """Return average, peak, best window, and worst window for readings."""
    if not hourly:
        return {"avg": None, "peak": None, "best": None, "worst": None}

    values = [reading for _, reading in hourly]
    return {
        "avg": sum(values) / len(values),
        "peak": max(values),
        "best": best_window(hourly),
        "worst": worst_window(hourly),
    }
