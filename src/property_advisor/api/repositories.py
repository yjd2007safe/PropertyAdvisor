from __future__ import annotations

"""Repository abstractions and mock implementations for API services."""

from typing import List, Optional, Protocol

from property_advisor.api.db import DatabaseSessionFactory
from property_advisor.api.mock_fixtures import (
    COMPARABLES_FIXTURE,
    PROPERTY_ADVISOR_FIXTURE,
    SUBURBS_OVERVIEW_FIXTURE,
    WATCHLIST_FIXTURE,
)
from property_advisor.api.schemas import (
    ComparableItem,
    PropertyAdvisorResponse,
    SuburbOverviewItem,
    WatchlistAlert,
    WatchlistEntry,
)


class SuburbRepository(Protocol):
    def list_overview(self) -> List[SuburbOverviewItem]:
        ...

    def get_by_slug(self, slug: str) -> Optional[SuburbOverviewItem]:
        ...


class PropertyAdviceRepository(Protocol):
    def get_by_address_or_slug(self, query: str) -> Optional[PropertyAdvisorResponse]:
        ...


class ComparableRepository(Protocol):
    def list_by_subject(self, query: str, max_items: int = 10) -> List[ComparableItem]:
        ...


class WatchlistRepository(Protocol):
    def list_entries(
        self,
        suburb_slug: Optional[str] = None,
        strategy: Optional[str] = None,
        state: Optional[str] = None,
        watch_status: Optional[str] = None,
    ) -> List[WatchlistEntry]:
        ...

    def get_entry(self, suburb_slug: str) -> Optional[WatchlistEntry]:
        ...

    def list_alerts(self, severity: Optional[str] = None) -> List[WatchlistAlert]:
        ...


class MockSuburbRepository:
    def list_overview(self) -> List[SuburbOverviewItem]:
        return list(SUBURBS_OVERVIEW_FIXTURE.items)

    def get_by_slug(self, slug: str) -> Optional[SuburbOverviewItem]:
        return next((item for item in SUBURBS_OVERVIEW_FIXTURE.items if item.slug == slug), None)


class MockPropertyAdviceRepository:
    def get_by_address_or_slug(self, query: str) -> Optional[PropertyAdvisorResponse]:
        normalized = query.strip().lower()
        default = PROPERTY_ADVISOR_FIXTURE
        if not normalized:
            return default

        suburb = normalized.split(",")[-1].strip()
        if "southport" in suburb or normalized == "southport-qld-4215":
            return default

        if normalized == "burleigh-heads-qld-4220" or "burleigh heads" in normalized:
            return default.model_copy(
                update={
                    "property": default.property.model_copy(
                        update={"address": "42 Ocean View Drive, Burleigh Heads QLD 4220", "beds": 3}
                    ),
                    "advice": default.advice.model_copy(
                        update={
                            "recommendation": "consider",
                            "confidence": "medium",
                            "headline": "Comparable spread is tighter and days-on-market signal is healthier.",
                        }
                    ),
                }
            )

        return None


class MockComparableRepository:
    def list_by_subject(self, query: str, max_items: int = 10) -> List[ComparableItem]:
        normalized = query.strip().lower()
        if not normalized:
            return list(COMPARABLES_FIXTURE.items)[:max_items]

        if normalized in {"none", "empty", "no-match"}:
            return []

        filtered = [item for item in COMPARABLES_FIXTURE.items if normalized in item.address.lower()]
        source = filtered if filtered else list(COMPARABLES_FIXTURE.items)
        return source[:max_items]


class MockWatchlistRepository:
    def list_entries(
        self,
        suburb_slug: Optional[str] = None,
        strategy: Optional[str] = None,
        state: Optional[str] = None,
        watch_status: Optional[str] = None,
    ) -> List[WatchlistEntry]:
        items = list(WATCHLIST_FIXTURE)
        if suburb_slug:
            items = [entry for entry in items if entry.suburb_slug == suburb_slug]
        if strategy:
            items = [entry for entry in items if entry.strategy == strategy]
        if state:
            items = [entry for entry in items if entry.state.lower() == state.lower()]
        if watch_status:
            items = [entry for entry in items if entry.watch_status == watch_status]
        return items

    def get_entry(self, suburb_slug: str) -> Optional[WatchlistEntry]:
        return next((entry for entry in WATCHLIST_FIXTURE if entry.suburb_slug == suburb_slug), None)

    def list_alerts(self, severity: Optional[str] = None) -> List[WatchlistAlert]:
        alerts = [alert for entry in WATCHLIST_FIXTURE for alert in entry.alerts]
        if severity:
            return [alert for alert in alerts if alert.severity == severity]
        return alerts


class PostgresSuburbRepository(MockSuburbRepository):
    def __init__(self, session_factory: DatabaseSessionFactory):
        self.session_factory = session_factory


class PostgresPropertyAdviceRepository(MockPropertyAdviceRepository):
    def __init__(self, session_factory: DatabaseSessionFactory):
        self.session_factory = session_factory


class PostgresComparableRepository(MockComparableRepository):
    def __init__(self, session_factory: DatabaseSessionFactory):
        self.session_factory = session_factory


class PostgresWatchlistRepository(MockWatchlistRepository):
    """Postgres-backed watchlist repository scaffold with mock fallbacks.

    The mapping helper keeps model shape close to expected DB rows so migration can
    progressively move from fixtures to SQL queries.
    """

    def __init__(self, session_factory: DatabaseSessionFactory):
        self.session_factory = session_factory

    def _map_row_to_entry(self, row: dict) -> WatchlistEntry:
        return WatchlistEntry.model_validate(row)
