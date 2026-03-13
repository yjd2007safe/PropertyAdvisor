from __future__ import annotations

"""Internal MVP service layer used by HTTP routes."""

from datetime import datetime, timezone
from statistics import mean
from typing import Dict, List, Literal, Optional

from property_advisor.api.data_access import DataAccessLayer
from property_advisor.api.db import create_session_factory
from property_advisor.api.mock_fixtures import PROPERTY_ADVISOR_FIXTURE
from property_advisor.api.repositories import ComparableQuery, WatchlistQuery
from property_advisor.api.schemas import (
    AdvisoryInputs,
    AdvisoryInvestorSignal,
    AdvisoryMarketContext,
    AdvisoryRationaleItem,
    ComparableNarrative,
    ComparableSnapshot,
    ComparableSummary,
    ComparablesResponse,
    DataSourceStatus,
    HealthResponse,
    PropertyAdvisorResponse,
    SuburbOverviewSummary,
    SuburbsOverviewResponse,
    SummaryCard,
    WatchlistAlertsResponse,
    WatchlistDetailResponse,
    WatchlistEntry,
    WatchlistGroup,
    WatchlistResponse,
    WatchlistSummary,
    WorkflowLink,
    WorkflowSnapshot,
)

_DAL = DataAccessLayer.create(create_session_factory())


def _resolve_data_source(dal: DataAccessLayer, repository: object, domain: str) -> DataSourceStatus:
    source = getattr(repository, "last_source", "mock")
    if source not in {"mock", "postgres", "fallback_mock"}:
        source = "mock"

    if source == "postgres":
        message = f"{domain} is served from PostgreSQL."
    elif dal.mode == "postgres":
        message = f"{domain} fell back to mock data because PostgreSQL data was unavailable."
    else:
        message = f"{domain} is running in mock mode."

    return DataSourceStatus(mode=dal.mode, source=source, is_fallback=(source == "fallback_mock"), message=message)


def get_health_status() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="propertyadvisor-api",
        timestamp=datetime.now(timezone.utc),
    )


def _product_workflow_links(suburb_slug: Optional[str] = None) -> List[WorkflowLink]:
    suffix = f"?detail_slug={suburb_slug}" if suburb_slug else ""
    return [
        WorkflowLink(label="Suburb dashboard", href="/suburbs", context="Re-check suburb-level momentum and liquidity."),
        WorkflowLink(label="Property advisor", href="/advisor", context="Convert evidence into a decision recommendation."),
        WorkflowLink(label="Comparables", href="/comparables", context="Validate pricing fit and comp confidence."),
        WorkflowLink(label="Watchlist", href=f"/watchlist{suffix}", context="Track strategy alerts and action queue."),
    ]


def _workflow_snapshot(
    stage: str,
    next_step: str,
    next_href: str,
    investor_message: str,
    primary_suburb_slug: Optional[str] = None,
) -> WorkflowSnapshot:
    return WorkflowSnapshot(
        stage=stage,
        primary_suburb_slug=primary_suburb_slug,
        next_step=next_step,
        next_href=next_href,
        investor_message=investor_message,
    )


def get_suburbs_overview(dal: DataAccessLayer = _DAL) -> SuburbsOverviewResponse:
    items = dal.suburbs.list_overview()
    watchlist_slugs = {item.suburb_slug for item in dal.watchlist.list_entries(WatchlistQuery())}
    summary = SuburbOverviewSummary(
        tracked_suburbs=len(items),
        watchlist_suburbs=sum(1 for item in items if item.slug in watchlist_slugs),
        data_freshness=f"{dal.mode}-weekly" if items else "empty",
    )

    improving_count = sum(1 for item in items if item.trend == "improving")
    watching_count = sum(1 for item in items if item.trend == "watching")
    median_dom = round(mean([item.avg_days_on_market for item in items])) if items else 0

    return SuburbsOverviewResponse(
        generated_at=datetime.now(timezone.utc),
        data_source=_resolve_data_source(dal, dal.suburbs, "Suburb overview"),
        summary=summary,
        investor_signals=[
            SummaryCard(
                title="Trend balance",
                value=f"{improving_count} improving / {watching_count} watching",
                detail="Use this to calibrate how aggressive to be with pipeline expansion.",
            ),
            SummaryCard(
                title="Average liquidity",
                value=f"{median_dom} DOM",
                detail="Lower days-on-market can reduce negotiation windows.",
            ),
        ],
        workflow_links=_product_workflow_links(),
        workflow_snapshot=_workflow_snapshot(
            stage="suburb_dashboard",
            primary_suburb_slug=(items[0].slug if items else None),
            next_step="Open advisor for the highest-priority suburb and run a strategy-aligned recommendation.",
            next_href=(f"/advisor?query={items[0].slug}&query_type=slug" if items else "/advisor"),
            investor_message="Convert suburb-level momentum into a property-level go/no-go recommendation.",
        ),
        items=items,
    )


