from __future__ import annotations

"""HTTP routes for the PropertyAdvisor MVP API."""

from fastapi import APIRouter, Query

from property_advisor.api.schemas import (
    ComparablesResponse,
    HealthResponse,
    PropertyAdvisorResponse,
    SuburbsOverviewResponse,
)
from property_advisor.api.services import (
    get_comparables,
    get_health_status,
    get_property_advice,
    get_suburbs_overview,
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
) -> PropertyAdvisorResponse:
    return get_property_advice(query=query)


@router.get("/comparables", response_model=ComparablesResponse)
def comparables(
    query: str = Query(default="southport", min_length=3),
) -> ComparablesResponse:
    return get_comparables(query=query)
