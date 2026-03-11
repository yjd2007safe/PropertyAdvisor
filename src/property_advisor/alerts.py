"""Alert evaluation placeholders for user-facing signals."""

from typing import Any


def evaluate_alerts(advisory_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Return triggered alerts for an advisory snapshot.

    Alert rules are intentionally deferred until product behavior is defined.
    """

    _ = advisory_snapshot
    return []
