from __future__ import annotations

"""Rule-based alert evaluation for advisory snapshots."""

from datetime import datetime, timedelta, timezone
from typing import Any


def evaluate_alerts(advisory_snapshot: dict[str, Any]) -> list[dict[str, Any]]:
    """Return triggered alerts for an advisory snapshot.

    The evaluator is deterministic and tolerant of dict payloads from both API model
    dumps and persisted snapshot-style payloads.
    """
    observed_at = _resolve_observed_at(advisory_snapshot)
    advice = _extract_advice(advisory_snapshot)
    comparable_snapshot = _extract_comparable_snapshot(advisory_snapshot)
    market_context = _extract_market_context(advisory_snapshot)

    recommendation = str(advice.get("recommendation") or advisory_snapshot.get("recommendation") or "").strip().lower()
    confidence = str(advice.get("confidence") or advisory_snapshot.get("confidence") or "").strip().lower()
    fallback_state = str(advice.get("fallback_state") or "").strip().lower()
    freshness = str(advice.get("freshness") or advice.get("freshness_status") or "").strip().lower()
    sample_depth = str(advice.get("sample_depth") or "").strip().lower()
    evidence_agreement = str(advice.get("evidence_agreement") or "").strip().lower()

    comp_sample_size = _coerce_int(comparable_snapshot.get("sample_size"))
    comp_position = str(comparable_snapshot.get("price_position") or "").strip().lower()

    demand_score = _extract_numeric_score(market_context.get("demand_signal"))
    supply_score = _extract_numeric_score(market_context.get("supply_signal"))
    demand_supply_delta = None
    if demand_score is not None and supply_score is not None:
        demand_supply_delta = demand_score - supply_score

    alerts: list[dict[str, Any]] = []

    if recommendation == "pass" or fallback_state in {"conflicting_evidence", "missing_subject_attributes"}:
        alerts.append(
            _alert(
                severity="high",
                title="Recommendation risk requires manual review",
                detail=f"Recommendation={recommendation or 'unknown'} with fallback state {fallback_state or 'none'}.",
                metric="recommendation_risk",
                observed_at=observed_at,
                context={"recommendation": recommendation, "fallback_state": fallback_state},
            )
        )

    if confidence == "low" or fallback_state in {"insufficient_evidence", "low_sample", "missing_listing_context", "missing_market_context"}:
        alerts.append(
            _alert(
                severity="watch",
                title="Low confidence or thin evidence",
                detail=f"Confidence={confidence or 'unknown'}; fallback={fallback_state or 'none'}.",
                metric="confidence",
                observed_at=observed_at,
                threshold="confidence >= medium",
                actual=f"confidence={confidence or 'unknown'}",
                context={
                    "confidence_reasons": list(advice.get("confidence_reasons") or []),
                    "fallback_reasons": list(advice.get("fallback_reasons") or []),
                },
            )
        )

    if comp_position in {"above_range", "below_range"}:
        price_direction = "above" if comp_position == "above_range" else "below"
        alerts.append(
            _alert(
                severity="high" if comp_position == "above_range" else "watch",
                title="Price tension vs comparable range",
                detail=f"Subject pricing appears {price_direction} current comparable range.",
                metric="price_position",
                observed_at=observed_at,
                threshold="subject inside comparable range",
                actual=comp_position,
                context={"comparable_summary": comparable_snapshot.get("summary")},
            )
        )

    if comp_sample_size < 3 or sample_depth in {"none", "low"}:
        alerts.append(
            _alert(
                severity="watch",
                title="Comparable sample is thin",
                detail=f"Only {comp_sample_size} comparable(s); treat valuation as directional.",
                metric="comparable_sample_size",
                observed_at=observed_at,
                threshold=">= 3 comparables",
                actual=comp_sample_size,
            )
        )

    if freshness == "stale" or fallback_state == "stale_evidence" or _is_snapshot_stale(advisory_snapshot):
        alerts.append(
            _alert(
                severity="watch",
                title="Evidence freshness is stale",
                detail="Snapshot evidence is outside freshness window; refresh advice/comparables.",
                metric="evidence_freshness",
                observed_at=observed_at,
                threshold="snapshot age <= 45 days",
            )
        )

    if demand_supply_delta is not None and abs(demand_supply_delta) >= 8:
        demand_label = "demand-led" if demand_supply_delta >= 8 else "supply-led"
        alerts.append(
            _alert(
                severity="watch",
                title="Market pressure shifted materially",
                detail=f"Demand/supply delta is {demand_supply_delta:.1f} ({demand_label} shift).",
                metric="demand_supply_delta",
                observed_at=observed_at,
                threshold="|demand-supply| < 8",
                actual=round(demand_supply_delta, 2),
            )
        )

    if evidence_agreement == "conflicting":
        alerts.append(
            _alert(
                severity="high",
                title="Evidence conflict across signals",
                detail="Pricing and market signals disagree; hold for explicit reviewer decision.",
                metric="evidence_agreement",
                observed_at=observed_at,
                actual=evidence_agreement,
            )
        )

    # prefer deterministic order and dedupe by metric+title
    deduped: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    for alert in alerts:
        key = (str(alert.get("metric")), str(alert.get("title")))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(alert)
    return deduped


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _extract_advice(snapshot: dict[str, Any]) -> dict[str, Any]:
    advice = _as_dict(snapshot.get("advice"))
    if advice:
        return advice
    return {
        "recommendation": snapshot.get("recommendation") or snapshot.get("stance"),
        "confidence": snapshot.get("confidence"),
        "confidence_reasons": snapshot.get("warnings") or [],
        "fallback_reasons": snapshot.get("fallback_notes") or [],
    }


