from __future__ import annotations

"""Internal MVP service layer used by HTTP routes."""

import json
from datetime import datetime, timedelta, timezone
from statistics import mean
from pathlib import Path
from typing import Dict, List, Literal, Optional

from property_advisor.api.data_access import DataAccessLayer
from property_advisor.api.db import create_session_factory
from property_advisor.api.mock_fixtures import PROPERTY_ADVISOR_FIXTURE
from property_advisor.api.repositories import ComparableQuery, WatchlistQuery, WatchlistUpsertRequest
from property_advisor.api.schemas import (
    OrchestrationPlanItem,
    OrchestrationReviewResponse,
    OrchestrationReviewSummary,
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
    WatchlistActionRequest,
    WatchlistActionResponse,
    WatchlistContextSummary,
    WatchlistDetailResponse,
    WatchlistEntry,
    WatchlistGroup,
    WatchlistResponse,
    WatchlistSummary,
    WorkflowLink,
    WorkflowSnapshot,
)



_DAL = DataAccessLayer.create(create_session_factory())

_ORCHESTRATION_EVENT_TYPES = {
    "completed",
    "blocked",
    "interrupted",
    "ready_for_evaluation",
    "evaluation_failed",
    "delivered",
    "evaluated",
}

_ORCHESTRATION_POLICY: dict[str, dict[str, object]] = {
    "ready_for_evaluation": {"priority": 100, "action": "notify_and_pause_for_review", "auto_continue": False, "requires_human_review": True, "bucket": "review"},
    "evaluation_failed": {"priority": 90, "action": "notify_and_resume_fix", "auto_continue": True, "requires_human_review": False, "bucket": "recovery"},
    "blocked": {"priority": 80, "action": "notify_and_wait_on_blocker", "auto_continue": False, "requires_human_review": False, "bucket": "blocked"},
    "interrupted": {"priority": 70, "action": "notify_and_resume", "auto_continue": True, "requires_human_review": False, "bucket": "recovery"},
    "completed": {"priority": 60, "action": "notify_progress_and_continue", "auto_continue": True, "requires_human_review": False, "bucket": "progress"},
    "evaluated": {"priority": 50, "action": "notify_progress_and_continue", "auto_continue": True, "requires_human_review": False, "bucket": "progress"},
    "delivered": {"priority": 40, "action": "notify_closure", "auto_continue": False, "requires_human_review": False, "bucket": "closure"},
}

_DEFAULT_ORCHESTRATION_POLICY = {"priority": 10, "action": "notify_only", "auto_continue": False, "requires_human_review": False, "bucket": "other"}

_ORCHESTRATION_STRATEGY_SUMMARY = {
    "notify_and_pause_for_review": "通知关键进展，并暂停等待人工复核。",
    "notify_and_resume_fix": "通知失败原因，并自动继续修复链路。",
    "notify_and_wait_on_blocker": "通知阻塞点，等待外部条件解除。",
    "notify_and_resume": "通知中断原因，并尝试自动恢复执行。",
    "notify_progress_and_continue": "反馈阶段性进展，并在已授权前提下继续推进下一步。",
    "notify_closure": "通知该轮结果已正式交付闭环。",
    "notify_only": "仅通知，不自动推进。",
}


def _build_orchestration_plan(record: dict[str, object]) -> dict[str, object]:
    event_type = str(record.get("event_type") or "")
    policy = dict(_DEFAULT_ORCHESTRATION_POLICY)
    policy.update(_ORCHESTRATION_POLICY.get(event_type, {}))
    action = str(policy["action"])
    return {
        "event_id": record.get("event_id"),
        "event_type": event_type,
        "queued_at": record.get("queued_at"),
        "created_at": record.get("created_at"),
        "session_key": record.get("session_key"),
        "message": record.get("message"),
        "priority": int(policy["priority"]),
        "bucket": str(policy["bucket"]),
        "action": action,
        "auto_continue": bool(policy["auto_continue"]),
        "requires_human_review": bool(policy["requires_human_review"]),
        "strategy_summary": _ORCHESTRATION_STRATEGY_SUMMARY[action],
    }


