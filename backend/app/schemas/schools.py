"""Request and response models for school registration and status APIs."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas.forecast import ActivityWindow, ForecastSource, HourlyForecast, Status


class SchoolCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=3, max_length=80)
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    language: Literal["English", "Hindi", "Marathi"]

    @field_validator("name")
    @classmethod
    def name_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()
        if len(value) < 3:
            raise ValueError("name must contain at least three non-space characters")
        return value


class SchoolSummary(BaseModel):
    school_id: str
    name: str


class SchoolOption(SchoolSummary):
    """School picker record, including its saved forecast coordinates."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class SchoolCreated(SchoolSummary):
    status: Literal["created"] = "created"


class SubscribeRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    school_id: str = Field(min_length=1, max_length=128)
    email: str = Field(min_length=3, max_length=254, pattern=r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
    sensitive: bool = False


class SubscribeResponse(BaseModel):
    status: Literal["pending_confirmation", "demo_only"]


class StatusResponse(BaseModel):
    school: SchoolSummary
    date: str | None
    status: Status
    average_pm25: float | None
    peak_pm25: float | None
    best_window: ActivityWindow | None
    worst_window: ActivityWindow | None
    hourly: list[HourlyForecast]
    source: ForecastSource
    retrieved_at: datetime


class HistoryEntry(BaseModel):
    date: str
    average_pm25: float | None
    peak_pm25: float | None
    status: Status
    best_window: ActivityWindow | None = None
    worst_window: ActivityWindow | None = None


class HistoryCounts(BaseModel):
    green: int = Field(ge=0)
    yellow: int = Field(ge=0)
    red: int = Field(ge=0)


class HistoryResponse(BaseModel):
    school: SchoolSummary
    days: int = Field(ge=1, le=90)
    counts: HistoryCounts
    daily: list[HistoryEntry]