def _extract_comparable_snapshot(snapshot: dict[str, Any]) -> dict[str, Any]:
    comparable_snapshot = _as_dict(snapshot.get("comparable_snapshot"))
    if comparable_snapshot:
        return comparable_snapshot
    comparables = snapshot.get("comparables")
    sample_size = len(comparables) if isinstance(comparables, list) else None
    return {
        "sample_size": sample_size,
        "price_position": snapshot.get("price_position"),
        "summary": snapshot.get("summary"),
    }


def _extract_market_context(snapshot: dict[str, Any]) -> dict[str, Any]:
    market_context = _as_dict(snapshot.get("market_context"))
    if market_context:
        return market_context
    market_summary = _as_dict(snapshot.get("market_summary"))
    return {
        "demand_signal": market_summary.get("demand_signal") or market_summary.get("demand_score"),
        "supply_signal": market_summary.get("supply_signal") or market_summary.get("supply_score"),
    }


def _coerce_int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _resolve_observed_at(snapshot: dict[str, Any]) -> str:
    raw = str(snapshot.get("generated_at") or snapshot.get("observed_at") or "").strip()
    parsed = _parse_datetime(raw) if raw else None
    if parsed:
        return parsed.astimezone(timezone.utc).isoformat()
    return datetime.now(timezone.utc).isoformat()


def _parse_datetime(value: str) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def _is_snapshot_stale(snapshot: dict[str, Any], stale_after_days: int = 45) -> bool:
    generated_at = _parse_datetime(str(snapshot.get("generated_at") or ""))
    if not generated_at:
        return False
    return generated_at < datetime.now(timezone.utc) - timedelta(days=stale_after_days)


def _extract_numeric_score(text: Any) -> float | None:
    if not isinstance(text, str):
        return None
    token = ""
    for ch in text:
        if ch.isdigit() or ch in {".", "-"}:
            token += ch
        elif token:
            break
    try:
        return float(token) if token else None
    except ValueError:
        return None


def _alert(
    *,
    severity: str,
    title: str,
    detail: str,
    metric: str,
    observed_at: str,
    threshold: Any = None,
    actual: Any = None,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "severity": severity,
        "title": title,
        "detail": detail,
        "metric": metric,
        "observed_at": observed_at,
    }
    if threshold is not None:
        payload["threshold"] = threshold
    if actual is not None:
        payload["actual"] = actual
    if context:
        payload["context"] = context
    return payload
