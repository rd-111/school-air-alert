import asyncio

import httpx
import pytest

from app.config import Settings
from app.main import create_app

LOCAL_FRONTEND_ORIGINS = (
    "http://localhost:5173",
    "http://localhost:5174",
    "http://localhost:5175",
    "http://127.0.0.1:5173",
    "http://127.0.0.1:5174",
    "http://127.0.0.1:5175",
)


async def _preflight(app, origin):
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        return await client.options(
            "/api/v1/forecast",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "accept",
            },
        )


@pytest.mark.parametrize("origin", LOCAL_FRONTEND_ORIGINS)
def test_local_frontend_origins_are_allowed(origin):
    response = asyncio.run(_preflight(create_app(Settings()), origin))

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == origin


def test_unapproved_origin_is_not_reflected():
    response = asyncio.run(
        _preflight(create_app(Settings()), "http://unapproved.example")
    )

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


def test_explicit_deployment_origins_replace_local_defaults():
    deployment_origin = "https://school.example"
    app = create_app(Settings(cors_origins=deployment_origin))

    allowed = asyncio.run(_preflight(app, deployment_origin))
    local = asyncio.run(_preflight(app, "http://localhost:5174"))

    assert allowed.status_code == 200
    assert allowed.headers["access-control-allow-origin"] == deployment_origin
    assert local.status_code == 400
    assert "access-control-allow-origin" not in local.headers
