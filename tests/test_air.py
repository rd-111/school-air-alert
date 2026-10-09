import json
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs, urlparse

from src.common.air import fetch_hourly_pm25, parse_school_hours


FIXTURE_PATH = Path(__file__).parent / "fixtures" / "open_meteo_sample.json"


class AirForecastTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with FIXTURE_PATH.open(encoding="utf-8") as fixture_file:
            cls.fixture = json.load(fixture_file)

    def test_parse_school_hours_from_fixture_and_skip_missing_reading(self):
        self.assertEqual(
            parse_school_hours(self.fixture),
            [(7, 13.4), (9, 16.2), (10, 17.5), (11, 18.1), (12, 17.3), (13, 15.8), (14, 14.2)],
        )

    def test_empty_or_malformed_data_returns_empty_list(self):
        for data in (None, {}, {"hourly": None}, {"hourly": {"time": [], "pm2_5": []}}):
            with self.subTest(data=data):
                self.assertEqual(parse_school_hours(data), [])

    @patch("src.common.air.urlopen")
    def test_fetch_uses_required_query_and_timeout(self, mock_urlopen):
        response = mock_urlopen.return_value.__enter__.return_value
        response.read.return_value = json.dumps(self.fixture).encode("utf-8")

        result = fetch_hourly_pm25(28.625, 77.25)

        self.assertEqual(result, self.fixture)
        args, kwargs = mock_urlopen.call_args
        query = parse_qs(urlparse(args[0]).query)
        self.assertEqual(query["hourly"], ["pm2_5"])
        self.assertEqual(query["forecast_days"], ["1"])
        self.assertEqual(query["timezone"], ["Asia/Kolkata"])
        self.assertEqual(query["latitude"], ["28.625"])
        self.assertEqual(query["longitude"], ["77.25"])
        self.assertEqual(kwargs["timeout"], 10)


if __name__ == "__main__":
    unittest.main()
