from __future__ import annotations

"""Typed API response models for MVP routes."""

from datetime import datetime
from typing import List, Literal, Optional

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
    next_steps: List[str]


class AdvisoryInputs(BaseModel):
    query: str
    query_type: Literal["address", "slug", "auto"]
    suburb_slug: Optional[str] = None


class PropertyAdvisorResponse(BaseModel):
    property: SubjectProperty
    advice: PropertyAdvice
    inputs: AdvisoryInputs


class ComparableItem(BaseModel):
    address: str
    price: int
    distance_km: float
    match_reason: str


class ComparableSummary(BaseModel):
    count: int
    min_price: int
    max_price: int
    average_price: int


class ComparablesResponse(BaseModel):
    subject: str
    set_quality: str
    query: str
    items: List[ComparableItem]
    summary: ComparableSummary
