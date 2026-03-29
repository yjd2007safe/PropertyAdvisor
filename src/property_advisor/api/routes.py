from __future__ import annotations

"""HTTP routes for the PropertyAdvisor MVP API."""

from typing import Literal, Optional

from fastapi import APIRouter, HTTPException, Query

from property_advisor.api.schemas import (
    ComparablesResponse,
    HealthResponse,
    OrchestrationReviewResponse,
    PropertyAdvisorResponse,
    SuburbsOverviewResponse,
    WatchlistAlertsResponse,
    WatchlistDetailResponse,
    WatchlistResponse,
)
from property_advisor.api.services import (
    get_comparables,
    get_health_status,
    get_orchestration_review_status,
    get_property_advice,
    get_suburbs_overview,
    get_watchlist,
    get_watchlist_alerts,
    get_watchlist_detail,
)

router = APIRouter(prefix="/api")


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return get_health_status()


@router.get("/suburbs/overview", response_model=SuburbsOverviewResponse)
def suburbs_overview() -> SuburbsOverviewResponse:
    return get_suburbs_overview()


@router.get("/advisor/property", response_model=PropertyAdvisorResponse)
def property_advisor(
    query: str = Query(default="12 Example Avenue, Southport QLD 4215", min_length=3),
    query_type: Literal["address", "slug", "auto"] = Query(default="auto"),
    focus_strategy: Optional[Literal["yield", "owner-occupier", "balanced"]] = Query(default=None),
) -> PropertyAdvisorResponse:
    return get_property_advice(query=query, query_type=query_type, focus_strategy=focus_strategy)


@router.get("/comparables", response_model=ComparablesResponse)
def comparables(
    query: str = Query(default="southport", min_length=3),
    max_items: int = Query(default=5, ge=1, le=20),
    min_price: Optional[int] = Query(default=None, ge=0),
    max_price: Optional[int] = Query(default=None, ge=0),
    max_distance_km: Optional[float] = Query(default=None, ge=0),
) -> ComparablesResponse:
    return get_comparables(
        query=query,
        max_items=max_items,
        min_price=min_price,
        max_price=max_price,
        max_distance_km=max_distance_km,
    )


@router.get("/orchestration/review", response_model=OrchestrationReviewResponse)
def orchestration_review() -> OrchestrationReviewResponse:
    return get_orchestration_review_status()


@router.get("/watchlist", response_model=WatchlistResponse)
def watchlist(
    suburb_slug: Optional[str] = Query(default=None),
    strategy: Optional[Literal["yield", "owner-occupier", "balanced"]] = Query(default=None),
    state: Optional[str] = Query(default=None, min_length=2, max_length=3),
    watch_status: Optional[Literal["active", "review", "paused"]] = Query(default=None),
    group_by: Literal["none", "state", "strategy"] = Query(default="none"),
) -> WatchlistResponse:
    return get_watchlist(
        suburb_slug=suburb_slug,
        strategy=strategy,
        state=state,
        watch_status=watch_status,
        group_by=group_by,
    )


@router.get("/watchlist/alerts", response_model=WatchlistAlertsResponse)
def watchlist_alerts(
    severity: Optional[Literal["info", "watch", "high"]] = Query(default=None),
) -> WatchlistAlertsResponse:
    return get_watchlist_alerts(severity=severity)


@router.get("/watchlist/{suburb_slug}", response_model=WatchlistDetailResponse)
def watchlist_detail(suburb_slug: str) -> WatchlistDetailResponse:
    payload = get_watchlist_detail(suburb_slug=suburb_slug)
    if payload is None:
        raise HTTPException(status_code=404, detail="Watchlist entry not found")
    return payload
