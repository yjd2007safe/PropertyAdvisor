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
    AdviceEvidenceSummary,
    AdviceEvidenceSummarySection,
    AdvisoryInputs,
    AdvisoryInvestorSignal,
    AdvisoryMarketContext,
    AdvisoryRationaleItem,
    ComparableItem,
    ComparableSnapshot,
    DataSourceStatus,
    PropertyAdvice,
    PropertyAdvisorResponse,
    SubjectProperty,
    SuburbOverviewItem,
    SummaryCard,
    WatchlistAlert,
    WatchlistEntry,
    WorkflowLink,
    WorkflowSnapshot,
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
class AdviceConfidenceSemantics:
    confidence: Literal["low", "medium", "high"]
    confidence_reasons: List[str]
    fallback_state: Literal[
        "none",
        "insufficient_evidence",
        "stale_evidence",
        "low_sample",
        "conflicting_evidence",
        "missing_subject_attributes",
        "missing_listing_context",
        "missing_market_context",
    ]
    fallback_reasons: List[str]
    limitations: List[str]
    freshness: Literal["fresh", "stale", "unknown"]
    sample_depth: Literal["none", "low", "moderate", "high"]
    evidence_agreement: Literal["aligned", "mixed", "conflicting", "unknown"]
    evidence_strength: Literal["weak", "moderate", "strong"]


@dataclass(frozen=True)
class WatchlistQuery:
    suburb_slug: Optional[str] = None
    strategy: Optional[str] = None
    state: Optional[str] = None
    watch_status: Optional[str] = None


@dataclass(frozen=True)
class WatchlistUpsertRequest:
    suburb_slug: str
    source_surface: Literal["advisor", "comparables", "watchlist"]
    strategy: Optional[Literal["yield", "owner-occupier", "balanced"]] = None
    watch_status: Optional[Literal["active", "review", "paused"]] = None
    notes: Optional[str] = None


class SuburbRepository(Protocol):
    def list_overview(self) -> List[SuburbOverviewItem]:
        ...

    def get_by_slug(self, slug: str) -> Optional[SuburbOverviewItem]:
        ...


class PropertyAdviceRepository(Protocol):
    def get_by_address_or_slug(self, query: str) -> Optional[PropertyAdvisorResponse]:
        ...

    def generate_snapshot(self, query: str, query_type: str = "auto", focus_strategy: Optional[str] = None) -> Optional[PropertyAdvisorResponse]:
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

    def upsert_entry(self, request: WatchlistUpsertRequest) -> tuple[Literal["created", "updated"], WatchlistEntry]:
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



def _parse_json_payload(value: Any, default: Any) -> Any:
    if value is None:
        return default
    if isinstance(value, (dict, list)):
        return value
    if isinstance(value, str):
        try:
            return json.loads(value)
        except json.JSONDecodeError:
            return default
    return default


def _coerce_confidence_band(score: int) -> Literal["low", "medium", "high"]:
    if score >= 4:
        return "high"
    if score >= 2:
        return "medium"
    return "low"


def _sample_depth_band(sample_size: int) -> Literal["none", "low", "moderate", "high"]:
    if sample_size <= 0:
        return "none"
    if sample_size < 3:
        return "low"
    if sample_size < 5:
        return "moderate"
    return "high"


def _derive_evidence_agreement(
    recommendation: Literal["watch", "consider", "pass"],
    listing_price: int,
    market_price: int,
    demand_score: Optional[float],
    supply_score: Optional[float],
) -> Literal["aligned", "mixed", "conflicting", "unknown"]:
    signals: List[int] = []
    if listing_price and market_price:
        ratio = listing_price / market_price if market_price else 1.0
        if ratio <= 0.98:
            signals.append(1)
        elif ratio >= 1.05:
            signals.append(-1)
        else:
            signals.append(0)
    if demand_score is not None and supply_score is not None:
        delta = demand_score - supply_score
        if delta >= 8:
            signals.append(1)
        elif delta <= -8:
            signals.append(-1)
        else:
            signals.append(0)
    directional = [signal for signal in signals if signal != 0]
    if not directional:
        return "unknown" if not signals else "mixed"
    if 1 in directional and -1 in directional:
        return "conflicting"
    if len(directional) == len(signals):
        return "aligned"
    expected = 1 if recommendation == "consider" else -1 if recommendation == "pass" else 0
    if expected == 0:
        return "mixed"
    return "aligned" if all(signal == expected for signal in directional) else "mixed"


