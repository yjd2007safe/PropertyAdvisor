import json

import property_advisor.api.services as services_module
from property_advisor.alert_scan import main as alert_scan_main
from property_advisor.api.data_access import DataAccessLayer
from property_advisor.api.db import DatabaseConfig, DatabaseSessionFactory
from property_advisor.api.services import scan_watchlist_alert_events


def test_alert_scan_cli_json_output_shape(capsys) -> None:
    code = alert_scan_main(["--json", "--mode", "mock", "--limit", "1"])
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert code == 0
    assert payload["counts"]["entries_scanned"] == 1
    assert set(payload["counts"].keys()) == {"entries_scanned", "alerts_scanned", "persisted", "new", "changed", "unchanged"}
    assert "generated_at" in payload
    assert "data_source" in payload


def test_alert_scan_is_idempotent_across_repeated_runs() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    first = scan_watchlist_alert_events(suburb_slug="southport-qld-4215", dal=dal)
    second = scan_watchlist_alert_events(suburb_slug="southport-qld-4215", dal=dal)
    assert first.counts.persisted > 0
    assert first.counts.new == first.counts.persisted
    assert second.counts.persisted == first.counts.persisted
    assert second.counts.unchanged == second.counts.persisted


def test_alert_scan_suburb_filter_behavior() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    response = scan_watchlist_alert_events(suburb_slug="southport-qld-4215", dal=dal)
    assert response.counts.entries_scanned == 1


def test_alert_scan_lifecycle_counts_include_changed(monkeypatch) -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    baseline = scan_watchlist_alert_events(suburb_slug="southport-qld-4215", dal=dal)
    assert baseline.counts.new > 0

    original_get_property_advice = services_module.get_property_advice

    def _patched_get_property_advice(*args, **kwargs):
        response = original_get_property_advice(*args, **kwargs)
        return response.model_copy(
            update={"advice": response.advice.model_copy(update={"confidence": "high", "recommendation": "consider"})}
        )

    monkeypatch.setattr(services_module, "get_property_advice", _patched_get_property_advice)
    changed = scan_watchlist_alert_events(suburb_slug="southport-qld-4215", dal=dal)
    assert changed.counts.changed > 0


def test_alert_scan_reports_fallback_mock_chain_when_postgres_unavailable() -> None:
    dal = DataAccessLayer.create(
        DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="postgres"))
    )
    response = scan_watchlist_alert_events(limit=1, dal=dal)
    assert response.fallback_detected is True
    assert response.fallback_repositories

from pathlib import Path
from property_advisor.api.services import get_watchlist

def test_alert_scan_cli_writes_ledger_file(tmp_path: Path) -> None:
    ledger_path = tmp_path / "scan-ledger.json"
    code = alert_scan_main(["--json", "--mode", "mock", "--limit", "1", "--ledger-path", str(ledger_path)])
    assert code == 0
    payload = json.loads(ledger_path.read_text())
    assert payload["runs"]
    latest = payload["runs"][-1]
    assert latest["status"] == "success"
    assert latest["persistence_attempted"] is True
    assert "regenerate_command" in latest


def test_watchlist_exposes_latest_alert_scan_ledger_summary(tmp_path: Path) -> None:
    ledger_path = tmp_path / "ops.json"
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    result = scan_watchlist_alert_events(suburb_slug="southport-qld-4215", dal=dal)
    from property_advisor.operations_ledger import append_alert_scan_run_record
    append_alert_scan_run_record(
        path=ledger_path,
        mode="mock",
        filters={"suburb_slug": "southport-qld-4215", "severity": None, "limit": 1},
        result=result,
        persistence_attempted=True,
    )

    import property_advisor.api.services as services
    original = services.default_alert_scan_ledger_path
    services.default_alert_scan_ledger_path = lambda: ledger_path
    try:
        watchlist = get_watchlist(dal=dal)
        assert watchlist.summary.alert_scan_ledger is not None
        assert watchlist.summary.alert_scan_ledger.latest_run is not None
        assert watchlist.summary.alert_scan_ledger.latest_run.counts.persisted >= 0
    finally:
        services.default_alert_scan_ledger_path = original
