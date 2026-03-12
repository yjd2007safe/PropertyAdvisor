from property_advisor.api.data_access import DataAccessLayer
from property_advisor.api.db import DatabaseConfig, DatabaseSessionFactory
from property_advisor.api.repositories import (
    MockComparableRepository,
    MockPropertyAdviceRepository,
    MockSuburbRepository,
    MockWatchlistRepository,
    PostgresComparableRepository,
)
from property_advisor.api.services import get_comparables, get_property_advice, get_suburbs_overview, get_watchlist


def test_data_access_layer_defaults_to_mock_when_db_disabled() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    assert dal.mode == "mock"
    assert isinstance(dal.suburbs, MockSuburbRepository)
    assert isinstance(dal.property_advice, MockPropertyAdviceRepository)
    assert isinstance(dal.comparables, MockComparableRepository)
    assert isinstance(dal.watchlist, MockWatchlistRepository)


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


def test_service_property_advice_query_flow_supports_slug() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    response = get_property_advice(query="burleigh-heads-qld-4220", query_type="slug", dal=dal)
    assert response.inputs.query_type == "slug"
    assert response.advice.recommendation == "consider"


def test_suburbs_overview_summary_matches_items() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    response = get_suburbs_overview(dal=dal)
    assert response.summary.tracked_suburbs == len(response.items)


def test_watchlist_filter_returns_empty_for_unknown_slug() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    response = get_watchlist(suburb_slug="unknown-suburb", dal=dal)
    assert response.items == []


def test_service_comparables_empty_state() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    response = get_comparables(query="empty", dal=dal)
    assert response.items == []
    assert response.summary.count == 0