def _derive_confidence_semantics(
    *,
    comparable_count: int,
    quality_score: float,
    quality_label: str,
    freshness: Literal["fresh", "stale", "unknown"],
    missing_key_attributes: bool,
    has_listing: bool,
    has_market_metrics: bool,
    evidence_agreement: Literal["aligned", "mixed", "conflicting", "unknown"],
) -> AdviceConfidenceSemantics:
    sample_depth = _sample_depth_band(comparable_count)
    confidence_score = 0
    confidence_reasons: List[str] = []
    fallback_reasons: List[str] = []
    limitations: List[str] = []
    fallback_state: AdviceConfidenceSemantics.__annotations__["fallback_state"] = "none"

    if sample_depth == "high":
        confidence_score += 2
        confidence_reasons.append(f"Comparable sample depth is high with {comparable_count} persisted members.")
    elif sample_depth == "moderate":
        confidence_score += 1
        confidence_reasons.append(f"Comparable sample depth is usable with {comparable_count} persisted members.")
    elif sample_depth == "low":
        confidence_score -= 2
        confidence_reasons.append(f"Comparable sample depth is thin with only {comparable_count} persisted members.")
        fallback_state = "low_sample"
        fallback_reasons.append("Comparable sample depth is below the minimum preferred threshold.")
        limitations.append("Comparable depth is too thin for a strong conviction call.")
    else:
        confidence_score -= 3
        confidence_reasons.append("No persisted comparable sample is available.")
        fallback_state = "insufficient_evidence"
        fallback_reasons.append("No comparable evidence is available.")
        limitations.append("Recommendation relies on partial context without comparable anchors.")

    if quality_score >= 0.78:
        confidence_score += 2
        confidence_reasons.append(f"Comparable set quality is strong at {quality_score:.3f}.")
    elif quality_score >= 0.62:
        confidence_score += 1
        confidence_reasons.append(f"Comparable set quality is moderate at {quality_score:.3f}.")
    else:
        confidence_score -= 1
        confidence_reasons.append(f"Comparable set quality is weak ({quality_label or 'unknown'}, {quality_score:.3f}).")
        limitations.append("Comparable quality is weak, so pricing precision is reduced.")

    if freshness == "fresh":
        confidence_score += 1
        confidence_reasons.append("Evidence freshness is within the supported window.")
    else:
        confidence_score -= 2
        confidence_reasons.append("Evidence freshness is stale or unknown.")
        if fallback_state == "none":
            fallback_state = "stale_evidence"
        fallback_reasons.append("Evidence is outside the freshness window for a stable recommendation.")
        limitations.append("Snapshot should be treated as directional until fresher evidence lands.")

    if missing_key_attributes:
        confidence_score -= 2
        confidence_reasons.append("Subject property facts are incomplete.")
        if fallback_state == "none":
            fallback_state = "missing_subject_attributes"
        fallback_reasons.append("Critical subject attributes required for comparable matching are missing.")
        limitations.append("Similarity scoring is degraded because subject property facts are incomplete.")
    else:
        confidence_score += 1
        confidence_reasons.append("Subject property facts are complete enough for rule-based matching.")

    if not has_listing:
        confidence_score -= 1
        confidence_reasons.append("Current listing context is missing.")
        if fallback_state == "none":
            fallback_state = "missing_listing_context"
        fallback_reasons.append("Latest listing status and asking context are unavailable.")
        limitations.append("Recommendation cannot fully validate current pricing without listing context.")
    else:
        confidence_score += 1
        confidence_reasons.append("Listing-state context is available.")

    if not has_market_metrics:
        confidence_score -= 1
        confidence_reasons.append("Suburb market metrics are missing.")
        if fallback_state == "none":
            fallback_state = "missing_market_context"
        fallback_reasons.append("Suburb market metrics are unavailable.")
        limitations.append("Market context is incomplete because suburb metrics are missing.")
    else:
        confidence_score += 1
        confidence_reasons.append("Suburb market metrics are available.")

    if evidence_agreement == "aligned":
        confidence_score += 1
        confidence_reasons.append("Pricing and market signals broadly agree.")
    elif evidence_agreement == "mixed":
        confidence_reasons.append("Evidence is mixed across pricing and market signals.")
        limitations.append("Signals are mixed, so position sizing should stay cautious.")
    elif evidence_agreement == "conflicting":
        confidence_score -= 2
        confidence_reasons.append("Evidence conflicts across pricing and market signals.")
        fallback_state = "conflicting_evidence"
        fallback_reasons.append("Material evidence disagreement was detected.")
        limitations.append("Conflicting signals limit how confidently the snapshot can separate watch vs action.")
    else:
        confidence_reasons.append("Evidence agreement could not be fully assessed.")

    if evidence_agreement == "conflicting":
        confidence_score = min(confidence_score, 3)

    confidence = _coerce_confidence_band(confidence_score)
    evidence_strength = "strong" if confidence_score >= 4 else "moderate" if confidence_score >= 1 else "weak"
    return AdviceConfidenceSemantics(
        confidence=confidence,
        confidence_reasons=confidence_reasons,
        fallback_state=fallback_state,
        fallback_reasons=fallback_reasons,
        limitations=limitations,
        freshness=freshness,
        sample_depth=sample_depth,
        evidence_agreement=evidence_agreement,
        evidence_strength=evidence_strength,
    )

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

    def generate_snapshot(self, query: str, query_type: str = "auto", focus_strategy: Optional[str] = None) -> Optional[PropertyAdvisorResponse]:
        _ = (query, query_type, focus_strategy)
        return self.get_by_address_or_slug(query)

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
    
    def __init__(self):
        self._entries = {entry.suburb_slug: entry.model_copy(deep=True) for entry in WATCHLIST_FIXTURE}

    def list_entries(self, criteria: WatchlistQuery) -> List[WatchlistEntry]:
        self.last_source = "mock"
        self.last_fallback_reason = None
        items = list(self._entries.values())
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
        return self._entries.get(suburb_slug)

    def list_alerts(self, severity: Optional[str] = None) -> List[WatchlistAlert]:
        self.last_source = "mock"
        self.last_fallback_reason = None
        alerts = [alert for entry in WATCHLIST_FIXTURE for alert in entry.alerts]
        if severity:
            return [alert for alert in alerts if alert.severity == severity]
        return alerts

    def upsert_entry(self, request: WatchlistUpsertRequest) -> tuple[Literal["created", "updated"], WatchlistEntry]:
        existing = self._entries.get(request.suburb_slug)
        if existing:
            updated = existing.model_copy(
                update={
                    "strategy": request.strategy or existing.strategy,
                    "watch_status": request.watch_status or "review",
                    "notes": request.notes or f"Updated from {request.source_surface} workflow.",
                }
            )
            self._entries[request.suburb_slug] = updated
            return ("updated", updated)

        fallback_suburb = request.suburb_slug.split("-")[0].replace("-", " ").title() or "Unknown"
        new_entry = WatchlistEntry(
            suburb_slug=request.suburb_slug,
            suburb_name=fallback_suburb,
            state="QLD",
            strategy=request.strategy or "balanced",
            watch_status=request.watch_status or "review",
            notes=request.notes or f"Saved from {request.source_surface} workflow.",
            target_buy_range_min=0,
            target_buy_range_max=0,
            alerts=[],
        )
        self._entries[request.suburb_slug] = new_entry
        return ("created", new_entry)


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
    algorithm_version = "phase2.round3.v1"
    advisory_context = "buyer"

    def __init__(self, session_factory: DatabaseSessionFactory):
        self.session_factory = session_factory

    def _load_subject(self, cur, query: str):
        normalized = _normalize_query(query)
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
              p.bathrooms,
              p.suburb_id
            from properties p
            where lower(coalesce(p.address_line_1, '') || ', ' || coalesce(p.suburb_name, '') || ' ' || coalesce(p.state_code, '') || ' ' || coalesce(p.postcode::text, '')) like %s
               or lower(coalesce(p.suburb_name, '')) = %s
               or lower(replace(coalesce(p.suburb_name, ''), ' ', '-') || '-' || lower(coalesce(p.state_code, '')) || '-' || coalesce(p.postcode::text, '')) = %s
            order by
              case
                when lower(replace(coalesce(p.suburb_name, ''), ' ', '-') || '-' || lower(coalesce(p.state_code, '')) || '-' || coalesce(p.postcode::text, '')) = %s then 0
                when lower(coalesce(p.address_line_1, '') || ', ' || coalesce(p.suburb_name, '') || ' ' || coalesce(p.state_code, '') || ' ' || coalesce(p.postcode::text, '')) = %s then 1
                when lower(coalesce(p.suburb_name, '')) = %s then 2
                else 3
              end,
              p.updated_at desc nulls last,
              p.created_at desc
            limit 1
            """,
            (f"%{normalized}%", normalized, normalized, normalized, normalized, normalized),
        )
        row = cur.fetchone() if hasattr(cur, "fetchone") else (cur.fetchall() or [None])[0]
        return row

    def _load_latest_listing(self, cur, property_id: str):
        cur.execute(
            """
            select l.id, l.status, l.asking_price, l.rent_price_weekly, ls.observed_at, ls.status, ls.asking_price, ls.days_on_market
            from listings l
            left join lateral (
              select observed_at, status, asking_price, days_on_market
              from listing_snapshots ls
              where ls.listing_id = l.id
              order by ls.observed_at desc, ls.created_at desc
              limit 1
            ) ls on true
            where l.property_id = %s
            order by coalesce(ls.observed_at, l.updated_at, l.created_at) desc
            limit 1
            """,
            (property_id,),
        )
        return cur.fetchone() if hasattr(cur, "fetchone") else (cur.fetchall() or [None])[0]

    def _load_latest_market_metrics(self, cur, suburb_id: Optional[str], property_type: Optional[str]):
        if not suburb_id:
            return None
        cur.execute(
            """
            select id, median_sale_price, median_weekly_rent, avg_days_on_market, demand_score, supply_score, market_temperature, period_end
            from market_metrics
            where suburb_id = %s
              and (property_type = %s or property_type is null)
            order by case when property_type = %s then 0 else 1 end, period_start desc, created_at desc
            limit 1
            """,
            (suburb_id, property_type, property_type),
        )
        return cur.fetchone() if hasattr(cur, "fetchone") else (cur.fetchall() or [None])[0]

    def _load_latest_comparable_set(self, cur, property_id: str):
        cur.execute(
            """
            select cs.id, cs.algorithm_version, cs.generated_at, cs.quality_score, cs.notes, cm.comparable_property_id
            from comparable_sets cs
            left join comparable_members cm on cm.comparable_set_id = cs.id
            where cs.target_property_id = %s
              and cs.purpose = 'buy_eval'
              and cs.basis = 'sales'
              and cs.status = 'complete'
            order by cs.generated_at desc, cm.rank_order asc
            """,
            (property_id,),
        )
        rows = cur.fetchall()
        return rows

    def _build_snapshot_payload(self, query: str, query_type: str, focus_strategy: Optional[str], evidence: dict[str, Any]) -> PropertyAdvisorResponse:
        subject = evidence["subject"]
        listing = evidence.get("listing")
        metrics = evidence.get("market_metrics")
        comparable_rows = evidence.get("comparables") or []
        fixture = PROPERTY_ADVISOR_FIXTURE
        comparable_count = len({str(row[5]) for row in comparable_rows if len(row) > 5 and row[5] is not None})
        quality_score = round(_safe_float(comparable_rows[0][3]), 3) if comparable_rows else 0.0
        notes = _parse_json_payload(comparable_rows[0][4], {}) if comparable_rows else {}
        listing_price = _safe_int((listing[6] if listing and len(listing) > 6 and listing[6] is not None else (listing[2] if listing and len(listing) > 2 else 0)))
        market_price = _safe_int(metrics[1]) if metrics else 0
        missing_key_attributes = any(subject[index] is None for index in (5, 6, 7))
        warnings: List[str] = []
        fallback_notes: List[str] = []
        rationale_bullets: List[str] = []
        freshness: Literal["fresh", "stale", "unknown"] = "unknown"
        if comparable_count < 3:
            warnings.append("Comparable evidence is weak; fewer than 3 persisted members are available.")
            fallback_notes.append("Confidence is capped until a denser comparable set is generated.")
        if not listing:
            warnings.append("Listing facts are missing; recommendation is based on property, suburb, and comparable evidence only.")
        if missing_key_attributes:
            warnings.append("Key property attributes are incomplete; similarity scoring and stance confidence are degraded.")
        evidence_dates = [
            _coerce_to_date(listing[4]) if listing and len(listing) > 4 else None,
            _coerce_to_date(comparable_rows[0][2]) if comparable_rows else None,
            _coerce_to_date(metrics[7]) if metrics else None,
        ]
        freshness_anchor = max((d for d in evidence_dates if d is not None), default=None)
        stale_evidence = freshness_anchor is None or (date.today() - freshness_anchor).days > 90
        freshness = "stale" if stale_evidence else "fresh"
        if stale_evidence:
            warnings.append("Persisted evidence is stale or insufficiently fresh for a stronger recommendation.")
            fallback_notes.append("Treat the snapshot as directional until newer listing, comp, or suburb inputs land.")
        demand_score = _safe_float(metrics[4]) if metrics and len(metrics) > 4 and metrics[4] is not None else None
        supply_score = _safe_float(metrics[5]) if metrics and len(metrics) > 5 and metrics[5] is not None else None
        if listing_price and market_price and comparable_count >= 3 and not stale_evidence:
            ratio = listing_price / market_price if market_price else 1
            if ratio <= 0.98:
                recommendation = "consider"
                rationale_bullets.append("Latest asking price sits at or below suburb sale median while evidence depth is usable.")
            elif ratio >= 1.05:
                recommendation = "pass"
                rationale_bullets.append("Latest asking price is stretched against suburb pricing anchors.")
            else:
                recommendation = "watch"
                rationale_bullets.append("Pricing is broadly aligned, but not discounted enough to force action.")
        elif comparable_count == 0 or missing_key_attributes or stale_evidence:
            recommendation = "watch"
            rationale_bullets.append("Evidence quality does not support a stronger buy/pass stance.")
        else:
            recommendation = "watch"
            rationale_bullets.append("Comparable and market evidence is only partially complete, so stance remains conservative.")
        evidence_agreement = _derive_evidence_agreement(recommendation, listing_price, market_price, demand_score, supply_score)
        semantics = _derive_confidence_semantics(
            comparable_count=comparable_count,
            quality_score=quality_score,
            quality_label=str(notes.get("quality_label", "unknown")),
            freshness=freshness,
            missing_key_attributes=missing_key_attributes,
            has_listing=bool(listing),
            has_market_metrics=bool(metrics),
            evidence_agreement=evidence_agreement,
        )
        confidence = semantics.confidence
        warnings = list(dict.fromkeys(warnings + semantics.fallback_reasons))
        fallback_notes = list(dict.fromkeys(fallback_notes + semantics.fallback_reasons))
        summary = {
            "consider": "Persisted evidence supports progressing with cautious underwriting.",
            "watch": "Persisted evidence supports monitoring until conviction improves.",
            "pass": "Persisted evidence suggests avoiding the opportunity at the current setup.",
        }[recommendation]
        rationale_bullets.append(f"Comparable set quality is {notes.get('quality_label', 'unknown')} with {comparable_count} persisted members.")
        if metrics:
            rationale_bullets.append(f"Suburb market temperature is {metrics[6] or 'unknown'} with median sale price anchor ${market_price:,}." if market_price else "Suburb metrics are available but price anchors are incomplete.")
        evidence_summary = AdviceEvidenceSummary(
            contract_version="phase2.round4",
            algorithm_version=self.algorithm_version,
            freshness_status=semantics.freshness,
            required_inputs={
                "property_facts": True,
                "evidence_freshness": True,
                "algorithm_version": True,
            },
            optional_inputs={
                "listing_facts": bool(listing),
                "suburb_metrics": bool(metrics),
                "comparable_set": bool(comparable_rows),
            },
            sections=[
                AdviceEvidenceSummarySection(name="property_facts", status="available", summary="Persisted property facts loaded from properties table."),
                AdviceEvidenceSummarySection(name="listing_facts", status=("available" if listing else "missing"), summary=(f"Latest listing status {(listing[5] or listing[1] or 'unknown')} with asking price ${listing_price:,}." if listing and listing_price else "No current listing facts were available.")),
                AdviceEvidenceSummarySection(name="suburb_metrics", status=("available" if metrics else "missing"), summary=(f"Latest suburb metrics temperature {(metrics[6] or 'unknown')} and median sale price ${market_price:,}." if metrics and market_price else "No suburb metrics row was available.")),
                AdviceEvidenceSummarySection(name="comparable_set", status=("available" if comparable_rows else "missing"), summary=(f"Latest comparable set {comparable_rows[0][0]} produced {comparable_count} member(s)." if comparable_rows else "No persisted comparable set was available.")),
            ],
            warnings=warnings,
            fallback_notes=fallback_notes,
            limitations=semantics.limitations,
            confidence_reasons=semantics.confidence_reasons,
            fallback_state=semantics.fallback_state,
            fallback_reasons=semantics.fallback_reasons,
            sample_depth=semantics.sample_depth,
            evidence_agreement=semantics.evidence_agreement,
            evidence_strength=semantics.evidence_strength,
        )
        return PropertyAdvisorResponse(
            data_source=DataSourceStatus(mode="postgres", source="postgres", is_fallback=False, message="Property advice snapshot loaded from PostgreSQL."),
            property=SubjectProperty(
                address=_format_property_address(subject[1], subject[2], subject[3], subject[4]),
                property_type=subject[5] or fixture.property.property_type,
                beds=int(subject[6]) if subject[6] is not None else 0,
                baths=int(subject[7]) if subject[7] is not None else 0,
            ),
            advice=PropertyAdvice(
                recommendation=recommendation,
                confidence=confidence,
                headline=summary,
                summary=summary,
                stance=recommendation,
                rationale_bullets=rationale_bullets,
                warnings=warnings,
                fallback_notes=fallback_notes,
                confidence_reasons=semantics.confidence_reasons,
                fallback_state=semantics.fallback_state,
                fallback_reasons=semantics.fallback_reasons,
                limitations=semantics.limitations,
                freshness=semantics.freshness,
                sample_depth=semantics.sample_depth,
                evidence_agreement=semantics.evidence_agreement,
                risks=warnings,
                strengths=[bullet for bullet in rationale_bullets if "not" not in bullet.lower()][:3],
                next_steps=[
                    "Review the latest comparable members before pricing an offer.",
                    "Confirm fresh listing facts and suburb metrics on the next ingest cycle.",
                ],
                evidence_summary=evidence_summary,
            ),
            market_context=AdvisoryMarketContext(
                suburb=subject[2] or fixture.market_context.suburb,
                strategy_focus=focus_strategy or "balanced",
                demand_signal=(f"Demand score {metrics[4]} from latest suburb metrics." if metrics and metrics[4] is not None else "Demand signal unavailable; use balanced default wording."),
                supply_signal=(f"Supply score {metrics[5]} from latest suburb metrics." if metrics and metrics[5] is not None else "Supply signal unavailable; use balanced default wording."),
            ),
            comparable_snapshot=ComparableSnapshot(
                sample_size=comparable_count,
                price_position=("insufficient_data" if comparable_count == 0 or not listing_price or not market_price else ("below_range" if listing_price < market_price else "above_range" if listing_price > market_price else "in_range")),
                summary=("No persisted comparable members available." if comparable_count == 0 else f"Using {comparable_count} member(s) from the latest persisted comparable set."),
            ),
            decision_summary=summary,
            rationale=[AdvisoryRationaleItem(signal=f"Reason {index+1}", stance=("caution" if "stale" in bullet.lower() or "weak" in bullet.lower() or "stretched" in bullet.lower() else "neutral"), evidence=bullet) for index, bullet in enumerate(rationale_bullets[:3])],
            investor_signals=[
                AdvisoryInvestorSignal(title="Evidence freshness", status=("risk" if stale_evidence else "neutral"), detail=("Evidence is stale." if stale_evidence else "Evidence freshness is acceptable.")),
                AdvisoryInvestorSignal(title="Evidence agreement", status=("risk" if semantics.evidence_agreement == "conflicting" else "positive" if semantics.evidence_agreement == "aligned" else "neutral"), detail=f"Signals are {semantics.evidence_agreement}."),
            ],
            summary_cards=[SummaryCard(title="Recommendation", value=recommendation, detail=f"Confidence: {confidence}")],
            workflow_links=[WorkflowLink(label="Open comparables", href=f"/comparables?query={query}", context="Validate the persisted comparable set.")],
            workflow_snapshot=WorkflowSnapshot(stage="property_advisor", primary_suburb_slug=_slugify_suburb(subject[2] or '', subject[3], subject[4]), next_step="Validate persisted comparable evidence before taking action.", next_href=f"/comparables?query={query}", investor_message="Persisted advice snapshots should be reviewed alongside comps and watchlist context."),
            inputs=AdvisoryInputs(
                query=query,
                query_type=("slug" if query_type == "auto" and "-" in query and "," not in query else query_type),
                suburb_slug=_slugify_suburb(subject[2] or '', subject[3], subject[4]),
                contract_version="phase2.round4",
                required_persisted_inputs={"property_facts": True, "evidence_freshness": True, "algorithm_version": True},
                optional_persisted_inputs={"listing_facts": bool(listing), "suburb_metrics": bool(metrics), "comparable_set": bool(comparable_rows)},
                missing_data_behavior={
                    "weak_comparable_evidence": "Lower confidence explicitly while keeping recommendation polarity separate from evidence strength.",
                    "missing_listing_facts": "Retain advice using comparables and suburb metrics, and emit explicit warnings.",
                    "missing_key_property_attributes": "Keep watch stance and note degraded similarity quality.",
                    "stale_or_insufficient_evidence": "Treat snapshot as directional and surface explicit fallback state and limitations.",
                },
            ),
        )

    def _persist_snapshot(self, cur, property_id: str, payload: PropertyAdvisorResponse, evidence: dict[str, Any], query: str):
        comparable_rows = evidence.get("comparables") or []
        metrics = evidence.get("market_metrics")
        cur.execute(
            """
            select id
            from property_advice_snapshots
            where property_id = %s and advisory_context = %s and algorithm_version = %s
            order by generated_at desc, created_at desc
            limit 1
            """,
            (property_id, self.advisory_context, self.algorithm_version),
        )
        existing = cur.fetchone() if hasattr(cur, "fetchone") else (cur.fetchall() or [None])[0]
        metrics_payload = {
            "decision_summary": payload.decision_summary,
            "summary": payload.advice.summary,
            "stance": payload.advice.stance,
            "rationale_bullets": payload.advice.rationale_bullets,
            "warnings": payload.advice.warnings,
            "fallback_notes": payload.advice.fallback_notes,
            "confidence_reasons": payload.advice.confidence_reasons,
            "fallback_state": payload.advice.fallback_state,
            "fallback_reasons": payload.advice.fallback_reasons,
            "limitations": payload.advice.limitations,
            "freshness": payload.advice.freshness,
            "sample_depth": payload.advice.sample_depth,
            "evidence_agreement": payload.advice.evidence_agreement,
            "evidence_summary": payload.advice.evidence_summary.model_dump(),
            "query": query,
        }
        params = (
            evidence["subject"][0],
            str(comparable_rows[0][0]) if comparable_rows else None,
            str(metrics[0]) if metrics else None,
            datetime.now(timezone.utc).isoformat(),
            self.advisory_context,
            payload.advice.recommendation,
            payload.advice.confidence,
            None,
            None,
            None,
            payload.advice.summary,
            json.dumps(payload.advice.rationale_bullets, sort_keys=True),
            json.dumps(payload.advice.warnings, sort_keys=True),
            json.dumps(metrics_payload, sort_keys=True),
            self.algorithm_version,
        )
        if existing:
            cur.execute(
                """
                update property_advice_snapshots
                set comparable_set_id = %s, market_metrics_id = %s, generated_at = %s, advisory_context = %s, recommendation = %s,
                    confidence = %s, target_value_low = %s, target_value_high = %s, estimated_rent_weekly = %s, headline_summary = %s,
                    rationale = %s::jsonb, risks = %s::jsonb, metrics = %s::jsonb, algorithm_version = %s
                where id = %s
                """,
                params[1:] + (existing[0],),
            )
        else:
            cur.execute(
                """
                insert into property_advice_snapshots (
                  property_id, comparable_set_id, market_metrics_id, generated_at, advisory_context, recommendation, confidence,
                  target_value_low, target_value_high, estimated_rent_weekly, headline_summary, rationale, risks, metrics, algorithm_version
                ) values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb, %s::jsonb, %s)
                """,
                params,
            )

    def generate_snapshot(self, query: str, query_type: str = "auto", focus_strategy: Optional[str] = None) -> Optional[PropertyAdvisorResponse]:
        if not self.session_factory.config.url:
            self.last_source = "fallback_mock"
            self.last_fallback_reason = "No database URL configured for advice snapshot generation."
            return super().generate_snapshot(query, query_type=query_type, focus_strategy=focus_strategy)
        try:
            with psycopg.connect(self.session_factory.config.url) as conn:
                with conn.cursor() as cur:
                    subject = self._load_subject(cur, query)
                    if not subject:
                        self.last_source = "fallback_mock"
                        self.last_fallback_reason = "No persisted property matched for advice snapshot generation."
                        return None
                    evidence = {
                        "subject": subject,
                        "listing": self._load_latest_listing(cur, str(subject[0])),
                        "market_metrics": self._load_latest_market_metrics(cur, subject[8], subject[5]),
                        "comparables": self._load_latest_comparable_set(cur, str(subject[0])),
                    }
                    payload = self._build_snapshot_payload(query, query_type, focus_strategy, evidence)
                    self._persist_snapshot(cur, str(subject[0]), payload, evidence, query)
                    self.last_source = "postgres"
                    self.last_fallback_reason = None
                    return payload
        except psycopg.Error as exc:
            self.last_source = "fallback_mock"
            self.last_fallback_reason = f"Advice snapshot generation failed: {exc.__class__.__name__}"
            return super().generate_snapshot(query, query_type=query_type, focus_strategy=focus_strategy)

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
                          p.address_line_1, p.suburb_name, p.state_code, p.postcode, p.property_type, p.bedrooms, p.bathrooms,
                          pas.recommendation, pas.confidence, pas.headline_summary, pas.metrics, pas.algorithm_version
                        from property_advice_snapshots pas
                        join properties p on p.id = pas.property_id
                        where lower(coalesce(p.address_line_1, '') || ', ' || coalesce(p.suburb_name, '') || ' ' || coalesce(p.state_code, '') || ' ' || coalesce(p.postcode::text, '')) like %s
                           or lower(replace(coalesce(p.suburb_name, ''), ' ', '-') || '-' || lower(coalesce(p.state_code, '')) || '-' || coalesce(p.postcode::text, '')) = %s
                        order by pas.generated_at desc, pas.created_at desc
                        limit 1
                        """,
                        (f"%{normalized}%", normalized),
                    )
                    row = cur.fetchone() if hasattr(cur, "fetchone") else (cur.fetchall() or [None])[0]
        except psycopg.Error as exc:
            item = super().get_by_address_or_slug(query)
            self.last_source = "fallback_mock"
            self.last_fallback_reason = f"Property advice query failed: {exc.__class__.__name__}"
            return item
        if not row:
            self.last_source = "fallback_mock"
            self.last_fallback_reason = "No persisted advice snapshot exists for query; using fallback guidance."
            return super().get_by_address_or_slug(query)
        metrics = _parse_json_payload(row[10], {})
        evidence_summary = AdviceEvidenceSummary.model_validate(metrics.get("evidence_summary") or {
            "contract_version": "phase2.round4",
            "algorithm_version": row[11] or self.algorithm_version,
            "freshness_status": "unknown",
            "required_inputs": {"property_facts": True, "evidence_freshness": True, "algorithm_version": True},
            "optional_inputs": {},
            "sections": [],
            "warnings": metrics.get("warnings", []),
            "fallback_notes": metrics.get("fallback_notes", []),
            "limitations": metrics.get("limitations", []),
            "confidence_reasons": metrics.get("confidence_reasons", []),
            "fallback_state": metrics.get("fallback_state", "none"),
            "fallback_reasons": metrics.get("fallback_reasons", []),
            "sample_depth": metrics.get("sample_depth", "none"),
            "evidence_agreement": metrics.get("evidence_agreement", "unknown"),
            "evidence_strength": metrics.get("evidence_strength", "weak"),
        })
        self.last_source = "postgres"
        self.last_fallback_reason = None
        return PROPERTY_ADVISOR_FIXTURE.model_copy(update={
            "property": SubjectProperty(address=_format_property_address(row[0], row[1], row[2], row[3]), property_type=row[4] or PROPERTY_ADVISOR_FIXTURE.property.property_type, beds=int(row[5] or 0), baths=int(row[6] or 0)),
            "advice": PropertyAdvice(
                recommendation=row[7] or "watch", confidence=row[8] or "low", headline=row[9] or PROPERTY_ADVISOR_FIXTURE.advice.headline,
                summary=metrics.get("summary") or row[9] or PROPERTY_ADVISOR_FIXTURE.advice.headline,
                stance=metrics.get("stance") or row[7] or "watch",
                rationale_bullets=list(metrics.get("rationale_bullets") or []),
                warnings=list(metrics.get("warnings") or []),
                fallback_notes=list(metrics.get("fallback_notes") or []),
                confidence_reasons=list(metrics.get("confidence_reasons") or []),
                fallback_state=metrics.get("fallback_state") or "none",
                fallback_reasons=list(metrics.get("fallback_reasons") or []),
                limitations=list(metrics.get("limitations") or []),
                freshness=metrics.get("freshness") or evidence_summary.freshness_status,
                sample_depth=metrics.get("sample_depth") or "none",
                evidence_agreement=metrics.get("evidence_agreement") or "unknown",
                risks=list(metrics.get("warnings") or []), strengths=list(metrics.get("rationale_bullets") or [])[:3], next_steps=list(PROPERTY_ADVISOR_FIXTURE.advice.next_steps), evidence_summary=evidence_summary,
            ),
            "decision_summary": metrics.get("decision_summary") or row[9] or PROPERTY_ADVISOR_FIXTURE.decision_summary,
            "inputs": PROPERTY_ADVISOR_FIXTURE.inputs.model_copy(update={"contract_version": "phase2.round4"}),
        })


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
        super().__init__()
        self.session_factory = session_factory
        self._entries = {}

    def _map_row_to_entry(self, row: dict) -> WatchlistEntry:
        return WatchlistEntry.model_validate(row)

    def _load_entries(self) -> List[WatchlistEntry]:
        if not self.session_factory.config.url:
            items = list(WATCHLIST_FIXTURE)
            self.last_source = "fallback_mock"
            self.last_fallback_reason = "No database URL configured for watchlist."
            return self._merge_runtime_entries(items)
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
            return self._merge_runtime_entries(items)
        if not rows:
            items = list(WATCHLIST_FIXTURE)
            self.last_source = "fallback_mock"
            self.last_fallback_reason = "Watchlist query returned 0 rows."
            return self._merge_runtime_entries(items)
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
        return self._merge_runtime_entries(entries)

    def _merge_runtime_entries(self, loaded: List[WatchlistEntry]) -> List[WatchlistEntry]:
        merged = {entry.suburb_slug: entry for entry in loaded}
        for slug, entry in self._entries.items():
            merged[slug] = entry
        return list(merged.values())

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
