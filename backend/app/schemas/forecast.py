"""Stable API models for hourly PM2.5 forecasts and planning hints."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Status = Literal["GREEN", "YELLOW", "RED", "UNKNOWN"]


class Location(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class ForecastSource(BaseModel):
    provider: str
    model: str
    provider_url: str
    model_url: str
    license: str
    attribution: str
    model_resolution_note: str


class HourlyForecast(BaseModel):
    time: datetime
    pm25: float | None = Field(default=None, ge=0)
    status: Status


class AirQualitySummary(BaseModel):
    average_pm25: float | None = Field(default=None, ge=0)
    peak_pm25: float | None = Field(default=None, ge=0)
    status: Status
    valid_reading_count: int = Field(ge=0)
    missing_school_hour_count: int = Field(ge=0)
    policy_note: str
    advice: str


class ActivityWindow(BaseModel):
    start: datetime
    end: datetime
    average_pm25: float = Field(ge=0)
    status: Status
    outdoor_activity_recommended: bool
    reason_code: Literal[
        "LOWEST_PM25_WINDOW",
        "LOWEST_PM25_WINDOW_BUT_RED",
        "HIGHEST_PM25_WINDOW",
    ]


class ActivityRecommendations(BaseModel):
    best_window: ActivityWindow | None
    worst_window: ActivityWindow | None
    no_suitable_window: bool
    note: str
    activity_guidance: list["ActivityGuidance"] = Field(default_factory=list)


class ActivityGuidance(BaseModel):
    activity: Literal["pe", "sports", "recess", "assembly", "bus_wait"]
    guidance_code: Literal[
        "INCOMPLETE_FORECAST", "RED_POLICY_REVIEW", "GENERAL_POLICY"
    ]


class ForecastResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    data_type: Literal["forecast"] = "forecast"
    location: Location
    timezone: str
    retrieved_at: datetime
    stale: bool = False
    source: ForecastSource
    hourly: list[HourlyForecast]
    school_hours_summary: AirQualitySummary
    recommendations: ActivityRecommendations


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorDetail
