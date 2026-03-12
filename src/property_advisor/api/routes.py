from __future__ import annotations

"""HTTP routes for the PropertyAdvisor MVP API."""

from typing import Literal, Optional

from fastapi import APIRouter, Query

from property_advisor.api.schemas import (
    ComparablesResponse,
    HealthResponse,
    PropertyAdvisorResponse,
    SuburbsOverviewResponse,
    WatchlistResponse,
)
from property_advisor.api.services import (
    get_comparables,
    get_health_status,
    get_property_advice,
    get_suburbs_overview,
    get_watchlist,
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
) -> PropertyAdvisorResponse:
    return get_property_advice(query=query, query_type=query_type)


@router.get("/comparables", response_model=ComparablesResponse)
def comparables(
    query: str = Query(default="southport", min_length=3),
    max_items: int = Query(default=5, ge=1, le=20),
) -> ComparablesResponse:
    return get_comparables(query=query, max_items=max_items)


@router.get("/watchlist", response_model=WatchlistResponse)
def watchlist(suburb_slug: Optional[str] = Query(default=None)) -> WatchlistResponse:
    return get_watchlist(suburb_slug=suburb_slug)
