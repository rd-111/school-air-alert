"""API router aggregation."""

from fastapi import APIRouter

from app.routers.forecast import router as forecast_router
from app.routers.health import router as health_router
from app.routers.schools import router as schools_router
from app.routers.telegram import router as telegram_router

api_router = APIRouter()
api_router.include_router(health_router)
api_router.include_router(forecast_router)
api_router.include_router(schools_router)
api_router.include_router(telegram_router)
