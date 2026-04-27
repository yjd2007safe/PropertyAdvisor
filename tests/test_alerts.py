from datetime import datetime, timedelta, timezone

from property_advisor.alerts import evaluate_alerts


def _base_snapshot() -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "advice": {
            "recommendation": "watch",
            "confidence": "medium",
            "fallback_state": "none",
            "freshness": "fresh",
            "sample_depth": "moderate",
            "evidence_agreement": "aligned",
            "confidence_reasons": [],
            "fallback_reasons": [],
        },
        "comparable_snapshot": {
            "sample_size": 4,
            "price_position": "in_range",
            "summary": "Inside range",
        },
        "market_context": {
            "demand_signal": "Demand score 58 from latest suburb metrics.",
            "supply_signal": "Supply score 52 from latest suburb metrics.",
        },
    }


def test_evaluate_alerts_flags_low_confidence_and_thin_sample() -> None:
    snapshot = _base_snapshot()
    snapshot["advice"]["confidence"] = "low"
    snapshot["advice"]["fallback_state"] = "low_sample"
    snapshot["comparable_snapshot"]["sample_size"] = 2
    alerts = evaluate_alerts(snapshot)
    metrics = {item["metric"] for item in alerts}
    assert "confidence" in metrics
    assert "comparable_sample_size" in metrics


def test_evaluate_alerts_flags_pricing_tension_and_conflict() -> None:
    snapshot = _base_snapshot()
    snapshot["advice"]["fallback_state"] = "conflicting_evidence"
    snapshot["advice"]["evidence_agreement"] = "conflicting"
    snapshot["comparable_snapshot"]["price_position"] = "above_range"
    alerts = evaluate_alerts(snapshot)
    metrics = {item["metric"] for item in alerts}
    assert "recommendation_risk" in metrics
    assert "evidence_agreement" in metrics
    assert "price_position" in metrics


def test_evaluate_alerts_flags_stale_evidence() -> None:
    snapshot = _base_snapshot()
    snapshot["generated_at"] = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    snapshot["advice"]["freshness"] = "stale"
    alerts = evaluate_alerts(snapshot)
    assert any(item["metric"] == "evidence_freshness" for item in alerts)


def test_evaluate_alerts_flags_market_shift_when_demand_supply_delta_is_large() -> None:
    snapshot = _base_snapshot()
    snapshot["market_context"]["demand_signal"] = "Demand score 71 from latest suburb metrics."
    snapshot["market_context"]["supply_signal"] = "Supply score 58 from latest suburb metrics."
    alerts = evaluate_alerts(snapshot)
    assert any(item["metric"] == "demand_supply_delta" for item in alerts)
