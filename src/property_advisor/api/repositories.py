from __future__ import annotations

"""Repository abstractions and mock implementations for API services."""

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from statistics import mean
from typing import Any, Dict, List, Literal, Optional, Protocol
import json

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
class ComparableSubject:
    property_id: str
    address: str
    suburb_name: str
    state_code: Optional[str]
    postcode: Optional[object]
    property_type: Optional[str]
    bedrooms: Optional[int]
    bathrooms: Optional[int]


@dataclass(frozen=True)
class ComparableCandidate:
    property_id: str
    address: str
    suburb_name: str
    suburb_slug: str
    property_type: Optional[str]
    sale_price: int
    sale_date: object
    bedrooms: Optional[int]
    bathrooms: Optional[int]
    metadata: dict


@dataclass(frozen=True)
class ScoredComparableCandidate:
    candidate: ComparableCandidate
    rank_order: int
    similarity_score: float
    distance_km: float
    price_delta_pct: float
    rationale: Dict[str, Any]
    match_reason: str
    feature_summary: str


@dataclass(frozen=True)
class ComparableSetResult:
    set_id: Optional[str]
    algorithm_version: str
    generated_at: Optional[str]
    quality_score: float
    quality_label: str
    items: List[ComparableItem]


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

    def get_latest_set(self, criteria: ComparableQuery) -> Optional[ComparableSetResult]:
        ...

    def generate_comparable_set(self, criteria: ComparableQuery) -> ComparableSetResult:
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


def _coerce_to_date(value: object) -> Optional[date]:
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).date()
        except ValueError:
            return None
    return None


def _normalize_property_type(value: Optional[str]) -> str:
    return (value or "").strip().lower()


def _bedroom_band_matches(subject: ComparableSubject, candidate: ComparableCandidate) -> bool:
    if subject.bedrooms is None or candidate.bedrooms is None:
        return True
    return abs(subject.bedrooms - candidate.bedrooms) <= 1


def _bathroom_band_matches(subject: ComparableSubject, candidate: ComparableCandidate) -> bool:
    if subject.bathrooms is None or candidate.bathrooms is None:
        return True
    return abs(subject.bathrooms - candidate.bathrooms) <= 1


def _candidate_within_recency_window(candidate: ComparableCandidate, today: Optional[date] = None) -> bool:
    candidate_date = _coerce_to_date(candidate.sale_date)
    if candidate_date is None:
        return False
    anchor = today or date.today()
    return candidate_date >= anchor - timedelta(days=365)


def _candidate_sort_key(subject: ComparableSubject, candidate: ComparableCandidate) -> tuple:
    same_suburb = 0 if _normalize_query(candidate.suburb_name) == _normalize_query(subject.suburb_name) else 1
    same_type = 0 if _normalize_property_type(candidate.property_type) == _normalize_property_type(subject.property_type) else 1
    bed_gap = abs((candidate.bedrooms or subject.bedrooms or 0) - (subject.bedrooms or candidate.bedrooms or 0))
    bath_gap = abs((candidate.bathrooms or subject.bathrooms or 0) - (subject.bathrooms or candidate.bathrooms or 0))
    candidate_date = _coerce_to_date(candidate.sale_date) or date.min
    return (same_suburb, same_type, bed_gap, bath_gap, -candidate_date.toordinal(), candidate.sale_price)


def select_comparable_candidates(
    subject: ComparableSubject,
    candidates: List[ComparableCandidate],
    max_items: int,
) -> List[ComparableCandidate]:
    eligible = [
        candidate
        for candidate in candidates
        if candidate.property_id != subject.property_id
        and _candidate_within_recency_window(candidate)
        and _bedroom_band_matches(subject, candidate)
        and _bathroom_band_matches(subject, candidate)
    ]
    eligible.sort(key=lambda candidate: _candidate_sort_key(subject, candidate))
    return eligible[:max_items]