def _get_price_position(subject_price: int, low: int, high: int) -> str:
    if high == 0:
        return "insufficient_data"
    if subject_price < low:
        return "below_range"
    if subject_price > high:
        return "above_range"
    return "in_range"


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
    if not isinstance(focus_strategy, str):
        focus_strategy = None
    strategy_focus = focus_strategy or "balanced"

    comparable_items = dal.comparables.list_by_subject(ComparableQuery(query=query, max_items=5))
    prices = [item.price for item in comparable_items]
    comparable_min = min(prices) if prices else 0
    comparable_max = max(prices) if prices else 0
    position = _get_price_position(895000, comparable_min, comparable_max)

    strategy_note = f"Align recommendation with {strategy_focus} watchlist strategy assumptions."
    next_steps = list(advice.advice.next_steps)
    if strategy_note not in next_steps:
        next_steps.append(strategy_note)

    market_context = AdvisoryMarketContext(
        suburb=(suburb.name if suburb else "Southport"),
        strategy_focus=strategy_focus,
        demand_signal="Rental demand remains resilient with low vacancy in sample feed.",
        supply_signal="Listing momentum is elevated, which can soften short-term negotiation leverage.",
    )

    comparable_snapshot = ComparableSnapshot(
        sample_size=len(comparable_items),
        price_position=position,
        summary=(
            "Subject pricing sits inside the current comparable range."
            if position == "in_range"
            else "Subject pricing appears stretched relative to recent sample comparables."
        ),
    )

    rationale = [
        AdvisoryRationaleItem(
            signal="Comparable pricing fit",
            stance="supporting" if position == "in_range" else "caution",
            evidence=comparable_snapshot.summary,
        ),
        AdvisoryRationaleItem(
            signal="Demand vs supply",
            stance="neutral",
            evidence=f"Demand: {market_context.demand_signal} Supply: {market_context.supply_signal}",
        ),
        AdvisoryRationaleItem(
            signal="Strategy alignment",
            stance="supporting" if strategy_focus != "owner-occupier" else "neutral",
            evidence=f"Recommendation evaluated with {strategy_focus} strategy framing.",
        ),
    ]

    investor_signals = [
        AdvisoryInvestorSignal(
            title="Comp confidence",
            status="positive" if comparable_snapshot.sample_size >= 3 else "risk",
            detail=f"{comparable_snapshot.sample_size} nearby comparables currently available.",
        ),
        AdvisoryInvestorSignal(
            title="Supply pressure",
            status="risk",
            detail="Inventory momentum is elevated; model discount assumptions should stay conservative.",
        ),
    ]

    return advice.model_copy(
        update={
            "data_source": _resolve_data_source(dal, dal.property_advice, "Property advice"),
            "advice": advice.advice.model_copy(update={"next_steps": next_steps}),
            "market_context": market_context,
            "comparable_snapshot": comparable_snapshot,
            "decision_summary": (
                f"{advice.advice.recommendation.title()} with {advice.advice.confidence} confidence. "
                "Use comparables and watchlist alerts together before placing an offer."
            ),
            "rationale": rationale,
            "investor_signals": investor_signals,
            "summary_cards": [
                SummaryCard(
                    title="Recommendation",
                    value=advice.advice.recommendation.title(),
                    detail=f"Confidence: {advice.advice.confidence}",
                ),
                SummaryCard(
                    title="Comparable position",
                    value=comparable_snapshot.price_position.replace("_", " "),
                    detail=comparable_snapshot.summary,
                ),
                SummaryCard(
                    title="Strategy lens",
                    value=strategy_focus,
                    detail="Decision framing aligned to selected strategy.",
                ),
            ],
            "workflow_links": _product_workflow_links(suburb_slug=suburb.slug if suburb else advice.inputs.suburb_slug),
            "workflow_snapshot": _workflow_snapshot(
                stage="property_advisor",
                primary_suburb_slug=(suburb.slug if suburb else advice.inputs.suburb_slug),
                next_step="Validate price confidence in comparables before progressing offer assumptions.",
                next_href=f"/comparables?query={(suburb.slug if suburb else query)}",
                investor_message="Use this recommendation with comp evidence and watchlist alerts as one decision chain.",
            ),
            "inputs": AdvisoryInputs(
                query=query,
                query_type=effective_type,
                suburb_slug=suburb.slug if suburb else advice.inputs.suburb_slug,
            ),
        }
    )


