from __future__ import annotations

"""Internal MVP service layer used by HTTP routes."""

from datetime import datetime, timezone
from statistics import mean
from typing import Dict, List, Literal, Optional

from property_advisor.api.data_access import DataAccessLayer
from property_advisor.api.db import create_session_factory
from property_advisor.api.mock_fixtures import PROPERTY_ADVISOR_FIXTURE
from property_advisor.api.schemas import (
    AdvisoryInputs,
    ComparableSummary,
    ComparablesResponse,
    HealthResponse,
    PropertyAdvisorResponse,
    SuburbOverviewSummary,
    SuburbsOverviewResponse,
    WatchlistAlertsResponse,
    WatchlistDetailResponse,
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
    watchlist_slugs = {item.suburb_slug for item in dal.watchlist.list_entries()}
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

    strategy_note = (
        f"Align recommendation with {focus_strategy} watchlist strategy assumptions."
        if focus_strategy
        else None
    )

    next_steps = list(advice.advice.next_steps)
    if strategy_note and strategy_note not in next_steps:
        next_steps.append(strategy_note)

    return advice.model_copy(
        update={
            "advice": advice.advice.model_copy(update={"next_steps": next_steps}),
            "inputs": AdvisoryInputs(
                query=query,
                query_type=effective_type,
                suburb_slug=suburb.slug if suburb else advice.inputs.suburb_slug,
            ),
        }
    )


def get_comparables(
    query: str = PROPERTY_ADVISOR_FIXTURE.property.address,
    max_items: int = 5,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    max_distance_km: Optional[float] = None,
    dal: DataAccessLayer = _DAL,
) -> ComparablesResponse:
    items = dal.comparables.list_by_subject(query=query, max_items=max_items)
    if min_price is not None:
        items = [item for item in items if item.price >= min_price]
    if max_price is not None:
        items = [item for item in items if item.price <= max_price]
    if max_distance_km is not None:
        items = [item for item in items if item.distance_km <= max_distance_km]

    if not items:
        return ComparablesResponse(
            subject=query,
            set_quality="empty",
            query=query,
            items=[],
            summary=ComparableSummary(count=0, min_price=0, max_price=0, average_price=0),
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
    )


def _build_watchlist_groups(group_by: Literal["none", "state", "strategy"], items: List) -> List[WatchlistGroup]:
    if group_by == "none":
        return []

    grouped: Dict[str, List] = {}
    for item in items:
        key = item.state if group_by == "state" else item.strategy
        grouped.setdefault(key, []).append(item)

    return [
        WatchlistGroup(key=key.lower(), label=key, entries=entries)
        for key, entries in sorted(grouped.items(), key=lambda pair: pair[0])
    ]


def get_watchlist(
    suburb_slug: Optional[str] = None,
    strategy: Optional[str] = None,
    state: Optional[str] = None,
    watch_status: Optional[str] = None,
    group_by: Literal["none", "state", "strategy"] = "none",
    dal: DataAccessLayer = _DAL,
) -> WatchlistResponse:
    items = dal.watchlist.list_entries(
        suburb_slug=suburb_slug,
        strategy=strategy,
        state=state,
        watch_status=watch_status,
    )
    alert_counts = {"info": 0, "watch": 0, "high": 0}
    for item in items:
        for alert in item.alerts:
            alert_counts[alert.severity] += 1

    summary = WatchlistSummary(
        total_entries=len(items),
        active_entries=sum(1 for item in items if item.watch_status == "active"),
        grouped_view=group_by,
        alert_counts=alert_counts,
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
