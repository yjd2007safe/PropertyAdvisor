from property_advisor.api.data_access import DataAccessLayer
from property_advisor.api.db import DatabaseConfig, DatabaseSessionFactory
from property_advisor.api.schemas import WatchlistActionRequest
from property_advisor.api.services import (
    get_comparables,
    get_property_advice,
    get_suburbs_overview,
    get_watchlist,
    get_watchlist_alerts,
    get_watchlist_events,
    upsert_watchlist_action,
)


def _mock_dal() -> DataAccessLayer:
    return DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))


def test_phase3_workflow_smoke_main_user_journey() -> None:
    dal = _mock_dal()

    suburbs = get_suburbs_overview(dal=dal)
    assert suburbs.summary.tracked_suburbs > 0
    assert suburbs.generated_at is not None
    assert suburbs.workflow_snapshot.stage == "suburb_dashboard"
    assert suburbs.workflow_snapshot.next_href.startswith("/advisor")
    assert suburbs.workflow_snapshot.next_step
    assert suburbs.workflow_snapshot.investor_message
    assert suburbs.data_source.message
    assert suburbs.data_source.investor_note

    chosen_slug = suburbs.workflow_snapshot.primary_suburb_slug or suburbs.items[0].slug
    advisor = get_property_advice(query=chosen_slug, query_type="slug", dal=dal)
    assert advisor.generated_at is not None
    assert advisor.inputs.query_type == "slug"
    assert advisor.advice.confidence in {"low", "medium", "high"}
    assert advisor.advice.freshness in {"fresh", "stale", "unknown"}
    assert advisor.advice.next_steps
    assert advisor.advice.fallback_state in {
        "none",
        "insufficient_evidence",
        "stale_evidence",
        "low_sample",
        "conflicting_evidence",
        "missing_subject_attributes",
        "missing_listing_context",
        "missing_market_context",
    }
    assert advisor.workflow_snapshot.next_href.startswith("/comparables")
    assert advisor.data_source.source_breakdown[advisor.data_source.source] >= 1

    comps = get_comparables(query=chosen_slug, max_items=5, dal=dal)
    assert comps.generated_at is not None
    assert comps.summary.count == len(comps.items)
    assert comps.summary.sample_state in {"empty", "low", "adequate"}
    assert comps.workflow_snapshot.stage == "comparables"
    assert comps.workflow_snapshot.next_step
    assert comps.narrative.action_prompt
    assert comps.data_source.message

    action = upsert_watchlist_action(
        WatchlistActionRequest(suburb_slug=chosen_slug, source_surface="comparables", watch_status="review"),
        dal=dal,
    )
    assert action.action in {"created", "updated"}
    assert action.item.suburb_slug == chosen_slug
    assert action.item.latest_context is not None
    assert action.item.latest_context.advisory
    assert action.item.latest_context.comparables

    watchlist = get_watchlist(suburb_slug=chosen_slug, group_by="none", dal=dal)
    assert watchlist.generated_at is not None
    assert watchlist.summary.total_entries >= 1
    assert watchlist.workflow_snapshot.stage == "watchlist"
    assert watchlist.workflow_snapshot.next_href.startswith("/advisor")
    assert watchlist.workflow_snapshot.next_step
    assert watchlist.data_source.source in {"mock", "postgres", "fallback_mock"}

    alerts = get_watchlist_alerts(severity="high", dal=dal)
    assert alerts.generated_at is not None
    assert alerts.total >= 0
    assert all(item.severity == "high" for item in alerts.items)
    assert alerts.data_source.message

    events = get_watchlist_events(limit=10, dal=dal)
    assert events.generated_at is not None
    assert events.total <= 10
    assert isinstance(events.items, list)
    if events.items:
        assert all(item.follow_up_href.startswith("/") for item in events.items)
        assert all(item.follow_up_label for item in events.items)


def test_phase3_workflow_smoke_thin_data_and_empty_states() -> None:
    dal = _mock_dal()

    thin_advisor = get_property_advice(query="unknown-slug", query_type="slug", dal=dal)
    assert thin_advisor.advice.recommendation == "watch"
    assert thin_advisor.advice.confidence == "low"
    assert thin_advisor.advice.fallback_state != "none"
    assert thin_advisor.advice.fallback_reasons
    assert thin_advisor.advice.limitations
    assert thin_advisor.workflow_snapshot.next_href.startswith("/comparables")

    empty_comps = get_comparables(query="empty", max_items=5, dal=dal)
    assert empty_comps.items == []
    assert empty_comps.summary.count == 0
    assert empty_comps.summary.sample_state == "empty"
    assert empty_comps.set_quality == "empty"
    assert empty_comps.narrative.price_position == "insufficient_data"
    assert empty_comps.narrative.action_prompt
    assert empty_comps.summary_cards

    watchlist_empty = get_watchlist(suburb_slug="missing-suburb-qld-0000", dal=dal)
    assert watchlist_empty.items == []
    assert watchlist_empty.summary.total_entries == 0
    assert watchlist_empty.workflow_snapshot.stage == "watchlist"
    assert watchlist_empty.workflow_snapshot.next_href.startswith("/advisor")
    assert watchlist_empty.summary.investor_brief

    no_alerts = get_watchlist_alerts(severity="critical", dal=dal)
    assert no_alerts.total == 0
    assert no_alerts.items == []
    assert no_alerts.data_source.message


def test_phase3_watchlist_event_follow_up_labels_are_concise() -> None:
    dal = _mock_dal()
    events = get_watchlist_events(limit=12, dal=dal)
    assert events.items
    labels = [item.follow_up_label for item in events.items]
    assert all(label.strip() for label in labels)
    assert set(labels).issubset(
        {
            "Review suburb detail",
            "Refresh advisor view",
            "Check advisor recommendation",
            "Open orchestration review",
        }
    )
    assert all("follow-up" not in label.lower() for label in labels)
