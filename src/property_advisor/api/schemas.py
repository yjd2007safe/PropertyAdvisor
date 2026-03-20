from __future__ import annotations

"""Typed API response models for MVP routes."""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel
from pydantic import Field


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime


class WorkflowLink(BaseModel):
    label: str
    href: str
    context: str


class SummaryCard(BaseModel):
    title: str
    value: str
    detail: str


class WorkflowSnapshot(BaseModel):
    stage: str
    primary_suburb_slug: Optional[str] = None
    next_step: str
    next_href: str
    investor_message: str




class DataSourceStatus(BaseModel):
    mode: Literal["mock", "postgres"]
    source: Literal["mock", "postgres", "fallback_mock"]
    is_fallback: bool
    message: str
    status_label: Literal["live_db", "fallback", "sample_data"] = "sample_data"
    investor_note: str = "Sample fixtures are active; use as directional guidance only."
    consistency: Literal["uniform", "mixed"] = "uniform"
    upstream_sources: Dict[str, Literal["mock", "postgres", "fallback_mock"]] = Field(default_factory=dict)
    source_breakdown: Dict[Literal["mock", "postgres", "fallback_mock"], int] = Field(default_factory=dict)
    fallback_reason: Optional[str] = None

class SuburbOverviewSummary(BaseModel):
    tracked_suburbs: int
    watchlist_suburbs: int
    data_freshness: str


class SuburbOverviewItem(BaseModel):
    slug: str
    name: str
    state: str
    median_price: int
    median_rent: int
    trend: Literal["watching", "steady", "improving"]
    note: str
    avg_days_on_market: int
    vacancy_rate_pct: float


class SuburbsOverviewResponse(BaseModel):
    generated_at: datetime
    data_source: DataSourceStatus
    summary: SuburbOverviewSummary
    items: List[SuburbOverviewItem]
    investor_signals: List[SummaryCard]
    workflow_links: List[WorkflowLink]
    workflow_snapshot: WorkflowSnapshot


class SubjectProperty(BaseModel):
    address: str
    property_type: str
    beds: int
    baths: int


class AdviceEvidenceSummarySection(BaseModel):
    name: str
    status: Literal["available", "missing", "stale", "insufficient"]
    summary: str


class AdviceEvidenceSummary(BaseModel):
    contract_version: str = "phase2.round3"
    algorithm_version: str
    freshness_status: Literal["fresh", "stale", "unknown"] = "unknown"
    required_inputs: Dict[str, bool] = Field(default_factory=dict)
    optional_inputs: Dict[str, bool] = Field(default_factory=dict)
    sections: List[AdviceEvidenceSummarySection] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    fallback_notes: List[str] = Field(default_factory=list)


class PropertyAdvice(BaseModel):
    recommendation: Literal["watch", "consider", "pass"]
    confidence: Literal["low", "medium", "high"]
    headline: str
    summary: Optional[str] = None
    stance: Optional[Literal["watch", "consider", "pass"]] = None
    rationale_bullets: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    fallback_notes: List[str] = Field(default_factory=list)
    risks: List[str]
    strengths: List[str]
    next_steps: List[str]
    evidence_summary: Optional[AdviceEvidenceSummary] = None


class AdvisoryMarketContext(BaseModel):
    suburb: str
    strategy_focus: str
    demand_signal: str
    supply_signal: str


class ComparableSnapshot(BaseModel):
    sample_size: int
    price_position: Literal["below_range", "in_range", "above_range", "insufficient_data"]
    summary: str


class AdvisoryRationaleItem(BaseModel):
    signal: str
    stance: Literal["supporting", "caution", "neutral"]
    evidence: str


class AdvisoryInvestorSignal(BaseModel):
    title: str
    status: Literal["positive", "neutral", "risk"]
    detail: str


class AdvisoryInputs(BaseModel):
    query: str
    query_type: Literal["address", "slug", "auto"]
    suburb_slug: Optional[str] = None
    contract_version: str = "phase2.round3"
    required_persisted_inputs: Dict[str, bool] = Field(default_factory=dict)
    optional_persisted_inputs: Dict[str, bool] = Field(default_factory=dict)
    missing_data_behavior: Dict[str, str] = Field(default_factory=dict)


class PropertyAdvisorResponse(BaseModel):
    data_source: DataSourceStatus
    property: SubjectProperty
    advice: PropertyAdvice
    market_context: AdvisoryMarketContext
    comparable_snapshot: ComparableSnapshot
    decision_summary: str
    rationale: List[AdvisoryRationaleItem]
    investor_signals: List[AdvisoryInvestorSignal]
    summary_cards: List[SummaryCard]
    workflow_links: List[WorkflowLink]
    workflow_snapshot: WorkflowSnapshot
    inputs: AdvisoryInputs


class ComparableItem(BaseModel):
    property_id: Optional[str] = None
    address: str
    price: int
    distance_km: float
    match_reason: str
    sold_date: str
    beds: int
    baths: int
    score: Optional[float] = None
    rationale: Dict[str, object] = Field(default_factory=dict)


class ComparableSummary(BaseModel):
    count: int
    min_price: int
    max_price: int
    average_price: int
    sample_state: Literal["empty", "low", "adequate"] = "adequate"
    quality_score: Optional[float] = None
    quality_label: Optional[str] = None
    algorithm_version: Optional[str] = None


class ComparableNarrative(BaseModel):
    price_position: Literal["discount", "aligned", "premium", "insufficient_data"]
    spread_commentary: str
    investor_takeaway: str
    action_prompt: str


class ComparablesResponse(BaseModel):
    data_source: DataSourceStatus
    subject: str
    set_quality: str
    query: str
    items: List[ComparableItem]
    summary: ComparableSummary
    narrative: ComparableNarrative
    summary_cards: List[SummaryCard]
    workflow_links: List[WorkflowLink]
    workflow_snapshot: WorkflowSnapshot


class WatchlistAlert(BaseModel):
    severity: Literal["info", "watch", "high"]
    title: str
    detail: str
    metric: str
    observed_at: str


class WatchlistEntry(BaseModel):
    suburb_slug: str
    suburb_name: str
    state: str
    strategy: Literal["yield", "owner-occupier", "balanced"]
    watch_status: Literal["active", "review", "paused"]
    notes: str
    target_buy_range_min: int
    target_buy_range_max: int
    alerts: List[WatchlistAlert]


class WatchlistSummary(BaseModel):
    total_entries: int
    active_entries: int
    grouped_view: Literal["none", "state", "strategy"]
    alert_counts: Dict[str, int]
    by_status: Dict[str, int]
    by_strategy: Dict[str, int]
    action_counts: Dict[str, int]
    investor_brief: str


class WatchlistGroup(BaseModel):
    key: str
    label: str
    entries: List[WatchlistEntry]
    action_required: int
    high_alerts: int


class WatchlistResponse(BaseModel):
    generated_at: datetime
    mode: Literal["mock", "postgres"]
    data_source: DataSourceStatus
    summary: WatchlistSummary
    items: List[WatchlistEntry]
    groups: List[WatchlistGroup]
    summary_cards: List[SummaryCard]
    workflow_links: List[WorkflowLink]
    workflow_snapshot: WorkflowSnapshot


class WatchlistDetailResponse(BaseModel):
    generated_at: datetime
    mode: Literal["mock", "postgres"]
    data_source: DataSourceStatus
    item: WatchlistEntry


class WatchlistAlertsResponse(BaseModel):
    generated_at: datetime
    mode: Literal["mock", "postgres"]
    data_source: DataSourceStatus
    total: int
    items: List[WatchlistAlert]