def _build_orchestration_queue(records: list[dict[str, object]]) -> list[dict[str, object]]:
    plans = [_build_orchestration_plan(record) for record in records]
    plans.sort(key=lambda plan: (-int(plan["priority"]), str(plan.get("queued_at") or ""), str(plan.get("created_at") or ""), str(plan.get("event_id") or "")))
    return plans


def _read_source(repository: object) -> Literal["mock", "postgres", "fallback_mock"]:
    source = getattr(repository, "last_source", "mock")
    if source not in {"mock", "postgres", "fallback_mock"}:
        return "mock"
    return source


def _resolve_data_source(
    dal: DataAccessLayer,
    repository: object,
    domain: str,
    upstream_repositories: Optional[Dict[str, object]] = None,
) -> DataSourceStatus:
    source = _read_source(repository)
    fallback_reason = getattr(repository, "last_fallback_reason", None)
    upstream_sources = {name: _read_source(repo) for name, repo in (upstream_repositories or {}).items()}
    source_breakdown = {"mock": 0, "postgres": 0, "fallback_mock": 0}
    source_breakdown[source] += 1
    for upstream_source in upstream_sources.values():
        source_breakdown[upstream_source] += 1
    all_sources = {key for key, count in source_breakdown.items() if count > 0}
    consistency = "uniform" if len(all_sources) <= 1 else "mixed"

    if source == "postgres":
        primary_message = f"{domain} is DB-backed from PostgreSQL."
        status_label = "live_db"
        investor_note = "Live DB feed available for this view."
    elif source == "fallback_mock":
        primary_message = f"{domain} is using fallback mock payloads because PostgreSQL data was unavailable."
        status_label = "fallback"
        investor_note = "Fallback sample payloads are shown while DB reads recover."
    else:
        primary_message = f"{domain} is using mock fixtures."
        status_label = "sample_data"
        investor_note = "Sample fixtures are active; use as directional guidance only."

    if upstream_sources:
        details = ", ".join(f"{name}:{value}" for name, value in sorted(upstream_sources.items()))
        primary_message = f"{primary_message} Upstream sources -> {details}."

    if fallback_reason:
        primary_message = f"{primary_message} Fallback reason: {fallback_reason}"

    if consistency == "mixed":
        primary_message = f"{primary_message} Response uses a mixed-source chain."

    return DataSourceStatus(
        mode=dal.mode,
        source=source,
        is_fallback=(source == "fallback_mock"),
        message=primary_message,
        status_label=status_label,
        investor_note=(
            f"{investor_note} Mixed-source response detected across dependencies."
            if consistency == "mixed"
            else investor_note
        ),
        consistency=consistency,
        upstream_sources=upstream_sources,
        source_breakdown=source_breakdown,
        fallback_reason=fallback_reason,
    )


def get_health_status() -> HealthResponse:
    return HealthResponse(
        status="ok",
        service="propertyadvisor-api",
        timestamp=datetime.now(timezone.utc),
    )


