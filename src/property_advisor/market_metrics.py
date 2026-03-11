from __future__ import annotations

"""Market metric derivation and aggregation placeholders."""

from collections.abc import Iterable


def summarize_days_on_market(values: Iterable[int]) -> dict[str, float | int | None]:
    """Produce a simple average-based metric bundle."""

    items = list(values)
    if not items:
        return {"count": 0, "average": None}

    return {
        "count": len(items),
        "average": sum(items) / len(items),
    }
