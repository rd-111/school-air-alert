"""FastAPI application entry point."""

import logging

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.routers import api_router

logger = logging.getLogger(__name__)


def _http_error_code(status_code: int) -> str:
    if status_code == 404:
        return "NOT_FOUND"
    if status_code == 405:
        return "METHOD_NOT_ALLOWED"
    return "HTTP_ERROR"


def create_app() -> FastAPI:
    """Create the API app with versioned routes and safe error responses."""
    application = FastAPI(title="School Air Alert API", version="1.0.0")
    application.include_router(api_router, prefix="/api/v1")

    @application.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request, exc: StarletteHTTPException
    ) -> JSONResponse:
        del request
        detail = exc.detail if isinstance(exc.detail, str) else "Request failed."
        return JSONResponse(
            status_code=exc.status_code,
            content={
                "error": {
                    "code": _http_error_code(exc.status_code),
                    "message": detail,
                }
            },
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
