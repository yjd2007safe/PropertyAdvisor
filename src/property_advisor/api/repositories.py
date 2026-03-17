from __future__ import annotations

"""Repository abstractions and mock implementations for API services."""

from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Literal, Optional, Protocol

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




def _normalize_query(value: str) -> str:
    return value.strip().lower()


def _slugify_suburb(suburb_name: str, state_code: Optional[str], postcode: Optional[object]) -> str:
    base = suburb_name.strip().lower().replace(" ", "-")
    state = (state_code or "").strip().lower()
    postcode_text = str(postcode).strip() if postcode is not None else ""
    if state and postcode_text:
        return f"{base}-{state}-{postcode_text}"
    if state:
        return f"{base}-{state}"
    if postcode_text:
        return f"{base}-{postcode_text}"
    return base


def _format_property_address(address_line_1: Optional[str], suburb_name: Optional[str], state_code: Optional[str], postcode: Optional[object]) -> str:
    street = (address_line_1 or "").strip()
    suburb = (suburb_name or "").strip()
    state = (state_code or "").strip()
    post = str(postcode).strip() if postcode is not None else ""
    locality = " ".join(part for part in [suburb, state, post] if part)
    if street and locality:
        return f"{street}, {locality}"
    return street or locality


def _normalize_watch_status(value: Optional[str]) -> Literal["active", "review", "paused"]:
    normalized = (value or "").strip().lower()
    if normalized in {"active", "review", "paused"}:
        return normalized
    if "pause" in normalized:
        return "paused"
    if "review" in normalized or "watch" in normalized:
        return "review"
    return "active"


def _coerce_sale_date(value: object) -> str:
    if value is None:
        return "unknown"
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)

class MockSuburbRepository:
    last_source: Literal["mock", "postgres", "fallback_mock"] = "mock"
    last_fallback_reason: Optional[str] = None

    def list_overview(self) -> List[SuburbOverviewItem]:
        self.last_source = "mock"
        self.last_fallback_reason = None
        return list(SUBURBS_OVERVIEW_FIXTURE.items)

    def get_by_slug(self, slug: str) -> Optional[SuburbOverviewItem]:
        return next((item for item in SUBURBS_OVERVIEW_FIXTURE.items if item.slug == slug), None)


class MockPropertyAdviceRepository:
    last_source: Literal["mock", "postgres", "fallback_mock"] = "mock"
    last_fallback_reason: Optional[str] = None

    def get_by_address_or_slug(self, query: str) -> Optional[PropertyAdvisorResponse]:
        self.last_source = "mock"
        self.last_fallback_reason = None
        normalized = _normalize_query(query)
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
    last_source: Literal["mock", "postgres", "fallback_mock"] = "mock"
    last_fallback_reason: Optional[str] = None

    def list_by_subject(self, criteria: ComparableQuery) -> List[ComparableItem]:
        self.last_source = "mock"
        self.last_fallback_reason = None
        normalized = _normalize_query(criteria.query)
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
    last_source: Literal["mock", "postgres", "fallback_mock"] = "mock"
    last_fallback_reason: Optional[str] = None

    def list_entries(self, criteria: WatchlistQuery) -> List[WatchlistEntry]:
        self.last_source = "mock"
        self.last_fallback_reason = None
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
        self.last_source = "mock"
        self.last_fallback_reason = None
        return next((entry for entry in WATCHLIST_FIXTURE if entry.suburb_slug == suburb_slug), None)

    def list_alerts(self, severity: Optional[str] = None) -> List[WatchlistAlert]:
        self.last_source = "mock"
        self.last_fallback_reason = None
        alerts = [alert for entry in WATCHLIST_FIXTURE for alert in entry.alerts]
        if severity:
            return [alert for alert in alerts if alert.severity == severity]
        return alerts


