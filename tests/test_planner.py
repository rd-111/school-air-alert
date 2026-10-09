import unittest

from src.common.planner import best_window, summary, worst_window


class PlannerTests(unittest.TestCase):
    def test_best_and_worst_single_hour_windows(self):
        hourly = [(7, 20), (8, 10), (9, 30)]
        self.assertEqual(best_window(hourly), (8, 9))
        self.assertEqual(worst_window(hourly), (9, 10))

    def test_best_and_worst_multi_hour_windows(self):
        hourly = [(7, 20), (8, 10), (9, 30), (10, 40)]
        self.assertEqual(best_window(hourly, length=2), (7, 9))
        self.assertEqual(worst_window(hourly, length=2), (9, 11))

    def test_ties_choose_earliest_window(self):
        hourly = [(7, 5), (8, 10), (9, 5), (10, 10)]
        self.assertEqual(best_window(hourly), (7, 8))
        self.assertEqual(worst_window(hourly), (8, 9))

    def test_empty_input(self):
        self.assertIsNone(best_window([]))
        self.assertIsNone(worst_window([]))
        self.assertEqual(
            summary([]), {"avg": None, "peak": None, "best": None, "worst": None}
        )

    def test_short_input_returns_no_window(self):
        hourly = [(7, 10)]
        self.assertIsNone(best_window(hourly, length=2))
        self.assertIsNone(worst_window(hourly, length=2))

    def test_summary_calculates_values_and_windows(self):
        hourly = [(7, 20), (8, 10), (9, 30)]
        self.assertEqual(
            summary(hourly),
            {"avg": 20, "peak": 30, "best": (8, 9), "worst": (9, 10)},
        )

    def test_windows_require_contiguous_hours(self):
        hourly = [(7, 5), (9, 1)]
        self.assertIsNone(best_window(hourly, length=2))
        self.assertIsNone(worst_window(hourly, length=2))


if __name__ == "__main__":
    unittest.main()
