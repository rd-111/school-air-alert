"""Shared FastAPI dependencies."""

from functools import lru_cache

from app.config import Settings


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings; tests can override this dependency or clear its cache."""
    return Settings()
