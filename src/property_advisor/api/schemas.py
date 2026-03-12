from __future__ import annotations

"""Typed API response models for MVP routes."""

from datetime import datetime
from typing import Dict, List, Literal, Optional

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str
    service: str
    timestamp: datetime


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
    summary: SuburbOverviewSummary
    items: List[SuburbOverviewItem]


class SubjectProperty(BaseModel):
    address: str
    property_type: str
    beds: int
    baths: int


class PropertyAdvice(BaseModel):
    recommendation: Literal["watch", "consider", "pass"]
    confidence: Literal["low", "medium", "high"]
    headline: str
    risks: List[str]
    strengths: List[str]
    next_steps: List[str]


class AdvisoryMarketContext(BaseModel):
    suburb: str
    strategy_focus: str
    demand_signal: str
    supply_signal: str


class ComparableSnapshot(BaseModel):
    sample_size: int
    price_position: Literal["below_range", "in_range", "above_range", "insufficient_data"]
    summary: str


class AdvisoryInputs(BaseModel):
    query: str
    query_type: Literal["address", "slug", "auto"]
    suburb_slug: Optional[str] = None


class PropertyAdvisorResponse(BaseModel):
    property: SubjectProperty
    advice: PropertyAdvice
    market_context: AdvisoryMarketContext
    comparable_snapshot: ComparableSnapshot
    decision_summary: str
    inputs: AdvisoryInputs


class ComparableItem(BaseModel):
    address: str
    price: int
    distance_km: float
    match_reason: str
    sold_date: str
    beds: int
    baths: int


class ComparableSummary(BaseModel):
    count: int
    min_price: int
    max_price: int
    average_price: int


class ComparableNarrative(BaseModel):
    price_position: Literal["discount", "aligned", "premium", "insufficient_data"]
    spread_commentary: str
    investor_takeaway: str
    action_prompt: str


class ComparablesResponse(BaseModel):
    subject: str
    set_quality: str
    query: str
    items: List[ComparableItem]
    summary: ComparableSummary
    narrative: ComparableNarrative


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
    summary: WatchlistSummary
    items: List[WatchlistEntry]
    groups: List[WatchlistGroup]


class WatchlistDetailResponse(BaseModel):
    generated_at: datetime
    mode: Literal["mock", "postgres"]
    item: WatchlistEntry


class WatchlistAlertsResponse(BaseModel):
    generated_at: datetime
    mode: Literal["mock", "postgres"]
    total: int
    items: List[WatchlistAlert]
