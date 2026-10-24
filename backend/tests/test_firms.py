"""NASA FIRMS normalization, proximity, time-window, and failure tests."""

from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.error import HTTPError

import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app
from app.schemas.smoke import FireDetection
from app.services import firms
from app.services.firms import FirmsProviderError, FirmsProviderTimeout
from app.services.wind import WindDataError, WindProviderError, WindSample

FIXTURE = Path(__file__).parent / "fixtures/firms_sample.csv"
SAMPLE = FIXTURE.read_text()
NOW = datetime(2026, 10, 23, 12, 0, tzinfo=timezone.utc)
SCHOOL = {
    "school_id": "demo-school",
    "name": "Demo School",
    "lat": 19.076,
    "lon": 72.8777,
}


def setup_function():
    firms.clear_cache()


def teardown_function():
    firms.clear_cache()


def test_parser_returns_recent_detections_and_marks_older_nearby_data_stale():
    detections, stale_latest = firms.parse_firms_csv(
        SAMPLE,
        latitude=SCHOOL["lat"],
        longitude=SCHOOL["lon"],
        radius_km=25,
        now=NOW,
    )

    assert len(detections) == 1
    assert detections[0].satellite == "N21"
    assert detections[0].confidence == "n"
    assert detections[0].observed_at == datetime(2026, 10, 23, 11, tzinfo=timezone.utc)
    assert detections[0].distance_km < 1
    assert stale_latest == datetime(2026, 10, 22, 10, tzinfo=timezone.utc)


def test_parser_filters_detections_outside_exact_radius():
    detections, stale_latest = firms.parse_firms_csv(
        SAMPLE,
        latitude=SCHOOL["lat"],
        longitude=SCHOOL["lon"],
        radius_km=0.3,
        now=NOW,
    )

    assert detections == []
    assert stale_latest is None


def test_parser_returns_empty_for_header_only_no_detection_response():
    header = SAMPLE.splitlines()[0]
    detections, stale_latest = firms.parse_firms_csv(
        f"{header}\n",
        latitude=SCHOOL["lat"],
        longitude=SCHOOL["lon"],
        radius_km=25,
        now=NOW,
    )
    assert detections == []
    assert stale_latest is None


@pytest.mark.parametrize("payload", ["", "invalid response", "latitude,longitude\n19,72\n"])
def test_parser_rejects_malformed_provider_responses(payload):
    with pytest.raises(FirmsProviderError):
        firms.parse_firms_csv(
            payload,
            latitude=SCHOOL["lat"],
            longitude=SCHOOL["lon"],
            radius_km=25,
            now=NOW,
        )


def test_parser_rejects_response_with_only_malformed_rows():
    header = SAMPLE.splitlines()[0]
    with pytest.raises(FirmsProviderError):
        firms.parse_firms_csv(
            f"{header}\nnot-a-latitude,72,330,.4,.4,2026-10-23,1100,N21,VIIRS,n,2,300,2,D\n",
            latitude=SCHOOL["lat"],
            longitude=SCHOOL["lon"],
            radius_km=25,
            now=NOW,
        )


def test_search_box_is_bounded_and_uses_valid_area_order():
    west, south, east, north = firms._bounding_box(19.076, 72.8777, 25)
    assert -180 <= west < east <= 180
    assert -90 <= south < north <= 90
    assert east - west < 1
    assert north - south < 1


@pytest.mark.parametrize(
    "school",
    [
        {**SCHOOL, "lat": 91},
        {**SCHOOL, "lon": 181},
        {**SCHOOL, "lat": float("nan")},
    ],
)
def test_service_rejects_invalid_school_coordinates(school):
    with pytest.raises(ValueError, match="coordinates are invalid"):
        firms.get_smoke_hint(school, Settings(firms_map_key="test-map-key"), now=NOW)


def test_provider_timeout_is_converted_to_safe_timeout_error(monkeypatch):
    def timeout(*_args, **_kwargs):
        raise TimeoutError("private upstream detail")

    monkeypatch.setattr(firms, "urlopen", timeout)
    with pytest.raises(FirmsProviderTimeout, match="timed out"):
        firms.fetch_firms_csv(
            "test-map-key", latitude=19, longitude=72, radius_km=25
        )


