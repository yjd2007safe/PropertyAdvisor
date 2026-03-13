from __future__ import annotations

"""Mock response fixtures for MVP API mode."""

from property_advisor.api.schemas import (
    AdvisoryInputs,
    AdvisoryInvestorSignal,
    AdvisoryMarketContext,
    AdvisoryRationaleItem,
    ComparableItem,
    ComparableNarrative,
    ComparableSnapshot,
    ComparableSummary,
    ComparablesResponse,
    DataSourceStatus,
    PropertyAdvice,
    PropertyAdvisorResponse,
    SuburbOverviewItem,
    SuburbOverviewSummary,
    SuburbsOverviewResponse,
    SubjectProperty,
    SummaryCard,
    WatchlistAlert,
    WatchlistEntry,
    WorkflowLink,
    WorkflowSnapshot,
)

SUBURBS_OVERVIEW_FIXTURE = SuburbsOverviewResponse(
    generated_at="2026-01-07T00:00:00Z",
    data_source=DataSourceStatus(mode="mock", source="mock", is_fallback=False, message="Suburb overview is running in mock mode."),
    summary=SuburbOverviewSummary(
        tracked_suburbs=3,
        watchlist_suburbs=2,
        data_freshness="mock-weekly",
    ),
    investor_signals=[
        SummaryCard(title="Momentum mix", value="1 improving / 1 steady / 1 watching", detail="Use to balance conviction and risk."),
        SummaryCard(title="Median price band", value="$840k-$1.28m", detail="Current tracked suburbs envelope."),
    ],
    workflow_links=[
        WorkflowLink(label="Open Property Advisor", href="/advisor", context="Move from suburb signal to property decision."),
        WorkflowLink(label="Review Watchlist triage", href="/watchlist?group_by=strategy", context="Confirm strategy-level priorities."),
    ],
    workflow_snapshot=WorkflowSnapshot(
        stage="suburb_dashboard",
        primary_suburb_slug="southport-qld-4215",
        next_step="Open advisor for highest-priority suburb.",
        next_href="/advisor?query=southport-qld-4215&query_type=slug",
        investor_message="Move from suburb scan to property-level recommendation.",
    ),
    items=[
        SuburbOverviewItem(
            slug="southport-qld-4215",
            name="Southport",
            state="QLD",
            median_price=890000,
            median_rent=760,
            trend="watching",
            note="Inventory is rising; monitor negotiation leverage weekly.",
            avg_days_on_market=36,
            vacancy_rate_pct=1.3,
        ),
        SuburbOverviewItem(
            slug="burleigh-heads-qld-4220",
            name="Burleigh Heads",
            state="QLD",
            median_price=1280000,
            median_rent=910,
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
    data_source=DataSourceStatus(mode="mock", source="mock", is_fallback=False, message="Property advice is running in mock mode."),
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
    market_context=AdvisoryMarketContext(
        suburb="Southport",
        strategy_focus="balanced",
        demand_signal="Rental demand remains resilient with low vacancy in sample feed.",
        supply_signal="Listing momentum is elevated, which can soften short-term negotiation leverage.",
    ),
    comparable_snapshot=ComparableSnapshot(
        sample_size=3,
        price_position="in_range",
        summary="Subject pricing sits inside the current comparable range.",
    ),
    decision_summary="Watch with low confidence until new weekly comp evidence lands.",
    rationale=[
        AdvisoryRationaleItem(signal="Pricing fit", stance="neutral", evidence="Current ask is inside observed comp range."),
        AdvisoryRationaleItem(signal="Supply pressure", stance="caution", evidence="Inventory trend is up month-on-month in tracked suburb."),
    ],
    investor_signals=[
        AdvisoryInvestorSignal(title="Yield resilience", status="positive", detail="Rental demand remains stable in nearby stock."),
        AdvisoryInvestorSignal(title="Negotiation leverage", status="neutral", detail="DOM is improving but stock is also rising."),
    ],
    summary_cards=[
        SummaryCard(title="Recommendation", value="watch", detail="Low confidence pending fresher comparable evidence."),
        SummaryCard(title="Comparable sample", value="3", detail="More evidence needed for stronger conviction."),
    ],
    workflow_links=[
        WorkflowLink(label="Open comparables", href="/comparables?query=southport", context="Validate price position."),
        WorkflowLink(label="Open watchlist", href="/watchlist?detail_slug=southport-qld-4215", context="Check active suburb alerts."),
    ],
    workflow_snapshot=WorkflowSnapshot(
        stage="property_advisor",
        primary_suburb_slug="southport-qld-4215",
        next_step="Validate comparables before progressing.",
        next_href="/comparables?query=southport-qld-4215",
        investor_message="Recommendation confidence improves when comp and watchlist evidence align.",
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
    data_source=DataSourceStatus(mode="mock", source="mock", is_fallback=False, message="Comparables are running in mock mode."),
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
    narrative=ComparableNarrative(
        price_position="aligned",
        spread_commentary="Spread is 65,000 across 3 comparable sales for southport.",
        investor_takeaway="Treat this as a negotiation anchor, not a valuation substitute.",
        action_prompt="Prioritise the two closest matches and verify renovation/land deltas.",
    ),
    summary_cards=[
        SummaryCard(title="Average comp", value="$878,333", detail="Use as a directional anchor only."),
        SummaryCard(title="Spread", value="$65,000", detail="Lower spread generally improves confidence."),
    ],
    workflow_links=[
        WorkflowLink(label="Back to advisor", href="/advisor?query=southport-qld-4215&query_type=slug", context="Apply comp evidence to recommendation."),
        WorkflowLink(label="Open watchlist", href="/watchlist?suburb_slug=southport-qld-4215", context="Cross-check alert pressure."),
    ],
    workflow_snapshot=WorkflowSnapshot(
        stage="comparables",
        primary_suburb_slug="southport-qld-4215",
        next_step="Return to advisor with updated pricing context.",
        next_href="/advisor?query=southport-qld-4215&query_type=slug",
        investor_message="Comp evidence should directly drive recommendation confidence and watchlist action.",
    ),
)

WATCHLIST_FIXTURE = [
    WatchlistEntry(
        suburb_slug="southport-qld-4215",
        suburb_name="Southport",
        state="QLD",
        strategy="balanced",
        watch_status="review",
        notes="Track stock growth and weekly sale cadence.",
        target_buy_range_min=840000,
        target_buy_range_max=920000,
        alerts=[
            WatchlistAlert(
                severity="watch",
                title="Inventory rising",
                detail="Listings increased by 11% month-on-month.",
                metric="inventory_change_pct",
                observed_at="2026-01-07",
            ),
            WatchlistAlert(
                severity="info",
                title="Days on market easing",
                detail="Median DOM improved from 39 to 36 days.",
                metric="days_on_market",
                observed_at="2026-01-07",
            ),
        ],
    ),
    WatchlistEntry(
        suburb_slug="labrador-qld-4215",
        suburb_name="Labrador",
        state="QLD",
        strategy="yield",
        watch_status="active",
        notes="Monitor rent growth and investor demand.",
        target_buy_range_min=780000,
        target_buy_range_max=860000,
        alerts=[
            WatchlistAlert(
                severity="info",
                title="Yield holding",
                detail="Gross yield remains above 4.5% in the sample feed.",
                metric="gross_yield_pct",
                observed_at="2026-01-07",
            )
        ],
    ),
    WatchlistEntry(
        suburb_slug="burleigh-heads-qld-4220",
        suburb_name="Burleigh Heads",
        state="QLD",
        strategy="owner-occupier",
        watch_status="paused",
        notes="Paused while pricing remains above target strategy band.",
        target_buy_range_min=1180000,
        target_buy_range_max=1280000,
        alerts=[
            WatchlistAlert(
                severity="high",
                title="Pricing above target band",
                detail="Median sold price sits 6.2% above target ceiling.",
                metric="median_price_vs_target",
                observed_at="2026-01-07",
            )
        ],
    ),
]
