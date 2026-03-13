from __future__ import annotations

"""Shared API data-access layer for mock/postgres modes."""

from dataclasses import dataclass
from typing import Literal

from property_advisor.api.db import DatabaseSessionFactory
from property_advisor.api.repositories import (
    ComparableRepository,
    PostgresComparableRepository,
    PostgresPropertyAdviceRepository,
    PostgresSuburbRepository,
    PostgresWatchlistRepository,
    PropertyAdviceRepository,
    SuburbRepository,
    WatchlistRepository,
    MockComparableRepository,
    MockPropertyAdviceRepository,
    MockSuburbRepository,
    MockWatchlistRepository,
)

DataMode = Literal["mock", "postgres"]


@dataclass(frozen=True)
class DataAccessLayer:
    mode: DataMode
    suburbs: SuburbRepository
    property_advice: PropertyAdviceRepository
    comparables: ComparableRepository
    watchlist: WatchlistRepository

    @classmethod
    def create(cls, session_factory: DatabaseSessionFactory) -> "DataAccessLayer":
        if session_factory.target_mode() == "postgres":
            return cls(
                mode="postgres",
                suburbs=PostgresSuburbRepository(session_factory),
                property_advice=PostgresPropertyAdviceRepository(session_factory),
                comparables=PostgresComparableRepository(session_factory),
                watchlist=PostgresWatchlistRepository(session_factory),
            )

        return cls(
            mode="mock",
            suburbs=MockSuburbRepository(),
            property_advice=MockPropertyAdviceRepository(),
            comparables=MockComparableRepository(),
            watchlist=MockWatchlistRepository(),
        )
