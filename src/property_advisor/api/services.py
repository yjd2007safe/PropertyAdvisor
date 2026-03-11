from __future__ import annotations

"""Internal MVP service layer used by HTTP routes."""

from datetime import datetime, timezone
from statistics import mean

from property_advisor.api.db import create_session_factory
from property_advisor.api.mock_fixtures import PROPERTY_ADVISOR_FIXTURE
from property_advisor.api.repositories import (
    RepositoryContainer,
    create_repository_container,
)
from property_advisor.api.schemas import (
    AdvisoryInputs,
    ComparableSummary,
    ComparablesResponse,
    HealthResponse,
    PropertyAdvisorResponse,
    SuburbOverviewSummary,
    SuburbsOverviewResponse,
)

_REPOS = create_repository_container(create_session_factory())


def get_health_status() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="propertyadvisor-api",
        timestamp=datetime.now(timezone.utc),
    )


def get_suburbs_overview(repos: RepositoryContainer = _REPOS) -> SuburbsOverviewResponse:
    items = repos.suburbs.list_overview()
    summary = SuburbOverviewSummary(
        tracked_suburbs=len(items),
        watchlist_suburbs=sum(1 for item in items if item.trend == "watching"),
        data_freshness="mock-weekly" if items else "empty",
    )
    return SuburbsOverviewResponse(
        generated_at=datetime.now(timezone.utc),
        summary=summary,
        items=items,
    )


def get_property_advice(
    query: str = PROPERTY_ADVISOR_FIXTURE.property.address,
    repos: RepositoryContainer = _REPOS,
) -> PropertyAdvisorResponse:
    advice = repos.property_advice.get_by_address_or_slug(query) or PROPERTY_ADVISOR_FIXTURE
    query_type = "slug" if "-" in query and "," not in query else "address"
    suburb = repos.suburbs.get_by_slug(query) if query_type == "slug" else None

    return advice.model_copy(
        update={
            "inputs": AdvisoryInputs(
                query=query,
                query_type=query_type,
                suburb_slug=suburb.slug if suburb else advice.inputs.suburb_slug,
            )
        }
    )


def get_comparables(
    query: str = PROPERTY_ADVISOR_FIXTURE.property.address,
    repos: RepositoryContainer = _REPOS,
) -> ComparablesResponse:
    items = repos.comparables.list_by_subject(query)
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
