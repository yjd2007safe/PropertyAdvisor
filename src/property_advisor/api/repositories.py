from __future__ import annotations

"""Repository abstractions and mock implementations for API services."""

from dataclasses import dataclass
from typing import List, Optional, Protocol

import psycopg

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


@dataclass(frozen=True)
class ComparableQuery:
    query: str
    max_items: int = 10
    min_price: Optional[int] = None
    max_price: Optional[int] = None
    max_distance_km: Optional[float] = None


@dataclass(frozen=True)
class WatchlistQuery:
    suburb_slug: Optional[str] = None
    strategy: Optional[str] = None
    state: Optional[str] = None
    watch_status: Optional[str] = None


class SuburbRepository(Protocol):
    def list_overview(self) -> List[SuburbOverviewItem]:
        ...

    def get_by_slug(self, slug: str) -> Optional[SuburbOverviewItem]:
        ...


class PropertyAdviceRepository(Protocol):
    def get_by_address_or_slug(self, query: str) -> Optional[PropertyAdvisorResponse]:
        ...


class ComparableRepository(Protocol):
    def list_by_subject(self, criteria: ComparableQuery) -> List[ComparableItem]:
        ...


class WatchlistRepository(Protocol):
    def list_entries(self, criteria: WatchlistQuery) -> List[WatchlistEntry]:
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
    def list_by_subject(self, criteria: ComparableQuery) -> List[ComparableItem]:
        normalized = criteria.query.strip().lower()
        if not normalized:
            source = list(COMPARABLES_FIXTURE.items)
        elif normalized in {"none", "empty", "no-match"}:
            return []
        else:
            filtered = [item for item in COMPARABLES_FIXTURE.items if normalized in item.address.lower()]
            source = filtered if filtered else list(COMPARABLES_FIXTURE.items)

        if criteria.min_price is not None:
            source = [item for item in source if item.price >= criteria.min_price]
        if criteria.max_price is not None:
            source = [item for item in source if item.price <= criteria.max_price]
        if criteria.max_distance_km is not None:
            source = [item for item in source if item.distance_km <= criteria.max_distance_km]

        return source[: criteria.max_items]


class MockWatchlistRepository:
    def list_entries(self, criteria: WatchlistQuery) -> List[WatchlistEntry]:
        items = list(WATCHLIST_FIXTURE)
        if criteria.suburb_slug:
            items = [entry for entry in items if entry.suburb_slug == criteria.suburb_slug]
        if criteria.strategy:
            items = [entry for entry in items if entry.strategy == criteria.strategy]
        if criteria.state:
            items = [entry for entry in items if entry.state.lower() == criteria.state.lower()]
        if criteria.watch_status:
            items = [entry for entry in items if entry.watch_status == criteria.watch_status]
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

    def list_overview(self) -> List[SuburbOverviewItem]:
        if not self.session_factory.config.url:
            return super().list_overview()
        with psycopg.connect(self.session_factory.config.url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select suburb_name, state_code, postcode
                    from suburbs
                    order by suburb_name asc
                    limit 20
                    """
                )
                rows = cur.fetchall()
        if not rows:
            return super().list_overview()
        items: List[SuburbOverviewItem] = []
        mock_index = {item.slug: item for item in SUBURBS_OVERVIEW_FIXTURE.items}
        for suburb_name, state_code, postcode in rows:
            slug = f"{suburb_name.lower().replace(' ', '-')}-{(state_code or '').lower()}-{postcode}" if postcode else suburb_name.lower().replace(' ', '-')
            fixture = mock_index.get(slug)
            items.append(
                SuburbOverviewItem(
                    slug=slug,
                    name=suburb_name,
                    state=state_code or (fixture.state if fixture else 'QLD'),
                    median_price=fixture.median_price if fixture else 0,
                    median_rent=fixture.median_rent if fixture else 0,
                    trend=fixture.trend if fixture else 'watching',
                    note=fixture.note if fixture else 'DB-backed suburb loaded; richer metrics pending market_metrics wiring.',
                    avg_days_on_market=fixture.avg_days_on_market if fixture else 0,
                    vacancy_rate_pct=fixture.vacancy_rate_pct if fixture else 0.0,
                )
            )
        return items

    def get_by_slug(self, slug: str) -> Optional[SuburbOverviewItem]:
        return next((item for item in self.list_overview() if item.slug == slug), None)


class PostgresPropertyAdviceRepository(MockPropertyAdviceRepository):
    def __init__(self, session_factory: DatabaseSessionFactory):
        self.session_factory = session_factory

    def get_by_address_or_slug(self, query: str) -> Optional[PropertyAdvisorResponse]:
        if not self.session_factory.config.url:
            return super().get_by_address_or_slug(query)
        normalized = query.strip().lower()
        with psycopg.connect(self.session_factory.config.url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                      p.address_line_1,
                      p.suburb_name,
                      p.state_code,
                      p.postcode,
                      p.property_type,
                      p.bedrooms,
                      p.bathrooms,
                      pas.recommendation,
                      pas.confidence,
                      pas.target_value_low,
                      pas.target_value_high,
                      pas.estimated_rent_weekly,
                      pas.headline_summary,
                      pas.metrics
                    from property_advice_snapshots pas
                    join properties p on p.id = pas.property_id
                    order by pas.generated_at desc, pas.created_at desc
                    limit 20
                    """
                )
                rows = cur.fetchall()
        for row in rows:
            address = f"{row[0]}, {row[1]} {row[2]} {row[3]}".strip()
            slug = f"{row[1].lower().replace(' ', '-')}-{(row[2] or '').lower()}-{row[3]}" if row[3] else row[1].lower().replace(' ', '-')
            if normalized and normalized not in address.lower() and normalized != slug:
                continue
            fixture = PROPERTY_ADVISOR_FIXTURE
            metrics = row[13] or {}
            return fixture.model_copy(
                update={
                    'property': fixture.property.model_copy(
                        update={
                            'address': address,
                            'property_type': row[4] or fixture.property.property_type,
                            'beds': int(row[5] or fixture.property.beds),
                            'baths': int(row[6] or fixture.property.baths),
                        }
                    ),
                    'advice': fixture.advice.model_copy(
                        update={
                            'recommendation': row[7] or fixture.advice.recommendation,
                            'confidence': row[8] or fixture.advice.confidence,
                            'headline': row[11] or fixture.advice.headline,
                        }
                    ),
                    'decision_summary': metrics.get('decision_summary', fixture.decision_summary),
                }
            )
        return super().get_by_address_or_slug(query)


