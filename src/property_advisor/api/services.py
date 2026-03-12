from __future__ import annotations

"""Internal MVP service layer used by HTTP routes."""

from datetime import datetime, timezone
from statistics import mean
from typing import Dict, List, Literal, Optional

from property_advisor.api.data_access import DataAccessLayer
from property_advisor.api.db import create_session_factory
from property_advisor.api.mock_fixtures import PROPERTY_ADVISOR_FIXTURE
from property_advisor.api.repositories import ComparableQuery, WatchlistQuery
from property_advisor.api.schemas import (
    AdvisoryInputs,
    AdvisoryMarketContext,
    ComparableNarrative,
    ComparableSnapshot,
    ComparableSummary,
    ComparablesResponse,
    HealthResponse,
    PropertyAdvisorResponse,
    SuburbOverviewSummary,
    SuburbsOverviewResponse,
    WatchlistAlertsResponse,
    WatchlistDetailResponse,
    WatchlistEntry,
    WatchlistGroup,
    WatchlistResponse,
    WatchlistSummary,
)

_DAL = DataAccessLayer.create(create_session_factory())


def get_health_status() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="propertyadvisor-api",
        timestamp=datetime.now(timezone.utc),
    )


def get_suburbs_overview(dal: DataAccessLayer = _DAL) -> SuburbsOverviewResponse:
    items = dal.suburbs.list_overview()
    watchlist_slugs = {item.suburb_slug for item in dal.watchlist.list_entries(WatchlistQuery())}
    summary = SuburbOverviewSummary(
        tracked_suburbs=len(items),
        watchlist_suburbs=sum(1 for item in items if item.slug in watchlist_slugs),
        data_freshness=f"{dal.mode}-weekly" if items else "empty",
    )
    return SuburbsOverviewResponse(
        generated_at=datetime.now(timezone.utc),
        summary=summary,
        items=items,
    )


def _get_price_position(subject_price: int, low: int, high: int) -> str:
    if high == 0:
        return "insufficient_data"
    if subject_price < low:
        return "below_range"
    if subject_price > high:
        return "above_range"
    return "in_range"


def get_property_advice(
    query: str = PROPERTY_ADVISOR_FIXTURE.property.address,
    query_type: str = "auto",
    focus_strategy: Optional[str] = None,
    dal: DataAccessLayer = _DAL,
) -> PropertyAdvisorResponse:
    if query_type == "auto":
        effective_type = "slug" if "-" in query and "," not in query else "address"
    else:
        effective_type = query_type

    advice = dal.property_advice.get_by_address_or_slug(query) or PROPERTY_ADVISOR_FIXTURE.model_copy(
        update={
            "advice": PROPERTY_ADVISOR_FIXTURE.advice.model_copy(
                update={
                    "recommendation": "watch",
                    "confidence": "low",
                    "headline": "No direct property match found yet; showing baseline guidance.",
                }
            )
        }
    )
    suburb = dal.suburbs.get_by_slug(query) if effective_type == "slug" else None
    if not isinstance(focus_strategy, str):
        focus_strategy = None
    strategy_focus = focus_strategy or "balanced"

    comparable_items = dal.comparables.list_by_subject(ComparableQuery(query=query, max_items=5))
    prices = [item.price for item in comparable_items]
    comparable_min = min(prices) if prices else 0
    comparable_max = max(prices) if prices else 0
    position = _get_price_position(895000, comparable_min, comparable_max)

    strategy_note = f"Align recommendation with {strategy_focus} watchlist strategy assumptions."
    next_steps = list(advice.advice.next_steps)
    if strategy_note not in next_steps:
        next_steps.append(strategy_note)

    market_context = AdvisoryMarketContext(
        suburb=(suburb.name if suburb else "Southport"),
        strategy_focus=strategy_focus,
        demand_signal="Rental demand remains resilient with low vacancy in sample feed.",
        supply_signal="Listing momentum is elevated, which can soften short-term negotiation leverage.",
    )

    comparable_snapshot = ComparableSnapshot(
        sample_size=len(comparable_items),
        price_position=position,
        summary=(
            "Subject pricing sits inside the current comparable range."
            if position == "in_range"
            else "Subject pricing appears stretched relative to recent sample comparables."
        ),
    )

    return advice.model_copy(
        update={
            "advice": advice.advice.model_copy(update={"next_steps": next_steps}),
            "market_context": market_context,
            "comparable_snapshot": comparable_snapshot,
            "decision_summary": (
                f"{advice.advice.recommendation.title()} with {advice.advice.confidence} confidence. "
                "Use comparables and watchlist alerts together before placing an offer."
            ),
            "inputs": AdvisoryInputs(
                query=query,
                query_type=effective_type,
                suburb_slug=suburb.slug if suburb else advice.inputs.suburb_slug,
            ),
        }
    )


def _build_comparable_narrative(summary: ComparableSummary, query: str) -> ComparableNarrative:
    if summary.count == 0:
        return ComparableNarrative(
            price_position="insufficient_data",
            spread_commentary="No usable comps matched the current filters.",
            investor_takeaway="Broaden radius or price bounds before making a decision.",
            action_prompt="Relax one filter and rerun the comp set.",
        )

    spread = summary.max_price - summary.min_price
    if summary.average_price < 870000:
        position = "discount"
    elif summary.average_price > 900000:
        position = "premium"
    else:
        position = "aligned"

    return ComparableNarrative(
        price_position=position,
        spread_commentary=f"Spread is {spread:,} across {summary.count} comparable sales for {query}.",
        investor_takeaway="Treat this as a negotiation anchor, not a valuation substitute.",
        action_prompt="Prioritise the two closest matches and verify renovation/land deltas.",
    )


