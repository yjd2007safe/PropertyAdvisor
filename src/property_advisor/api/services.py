from __future__ import annotations

"""Internal MVP service layer used by HTTP routes."""

from datetime import datetime, timezone

from property_advisor.api.mock_fixtures import (
    COMPARABLES_FIXTURE,
    PROPERTY_ADVISOR_FIXTURE,
    SUBURBS_OVERVIEW_FIXTURE,
)
from property_advisor.api.schemas import (
    ComparablesResponse,
    HealthResponse,
    PropertyAdvisorResponse,
    SuburbsOverviewResponse,
)


def get_health_status() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="propertyadvisor-api",
        timestamp=datetime.now(timezone.utc),
    )


def get_suburbs_overview() -> SuburbsOverviewResponse:
    return SUBURBS_OVERVIEW_FIXTURE.model_copy(
        update={"generated_at": datetime.now(timezone.utc)}
    )


def get_property_advice() -> PropertyAdvisorResponse:
    return PROPERTY_ADVISOR_FIXTURE


def get_comparables() -> ComparablesResponse:
    return COMPARABLES_FIXTURE
