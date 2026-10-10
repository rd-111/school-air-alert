"""School, subscription, current status, and history API routes."""

from datetime import datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, Query

from app.config import Settings
from app.deps import get_repositories, get_settings
from app.schemas.forecast import ErrorResponse
from app.schemas.schools import (
    HistoryResponse,
    SchoolCreate,
    SchoolCreated,
    SchoolSummary,
    StatusResponse,
    SubscribeRequest,
    SubscribeResponse,
)
from app.services.air import AirProviderError, AirProviderTimeout
from app.services.forecast import build_forecast
from app.services.schools import (
    SchoolNotFound,
    SchoolTopicsUnavailable,
    add_email_subscription,
    build_history,
    build_status,
    register_school,
)

router = APIRouter(tags=["schools"])
Repositories = dict


@router.get("/schools", response_model=list[SchoolSummary])
def list_schools(
    repositories: Annotated[Repositories, Depends(get_repositories)],
):
    return [
        {"school_id": school["school_id"], "name": school["name"]}
        for school in repositories["schools"].list_all()
    ]


@router.post(
    "/schools",
    response_model=SchoolCreated,
    status_code=201,
    responses={400: {"model": ErrorResponse}, 502: {"model": ErrorResponse}},
)
def create_school(
    school: SchoolCreate,
    repositories: Annotated[Repositories, Depends(get_repositories)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        return register_school(
            repositories["schools"], school.model_dump(), settings
        )
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "SCHOOL_CREATE_FAILED", "message": "School could not be created."},
        ) from exc


@router.post(
    "/subscribe",
    response_model=SubscribeResponse,
    responses={400: {"model": ErrorResponse}, 404: {"model": ErrorResponse}},
)
def subscribe(
    request: SubscribeRequest,
    repositories: Annotated[Repositories, Depends(get_repositories)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    try:
        return add_email_subscription(
            repositories["schools"],
            repositories["subscribers"],
            request.model_dump(),
            settings,
        )
    except SchoolNotFound as exc:
        raise HTTPException(
            status_code=404,
            detail={"code": "SCHOOL_NOT_FOUND", "message": "School was not found."},
        ) from exc
    except SchoolTopicsUnavailable as exc:
        raise HTTPException(
            status_code=503,
            detail={"code": "SUBSCRIPTION_UNAVAILABLE", "message": "Email subscription is unavailable."},
        ) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "SUBSCRIPTION_FAILED", "message": "Email subscription could not be started."},
        ) from exc


@router.get(
    "/status",
    response_model=StatusResponse,
    responses={404: {"model": ErrorResponse}, 502: {"model": ErrorResponse}, 504: {"model": ErrorResponse}},
)
def get_status(
    school_id: Annotated[str, Query(min_length=1, max_length=128)],
    repositories: Annotated[Repositories, Depends(get_repositories)],
    settings: Annotated[Settings, Depends(get_settings)],
):
    school = repositories["schools"].get(school_id)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "SCHOOL_NOT_FOUND", "message": "School was not found."},
        )
    try:
        forecast = build_forecast(school["lat"], school["lon"], settings)
    except AirProviderTimeout as exc:
        raise HTTPException(
            status_code=504,
            detail={"code": "UPSTREAM_TIMEOUT", "message": "Forecast provider timed out."},
        ) from exc
    except AirProviderError as exc:
        raise HTTPException(
            status_code=502,
            detail={"code": "UPSTREAM_FAILURE", "message": "Forecast provider is unavailable."},
        ) from exc
    return build_status(school, repositories["history"].latest(school_id), forecast)


@router.get(
    "/history",
    response_model=HistoryResponse,
    responses={404: {"model": ErrorResponse}},
)
def get_history(
    school_id: Annotated[str, Query(min_length=1, max_length=128)],
    days: Annotated[int, Query(ge=1)] = 30,
    repositories: Annotated[Repositories, Depends(get_repositories)] = None,
):
    school = repositories["schools"].get(school_id)
    if school is None:
        raise HTTPException(
            status_code=404,
            detail={"code": "SCHOOL_NOT_FOUND", "message": "School was not found."},
        )
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    return build_history(school, repositories["history"], days, today=today)
