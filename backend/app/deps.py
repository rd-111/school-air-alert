"""Shared FastAPI dependencies."""

from functools import lru_cache

from app.config import Settings
from app.repositories.dynamodb import (
    DynamoHistoryRepository,
    DynamoSchoolRepository,
    DynamoSubscriberRepository,
)
from app.repositories.memory import MemoryRepositories
from app.repositories.notification_runs import DynamoNotificationRunRepository


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return cached settings; tests can override this dependency or clear its cache."""
    return Settings()


@lru_cache(maxsize=1)
def get_repositories():
    """Return configured repositories; tests can override this dependency."""
    return build_repositories(get_settings())


def build_repositories(settings: Settings):
    """Construct repositories from an explicit, test-overridable settings object."""
    if settings.use_memory_db:
        memory = MemoryRepositories.with_demo_school()
        return {
            "schools": memory.schools,
            "history": memory.history,
            "subscribers": memory.subscribers,
            "notifications": memory.notifications,
        }
    return {
        "schools": DynamoSchoolRepository(settings.schools_table, settings.aws_region),
        "history": DynamoHistoryRepository(settings.history_table, settings.aws_region),
        "subscribers": DynamoSubscriberRepository(
            settings.subscribers_table, settings.aws_region
        ),
        "notifications": DynamoNotificationRunRepository(
            settings.notification_runs_table, settings.aws_region
        ),
    }
