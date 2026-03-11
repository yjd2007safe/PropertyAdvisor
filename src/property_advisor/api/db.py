from __future__ import annotations

"""Database access primitives for repository implementations."""

import os
from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class DatabaseConfig:
    url: Optional[str]
    enabled: bool


class DatabaseSessionFactory:
    """Placeholder DB session factory for future Postgres wiring."""

    def __init__(self, config: DatabaseConfig):
        self.config = config

    def is_configured(self) -> bool:
        return self.config.enabled and bool(self.config.url)


def load_database_config() -> DatabaseConfig:
    database_url = os.getenv("DATABASE_URL")
    return DatabaseConfig(
        url=database_url,
        enabled=os.getenv("PROPERTY_ADVISOR_USE_DB", "0") == "1",
    )


def create_session_factory() -> DatabaseSessionFactory:
    return DatabaseSessionFactory(load_database_config())
