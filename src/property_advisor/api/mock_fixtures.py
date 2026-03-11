from __future__ import annotations

"""Lightweight mock fixtures used by MVP API services."""

from property_advisor.api.schemas import (
    ComparableItem,
    ComparablesResponse,
    PropertyAdvice,
    PropertyAdvisorResponse,
    SubjectProperty,
    SuburbOverviewItem,
    SuburbOverviewSummary,
    SuburbsOverviewResponse,
)

SUBURBS_OVERVIEW_FIXTURE = SuburbsOverviewResponse(
    generated_at="2026-01-10T00:00:00Z",
    summary=SuburbOverviewSummary(
        tracked_suburbs=3,
        watchlist_suburbs=2,
        data_freshness="mock-weekly",
    ),
    items=[
        SuburbOverviewItem(
            slug="southport-qld-4215",
            name="Southport",
            state="QLD",
            median_price=895000,
            median_rent=780,
            trend="watching",
            note="Large stock turnover keeps this suburb in watch mode.",
        ),
        SuburbOverviewItem(
            slug="burleigh-heads-qld-4220",
            name="Burleigh Heads",
            state="QLD",
            median_price=1350000,
            median_rent=950,
            trend="steady",
            note="Premium demand is stable with low days on market.",
        ),
        SuburbOverviewItem(
            slug="labrador-qld-4215",
            name="Labrador",
            state="QLD",
            median_price=840000,
            median_rent=740,
            trend="improving",
            note="Rent growth is improving investor yield narrative.",
        ),
    ],
)

PROPERTY_ADVISOR_FIXTURE = PropertyAdvisorResponse(
    property=SubjectProperty(
        address="12 Example Avenue, Southport QLD 4215",
        property_type="house",
        beds=4,
        baths=2,
    ),
    advice=PropertyAdvice(
        recommendation="watch",
        confidence="low",
        headline="Price looks broadly in range, but comparable confidence is still limited.",
        next_steps=[
            "Confirm latest listing updates and vendor guidance.",
            "Validate land and renovation differences against top comparables.",
            "Re-run recommendation when fresh weekly sales are ingested.",
        ],
    ),
)

COMPARABLES_FIXTURE = ComparablesResponse(
    subject="12 Example Avenue, Southport QLD 4215",
    set_quality="mvp-sample",
    items=[
        ComparableItem(
            address="8 Nearby Street, Southport QLD 4215",
            price=910000,
            distance_km=0.6,
            match_reason="Similar bed/bath count and recent sale date.",
        ),
        ComparableItem(
            address="17 Sample Road, Southport QLD 4215",
            price=875000,
            distance_km=0.9,
            match_reason="Comparable land profile with slightly lower finish level.",
        ),
        ComparableItem(
            address="31 Harbour View, Southport QLD 4215",
            price=940000,
            distance_km=1.2,
            match_reason="Renovated presentation provides upper-bound pricing context.",
        ),
    ],
)
