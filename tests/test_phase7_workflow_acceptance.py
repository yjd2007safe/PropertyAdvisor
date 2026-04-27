from property_advisor.api.data_access import DataAccessLayer
from property_advisor.api.db import DatabaseConfig, DatabaseSessionFactory
from property_advisor.api.schemas import WatchlistAlertEventActionRequest
from property_advisor.api.services import (
    apply_watchlist_alert_event_action,
    get_watchlist,
    get_watchlist_events,
    scan_watchlist_alert_events,
)


def _mock_dal() -> DataAccessLayer:
    return DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))


def test_phase7_evidence_alert_workflow_acceptance_loop() -> None:
    dal = _mock_dal()
    suburb_slug = "southport-qld-4215"

    first_scan = scan_watchlist_alert_events(suburb_slug=suburb_slug, dal=dal)
    assert first_scan.counts.persisted > 0
    assert first_scan.counts.new == first_scan.counts.persisted

    first_watchlist = get_watchlist(suburb_slug=suburb_slug, group_by="none", dal=dal)
    assert first_watchlist.summary.alert_event_summary is not None
    assert first_watchlist.summary.alert_event_summary.total >= first_scan.counts.persisted
    assert first_watchlist.summary.alert_event_summary.unresolved >= 0
    assert first_watchlist.items

    first_entry = first_watchlist.items[0]
    assert first_entry.alert_event_summary is not None
    lifecycle_total = (
        first_entry.alert_event_summary.lifecycle.new
        + first_entry.alert_event_summary.lifecycle.changed
        + first_entry.alert_event_summary.lifecycle.unchanged
    )
    assert lifecycle_total == first_entry.alert_event_summary.total
    persisted_alert = next((alert for alert in first_entry.alerts if alert.event_key), None)
    assert persisted_alert is not None
    assert persisted_alert.event_key is not None
    assert persisted_alert.event_change_state in {"new", "changed", "unchanged"}
    assert persisted_alert.event_last_seen_at is not None

    second_scan = scan_watchlist_alert_events(suburb_slug=suburb_slug, dal=dal)
    assert second_scan.counts.persisted == first_scan.counts.persisted
    assert second_scan.counts.unchanged == second_scan.counts.persisted

    action_result = apply_watchlist_alert_event_action(
        WatchlistAlertEventActionRequest(event_key=persisted_alert.event_key, action="acknowledge"),
        dal=dal,
    )
    assert action_result.event.event_action_state == "actioned"
    assert action_result.alert_event_summary is not None
    assert action_result.alert_event_summary.unresolved <= first_entry.alert_event_summary.unresolved

    updated_watchlist = get_watchlist(suburb_slug=suburb_slug, group_by="none", dal=dal)
    updated_alert = next((alert for alert in updated_watchlist.items[0].alerts if alert.event_key == persisted_alert.event_key), None)
    assert updated_alert is not None
    assert updated_alert.event_action_state == "actioned"
    assert updated_alert.event_status == "open"

    events = get_watchlist_events(limit=20, dal=dal)
    assert events.items
    alert_events = [item for item in events.items if item.category == "alert" and item.suburb_slug == suburb_slug]
    assert alert_events
    assert all(item.alert_event_change_state in {"new", "changed", "unchanged", None} for item in alert_events)
    assert any(item.alert_event_action_state in {"new", "seen", "actioned", None} for item in alert_events)
