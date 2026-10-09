import unittest

from src.common.classify import classify


class ClassifyTests(unittest.TestCase):
    def test_normal_threshold_boundaries(self):
        cases = ((60, "GREEN"), (61, "YELLOW"), (120, "YELLOW"), (121, "RED"))
        for pm25, expected_status in cases:
            with self.subTest(pm25=pm25):
                status, advice = classify(pm25)
                self.assertEqual(status, expected_status)
                self.assertTrue(advice)

    def test_sensitive_threshold_boundaries(self):
        cases = ((40, "GREEN"), (41, "YELLOW"), (90, "YELLOW"), (91, "RED"))
        for pm25, expected_status in cases:
            with self.subTest(pm25=pm25):
                status, advice = classify(pm25, sensitive=True)
                self.assertEqual(status, expected_status)
                self.assertTrue(advice)


if __name__ == "__main__":
    unittest.main()
