from app.services.planner import best_window, summary, worst_window


def test_best_and_worst_choose_earliest_tied_hour():
    hourly = [(7, 10), (8, 20), (9, 10)]
    assert best_window(hourly) == (7, 8)
    assert worst_window(hourly) == (8, 9)


def test_two_hour_windows_require_contiguous_hours_and_choose_earliest_tie():
    hourly = [(7, 10), (8, 20), (10, 10), (11, 20)]
    assert best_window(hourly, length=2) == (7, 9)


def test_empty_input_summary_has_no_values_or_windows():
    assert summary([]) == {"avg": None, "peak": None, "best": None, "worst": None}


def test_short_input_has_no_window():
    assert best_window([(7, 10)], length=2) is None
    assert worst_window([(7, 10)], length=2) is None


def test_summary_calculates_average_peak_and_windows():
    assert summary([(7, 10), (8, 30)]) == {
        "avg": 20,
        "peak": 30,
        "best": (7, 8),
        "worst": (8, 9),
    }