def _safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _safe_int(value: Any, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _score_candidate(subject: ComparableSubject, candidate: ComparableCandidate) -> ScoredComparableCandidate:
    meta = candidate.metadata or {}
    sale_date = _coerce_to_date(candidate.sale_date)
    anchor_date = date.today()
    recency_days = max((anchor_date - sale_date).days, 0) if sale_date else 365
    recency_score = max(0.0, 1.0 - min(recency_days, 365) / 365.0)

    distance_km = _safe_float(meta.get("distance_km"), 0.0)
    distance_score = max(0.0, 1.0 - min(distance_km, 10.0) / 10.0)

    bed_gap = abs((candidate.bedrooms or subject.bedrooms or 0) - (subject.bedrooms or candidate.bedrooms or 0))
    bath_gap = abs((candidate.bathrooms or subject.bathrooms or 0) - (subject.bathrooms or candidate.bathrooms or 0))
    same_type = _normalize_property_type(candidate.property_type) == _normalize_property_type(subject.property_type)
    same_suburb = _normalize_query(candidate.suburb_name) == _normalize_query(subject.suburb_name)
    feature_score = max(0.0, 1.0 - (bed_gap * 0.18 + bath_gap * 0.14))
    if same_type:
        feature_score = min(1.0, feature_score + 0.18)
    if same_suburb:
        feature_score = min(1.0, feature_score + 0.08)

    subject_price = _safe_float(meta.get("subject_price"))
    subject_rent = _safe_float(meta.get("subject_rent_weekly"))
    price_delta_pct = _safe_float(meta.get("price_delta_pct"))
    if not price_delta_pct and subject_price > 0:
        price_delta_pct = ((candidate.sale_price - subject_price) / subject_price) * 100.0
    price_relevance = max(0.0, 1.0 - min(abs(price_delta_pct), 40.0) / 40.0)

    rent_delta_pct = _safe_float(meta.get("rent_delta_pct"))
    if subject_rent > 0:
        rent_relevance = max(0.0, 1.0 - min(abs(rent_delta_pct), 40.0) / 40.0)
        relevance_score = round((price_relevance * 0.65) + (rent_relevance * 0.35), 3)
    else:
        relevance_score = round(price_relevance, 3)

    similarity_score = round(
        (recency_score * 0.30) + (distance_score * 0.25) + (feature_score * 0.30) + (relevance_score * 0.15),
        3,
    )

    rationale = {
        "recency_days": recency_days,
        "recency_score": round(recency_score, 3),
        "distance_km": round(distance_km, 3),
        "distance_score": round(distance_score, 3),
        "same_suburb": same_suburb,
        "same_property_type": same_type,
        "bedroom_gap": bed_gap,
        "bathroom_gap": bath_gap,
        "feature_score": round(feature_score, 3),
        "price_delta_pct": round(price_delta_pct, 3),
        "price_relevance_score": round(price_relevance, 3),
        "rent_delta_pct": round(rent_delta_pct, 3),
        "relevance_score": relevance_score,
    }
    feature_summary = f"{candidate.bedrooms or 'unknown'} bed/{candidate.bathrooms or 'unknown'} bath"
    match_reason = meta.get(
        "match_reason",
        (
            "same suburb, same property type, scored recent sale"
            if same_suburb and same_type
            else "scored persisted sale candidate"
        ),
    )
    return ScoredComparableCandidate(
        candidate=candidate,
        rank_order=0,
        similarity_score=similarity_score,
        distance_km=round(distance_km, 3),
        price_delta_pct=round(price_delta_pct, 3),
        rationale=rationale,
        match_reason=match_reason,
        feature_summary=feature_summary,
    )


def score_comparable_candidates(
    subject: ComparableSubject,
    candidates: List[ComparableCandidate],
    max_items: int,
) -> List[ScoredComparableCandidate]:
    shortlisted = select_comparable_candidates(subject, candidates, max_items=max_items)
    scored = [_score_candidate(subject, candidate) for candidate in shortlisted]
    scored.sort(
        key=lambda item: (
            -item.similarity_score,
            item.distance_km,
            abs(item.price_delta_pct),
            _candidate_sort_key(subject, item.candidate),
        )
    )
    ranked: List[ScoredComparableCandidate] = []
    for index, item in enumerate(scored, start=1):
        ranked.append(
            ScoredComparableCandidate(
                candidate=item.candidate,
                rank_order=index,
                similarity_score=item.similarity_score,
                distance_km=item.distance_km,
                price_delta_pct=item.price_delta_pct,
                rationale=item.rationale,
                match_reason=item.match_reason,
                feature_summary=item.feature_summary,
            )
        )
    return ranked


def _build_set_quality(scored: List[ScoredComparableCandidate]) -> tuple[float, str]:
    if not scored:
        return 0.0, "empty"
    avg_score = round(mean(item.similarity_score for item in scored), 3)
    if len(scored) < 3:
        return avg_score, "low_sample"
    if avg_score >= 0.78:
        return avg_score, "high"
    if avg_score >= 0.62:
        return avg_score, "moderate"
    return avg_score, "thin"


def _scored_to_item(item: ScoredComparableCandidate) -> ComparableItem:
    return ComparableItem(
        property_id=item.candidate.property_id,
        address=item.candidate.address,
        price=_safe_int(item.candidate.sale_price),
        distance_km=item.distance_km,
        match_reason=f"{item.match_reason}; {item.feature_summary}",
        sold_date=_coerce_sale_date(item.candidate.sale_date),
        beds=_safe_int(item.candidate.bedrooms),
        baths=_safe_int(item.candidate.bathrooms),
        score=item.similarity_score,
        rationale=dict(item.rationale),
    )

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

    def get_latest_set(self, criteria: ComparableQuery) -> Optional[ComparableSetResult]:
        _ = criteria
        return None

    def generate_comparable_set(self, criteria: ComparableQuery) -> ComparableSetResult:
        items = self.list_by_subject(criteria)
        quality_score, quality_label = _build_set_quality(
            [
                ScoredComparableCandidate(
                    candidate=ComparableCandidate(
                        property_id=item.property_id or item.address,
                        address=item.address,
                        suburb_name="",
                        suburb_slug="",
                        property_type=None,
                        sale_price=item.price,
                        sale_date=item.sold_date,
                        bedrooms=item.beds,
                        bathrooms=item.baths,
                        metadata=item.rationale,
                    ),
                    rank_order=index,
                    similarity_score=float(item.score or 0.5),
                    distance_km=item.distance_km,
                    price_delta_pct=_safe_float(item.rationale.get("price_delta_pct") if item.rationale else 0.0),
                    rationale=dict(item.rationale),
                    match_reason=item.match_reason,
                    feature_summary=f"{item.beds} bed/{item.baths} bath",
                )
                for index, item in enumerate(items, start=1)
            ]
        )
        return ComparableSetResult(
            set_id=None,
            algorithm_version="mock-v0",
            generated_at=None,
            quality_score=quality_score,
            quality_label=quality_label,
            items=items,
        )


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
    algorithm_version = "phase2.round2.v1"
    purpose = "buy_eval"
    basis = "sales"

    def __init__(self, session_factory: DatabaseSessionFactory):
        self.session_factory = session_factory

    def _load_subject(self, cur, criteria: ComparableQuery) -> Optional[ComparableSubject]:
        normalized = _normalize_query(criteria.query)
        cur.execute(
            """
            select
              p.id,
              p.address_line_1,
              p.suburb_name,
              p.state_code,
              p.postcode,
              p.property_type,
              p.bedrooms,
              p.bathrooms
            from properties p
            where lower(coalesce(p.address_line_1, '') || ', ' || coalesce(p.suburb_name, '') || ' ' || coalesce(p.state_code, '') || ' ' || coalesce(p.postcode::text, '')) like %s
               or lower(coalesce(p.suburb_name, '')) = %s
               or lower(
                    replace(coalesce(p.suburb_name, ''), ' ', '-') || '-' || lower(coalesce(p.state_code, '')) || '-' || coalesce(p.postcode::text, '')
                  ) = %s
            order by
              case
                when lower(
                    replace(coalesce(p.suburb_name, ''), ' ', '-') || '-' || lower(coalesce(p.state_code, '')) || '-' || coalesce(p.postcode::text, '')
                  ) = %s then 0
                when lower(coalesce(p.address_line_1, '') || ', ' || coalesce(p.suburb_name, '') || ' ' || coalesce(p.state_code, '') || ' ' || coalesce(p.postcode::text, '')) = %s then 1
                when lower(coalesce(p.suburb_name, '')) = %s then 2
                else 3
              end,
              p.updated_at desc nulls last,
              p.created_at desc
            limit 1
            """,
            (
                f"%{normalized}%",
                normalized,
                normalized,
                normalized,
                normalized,
                normalized,
            ),
        )
        if hasattr(cur, "fetchone"):
            row = cur.fetchone()
        else:
            rows = cur.fetchall()
            row = rows[0] if rows else None
        if not row:
            return None
        return ComparableSubject(
            property_id=str(row[0]),
            address=_format_property_address(row[1], row[2], row[3], row[4]),
            suburb_name=row[2] or "",
            state_code=row[3],
            postcode=row[4],
            property_type=row[5],
            bedrooms=int(row[6]) if row[6] is not None else None,
            bathrooms=int(row[7]) if row[7] is not None else None,
        )

    def _load_candidate_rows(self, cur) -> List[ComparableCandidate]:
        cur.execute(
            """
            select
              p.id,
              p.address_line_1,
              p.suburb_name,
              p.state_code,
              p.postcode,
              p.property_type,
              se.sale_price,
              se.sale_date,
              p.bedrooms,
              p.bathrooms,
              se.metadata
            from sales_events se
            join properties p on p.id = se.property_id
            where se.sale_price is not null
            order by se.sale_date desc nulls last, se.created_at desc
            limit 250
            """
        )
        rows = cur.fetchall()
        return [
            ComparableCandidate(
                property_id=str(row[0]),
                address=_format_property_address(row[1], row[2], row[3], row[4]),
                suburb_name=row[2] or "",
                suburb_slug=_slugify_suburb(row[2] or "", row[3], row[4]),
                property_type=row[5],
                sale_price=int(row[6] or 0),
                sale_date=row[7],
                bedrooms=int(row[8]) if row[8] is not None else None,
                bathrooms=int(row[9]) if row[9] is not None else None,
                metadata=row[10] or {},
            )
            for row in rows
        ]

    def _build_result_from_scored(
        self,
        scored: List[ScoredComparableCandidate],
        set_id: Optional[str],
        generated_at: Optional[str],
    ) -> ComparableSetResult:
        quality_score, quality_label = _build_set_quality(scored)
        return ComparableSetResult(
            set_id=set_id,
            algorithm_version=self.algorithm_version,
            generated_at=generated_at,
            quality_score=quality_score,
            quality_label=quality_label,
            items=[_scored_to_item(item) for item in scored],
        )

    def _generate_scored_candidates(self, cur, criteria: ComparableQuery) -> Optional[ComparableSetResult]:
        subject = self._load_subject(cur, criteria)
        candidate_rows = self._load_candidate_rows(cur)
        if subject is None:
            return None
        scored_rows = score_comparable_candidates(subject, candidate_rows, max_items=criteria.max_items)
        filtered: List[ScoredComparableCandidate] = []
        for item in scored_rows:
            price = _safe_int(item.candidate.sale_price)
            if criteria.min_price is not None and price < criteria.min_price:
                continue
            if criteria.max_price is not None and price > criteria.max_price:
                continue
            if criteria.max_distance_km is not None and item.distance_km > criteria.max_distance_km:
                continue
            filtered.append(item)
        return self._build_result_from_scored(filtered, set_id=None, generated_at=None)

    def get_latest_set(self, criteria: ComparableQuery) -> Optional[ComparableSetResult]:
        if not self.session_factory.config.url:
            return None
        try:
            with psycopg.connect(self.session_factory.config.url) as conn:
                with conn.cursor() as cur:
                    subject = self._load_subject(cur, criteria)
                    if subject is None:
                        return None
                    cur.execute(
                        """
                        select
                          cs.id,
                          cs.algorithm_version,
                          cs.generated_at,
                          coalesce(cs.quality_score, 0),
                          coalesce(cs.notes, ''),
                          cm.comparable_property_id,
                          p.address_line_1,
                          p.suburb_name,
                          p.state_code,
                          p.postcode,
                          se.sale_price,
                          cm.distance_km,
                          cm.rationale,
                          cm.feature_summary,
                          cm.similarity_score,
                          se.sale_date,
                          p.bedrooms,
                          p.bathrooms
                        from comparable_sets cs
                        join comparable_members cm on cm.comparable_set_id = cs.id
                        join properties p on p.id = cm.comparable_property_id
                        left join sales_events se on se.id = cm.sale_event_id
                        where cs.target_property_id = %s
                          and cs.purpose = %s
                          and cs.basis = %s
                          and cs.algorithm_version = %s
                          and cs.status = 'complete'
                        order by cs.generated_at desc, cm.rank_order asc
                        """,
                        (subject.property_id, self.purpose, self.basis, self.algorithm_version),
                    )
                    rows = cur.fetchall()
        except psycopg.Error:
            return None
        if not rows:
            return None
        if len(rows[0]) < 18:
            return None
        first = rows[0]
        items: List[ComparableItem] = []
        for row in rows:
            rationale_payload = row[12]
            if isinstance(rationale_payload, str):
                try:
                    rationale = json.loads(rationale_payload)
                except json.JSONDecodeError:
                    rationale = {"summary": rationale_payload}
            else:
                rationale = rationale_payload or {}
            items.append(
                ComparableItem(
                    property_id=str(row[5]),
                    address=_format_property_address(row[6], row[7], row[8], row[9]),
                    price=_safe_int(row[10]),
                    distance_km=_safe_float(row[11]),
                    match_reason=str(row[13] or "persisted comparable member"),
                    sold_date=_coerce_sale_date(row[15]),
                    beds=_safe_int(row[16]),
                    baths=_safe_int(row[17]),
                    score=round(_safe_float(row[14]), 3),
                    rationale=dict(rationale),
                )
            )
        notes_text = str(first[4] or "")
        quality_label = "persisted"
        if notes_text:
            try:
                quality_label = json.loads(notes_text).get("quality_label", quality_label)
            except json.JSONDecodeError:
                pass
        self.last_source = "postgres"
        self.last_fallback_reason = None
        return ComparableSetResult(
            set_id=str(first[0]),
            algorithm_version=str(first[1] or self.algorithm_version),
            generated_at=_coerce_sale_date(first[2]) if first[2] else None,
            quality_score=round(_safe_float(first[3]), 3),
            quality_label=quality_label,
            items=items[: criteria.max_items],
        )

    def generate_comparable_set(self, criteria: ComparableQuery) -> ComparableSetResult:
        if not self.session_factory.config.url:
            return super().generate_comparable_set(criteria)
        try:
            with psycopg.connect(self.session_factory.config.url) as conn:
                with conn.cursor() as cur:
                    subject = self._load_subject(cur, criteria)
                    if subject is None:
                        raise ValueError("missing_subject")
                    generated = self._generate_scored_candidates(cur, criteria)
                    if generated is None:
                        raise ValueError("missing_subject")
                    now = datetime.now(timezone.utc).isoformat()
                    notes = json.dumps(
                        {
                            "query": criteria.query,
                            "quality_label": generated.quality_label,
                            "max_items": criteria.max_items,
                        },
                        sort_keys=True,
                    )
                    cur.execute(
                        """
                        select id
                        from comparable_sets
                        where target_property_id = %s
                          and purpose = %s
                          and basis = %s
                          and algorithm_version = %s
                        order by generated_at desc
                        limit 1
                        """,
                        (subject.property_id, self.purpose, self.basis, self.algorithm_version),
                    )
                    if hasattr(cur, "fetchone"):
                        existing = cur.fetchone()
                    else:
                        existing_rows = cur.fetchall()
                        existing = existing_rows[0] if existing_rows else None
                    set_id = str(existing[0]) if existing else f"{subject.property_id}-{self.algorithm_version}"
                    if existing:
                        cur.execute("delete from comparable_members where comparable_set_id = %s", (set_id,))
                        cur.execute(
                            """
                            update comparable_sets
                            set generated_at = %s, quality_score = %s, notes = %s, status = 'complete'
                            where id = %s
                            """,
                            (now, generated.quality_score, notes, set_id),
                        )
                    else:
                        cur.execute(
                            """
                            insert into comparable_sets (
                              id, target_property_id, purpose, basis, status, generated_at, algorithm_version, quality_score, notes
                            ) values (%s, %s, %s, %s, 'complete', %s, %s, %s, %s)
                            """,
                            (
                                set_id,
                                subject.property_id,
                                self.purpose,
                                self.basis,
                                now,
                                self.algorithm_version,
                                generated.quality_score,
                                notes,
                            ),
                        )
                    for item in generated.items:
                        rationale_json = json.dumps(item.rationale, sort_keys=True)
                        cur.execute(
                            """
                            insert into comparable_members (
                              comparable_set_id, comparable_property_id, rank_order, similarity_score, distance_km, price_delta_pct, feature_summary, rationale
                            ) values (%s, %s, %s, %s, %s, %s, %s, %s)
                            """,
                            (
                                set_id,
                                item.property_id,
                                generated.items.index(item) + 1,
                                item.score,
                                item.distance_km,
                                _safe_float(item.rationale.get("price_delta_pct")) if item.rationale else 0.0,
                                item.match_reason,
                                rationale_json,
                            ),
                        )
            self.last_source = "postgres"
            self.last_fallback_reason = None
            return ComparableSetResult(
                set_id=set_id,
                algorithm_version=self.algorithm_version,
                generated_at=now,
                quality_score=generated.quality_score,
                quality_label=generated.quality_label,
                items=generated.items,
            )
        except (psycopg.Error, ValueError):
            self.last_source = "fallback_mock"
            self.last_fallback_reason = "Comparable set generation fell back to mock candidates."
            return super().generate_comparable_set(criteria)

    def list_by_subject(self, criteria: ComparableQuery) -> List[ComparableItem]:
        latest = self.get_latest_set(criteria)
        if latest is not None:
            return latest.items[: criteria.max_items]
        if not self.session_factory.config.url:
            items = super().list_by_subject(criteria)
            self.last_source = "fallback_mock"
            self.last_fallback_reason = "No database URL configured for comparables."
            return items
        try:
            with psycopg.connect(self.session_factory.config.url) as conn:
                with conn.cursor() as cur:
                    subject = self._load_subject(cur, criteria)
                    candidate_rows = self._load_candidate_rows(cur)
        except psycopg.Error as exc:
            items = super().list_by_subject(criteria)
            self.last_source = "fallback_mock"
            self.last_fallback_reason = f"Comparables query failed: {exc.__class__.__name__}"
            return items
        if subject is None:
            items = super().list_by_subject(criteria)
            self.last_source = "fallback_mock"
            self.last_fallback_reason = "No persisted subject property matched comparables query."
            return items
        scored_rows = score_comparable_candidates(subject, candidate_rows, max_items=criteria.max_items)
        items = [
            _scored_to_item(item)
            for item in scored_rows
            if (criteria.min_price is None or _safe_int(item.candidate.sale_price) >= criteria.min_price)
            and (criteria.max_price is None or _safe_int(item.candidate.sale_price) <= criteria.max_price)
            and (criteria.max_distance_km is None or item.distance_km <= criteria.max_distance_km)
        ]
        if items:
            self.last_source = "postgres"
            self.last_fallback_reason = None
            return items
        if candidate_rows:
            self.last_source = "postgres"
            self.last_fallback_reason = None
            return []
        items = super().list_by_subject(criteria)
        self.last_source = "fallback_mock"
        self.last_fallback_reason = "Comparable candidate query returned 0 persisted sale rows; served mock comps."
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