class PostgresSuburbRepository(MockSuburbRepository):
    def __init__(self, session_factory: DatabaseSessionFactory):
        self.session_factory = session_factory

    def list_overview(self) -> List[SuburbOverviewItem]:
        if not self.session_factory.config.url:
            items = super().list_overview()
            self.last_source = "fallback_mock"
            self.last_fallback_reason = "No database URL configured for suburb overview."
            return items
        try:
            with psycopg.connect(self.session_factory.config.url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        select
                          s.suburb_name,
                          s.state_code,
                          s.postcode,
                          mm.median_sale_price,
                          mm.median_weekly_rent,
                          mm.avg_days_on_market,
                          mm.market_temperature
                        from suburbs s
                        left join lateral (
                          select
                            m.median_sale_price,
                            m.median_weekly_rent,
                            m.avg_days_on_market,
                            m.market_temperature
                          from market_metrics m
                          where m.suburb_id = s.id
                            and m.property_type is null
                          order by m.period_start desc, m.created_at desc
                          limit 1
                        ) mm on true
                        order by suburb_name asc
                        limit 20
                        """
                    )
                    rows = cur.fetchall()
        except psycopg.Error as exc:
            items = super().list_overview()
            self.last_source = "fallback_mock"
            self.last_fallback_reason = f"Suburb overview query failed: {exc.__class__.__name__}"
            return items
        if not rows:
            items = super().list_overview()
            self.last_source = "fallback_mock"
            self.last_fallback_reason = "Suburb overview query returned 0 rows."
            return items
        self.last_source = "postgres"
        self.last_fallback_reason = None
        items: List[SuburbOverviewItem] = []
        mock_index = {item.slug: item for item in SUBURBS_OVERVIEW_FIXTURE.items}
        for row in rows:
            suburb_name, state_code, postcode = row[0], row[1], row[2]
            median_sale_price = row[3] if len(row) > 3 else None
            median_weekly_rent = row[4] if len(row) > 4 else None
            avg_dom = row[5] if len(row) > 5 else None
            market_temperature = row[6] if len(row) > 6 else None
            slug = _slugify_suburb(suburb_name, state_code, postcode)
            fixture = mock_index.get(slug)
            has_metrics = any(value is not None for value in [median_sale_price, median_weekly_rent, avg_dom, market_temperature])
            trend = fixture.trend if fixture else 'watching'
            if market_temperature in {'warm', 'hot'}:
                trend = 'improving'
            elif market_temperature in {'balanced'}:
                trend = 'steady'

            items.append(
                SuburbOverviewItem(
                    slug=slug,
                    name=suburb_name,
                    state=state_code or (fixture.state if fixture else 'QLD'),
                    median_price=int(median_sale_price or (fixture.median_price if fixture else 0)),
                    median_rent=int(median_weekly_rent or (fixture.median_rent if fixture else 0)),
                    trend=trend,
                    note=(
                        'Latest suburb metrics loaded from market_metrics.'
                        if has_metrics
                        else 'DB-backed suburb loaded; market_metrics row missing so fallback values are shown.'
                    ),
                    avg_days_on_market=int(avg_dom or (fixture.avg_days_on_market if fixture else 0)),
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
            item = super().get_by_address_or_slug(query)
            self.last_source = "fallback_mock"
            self.last_fallback_reason = "No database URL configured for property advice."
            return item
        normalized = _normalize_query(query)
        try:
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
        except psycopg.Error as exc:
            item = super().get_by_address_or_slug(query)
            self.last_source = "fallback_mock"
            self.last_fallback_reason = f"Property advice query failed: {exc.__class__.__name__}"
            return item
        for row in rows:
            address = _format_property_address(row[0], row[1], row[2], row[3])
            slug = _slugify_suburb(row[1], row[2], row[3])
            if normalized and normalized not in address.lower() and normalized != slug:
                continue
            fixture = PROPERTY_ADVISOR_FIXTURE
            metrics = row[13] or {}
            self.last_source = "postgres"
            self.last_fallback_reason = None
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
        item = super().get_by_address_or_slug(query)
        self.last_source = "fallback_mock"
        self.last_fallback_reason = "No property advice row matched query; served mock guidance."
        return item


class PostgresComparableRepository(MockComparableRepository):
    def __init__(self, session_factory: DatabaseSessionFactory):
        self.session_factory = session_factory

    def list_by_subject(self, criteria: ComparableQuery) -> List[ComparableItem]:
        if not self.session_factory.config.url:
            items = super().list_by_subject(criteria)
            self.last_source = "fallback_mock"
            self.last_fallback_reason = "No database URL configured for comparables."
            return items
        try:
            with psycopg.connect(self.session_factory.config.url) as conn:
                with conn.cursor() as cur:
                    cur.execute(
                        """
                        select
                          p.address_line_1,
                          p.suburb_name,
                          p.state_code,
                          p.postcode,
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
        except psycopg.Error as exc:
            items = super().list_by_subject(criteria)
            self.last_source = "fallback_mock"
            self.last_fallback_reason = f"Comparables query failed: {exc.__class__.__name__}"
            return items
        items: List[ComparableItem] = []
        query_text = _normalize_query(criteria.query or "")
        for address_line_1, suburb_name, state_code, postcode, sale_price, sale_date, bedrooms, bathrooms, metadata in rows:
            address = _format_property_address(address_line_1, suburb_name, state_code, postcode)
            suburb_slug = _slugify_suburb(suburb_name, state_code, postcode)
            if query_text and query_text not in address.lower() and query_text not in suburb_name.lower() and query_text != suburb_slug:
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
                    sold_date=_coerce_sale_date(sale_date),
                    beds=int(bedrooms or 0),
                    baths=int(bathrooms or 0),
                )
            )
        if items:
            self.last_source = "postgres"
            self.last_fallback_reason = None
            return items
        if rows:
            self.last_source = "postgres"
            self.last_fallback_reason = None
            return []
        items = super().list_by_subject(criteria)
        self.last_source = "fallback_mock"
        self.last_fallback_reason = "Comparable query returned 0 matches after filters; served mock comps."
        return items


