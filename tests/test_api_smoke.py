import pytest

from property_advisor.api.routes import (
    comparables,
    health,
    orchestration_review,
    property_advisor,
    suburbs_overview,
    watchlist,
    watchlist_alerts,
    watchlist_action,
    watchlist_detail,
)
from property_advisor.api.schemas import WatchlistActionRequest


def test_health_endpoint() -> None:
    payload = health().model_dump(mode="json")
    assert payload["status"] == "ok"
    assert payload["service"] == "propertyadvisor-api"
    assert payload["timestamp"]


def test_suburbs_overview_shape() -> None:
    payload = suburbs_overview().model_dump(mode="json")
    assert payload["summary"]["tracked_suburbs"] == 3
    assert len(payload["items"]) == 3
    assert payload["investor_signals"]
    assert payload["workflow_links"]
    assert payload["workflow_snapshot"]["stage"] == "suburb_dashboard"
    assert payload["data_source"]["source"] in {"mock", "postgres", "fallback_mock"}
    assert payload["data_source"]["consistency"] in {"uniform", "mixed"}
    assert {item["trend"] for item in payload["items"]} == {
        "watching",
        "steady",
        "improving",
    }


def test_property_advisor_shape() -> None:
    payload = property_advisor(query="southport-qld-4215", query_type="slug").model_dump(mode="json")
    assert payload["advice"]["recommendation"] == "watch"
    assert payload["advice"]["confidence"] == "low"
    assert payload["inputs"]["query_type"] == "slug"
    assert payload["rationale"]
    assert payload["summary_cards"]
    assert payload["workflow_snapshot"]["next_href"].startswith("/comparables")
    assert payload["data_source"]["source"] in {"mock", "postgres", "fallback_mock"}
    assert payload["data_source"]["consistency"] in {"uniform", "mixed"}


def test_comparables_shape() -> None:
    payload = comparables(query="southport", max_items=2, min_price=None, max_price=None, max_distance_km=None).model_dump(mode="json")
    assert payload["set_quality"] == "mvp-sample"
    assert len(payload["items"]) == 2
    assert payload["summary"]["count"] == len(payload["items"])
    assert payload["summary_cards"]
    assert payload["workflow_snapshot"]["stage"] == "comparables"
    assert payload["data_source"]["source"] in {"mock", "postgres", "fallback_mock"}
    assert payload["data_source"]["consistency"] in {"uniform", "mixed"}


def test_watchlist_shape() -> None:
    payload = watchlist(suburb_slug=None, strategy=None, state=None, watch_status=None, group_by="none").model_dump(mode="json")
    assert payload["mode"] in {"mock", "postgres"}
    assert payload["summary"]["total_entries"] >= 1
    assert payload["items"][0]["alerts"]
    assert payload["workflow_links"]
    assert payload["workflow_snapshot"]["stage"] == "watchlist"
    assert isinstance(payload["data_source"]["upstream_sources"], dict)
    assert payload["data_source"]["source"] in {"mock", "postgres", "fallback_mock"}
    assert payload["data_source"]["consistency"] in {"uniform", "mixed"}
    assert payload["items"][0]["latest_context"]["advisory"]


def test_watchlist_group_and_detail_routes() -> None:
    grouped_payload = watchlist(suburb_slug=None, strategy=None, state="QLD", watch_status=None, group_by="strategy").model_dump(mode="json")
    detail_payload = watchlist_detail(suburb_slug="southport-qld-4215").model_dump(mode="json")
    assert grouped_payload["groups"]
    assert detail_payload["item"]["suburb_slug"] == "southport-qld-4215"
    assert detail_payload["data_source"]["source"] in {"mock", "postgres", "fallback_mock"}


def test_watchlist_alerts_route() -> None:
    payload = watchlist_alerts(severity="high").model_dump(mode="json")
    assert payload["total"] >= 1
    assert all(item["severity"] == "high" for item in payload["items"])
    assert payload["data_source"]["source"] in {"mock", "postgres", "fallback_mock"}
    assert payload["data_source"]["consistency"] in {"uniform", "mixed"}


def test_watchlist_detail_not_found() -> None:
    with pytest.raises(Exception) as exc_info:
        watchlist_detail(suburb_slug="unknown")
    assert "404" in str(exc_info.value)


def test_watchlist_action_route_creates_entry() -> None:
    payload = watchlist_action(
        WatchlistActionRequest(suburb_slug="new-suburb-qld-4300", source_surface="advisor")
    ).model_dump(mode="json")
    assert payload["action"] in {"created", "updated"}
    assert payload["item"]["suburb_slug"] == "new-suburb-qld-4300"
    assert payload["item"]["latest_context"]["comparables"]


def test_orchestration_review_shape() -> None:
    payload = orchestration_review().model_dump(mode="json")
    assert payload["summary"]["current_state"] in {"awaiting_review", "auto_progressing", "idle"}
    assert payload["summary"]["freshness"] in {"fresh", "stale", "empty"}
    assert isinstance(payload["summary"]["review_needed"], bool)
    assert payload["summary"]["generated_at"]
    assert isinstance(payload["plans"], list)
