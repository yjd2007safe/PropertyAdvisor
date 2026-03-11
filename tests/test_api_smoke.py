from property_advisor.api.app import create_app
from property_advisor.api.routes import comparables, health, property_advisor, suburbs_overview


def test_health_endpoint() -> None:
    payload = health().model_dump(mode="json")
    assert payload["status"] == "ok"
    assert payload["service"] == "propertyadvisor-api"
    assert payload["timestamp"]


def test_suburbs_overview_shape() -> None:
    payload = suburbs_overview().model_dump(mode="json")
    assert payload["summary"]["tracked_suburbs"] == 3
    assert len(payload["items"]) == 3
    assert {item["trend"] for item in payload["items"]} == {
        "watching",
        "steady",
        "improving",
    }


def test_property_advisor_shape() -> None:
    payload = property_advisor(query="southport-qld-4215").model_dump(mode="json")
    assert payload["advice"]["recommendation"] == "watch"
    assert payload["advice"]["confidence"] == "low"
    assert payload["inputs"]["query_type"] == "slug"


def test_comparables_shape() -> None:
    payload = comparables(query="southport").model_dump(mode="json")
    assert payload["set_quality"] == "mvp-sample"
    assert len(payload["items"]) >= 1
    assert payload["summary"]["count"] == len(payload["items"])