def _build_comparable_narrative(summary: ComparableSummary, query: str) -> ComparableNarrative:
    if summary.count == 0:
        return ComparableNarrative(
            price_position="insufficient_data",
            spread_commentary="No usable comps matched the current filters.",
            investor_takeaway="Broaden radius or price bounds before making a decision.",
            action_prompt="Relax one filter and rerun the comp set.",
        )

    spread = summary.max_price - summary.min_price
    if summary.average_price < 870000:
        position = "discount"
    elif summary.average_price > 900000:
        position = "premium"
    else:
        position = "aligned"

    return ComparableNarrative(
        price_position=position,
        spread_commentary=f"Spread is {spread:,} across {summary.count} comparable sales for {query}.",
        investor_takeaway="Treat this as a negotiation anchor, not a valuation substitute.",
        action_prompt="Prioritise the two closest matches and verify renovation/land deltas.",
    )


def _build_comparable_summary_cards(summary: ComparableSummary, narrative: ComparableNarrative) -> List[SummaryCard]:
    if summary.count == 0:
        return [SummaryCard(title="Comp set", value="No matches", detail="Widen filters to restore signal quality.")]
    return [
        SummaryCard(title="Average price", value=f"${summary.average_price:,}", detail="Directional anchor for negotiation planning."),
        SummaryCard(title="Price spread", value=f"${summary.max_price - summary.min_price:,}", detail="Tighter spreads usually improve confidence."),
        SummaryCard(title="Position signal", value=narrative.price_position, detail=narrative.investor_takeaway),
    ]


def get_comparables(
    query: str = PROPERTY_ADVISOR_FIXTURE.property.address,
    max_items: int = 5,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    max_distance_km: Optional[float] = None,
    dal: DataAccessLayer = _DAL,
) -> ComparablesResponse:
    items = dal.comparables.list_by_subject(
        ComparableQuery(
            query=query,
            max_items=max_items,
            min_price=min_price,
            max_price=max_price,
            max_distance_km=max_distance_km,
        )
    )

    if not items:
        empty_summary = ComparableSummary(count=0, min_price=0, max_price=0, average_price=0)
        narrative = _build_comparable_narrative(empty_summary, query)
        return ComparablesResponse(
            data_source=_resolve_data_source(dal, dal.comparables, "Comparables"),
            subject=query,
            set_quality="empty",
            query=query,
            items=[],
            summary=empty_summary,
            narrative=narrative,
            summary_cards=_build_comparable_summary_cards(empty_summary, narrative),
            workflow_links=_product_workflow_links(),
            workflow_snapshot=_workflow_snapshot(
                stage="comparables",
                next_step="Return to advisor and apply this pricing evidence to recommendation confidence.",
                next_href=f"/advisor?query={query}&query_type=auto",
                investor_message="Comparables are a negotiation anchor that should feed recommendation confidence.",
            ),
        )

    prices = [item.price for item in items]
    summary = ComparableSummary(
        count=len(items),
        min_price=min(prices),
        max_price=max(prices),
        average_price=round(mean(prices)),
    )
    narrative = _build_comparable_narrative(summary, query)
    return ComparablesResponse(
        data_source=_resolve_data_source(dal, dal.comparables, "Comparables"),
        subject=query,
        set_quality="mvp-sample-filtered" if any(v is not None for v in [min_price, max_price, max_distance_km]) else "mvp-sample",
        query=query,
        items=items,
        summary=summary,
        narrative=narrative,
        summary_cards=_build_comparable_summary_cards(summary, narrative),
        workflow_links=_product_workflow_links(),
        workflow_snapshot=_workflow_snapshot(
            stage="comparables",
            next_step="Push this comp evidence into advisor and then confirm watchlist action status.",
            next_href=f"/advisor?query={query}&query_type=auto",
            investor_message="Treat comp pricing as evidence, then decide via advisor and action through watchlist.",
        ),
    )


