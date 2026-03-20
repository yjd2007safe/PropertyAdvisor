from __future__ import annotations

"""Advisory output assembly for property-level recommendations."""

from typing import Any


ALGORITHM_VERSION = "phase2.round3.v1"
CONTRACT_VERSION = "phase2.round3"


def build_advisory_snapshot(
    property_record: dict[str, Any],
    comparable_set: list[dict[str, Any]],
    market_summary: dict[str, Any],
) -> dict[str, Any]:
    """Build a stable advisory contract from persisted evidence summaries."""

    comparable_count = len(comparable_set)
    missing_key_attributes = any(property_record.get(key) in {None, ""} for key in ("property_type", "beds", "baths"))
    warnings: list[str] = []
    fallback_notes: list[str] = []

    if comparable_count < 3:
        warnings.append("Comparable evidence is weak; fewer than 3 records are available.")
    if property_record.get("listing_facts_available") is False:
        warnings.append("Listing facts are missing; stance excludes listing-specific pricing context.")
    if missing_key_attributes:
        warnings.append("Key property attributes are missing; similarity confidence is degraded.")
    if market_summary.get("freshness") in {"stale", "insufficient"}:
        warnings.append("Evidence is stale or insufficiently fresh.")
        fallback_notes.append("Treat this advice as directional until newer persisted evidence arrives.")

    if comparable_count == 0 or missing_key_attributes or market_summary.get("freshness") == "stale":
        recommendation = "watch"
    elif market_summary.get("price_position") == "premium":
        recommendation = "pass"
    elif market_summary.get("price_position") == "discount":
        recommendation = "consider"
    else:
        recommendation = "watch"

    confidence = "high" if comparable_count >= 5 and not warnings else "medium" if comparable_count >= 3 and len(warnings) <= 1 else "low"
    summary = {
        "consider": "Persisted evidence supports progressing carefully.",
        "watch": "Persisted evidence supports monitoring until confidence improves.",
        "pass": "Persisted evidence suggests passing at current terms.",
    }[recommendation]
    rationale_bullets = [
        f"Comparable sample size: {comparable_count}.",
        f"Market price position: {market_summary.get('price_position', 'unknown')}.",
        f"Evidence freshness: {market_summary.get('freshness', 'unknown')}.",
    ]

    return {
        "contract_version": CONTRACT_VERSION,
        "algorithm_version": ALGORITHM_VERSION,
        "property": property_record,
        "comparables": comparable_set,
        "market_summary": market_summary,
        "recommendation": recommendation,
        "stance": recommendation,
        "summary": summary,
        "rationale_bullets": rationale_bullets,
        "confidence": confidence,
        "warnings": warnings,
        "fallback_notes": fallback_notes,
        "evidence_summary": {
            "required_inputs": {
                "property_facts": bool(property_record),
                "evidence_freshness": True,
                "algorithm_version": True,
            },
            "optional_inputs": {
                "listing_facts": property_record.get("listing_facts_available", False),
                "suburb_metrics": bool(market_summary),
                "comparable_set": bool(comparable_set),
            },
        },
        "notes": [],
    }
