"""FastAPI application entry point."""

import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config import Settings
from app.deps import build_repositories, get_repositories, get_settings
from app.routers import api_router

logger = logging.getLogger(__name__)


def _http_error_code(status_code: int) -> str:
    if status_code == 404:
        return "NOT_FOUND"
    if status_code == 405:
        return "METHOD_NOT_ALLOWED"
    if status_code == 422:
        return "VALIDATION_ERROR"
    return "HTTP_ERROR"


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create the API app with versioned routes and safe error responses."""
    application = FastAPI(title="School Air Alert API", version="1.0.0")
    active_settings = settings or get_settings()
    if settings is not None:
        application.dependency_overrides[get_settings] = lambda: active_settings
        repository_cache = {}

        def get_app_repositories():
            if "repositories" not in repository_cache:
                repository_cache["repositories"] = build_repositories(active_settings)
            return repository_cache["repositories"]

        application.dependency_overrides[get_repositories] = get_app_repositories
    origins = [
        origin.strip()
        for origin in active_settings.cors_origins.split(",")
        if origin.strip()
    ]
    application.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type", "X-Telegram-Bot-Api-Secret-Token"],
        allow_credentials=False,
    )
    application.include_router(api_router, prefix="/api/v1")

    @application.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        del exc
        status_code = (
            400
            if request.url.path in {"/api/v1/schools", "/api/v1/subscribe"}
            else 422
        )
        return JSONResponse(
            status_code=status_code,
            content={
                "error": {
                    "code": "VALIDATION_ERROR",
                    "message": "Request parameters are invalid.",
                }
            },
        )

    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        del request
        if isinstance(exc.detail, dict) and {"code", "message"} <= exc.detail.keys():
            error = exc.detail
        else:
            detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
            error = {"code": _http_error_code(exc.status_code), "message": detail}
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": error},
            headers=exc.headers,
        )

    @application.exception_handler(Exception)
    async def unexpected_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        del request, exc
        logger.error("Unhandled API error")
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_SERVER_ERROR",
                    "message": "An unexpected error occurred.",
                }
            },
        )

    return application


app = create_app()