def get_comparables(
    query: str = PROPERTY_ADVISOR_FIXTURE.property.address,
    max_items: int = 5,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    max_distance_km: Optional[float] = None,
    dal: DataAccessLayer = _DAL,
) -> ComparablesResponse:
    items = dal.comparables.list_by_subject(ComparableQuery(query=query, max_items=max_items))
    if min_price is not None:
        items = [item for item in items if item.price >= min_price]
    if max_price is not None:
        items = [item for item in items if item.price <= max_price]
    if max_distance_km is not None:
        items = [item for item in items if item.distance_km <= max_distance_km]

    if not items:
        empty_summary = ComparableSummary(count=0, min_price=0, max_price=0, average_price=0)
        return ComparablesResponse(
            subject=query,
            set_quality="empty",
            query=query,
            items=[],
            summary=empty_summary,
            narrative=_build_comparable_narrative(empty_summary, query),
        )

    prices = [item.price for item in items]
    summary = ComparableSummary(
        count=len(items),
        min_price=min(prices),
        max_price=max(prices),
        average_price=round(mean(prices)),
    )
    return ComparablesResponse(
        subject=query,
        set_quality="mvp-sample-filtered" if any(v is not None for v in [min_price, max_price, max_distance_km]) else "mvp-sample",
        query=query,
        items=items,
        summary=summary,
        narrative=_build_comparable_narrative(summary, query),
    )


def _build_watchlist_groups(group_by: Literal["none", "state", "strategy"], items: List[WatchlistEntry]) -> List[WatchlistGroup]:
    if group_by == "none":
        return []

    grouped: Dict[str, List[WatchlistEntry]] = {}
    for item in items:
        key = item.state if group_by == "state" else item.strategy
        grouped.setdefault(key, []).append(item)

    groups: List[WatchlistGroup] = []
    for key, entries in sorted(grouped.items(), key=lambda pair: pair[0]):
        groups.append(
            WatchlistGroup(
                key=key.lower(),
                label=key,
                entries=entries,
                action_required=sum(1 for entry in entries if entry.watch_status in {"review", "paused"}),
                high_alerts=sum(
                    1
                    for entry in entries
                    for alert in entry.alerts
                    if alert.severity == "high"
                ),
            )
        )
    return groups


def get_watchlist(
    suburb_slug: Optional[str] = None,
    strategy: Optional[str] = None,
    state: Optional[str] = None,
    watch_status: Optional[str] = None,
    group_by: Literal["none", "state", "strategy"] = "none",
    dal: DataAccessLayer = _DAL,
) -> WatchlistResponse:
    items = dal.watchlist.list_entries(
        WatchlistQuery(
            suburb_slug=suburb_slug,
            strategy=strategy,
            state=state,
            watch_status=watch_status,
        )
    )
    alert_counts = {"info": 0, "watch": 0, "high": 0}
    by_status = {"active": 0, "review": 0, "paused": 0}
    by_strategy = {"yield": 0, "owner-occupier": 0, "balanced": 0}
    action_counts = {"needs_review": 0, "ready_to_progress": 0, "on_hold": 0}

    for item in items:
        by_status[item.watch_status] += 1
        by_strategy[item.strategy] += 1
        if item.watch_status == "review":
            action_counts["needs_review"] += 1
        elif item.watch_status == "active":
            action_counts["ready_to_progress"] += 1
        else:
            action_counts["on_hold"] += 1

        for alert in item.alerts:
            alert_counts[alert.severity] += 1

    summary = WatchlistSummary(
        total_entries=len(items),
        active_entries=by_status["active"],
        grouped_view=group_by,
        alert_counts=alert_counts,
        by_status=by_status,
        by_strategy=by_strategy,
        action_counts=action_counts,
        investor_brief=(
            "Focus this week on review and paused suburbs with high-severity pricing alerts."
            if alert_counts["high"] > 0
            else "No critical alerts detected; continue weekly monitoring cadence."
        ),
    )
    return WatchlistResponse(
        generated_at=datetime.now(timezone.utc),
        mode=dal.mode,
        summary=summary,
        items=items,
        groups=_build_watchlist_groups(group_by, items),
    )


def get_watchlist_detail(suburb_slug: str, dal: DataAccessLayer = _DAL) -> Optional[WatchlistDetailResponse]:
    item = dal.watchlist.get_entry(suburb_slug)
    if not item:
        return None
    return WatchlistDetailResponse(
        generated_at=datetime.now(timezone.utc),
        mode=dal.mode,
        item=item,
    )


def get_watchlist_alerts(severity: Optional[str] = None, dal: DataAccessLayer = _DAL) -> WatchlistAlertsResponse:
    items = dal.watchlist.list_alerts(severity=severity)
    return WatchlistAlertsResponse(
        generated_at=datetime.now(timezone.utc),
        mode=dal.mode,
        total=len(items),
        items=items,
    )