def _product_workflow_links(suburb_slug: Optional[str] = None, source_surface: Optional[str] = None) -> List[WorkflowLink]:
    suffix = f"?detail_slug={suburb_slug}" if suburb_slug else ""
    save_href = "/watchlist"
    if suburb_slug and source_surface:
        save_href = f"/watchlist/actions?suburb_slug={suburb_slug}&source_surface={source_surface}"
    return [
        WorkflowLink(label="Suburb dashboard", href="/suburbs", context="Re-check suburb-level momentum and liquidity."),
        WorkflowLink(label="Property advisor", href="/advisor", context="Convert evidence into a decision recommendation."),
        WorkflowLink(label="Comparables", href="/comparables", context="Validate pricing fit and comp confidence."),
        WorkflowLink(label="Watchlist", href=f"/watchlist{suffix}", context="Track strategy alerts and action queue."),
        WorkflowLink(label="Save to watchlist", href=save_href, context="Capture this suburb into watchlist action review."),
        WorkflowLink(label="Orchestration review", href="/orchestration", context="Check runtime review blockers, freshness, and operator actions."),
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
        data_source=_resolve_data_source(
            dal,
            dal.suburbs,
            "Suburb overview",
            upstream_repositories={"watchlist": dal.watchlist},
        ),
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
        workflow_links=_product_workflow_links(source_surface="suburbs"),
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


def _build_advisory_input_contract(
    query: str,
    effective_type: str,
    suburb_slug: Optional[str],
    comparable_count: int,
) -> AdvisoryInputs:
    required_inputs = {
        "subject_property_identity": bool(query),
        "persisted_property_record": bool(suburb_slug or effective_type in {"address", "slug"}),
    }
    optional_inputs = {
        "persisted_comparable_sales": comparable_count > 0,
        "persisted_suburb_metrics": suburb_slug is not None,
        "persisted_watchlist_context": True,
    }
    missing_behavior = {
        "required": "If required persisted identity is missing, return baseline watch guidance rather than synthesizing unsupported advice.",
        "persisted_comparable_sales": (
            "If no comparable candidates pass selection rules, advice remains available but confidence and comparable snapshot move to explicit insufficient-data semantics."
        ),
        "persisted_suburb_metrics": "If suburb metrics are missing, retain property advice output and use baseline demand/supply wording.",
        "persisted_watchlist_context": "If watchlist context is missing, omit strategy-specific reinforcement and keep a balanced default lens.",
    }
    return AdvisoryInputs(
        query=query,
        query_type=effective_type,
        suburb_slug=suburb_slug,
        contract_version="phase2.round3",
        required_persisted_inputs=required_inputs,
        optional_persisted_inputs=optional_inputs,
        missing_data_behavior=missing_behavior,
    )


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
    subject_price = 895000
    position = _get_price_position(subject_price, comparable_min, comparable_max)

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
            else (
                "No matched comparables available yet; confidence is constrained by sample depth."
                if position == "insufficient_data"
                else "Subject pricing appears stretched relative to recent sample comparables."
            )
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

    advisory_inputs = _build_advisory_input_contract(
        query=query,
        effective_type=effective_type,
        suburb_slug=(suburb.slug if suburb else advice.inputs.suburb_slug),
        comparable_count=len(comparable_items),
    )
    use_persisted_snapshot = _read_source(dal.property_advice) == "postgres" and advice.advice.evidence_summary is not None

    return advice.model_copy(
        update={
            "data_source": _resolve_data_source(
                dal,
                dal.property_advice,
                "Property advice",
                upstream_repositories={"suburbs": dal.suburbs, "comparables": dal.comparables, "watchlist": dal.watchlist},
            ),
            "advice": advice.advice.model_copy(update={"next_steps": next_steps}),
            "market_context": (advice.market_context if use_persisted_snapshot else market_context),
            "comparable_snapshot": (advice.comparable_snapshot if use_persisted_snapshot else comparable_snapshot),
            "decision_summary": (
                advice.decision_summary
                if use_persisted_snapshot
                else (
                    f"{advice.advice.recommendation.title()} with {advice.advice.confidence} confidence. "
                    f"Subject price anchor ${subject_price:,}; comp range ${comparable_min:,}-${comparable_max:,}. "
                    "Use comparables and watchlist alerts together before placing an offer."
                )
            ),
            "rationale": (advice.rationale if use_persisted_snapshot and advice.rationale else rationale),
            "investor_signals": (advice.investor_signals if use_persisted_snapshot and advice.investor_signals else investor_signals),
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
            "workflow_links": _product_workflow_links(suburb_slug=suburb.slug if suburb else advice.inputs.suburb_slug, source_surface="advisor"),
            "workflow_snapshot": _workflow_snapshot(
                stage="property_advisor",
                primary_suburb_slug=(suburb.slug if suburb else advice.inputs.suburb_slug),
                next_step="Validate price confidence in comparables before progressing offer assumptions.",
                next_href=f"/comparables?query={(suburb.slug if suburb else query)}",
                investor_message="Use this recommendation with comp evidence and watchlist alerts as one decision chain.",
            ),
            "inputs": advisory_inputs,
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
    if summary.sample_state == "low":
        return ComparableNarrative(
            price_position="aligned",
            spread_commentary=f"Only {summary.count} persisted sale candidate(s) matched for {query}; treat the range as directional only.",
            investor_takeaway="Low sample depth means negotiation anchors are usable, but conviction should stay conservative.",
            action_prompt="Validate the closest sale manually and rerun when fresher evidence lands.",
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
    if summary.sample_state == "low":
        return [
            SummaryCard(title="Comp set", value="Low sample", detail="Persisted candidate rules found fewer than 3 matches."),
            SummaryCard(title="Average price", value=f"${summary.average_price:,}", detail="Directional only until more evidence is available."),
            SummaryCard(title="Action", value="Validate manually", detail=narrative.action_prompt),
        ]
    return [
        SummaryCard(title="Average price", value=f"${summary.average_price:,}", detail="Directional anchor for negotiation planning."),
        SummaryCard(title="Price spread", value=f"${summary.max_price - summary.min_price:,}", detail="Tighter spreads usually improve confidence."),
        SummaryCard(title="Position signal", value=narrative.price_position, detail=narrative.investor_takeaway),
    ]



def _resolve_comparable_set_quality(
    source: Literal["mock", "postgres", "fallback_mock"],
    min_price: Optional[int],
    max_price: Optional[int],
    max_distance_km: Optional[float],
) -> str:
    filtered = any(value is not None for value in [min_price, max_price, max_distance_km])
    if source == "postgres":
        return "db-backed-filtered" if filtered else "db-backed"
    return "mvp-sample-filtered" if filtered else "mvp-sample"

def get_comparables(
    query: str = PROPERTY_ADVISOR_FIXTURE.property.address,
    max_items: int = 5,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
    max_distance_km: Optional[float] = None,
    dal: DataAccessLayer = _DAL,
) -> ComparablesResponse:
    criteria = ComparableQuery(
        query=query,
        max_items=max_items,
        min_price=min_price,
        max_price=max_price,
        max_distance_km=max_distance_km,
    )
    latest_set = dal.comparables.get_latest_set(criteria)
    generated_set = latest_set or (
        dal.comparables.generate_comparable_set(criteria) if _read_source(dal.comparables) != "mock" else None
    )
    items = generated_set.items if generated_set is not None else dal.comparables.list_by_subject(criteria)

    if not items:
        empty_summary = ComparableSummary(
            count=0,
            min_price=0,
            max_price=0,
            average_price=0,
            sample_state="empty",
            quality_score=(generated_set.quality_score if generated_set is not None else None),
            quality_label=(generated_set.quality_label if generated_set is not None else None),
            algorithm_version=(generated_set.algorithm_version if generated_set is not None else None),
        )
        narrative = _build_comparable_narrative(empty_summary, query)
        return ComparablesResponse(
            data_source=_resolve_data_source(dal, dal.comparables, "Comparables", upstream_repositories={"suburbs": dal.suburbs}),
            subject=query,
            set_quality="empty",
            query=query,
            items=[],
            summary=empty_summary,
            narrative=narrative,
            summary_cards=_build_comparable_summary_cards(empty_summary, narrative),
            workflow_links=_product_workflow_links(suburb_slug=query, source_surface="comparables"),
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
        sample_state=("low" if len(items) < 3 else "adequate"),
        quality_score=(generated_set.quality_score if generated_set is not None else None),
        quality_label=(generated_set.quality_label if generated_set is not None else None),
        algorithm_version=(generated_set.algorithm_version if generated_set is not None else None),
    )
    narrative = _build_comparable_narrative(summary, query)
    return ComparablesResponse(
        data_source=_resolve_data_source(dal, dal.comparables, "Comparables", upstream_repositories={"suburbs": dal.suburbs}),
        subject=query,
        set_quality=(
            f"persisted-{generated_set.quality_label}"
            if latest_set is not None
            else (
                f"generated-{generated_set.quality_label}"
                if generated_set is not None and _read_source(dal.comparables) == "postgres"
                else (
                    "db-backed-low-sample"
                    if _read_source(dal.comparables) == "postgres" and summary.sample_state == "low"
                    else _resolve_comparable_set_quality(
                        _read_source(dal.comparables),
                        min_price=min_price,
                        max_price=max_price,
                        max_distance_km=max_distance_km,
                    )
                )
            )
        ),
        query=query,
        items=items,
        summary=summary,
        narrative=narrative,
        summary_cards=_build_comparable_summary_cards(summary, narrative),
        workflow_links=_product_workflow_links(suburb_slug=query, source_surface="comparables"),
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

    enriched_items = [_enrich_watchlist_entry_context(item, dal=dal) for item in items]

    summary = WatchlistSummary(
        total_entries=len(enriched_items),
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
        data_source=_resolve_data_source(dal, dal.watchlist, "Watchlist", upstream_repositories={"suburbs": dal.suburbs}),
        summary=summary,
        items=enriched_items,
        groups=_build_watchlist_groups(group_by, enriched_items),
        summary_cards=[
            SummaryCard(title="Action queue", value=str(action_counts["needs_review"]), detail="Suburbs needing manual review now."),
            SummaryCard(title="High-severity alerts", value=str(alert_counts["high"]), detail="Potential stop/go blockers."),
            SummaryCard(title="Ready to progress", value=str(action_counts["ready_to_progress"]), detail="Candidates for deeper due diligence."),
        ],
        workflow_links=_product_workflow_links(suburb_slug=suburb_slug, source_surface="watchlist"),
        workflow_snapshot=_workflow_snapshot(
            stage="watchlist",
            primary_suburb_slug=(suburb_slug if suburb_slug else (enriched_items[0].suburb_slug if enriched_items else None)),
            next_step="Open advisor for a review-status suburb and confirm whether it can progress this week.",
            next_href=(f"/advisor?query={suburb_slug or enriched_items[0].suburb_slug}&query_type=slug" if (suburb_slug or enriched_items) else "/advisor"),
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
        data_source=_resolve_data_source(dal, dal.watchlist, "Watchlist detail", upstream_repositories={"suburbs": dal.suburbs}),
        item=_enrich_watchlist_entry_context(item, dal=dal),
    )


def _enrich_watchlist_entry_context(item: WatchlistEntry, dal: DataAccessLayer = _DAL) -> WatchlistEntry:
    advice = get_property_advice(query=item.suburb_slug, query_type="slug", dal=dal)
    comparables = get_comparables(query=item.suburb_slug, max_items=5, dal=dal)
    orchestration = get_orchestration_review_status(limit=3)
    return item.model_copy(
        update={
            "latest_context": WatchlistContextSummary(
                advisory=f"{advice.advice.recommendation} ({advice.advice.confidence}) — {advice.advice.headline}",
                comparables=f"{comparables.summary.count} comps, avg ${comparables.summary.average_price:,}, state={comparables.summary.sample_state}",
                orchestration=f"{orchestration.summary.current_state}; review_required={orchestration.summary.review_required_count}",
                updated_at=datetime.now(timezone.utc),
            )
        }
    )


def upsert_watchlist_action(payload: WatchlistActionRequest, dal: DataAccessLayer = _DAL) -> WatchlistActionResponse:
    action, item = dal.watchlist.upsert_entry(
        WatchlistUpsertRequest(
            suburb_slug=payload.suburb_slug,
            source_surface=payload.source_surface,
            strategy=payload.strategy,
            watch_status=payload.watch_status,
            notes=payload.notes,
        )
    )
    return WatchlistActionResponse(
        generated_at=datetime.now(timezone.utc),
        mode=dal.mode,
        data_source=_resolve_data_source(dal, dal.watchlist, "Watchlist action", upstream_repositories={"suburbs": dal.suburbs}),
        action=action,
        item=_enrich_watchlist_entry_context(item, dal=dal),
    )


def get_watchlist_alerts(severity: Optional[str] = None, dal: DataAccessLayer = _DAL) -> WatchlistAlertsResponse:
    items = dal.watchlist.list_alerts(severity=severity)
    return WatchlistAlertsResponse(
        generated_at=datetime.now(timezone.utc),
        mode=dal.mode,
        data_source=_resolve_data_source(dal, dal.watchlist, "Watchlist alerts", upstream_repositories={"suburbs": dal.suburbs}),
        total=len(items),
        items=items,
    )


def _parse_timestamp(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def get_orchestration_review_status(
    *,
    artifact_path: Path = Path(".dev_pipeline/notifications"),
    limit: int = 10,
) -> OrchestrationReviewResponse:
    state_path = artifact_path / "bridge_state.json"
    state_payload: dict[str, object] = {}
    if state_path.exists():
        loaded = json.loads(state_path.read_text())
        if isinstance(loaded, dict):
            state_payload = loaded

    delivered_state = state_payload.get("delivered_event_ids", {})
    queued_state = state_payload.get("queued_event_ids", {})
    if not isinstance(delivered_state, dict):
        delivered_state = {}
    if not isinstance(queued_state, dict):
        queued_state = {}

    records: list[dict[str, object]] = []
    if artifact_path.exists():
        for path in sorted(artifact_path.glob("*.json")):
            if path == state_path:
                continue
            artifact = json.loads(path.read_text())
            if not isinstance(artifact, dict):
                continue
            event_type = str(artifact.get("event_type") or "")
            event_id = str(artifact.get("event_id") or "")
            if not event_id or event_type not in _ORCHESTRATION_EVENT_TYPES or event_id in delivered_state:
                continue
            records.append(
                {
                    "event_id": event_id,
                    "event_type": event_type,
                    "session_key": (artifact.get("origin") or {}).get("session_key") if isinstance(artifact.get("origin"), dict) else None,
                    "message": str(artifact.get("summary") or ""),
                    "created_at": artifact.get("created_at"),
                    "queued_at": queued_state.get(event_id),
                }
            )

    plans = _build_orchestration_queue(records)
    if limit > 0:
        plans = plans[:limit]

    review_required_count = sum(1 for plan in plans if plan.get("requires_human_review"))
    auto_continue_count = sum(1 for plan in plans if plan.get("auto_continue"))
    queued_count = sum(1 for plan in plans if plan.get("queued_at"))

    latest_event_at = max(
        (
            ts
            for ts in (_parse_timestamp(plan.get("queued_at")) or _parse_timestamp(plan.get("created_at")) for plan in plans)
            if ts is not None
        ),
        default=None,
    )

    now = datetime.now(timezone.utc)
    if latest_event_at is None:
        freshness = "empty"
    elif now - latest_event_at <= timedelta(hours=24):
        freshness = "fresh"
    else:
        freshness = "stale"

    if review_required_count > 0:
        current_state = "awaiting_review"
        next_action = "Review the highest-priority orchestration event and acknowledge delivery before continuing."
    elif plans:
        current_state = "auto_progressing"
        next_action = "No manual review blocker is active; monitor auto-progress and queued delivery records."
    else:
        current_state = "idle"
        next_action = "No pending orchestration events. Wait for the next runtime notification cycle."

    return OrchestrationReviewResponse(
        summary=OrchestrationReviewSummary(
            current_state=current_state,
            latest_event_at=(latest_event_at.isoformat() if latest_event_at else None),
            generated_at=now,
            freshness=freshness,
            review_needed=review_required_count > 0,
            review_required_count=review_required_count,
            auto_continue_count=auto_continue_count,
            queued_count=queued_count,
            pending_count=len(plans),
            next_action=next_action,
        ),
        plans=[
            OrchestrationPlanItem(
                event_id=str(plan.get("event_id") or ""),
                event_type=str(plan.get("event_type") or ""),
                bucket=str(plan.get("bucket") or "other"),
                action=str(plan.get("action") or "notify_only"),
                requires_human_review=bool(plan.get("requires_human_review")),
                auto_continue=bool(plan.get("auto_continue")),
                created_at=plan.get("created_at"),
                queued_at=plan.get("queued_at"),
                strategy_summary=str(plan.get("strategy_summary") or ""),
                message=plan.get("message"),
            )
            for plan in plans
        ],
    )