def test_provider_uses_bounded_area_csv_for_noaa21_and_two_days(monkeypatch):
    captured = {}

    class FakeResponse(BytesIO):
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            self.close()

    def respond(request, timeout):
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        return FakeResponse(SAMPLE.encode())

    monkeypatch.setattr(firms, "urlopen", respond)
    result = firms.fetch_firms_csv(
        "test-map-key", latitude=19, longitude=72, radius_km=25
    )

    assert result == SAMPLE
    assert "/VIIRS_NOAA21_NRT/" in captured["url"]
    assert captured["url"].endswith("/2")
    assert "world" not in captured["url"]
    assert captured["timeout"] == firms.REQUEST_TIMEOUT_SECONDS


def test_provider_rate_limit_does_not_expose_url_or_credentials(monkeypatch):
    def rate_limited(*_args, **_kwargs):
        raise HTTPError("https://example.test/private-key", 429, "limit", {}, None)

    monkeypatch.setattr(firms, "urlopen", rate_limited)
    with pytest.raises(FirmsProviderError) as error:
        firms.fetch_firms_csv(
            "test-map-key", latitude=19, longitude=72, radius_km=25
        )
    assert "test-map-key" not in str(error.value)
    assert "private-key" not in str(error.value)


def test_unconfigured_service_never_calls_provider(monkeypatch):
    monkeypatch.setattr(
        firms,
        "fetch_firms_csv",
        lambda *_args, **_kwargs: pytest.fail("unconfigured service must not call NASA"),
    )
    result = firms.get_smoke_hint(SCHOOL, Settings(), now=NOW)
    assert result.status == "unconfigured"


def test_parser_removes_exact_duplicate_pixel_records():
    lines = SAMPLE.splitlines()
    detections, _ = firms.parse_firms_csv(
        "\n".join([*lines, lines[1]]),
        latitude=SCHOOL["lat"],
        longitude=SCHOOL["lon"],
        radius_km=25,
        now=NOW,
    )
    assert sum(item.observed_at.hour == 11 for item in detections) == 1
    assert detections[0].pixel_scan_km == pytest.approx(0.4)
    assert detections[0].pixel_track_km == pytest.approx(0.4)


def test_pixel_footprints_cluster_only_within_same_platform_and_overpass():
    observed_at = NOW.replace(minute=0)
    first = FireDetection(
        observed_at=observed_at, latitude=19.0, longitude=72.0, distance_km=1,
        satellite="N21", pixel_scan_km=0.4, pixel_track_km=0.4,
    )
    adjacent = FireDetection(
        observed_at=observed_at, latitude=19.0, longitude=72.000005, distance_km=1,
        satellite="N21", pixel_scan_km=0.4, pixel_track_km=0.4,
    )
    other_satellite = first.model_copy(update={"satellite": "N20"})
    other_overpass = first.model_copy(update={"observed_at": observed_at.replace(minute=1)})
    clusters = firms.cluster_detections([first, adjacent, other_satellite, other_overpass])
    assert sorted(len(cluster["pixels"]) for cluster in clusters) == [1, 1, 2]


def test_firms_failure_does_not_call_wind_provider(monkeypatch):
    firms.clear_cache()
    monkeypatch.setattr(
        firms, "fetch_firms_csv",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(FirmsProviderError("provider offline")),
    )
    monkeypatch.setattr(
        firms, "fetch_wind_samples",
        lambda *_args, **_kwargs: pytest.fail("wind must not run without FIRMS detections"),
    )
    result = firms.get_smoke_hint(SCHOOL, Settings(firms_map_key="fake-key"), now=NOW)
    assert result.status == "unavailable"