def _build_watchlist_groups(group_by: Literal["none", "state", "strategy"], items: List[WatchlistEntry]) -> List[WatchlistGroup]:
    if group_by == "none":
        return []

    grouped: Dict[str, List[WatchlistEntry]] = {}
    for item in items:
        key = item.state if group_by == "state" else item.strategy
        grouped.setdefault(key, []).append(item)

    groups: List[WatchlistGroup] = []
    for key, entries in sorted(grouped.items(), key=lambda pair: pair[0]):
        groups.append(
            WatchlistGroup(
                key=key.lower(),
                label=key,
                entries=entries,
                action_required=sum(1 for entry in entries if entry.watch_status in {"review", "paused"}),
                high_alerts=sum(1 for entry in entries for alert in entry.alerts if alert.severity == "high"),
            )
        )
    return groups


def get_watchlist(
    suburb_slug: Optional[str] = None,
    strategy: Optional[str] = None,
    state: Optional[str] = None,
    watch_status: Optional[str] = None,
    group_by: Literal["none", "state", "strategy"] = "none",
    dal: DataAccessLayer = _DAL,
) -> WatchlistResponse:
    items = dal.watchlist.list_entries(
        WatchlistQuery(
            suburb_slug=suburb_slug,
            strategy=strategy,
            state=state,
            watch_status=watch_status,
        )
    )
    alert_counts = {"info": 0, "watch": 0, "high": 0}
    by_status = {"active": 0, "review": 0, "paused": 0}
    by_strategy = {"yield": 0, "owner-occupier": 0, "balanced": 0}
    action_counts = {"needs_review": 0, "ready_to_progress": 0, "on_hold": 0}

    for item in items:
        by_status[item.watch_status] += 1
        by_strategy[item.strategy] += 1
        if item.watch_status == "review":
            action_counts["needs_review"] += 1
        elif item.watch_status == "active":
            action_counts["ready_to_progress"] += 1
        else:
            action_counts["on_hold"] += 1

        for alert in item.alerts:
            alert_counts[alert.severity] += 1

    summary = WatchlistSummary(
        total_entries=len(items),
        active_entries=by_status["active"],
        grouped_view=group_by,
        alert_counts=alert_counts,
        by_status=by_status,
        by_strategy=by_strategy,
        action_counts=action_counts,
        investor_brief=(
            "Focus this week on review and paused suburbs with high-severity pricing alerts."
            if alert_counts["high"] > 0
            else "No critical alerts detected; continue weekly monitoring cadence."
        ),
    )
    return WatchlistResponse(
        generated_at=datetime.now(timezone.utc),
        mode=dal.mode,
        data_source=_resolve_data_source(dal, dal.watchlist, "Watchlist"),
        summary=summary,
        items=items,
        groups=_build_watchlist_groups(group_by, items),
        summary_cards=[
            SummaryCard(title="Action queue", value=str(action_counts["needs_review"]), detail="Suburbs needing manual review now."),
            SummaryCard(title="High-severity alerts", value=str(alert_counts["high"]), detail="Potential stop/go blockers."),
            SummaryCard(title="Ready to progress", value=str(action_counts["ready_to_progress"]), detail="Candidates for deeper due diligence."),
        ],
        workflow_links=_product_workflow_links(suburb_slug=suburb_slug),
        workflow_snapshot=_workflow_snapshot(
            stage="watchlist",
            primary_suburb_slug=(suburb_slug if suburb_slug else (items[0].suburb_slug if items else None)),
            next_step="Open advisor for a review-status suburb and confirm whether it can progress this week.",
            next_href=(f"/advisor?query={suburb_slug or items[0].suburb_slug}&query_type=slug" if (suburb_slug or items) else "/advisor"),
            investor_message="Watchlist converts insights into weekly action: review, progress, or hold.",
        ),
    )


def get_watchlist_detail(suburb_slug: str, dal: DataAccessLayer = _DAL) -> Optional[WatchlistDetailResponse]:
    item = dal.watchlist.get_entry(suburb_slug)
    if not item:
        return None
    return WatchlistDetailResponse(
        generated_at=datetime.now(timezone.utc),
        mode=dal.mode,
        data_source=_resolve_data_source(dal, dal.watchlist, "Watchlist detail"),
        item=item,
    )


def get_watchlist_alerts(severity: Optional[str] = None, dal: DataAccessLayer = _DAL) -> WatchlistAlertsResponse:
    items = dal.watchlist.list_alerts(severity=severity)
    return WatchlistAlertsResponse(
        generated_at=datetime.now(timezone.utc),
        mode=dal.mode,
        data_source=_resolve_data_source(dal, dal.watchlist, "Watchlist alerts"),
        total=len(items),
        items=items,
    )
