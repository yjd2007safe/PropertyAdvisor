from __future__ import annotations

"""Database access primitives for repository implementations."""

import os
from dataclasses import dataclass
from typing import Literal, Optional

DataMode = Literal["mock", "postgres", "auto"]


@dataclass(frozen=True)
class DatabaseConfig:
    url: Optional[str]
    requested_mode: DataMode

    @property
    def has_url(self) -> bool:
        return bool(self.url)

    @property
    def enabled(self) -> bool:
        return self.requested_mode == "postgres"

    def resolved_mode(self) -> Literal["mock", "postgres"]:
        if self.requested_mode == "mock":
            return "mock"
        if self.requested_mode == "postgres":
            return "postgres"
        return "postgres" if self.has_url else "mock"

    def is_ready_for_postgres(self) -> bool:
        return self.resolved_mode() == "postgres" and self.has_url


class DatabaseSessionFactory:
    """Placeholder DB session factory for future Postgres wiring."""

    def __init__(self, config: DatabaseConfig):
        self.config = config

    def is_configured(self) -> bool:
        return self.config.is_ready_for_postgres()

    def target_mode(self) -> Literal["mock", "postgres"]:
        return self.config.resolved_mode()


def _parse_data_mode(value: Optional[str]) -> DataMode:
    normalized = (value or "auto").strip().lower()
    legacy_flag = os.getenv("PROPERTY_ADVISOR_USE_DB")

    if normalized in {"mock", "postgres", "auto"}:
        return normalized  # type: ignore[return-value]

    if legacy_flag == "1":
        return "postgres"
    if legacy_flag == "0":
        return "mock"
    return "auto"


def load_database_config() -> DatabaseConfig:
    database_url = (
        os.getenv("SUPABASE_DB_POOLER_URL")
        or os.getenv("DATABASE_URL")
        or os.getenv("SUPABASE_DB_URL")
    )
    requested_mode = _parse_data_mode(os.getenv("PROPERTY_ADVISOR_DATA_MODE"))
    return DatabaseConfig(url=database_url, requested_mode=requested_mode)


def create_session_factory() -> DatabaseSessionFactory:
    return DatabaseSessionFactory(load_database_config())