def test_wind_failure_keeps_firms_detections_and_is_indeterminate(monkeypatch):
    firms.clear_cache()
    monkeypatch.setattr(firms, "fetch_firms_csv", lambda *_args, **_kwargs: SAMPLE)
    monkeypatch.setattr(
        firms, "fetch_wind_samples",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(WindProviderError("offline")),
    )
    result = firms.get_smoke_hint(SCHOOL, Settings(firms_map_key="fake-key"), now=NOW)
    assert result.status == "wind_unavailable"
    assert result.detections
    assert result.clusters[0].wind_status == "indeterminate"


@pytest.mark.parametrize(
    ("direction_from", "expected_status"),
    [(45, "transport_possible"), (225, "no_upwind_clusters")],
)
def test_detected_cluster_is_matched_to_wind_at_its_place_and_time(
    monkeypatch, direction_from, expected_status
):
    firms.clear_cache()
    monkeypatch.setattr(firms, "fetch_firms_csv", lambda *_args, **_kwargs: SAMPLE)

    def wind_at_cluster(clusters):
        assert len(clusters) == 1
        assert clusters[0]["observed_at"].hour == 11
        assert clusters[0]["latitude"] == pytest.approx(19.08)
        assert clusters[0]["longitude"] == pytest.approx(72.88)
        return [[WindSample(clusters[0]["observed_at"], 2, direction_from)]]

    monkeypatch.setattr(firms, "fetch_wind_samples", wind_at_cluster)
    result = firms.get_smoke_hint(SCHOOL, Settings(firms_map_key="fake-key"), now=NOW)
    assert result.status == expected_status
    assert result.wind_source.dataset.startswith("Historical Forecast API; modeled")


def test_missing_wind_records_produce_indeterminate_cluster(monkeypatch):
    firms.clear_cache()
    monkeypatch.setattr(firms, "fetch_firms_csv", lambda *_args, **_kwargs: SAMPLE)
    monkeypatch.setattr(firms, "fetch_wind_samples", lambda clusters: [[] for _ in clusters])
    result = firms.get_smoke_hint(SCHOOL, Settings(firms_map_key="fake-key"), now=NOW)
    assert result.status == "wind_indeterminate"
    assert result.clusters[0].wind_status == "indeterminate"


def test_malformed_wind_response_is_indeterminate_not_a_firms_failure(monkeypatch):
    firms.clear_cache()
    monkeypatch.setattr(firms, "fetch_firms_csv", lambda *_args, **_kwargs: SAMPLE)
    monkeypatch.setattr(
        firms,
        "fetch_wind_samples",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(WindDataError("missing hourly data")),
    )
    result = firms.get_smoke_hint(SCHOOL, Settings(firms_map_key="fake-key"), now=NOW)
    assert result.status == "wind_indeterminate"
    assert result.detections


def test_no_firms_detections_does_not_request_wind(monkeypatch):
    firms.clear_cache()
    header = SAMPLE.splitlines()[0]
    monkeypatch.setattr(firms, "fetch_firms_csv", lambda *_args, **_kwargs: f"{header}\n")
    monkeypatch.setattr(
        firms, "fetch_wind_samples",
        lambda *_args, **_kwargs: pytest.fail("wind must not run without clusters"),
    )
    result = firms.get_smoke_hint(SCHOOL, Settings(firms_map_key="fake-key"), now=NOW)
    assert result.status == "no_detections"
    assert result.clusters == []
    assert result.school.latitude == SCHOOL["lat"]
    assert result.retrieved_at == NOW


def test_service_reports_relevant_nearby_detection_and_source(monkeypatch):
    monkeypatch.setattr(firms, "fetch_firms_csv", lambda *_args, **_kwargs: SAMPLE)
    monkeypatch.setattr(
        firms,
        "fetch_wind_samples",
        lambda clusters: [[WindSample(cluster["observed_at"], 2, 45)] for cluster in clusters],
    )
    settings = Settings(firms_map_key="test-map-key", firms_cache_ttl_seconds=0)
    result = firms.get_smoke_hint(SCHOOL, settings, now=NOW)
    assert result.status == "transport_possible"
    assert result.detections[0].distance_km < settings.firms_search_radius_km
    assert result.source.provider == "NASA FIRMS"
    assert result.retrieved_at == NOW


