from typing import Annotated

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.config import Settings
from app.deps import get_settings
from app.main import app, create_app


def test_health_route_is_versioned_and_uses_response_model():
    response = TestClient(app).get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    assert "/api/v1/health" in app.openapi()["paths"]


def test_unknown_route_returns_standard_404_error():
    response = TestClient(app).get("/api/v1/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {
        "error": {"code": "NOT_FOUND", "message": "Not Found"}
    }


def test_unexpected_errors_do_not_return_exception_details():
    test_app = create_app()

    @test_app.get("/api/v1/test-error")
    def raise_test_error():
        raise RuntimeError("private implementation detail")

    response = TestClient(test_app, raise_server_exceptions=False).get(
        "/api/v1/test-error"
    )

    assert response.status_code == 500
    assert response.json() == {
        "error": {
            "code": "INTERNAL_SERVER_ERROR",
            "message": "An unexpected error occurred.",
        }
    }


def test_settings_read_only_the_explicit_setting_from_environment(monkeypatch):
    monkeypatch.setenv("USE_MEMORY_DB", "true")
    get_settings.cache_clear()
    try:
        assert get_settings().use_memory_db is True
    finally:
        get_settings.cache_clear()


def test_settings_can_be_overridden_as_a_fastapi_dependency():
    test_app = FastAPI()

    @test_app.get("/setting")
    def read_setting(settings: Annotated[Settings, Depends(get_settings)]):
        return {"use_memory_db": settings.use_memory_db}

    test_app.dependency_overrides[get_settings] = lambda: Settings(use_memory_db=True)
    response = TestClient(test_app).get("/setting")

    assert response.status_code == 200
    assert response.json() == {"use_memory_db": True}


def test_settings_default_does_not_enable_memory_mode(monkeypatch):
    monkeypatch.delenv("USE_MEMORY_DB", raising=False)
    get_settings.cache_clear()
    try:
        assert get_settings().use_memory_db is False
    finally:
        get_settings.cache_clear()
