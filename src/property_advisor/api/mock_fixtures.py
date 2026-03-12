from __future__ import annotations

"""Lightweight mock fixtures used by MVP API services."""

from property_advisor.api.schemas import (
    AdvisoryInputs,
    ComparableItem,
    ComparableSummary,
    ComparablesResponse,
    PropertyAdvice,
    PropertyAdvisorResponse,
    SubjectProperty,
    SuburbOverviewItem,
    SuburbOverviewSummary,
    SuburbsOverviewResponse,
    WatchlistAlert,
    WatchlistEntry,
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
            avg_days_on_market=36,
            vacancy_rate_pct=1.5,
        ),
        SuburbOverviewItem(
            slug="burleigh-heads-qld-4220",
            name="Burleigh Heads",
            state="QLD",
            median_price=1350000,
            median_rent=950,
            trend="steady",
            note="Premium demand is stable with low days on market.",
            avg_days_on_market=24,
            vacancy_rate_pct=1.0,
        ),
        SuburbOverviewItem(
            slug="labrador-qld-4215",
            name="Labrador",
            state="QLD",
            median_price=840000,
            median_rent=740,
            trend="improving",
            note="Rent growth is improving investor yield narrative.",
            avg_days_on_market=29,
            vacancy_rate_pct=1.2,
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
        risks=[
            "Recent suburb stock increase can pressure short-term prices.",
            "Comparable set contains a wider spread than preferred.",
        ],
        strengths=[
            "Rent demand remains stable for family homes in this pocket.",
            "Property configuration aligns with active buyer demand.",
        ],
        next_steps=[
            "Confirm latest listing updates and vendor guidance.",
            "Validate land and renovation differences against top comparables.",
            "Re-run recommendation when fresh weekly sales are ingested.",
        ],
    ),
    inputs=AdvisoryInputs(
        query="12 Example Avenue, Southport QLD 4215",
        query_type="address",
        suburb_slug="southport-qld-4215",
    ),
)

COMPARABLE_ITEMS_FIXTURE = [
    ComparableItem(
        address="8 Nearby Street, Southport QLD 4215",
        price=910000,
        distance_km=0.6,
        match_reason="Similar bed/bath count and recent sale date.",
        sold_date="2026-01-04",
        beds=4,
        baths=2,
    ),
    ComparableItem(
        address="16 Lagoon Parade, Southport QLD 4215",
        price=880000,
        distance_km=0.9,
        match_reason="Comparable land size and renovation profile.",
        sold_date="2025-12-20",
        beds=4,
        baths=2,
    ),
    ComparableItem(
        address="5 Harbour Lane, Labrador QLD 4215",
        price=845000,
        distance_km=1.8,
        match_reason="Nearby fallback match with aligned rental demand profile.",
        sold_date="2025-12-14",
        beds=3,
        baths=2,
    ),
]

COMPARABLES_FIXTURE = ComparablesResponse(
    subject="12 Example Avenue, Southport QLD 4215",
    set_quality="mvp-sample",
    query="southport",
    items=COMPARABLE_ITEMS_FIXTURE,
    summary=ComparableSummary(
        count=3,
        min_price=845000,
        max_price=910000,
        average_price=878333,
    ),
)

WATCHLIST_FIXTURE = [
    WatchlistEntry(
        suburb_slug="southport-qld-4215",
        suburb_name="Southport",
        strategy="balanced",
        notes="Track stock growth and weekly sale cadence.",
        alerts=[
            WatchlistAlert(
                severity="watch",
                title="Inventory rising",
                detail="Listings increased by 11% month-on-month.",
            )
        ],
    ),
    WatchlistEntry(
        suburb_slug="labrador-qld-4215",
        suburb_name="Labrador",
        strategy="yield",
        notes="Monitor rent growth and investor demand.",
        alerts=[
            WatchlistAlert(
                severity="info",
                title="Yield holding",
                detail="Gross yield remains above 4.5% in the sample feed.",
            )
        ],
    ),
]