def test_service_caches_provider_payload_but_recomputes_the_24_hour_state(monkeypatch):
    calls = []

    def fetch(*_args, **_kwargs):
        calls.append(True)
        return SAMPLE

    monkeypatch.setattr(firms, "fetch_firms_csv", fetch)
    monkeypatch.setattr(
        firms,
        "fetch_wind_samples",
        lambda clusters: [[WindSample(cluster["observed_at"], 2, 45)] for cluster in clusters],
    )
    settings = Settings(firms_map_key="test-map-key", firms_cache_ttl_seconds=300)
    first = firms.get_smoke_hint(SCHOOL, settings, now=NOW)
    next_day = firms.get_smoke_hint(
        SCHOOL, settings, now=datetime(2026, 10, 24, 12, tzinfo=timezone.utc)
    )

    assert len(calls) == 1
    assert first.status == "transport_possible"
    assert next_day.status == "stale"
    assert next_day.retrieved_at == NOW


def test_service_caches_historical_wind_for_the_same_detection_clusters(monkeypatch):
    firms.clear_cache()
    wind_calls = []
    monkeypatch.setattr(firms, "fetch_firms_csv", lambda *_args, **_kwargs: SAMPLE)

    def fetch_wind(clusters):
        wind_calls.append(clusters)
        return [[WindSample(cluster["observed_at"], 2, 45)] for cluster in clusters]

    monkeypatch.setattr(firms, "fetch_wind_samples", fetch_wind)
    settings = Settings(firms_map_key="test-map-key", firms_cache_ttl_seconds=300)
    first = firms.get_smoke_hint(SCHOOL, settings, now=NOW)
    second = firms.get_smoke_hint(SCHOOL, settings, now=NOW)
    assert len(wind_calls) == 1
    assert first.wind_source.retrieved_at == second.wind_source.retrieved_at


def test_service_distinguishes_stale_and_no_detection_states(monkeypatch):
    header, *_ = SAMPLE.splitlines()
    stale_row = SAMPLE.splitlines()[3]
    monkeypatch.setattr(
        firms,
        "fetch_firms_csv",
        lambda *_args, **_kwargs: f"{header}\n{stale_row}\n",
    )
    settings = Settings(firms_map_key="test-map-key", firms_cache_ttl_seconds=0)
    stale = firms.get_smoke_hint(SCHOOL, settings, now=NOW)
    assert stale.status == "stale"
    assert stale.latest_observation_at == datetime(2026, 10, 22, 10, tzinfo=timezone.utc)

    monkeypatch.setattr(firms, "fetch_firms_csv", lambda *_args, **_kwargs: f"{header}\n")
    empty = firms.get_smoke_hint(SCHOOL, settings, now=NOW)
    assert empty.status == "no_detections"
    assert empty.latest_observation_at is None


def test_service_returns_unavailable_when_provider_times_out(monkeypatch):
    def timeout(*_args, **_kwargs):
        raise FirmsProviderTimeout("FIRMS request timed out")

    monkeypatch.setattr(firms, "fetch_firms_csv", timeout)
    result = firms.get_smoke_hint(
        SCHOOL,
        Settings(firms_map_key="test-map-key", firms_cache_ttl_seconds=0),
        now=NOW,
    )
    assert result.status == "unavailable"
    assert result.retrieved_at is None


def test_smoke_hint_endpoint_uses_registered_school_location_and_structured_404():
    client = TestClient(create_app(Settings(use_memory_db=True)))
    response = client.get("/api/v1/schools/demo-school/smoke-hint")
    assert response.status_code == 200
    assert response.json()["status"] == "unconfigured"
    assert response.json()["school"]["latitude"] == SCHOOL["lat"]
    assert response.json()["school"]["longitude"] == SCHOOL["lon"]

    missing = client.get("/api/v1/schools/not-a-school/smoke-hint")
    assert missing.status_code == 404
    assert missing.json() == {
        "error": {"code": "SCHOOL_NOT_FOUND", "message": "School was not found."}
    }