class PostgresComparableRepository(MockComparableRepository):
    def __init__(self, session_factory: DatabaseSessionFactory):
        self.session_factory = session_factory

    def list_by_subject(self, criteria: ComparableQuery) -> List[ComparableItem]:
        if not self.session_factory.config.url:
            return super().list_by_subject(criteria)
        with psycopg.connect(self.session_factory.config.url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                      p.address_line_1,
                      p.suburb_name,
                      se.sale_price,
                      se.sale_date,
                      p.bedrooms,
                      p.bathrooms,
                      se.metadata
                    from sales_events se
                    join properties p on p.id = se.property_id
                    order by se.sale_date desc nulls last, se.created_at desc
                    limit %s
                    """,
                    (criteria.max_items,)
                )
                rows = cur.fetchall()
        items: List[ComparableItem] = []
        query_text = (criteria.query or '').strip().lower()
        for address_line_1, suburb_name, sale_price, sale_date, bedrooms, bathrooms, metadata in rows:
            address = f"{address_line_1}, {suburb_name}"
            if query_text and query_text not in address.lower() and query_text not in suburb_name.lower():
                continue
            meta = metadata or {}
            price = int(sale_price or 0)
            distance_km = float(meta.get('distance_km', 0.0))
            if criteria.min_price is not None and price < criteria.min_price:
                continue
            if criteria.max_price is not None and price > criteria.max_price:
                continue
            if criteria.max_distance_km is not None and distance_km > criteria.max_distance_km:
                continue
            items.append(
                ComparableItem(
                    address=address,
                    price=price,
                    distance_km=distance_km,
                    match_reason=meta.get('match_reason', 'DB-backed comparable'),
                    sold_date=str(sale_date),
                    beds=int(bedrooms or 0),
                    baths=int(bathrooms or 0),
                )
            )
        return items if items else super().list_by_subject(criteria)


class PostgresWatchlistRepository(MockWatchlistRepository):
    """Postgres-backed watchlist repository with mock fallback behavior."""

    def __init__(self, session_factory: DatabaseSessionFactory):
        self.session_factory = session_factory

    def _map_row_to_entry(self, row: dict) -> WatchlistEntry:
        return WatchlistEntry.model_validate(row)

    def _load_entries(self) -> List[WatchlistEntry]:
        if not self.session_factory.config.url:
            return list(WATCHLIST_FIXTURE)
        with psycopg.connect(self.session_factory.config.url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select
                      s.suburb_name,
                      s.state_code,
                      s.postcode,
                      ar.threshold_text,
                      ar.config
                    from alert_rules ar
                    join watchlists w on w.id = ar.watchlist_id
                    join suburbs s on s.id = ar.suburb_id
                    where w.user_ref = 'default'
                    order by s.suburb_name asc
                    """
                )
                rows = cur.fetchall()
        if not rows:
            return list(WATCHLIST_FIXTURE)
        entries: List[WatchlistEntry] = []
        for suburb_name, state_code, postcode, threshold_text, config in rows:
            cfg = config or {}
            slug = cfg.get('suburb_slug') or f"{suburb_name.lower().replace(' ', '-')}-{(state_code or '').lower()}-{postcode}"
            alerts = [WatchlistAlert.model_validate(item) for item in cfg.get('alerts', [])]
            entries.append(
                WatchlistEntry(
                    suburb_slug=slug,
                    suburb_name=suburb_name,
                    state=state_code or 'QLD',
                    strategy=cfg.get('strategy', 'balanced'),
                    watch_status=cfg.get('watch_status', threshold_text or 'active'),
                    notes=cfg.get('notes', 'DB-backed watchlist entry loaded from alert_rules config.'),
                    target_buy_range_min=int(cfg.get('target_buy_range_min', 0)),
                    target_buy_range_max=int(cfg.get('target_buy_range_max', 0)),
                    alerts=alerts,
                )
            )
        return entries

    def list_entries(self, criteria: WatchlistQuery) -> List[WatchlistEntry]:
        items = self._load_entries()
        if criteria.suburb_slug:
            items = [entry for entry in items if entry.suburb_slug == criteria.suburb_slug]
        if criteria.strategy:
            items = [entry for entry in items if entry.strategy == criteria.strategy]
        if criteria.state:
            items = [entry for entry in items if entry.state.lower() == criteria.state.lower()]
        if criteria.watch_status:
            items = [entry for entry in items if entry.watch_status == criteria.watch_status]
        return items

    def get_entry(self, suburb_slug: str) -> Optional[WatchlistEntry]:
        return next((entry for entry in self._load_entries() if entry.suburb_slug == suburb_slug), None)

    def list_alerts(self, severity: Optional[str] = None) -> List[WatchlistAlert]:
        alerts = [alert for entry in self._load_entries() for alert in entry.alerts]
        if severity:
            return [alert for alert in alerts if alert.severity == severity]
        return alerts
