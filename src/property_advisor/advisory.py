from __future__ import annotations

"""Advisory output assembly for property-level recommendations."""

from typing import Any


def build_advisory_snapshot(
    property_record: dict[str, Any],
    comparable_set: list[dict[str, Any]],
    market_summary: dict[str, Any],
) -> dict[str, Any]:
    """Package inputs for a downstream recommendation workflow."""

    return {
        "property": property_record,
        "comparables": comparable_set,
        "market_summary": market_summary,
        "recommendation": None,
        "notes": [],
    }
