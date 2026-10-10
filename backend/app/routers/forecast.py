"""Forecast API endpoint."""

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings
from app.deps import get_settings
from app.schemas.forecast import ErrorResponse, ForecastResponse
from app.services.air import AirProviderError, AirProviderTimeout
from app.services.forecast import build_forecast

router = APIRouter(tags=["forecast"])


@router.get(
    "/forecast",
    response_model=ForecastResponse,
    responses={
        422: {"model": ErrorResponse},
        502: {"model": ErrorResponse},
        504: {"model": ErrorResponse},
    },
)
def get_forecast(
    latitude: Annotated[float, Query(ge=-90, le=90)],
    longitude: Annotated[float, Query(ge=-180, le=180)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> ForecastResponse:
    """Return an hourly PM2.5 forecast for the requested coordinates."""
    try:
        return build_forecast(latitude, longitude, settings)
    except AirProviderTimeout as exc:
        raise HTTPException(
            status_code=504,
            detail={
                "code": "UPSTREAM_TIMEOUT",
                "message": "Forecast provider timed out.",
            },
        ) from exc
    except AirProviderError as exc:
        raise HTTPException(
            status_code=502,
            detail={
                "code": "UPSTREAM_FAILURE",
                "message": "Forecast provider is unavailable.",
            },
        ) from exc
