from property_advisor.api.db import DatabaseConfig, DatabaseSessionFactory
from property_advisor.api.repositories import (
    MockComparableRepository,
    MockPropertyAdviceRepository,
    MockSuburbRepository,
    PostgresComparableRepository,
    create_repository_container,
)
from property_advisor.api.services import get_comparables, get_property_advice, get_suburbs_overview


def test_create_repository_container_defaults_to_mock_when_db_disabled() -> None:
    repos = create_repository_container(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    assert isinstance(repos.suburbs, MockSuburbRepository)
    assert isinstance(repos.property_advice, MockPropertyAdviceRepository)
    assert isinstance(repos.comparables, MockComparableRepository)


def test_create_repository_container_uses_postgres_placeholders_when_enabled() -> None:
    repos = create_repository_container(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", enabled=True))
    )
    assert isinstance(repos.comparables, PostgresComparableRepository)


def test_service_comparables_summary_is_derived_from_repository_data() -> None:
    repos = create_repository_container(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    response = get_comparables(query="southport", repos=repos)
    assert response.summary.count == len(response.items)
    assert response.summary.min_price <= response.summary.average_price <= response.summary.max_price


def test_service_property_advice_query_flow_supports_slug() -> None:
    repos = create_repository_container(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    response = get_property_advice(query="burleigh-heads-qld-4220", repos=repos)
    assert response.inputs.query_type == "slug"
    assert response.advice.recommendation == "consider"


def test_suburbs_overview_summary_matches_items() -> None:
    repos = create_repository_container(DatabaseSessionFactory(DatabaseConfig(url=None, enabled=False)))
    response = get_suburbs_overview(repos=repos)
    assert response.summary.tracked_suburbs == len(response.items)