class PostgresWatchlistRepository(MockWatchlistRepository):
    """Postgres-backed watchlist repository with mock fallback behavior."""

    def __init__(self, session_factory: DatabaseSessionFactory):
        self.session_factory = session_factory

    def _map_row_to_entry(self, row: dict) -> WatchlistEntry:
        return WatchlistEntry.model_validate(row)

    def _load_entries(self) -> List[WatchlistEntry]:
        if not self.session_factory.config.url:
            items = list(WATCHLIST_FIXTURE)
            self.last_source = "fallback_mock"
            self.last_fallback_reason = "No database URL configured for watchlist."
            return items
        try:
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
        except psycopg.Error as exc:
            items = list(WATCHLIST_FIXTURE)
            self.last_source = "fallback_mock"
            self.last_fallback_reason = f"Watchlist query failed: {exc.__class__.__name__}"
            return items
        if not rows:
            items = list(WATCHLIST_FIXTURE)
            self.last_source = "fallback_mock"
            self.last_fallback_reason = "Watchlist query returned 0 rows."
            return items
        self.last_source = "postgres"
        self.last_fallback_reason = None
        entries: List[WatchlistEntry] = []
        for suburb_name, state_code, postcode, threshold_text, config in rows:
            cfg = config or {}
            slug = cfg.get('suburb_slug') or _slugify_suburb(suburb_name, state_code, postcode)
            alerts = [WatchlistAlert.model_validate(item) for item in cfg.get('alerts', [])]
            entries.append(
                WatchlistEntry(
                    suburb_slug=slug,
                    suburb_name=suburb_name,
                    state=state_code or 'QLD',
                    strategy=cfg.get('strategy', 'balanced'),
                    watch_status=_normalize_watch_status(cfg.get('watch_status') or threshold_text),
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
