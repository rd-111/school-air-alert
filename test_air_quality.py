import unittest

from air_quality import classify_pm25


class ClassifyPm25Tests(unittest.TestCase):
    def test_green_below_yellow_threshold(self):
        self.assertEqual(classify_pm25(14.9), "Green")

    def test_yellow_at_and_below_red_threshold(self):
        self.assertEqual(classify_pm25(15), "Yellow")
        self.assertEqual(classify_pm25(34.9), "Yellow")

    def test_red_at_and_above_red_threshold(self):
        self.assertEqual(classify_pm25(35), "Red")
        self.assertEqual(classify_pm25(50), "Red")

    def test_zero_is_green(self):
        self.assertEqual(classify_pm25(0), "Green")

    def test_negative_reading_is_rejected(self):
        with self.assertRaises(ValueError):
            classify_pm25(-0.1)

    def test_non_numeric_reading_is_rejected(self):
        for reading in ("20", None, True):
            with self.subTest(reading=reading):
                with self.assertRaises(TypeError):
                    classify_pm25(reading)


if __name__ == "__main__":
    unittest.main()
