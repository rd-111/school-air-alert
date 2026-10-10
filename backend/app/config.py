"""Application settings sourced from explicitly named environment variables."""

from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.services.classify import LEVELS, LEVELS_SENSITIVE


class Settings(BaseSettings):
    """Settings for local and deployed application behavior."""

    model_config = SettingsConfigDict(
        env_file=None,
        case_sensitive=False,
        extra="ignore",
    )

    use_memory_db: bool = False
    cors_origins: str = (
        "http://localhost:5173,http://localhost:5174,http://localhost:5175,"
        "http://127.0.0.1:5173,http://127.0.0.1:5174,http://127.0.0.1:5175"
    )
    forecast_cache_ttl_seconds: int = Field(default=300, ge=0, le=3600)
    pm25_green_max: float = Field(default=LEVELS["GREEN"], ge=0)
    pm25_yellow_max: float = Field(default=LEVELS["YELLOW"], gt=0)
    pm25_sensitive_green_max: float = Field(
        default=LEVELS_SENSITIVE["GREEN"], ge=0
    )
    pm25_sensitive_yellow_max: float = Field(
        default=LEVELS_SENSITIVE["YELLOW"], gt=0
    )
    schools_table: str = ""
    history_table: str = ""
    subscribers_table: str = ""
    notification_runs_table: str = ""
    aws_region: str = ""
    telegram_token: str = ""
    telegram_secret: str = ""
    bedrock_model: str = ""

    @model_validator(mode="after")
    def validate_classification_thresholds(self) -> "Settings":
        if self.pm25_green_max >= self.pm25_yellow_max:
            raise ValueError("PM25_GREEN_MAX must be below PM25_YELLOW_MAX")
        if self.pm25_sensitive_green_max >= self.pm25_sensitive_yellow_max:
            raise ValueError(
                "PM25_SENSITIVE_GREEN_MAX must be below PM25_SENSITIVE_YELLOW_MAX"
            )
        return self
