from fastapi.testclient import TestClient

from property_advisor.api.app import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["service"] == "propertyadvisor-api"


def test_placeholder_endpoints_shape() -> None:
    suburbs = client.get("/api/suburbs/overview")
    advisor = client.get("/api/advisor/property")
    comparables = client.get("/api/comparables")

    assert suburbs.status_code == 200
    assert advisor.status_code == 200
    assert comparables.status_code == 200

    assert suburbs.json()["items"]
    assert advisor.json()["advice"]["recommendation"] == "watch"
    assert comparables.json()["items"]
