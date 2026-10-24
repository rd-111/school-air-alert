"""Response models for optional NASA FIRMS satellite fire detections."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SmokeHintSchool(BaseModel):
    school_id: str
    name: str
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class SmokeHintSource(BaseModel):
    provider: str = "NASA FIRMS"
    dataset: str = "VIIRS NOAA-21 Near Real-Time"
    url: str = "https://firms.modaps.eosdis.nasa.gov/api/area/"


class FireDetection(BaseModel):
    observed_at: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    distance_km: float = Field(ge=0)
    satellite: str | None = None
    confidence: str | None = None
    pixel_scan_km: float | None = Field(default=None, gt=0)
    pixel_track_km: float | None = Field(default=None, gt=0)


class WindSource(BaseModel):
    provider: str = "Open-Meteo"
    dataset: str = "Historical Forecast API; modeled 10 m wind (Best Match)"
    url: str = "https://open-meteo.com/en/docs/historical-forecast-api"
    wind_height_m: int = 10
    speed_unit: str = "m/s"
    retrieved_at: datetime | None = None


class FireCluster(BaseModel):
    cluster_id: str
    observed_at: datetime
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    pixel_count: int = Field(ge=1)
    wind_status: Literal["indeterminate", "transport_toward", "not_toward"]
    wind_speed_mps: float | None = Field(default=None, ge=0)
    wind_direction_from_degrees: float | None = Field(default=None, ge=0, le=360)


class SmokeHintResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal[
        "unconfigured",
        "unavailable",
        "no_detections",
        "stale",
        "relevant_detections",
        "wind_unavailable",
        "wind_indeterminate",
        "no_upwind_clusters",
        "transport_possible",
    ]
    school: SmokeHintSchool
    retrieved_at: datetime | None
    latest_observation_at: datetime | None = None
    lookback_hours: int = 24
    search_radius_km: float = Field(gt=0, le=100)
    detections: list[FireDetection] = Field(default_factory=list)
    clusters: list[FireCluster] = Field(default_factory=list)
    source: SmokeHintSource = Field(default_factory=SmokeHintSource)
    wind_source: WindSource | None = None
