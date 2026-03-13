from property_advisor.api.data_access import DataAccessLayer
from property_advisor.api.db import DatabaseConfig, DatabaseSessionFactory
from property_advisor.api.repositories import PostgresComparableRepository
from property_advisor.api.services import (
    get_comparables,
    get_property_advice,
    get_suburbs_overview,
    get_watchlist,
    get_watchlist_alerts,
    get_watchlist_detail,
)


def test_data_access_layer_uses_postgres_placeholders_when_enabled() -> None:
    dal = DataAccessLayer.create(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", enabled=True))
    )
    assert dal.mode == "postgres"
    assert isinstance(dal.comparables, PostgresComparableRepository)


def test_service_comparables_summary_is_derived_from_repository_data() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    response = get_comparables(query="southport", max_items=2, dal=dal)
    assert response.summary.count == len(response.items)
    assert response.summary.min_price <= response.summary.average_price <= response.summary.max_price
    assert response.narrative.price_position in {"discount", "aligned", "premium"}
    assert response.summary_cards
    assert response.workflow_links


def test_service_property_advice_query_flow_supports_slug() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    response = get_property_advice(query="burleigh-heads-qld-4220", query_type="slug", dal=dal)
    assert response.inputs.query_type == "slug"
    assert response.advice.recommendation == "consider"
    assert response.market_context.strategy_focus == "balanced"
    assert response.rationale
    assert response.investor_signals


def test_suburbs_overview_summary_matches_items() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    response = get_suburbs_overview(dal=dal)
    assert response.summary.tracked_suburbs == len(response.items)
    assert response.investor_signals


def test_watchlist_filter_returns_empty_for_unknown_slug() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    response = get_watchlist(suburb_slug="unknown-suburb", dal=dal)
    assert response.items == []


def test_service_comparables_empty_state() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    response = get_comparables(query="empty", dal=dal)
    assert response.items == []
    assert response.summary.count == 0
    assert response.narrative.price_position == "insufficient_data"


def test_watchlist_grouping_and_alert_count_summary() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    response = get_watchlist(group_by="strategy", dal=dal)
    assert response.summary.total_entries == len(response.items)
    assert response.summary.alert_counts["high"] >= 1
    assert response.summary.by_status["review"] >= 1
    assert any(group.key == "balanced" for group in response.groups)
    assert response.summary_cards


def test_watchlist_detail_and_alert_filter_flow() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    detail = get_watchlist_detail(suburb_slug="southport-qld-4215", dal=dal)
    high_alerts = get_watchlist_alerts(severity="high", dal=dal)
    assert detail is not None
    assert detail.item.suburb_slug == "southport-qld-4215"
    assert all(alert.severity == "high" for alert in high_alerts.items)


def test_comparables_filter_supports_price_and_distance() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    response = get_comparables(
        query="southport", max_items=5, min_price=890000, max_price=920000, max_distance_km=0.8, dal=dal
    )
    assert response.items
    assert all(item.price >= 890000 and item.price <= 920000 for item in response.items)
    assert all(item.distance_km <= 0.8 for item in response.items)


def test_workflow_snapshots_link_surfaces_across_services() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    suburb = get_suburbs_overview(dal=dal)
    advisor = get_property_advice(query="southport-qld-4215", query_type="slug", dal=dal)
    comps = get_comparables(query="southport-qld-4215", dal=dal)
    watchlist = get_watchlist(suburb_slug="southport-qld-4215", dal=dal)
    assert suburb.workflow_snapshot.next_href.startswith("/advisor")
    assert advisor.workflow_snapshot.next_href.startswith("/comparables")
    assert comps.workflow_snapshot.next_href.startswith("/advisor")
    assert watchlist.workflow_snapshot.primary_suburb_slug == "southport-qld-4215"
