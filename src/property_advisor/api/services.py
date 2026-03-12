from __future__ import annotations

"""Internal MVP service layer used by HTTP routes."""

from datetime import datetime, timezone
from statistics import mean
from typing import Optional

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
    WatchlistResponse,
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

    return advice.model_copy(
        update={
            "inputs": AdvisoryInputs(
                query=query,
                query_type=effective_type,
                suburb_slug=suburb.slug if suburb else advice.inputs.suburb_slug,
            )
        }
    )


def get_comparables(
    query: str = PROPERTY_ADVISOR_FIXTURE.property.address,
    max_items: int = 5,
    dal: DataAccessLayer = _DAL,
) -> ComparablesResponse:
    items = dal.comparables.list_by_subject(query=query, max_items=max_items)

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
        set_quality="mvp-sample",
        query=query,
        items=items,
        summary=summary,
    )


def get_watchlist(suburb_slug: Optional[str] = None, dal: DataAccessLayer = _DAL) -> WatchlistResponse:
    return WatchlistResponse(
        generated_at=datetime.now(timezone.utc),
        mode=dal.mode,
        items=dal.watchlist.list_entries(suburb_slug=suburb_slug),
    )
