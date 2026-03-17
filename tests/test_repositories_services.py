import psycopg

from property_advisor.api.data_access import DataAccessLayer
from property_advisor.api.db import DatabaseConfig, DatabaseSessionFactory
from property_advisor.api.repositories import (
    ComparableQuery,
    PostgresComparableRepository,
    PostgresSuburbRepository,
    WatchlistQuery,
)
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
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )
    assert dal.mode == "postgres"
    assert isinstance(dal.comparables, PostgresComparableRepository)


def test_postgres_suburb_repository_reads_real_rows_when_available() -> None:
    repo = PostgresSuburbRepository(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )
    repo.session_factory = DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock"))
    assert repo.list_overview()


def test_service_comparables_summary_is_derived_from_repository_data() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    response = get_comparables(query="southport", max_items=2, dal=dal)
    assert response.summary.count == len(response.items)
    assert response.summary.min_price <= response.summary.average_price <= response.summary.max_price
    assert response.narrative.price_position in {"discount", "aligned", "premium"}
    assert response.summary_cards
    assert response.workflow_links


def test_service_property_advice_query_flow_supports_slug() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    response = get_property_advice(query="burleigh-heads-qld-4220", query_type="slug", dal=dal)
    assert response.inputs.query_type == "slug"
    assert response.advice.recommendation == "consider"
    assert response.market_context.strategy_focus == "balanced"
    assert response.rationale
    assert response.investor_signals
    assert response.data_source.source in {"mock", "postgres", "fallback_mock"}


def test_suburbs_overview_summary_matches_items() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    response = get_suburbs_overview(dal=dal)
    assert response.summary.tracked_suburbs == len(response.items)
    assert response.investor_signals


def test_watchlist_filter_returns_empty_for_unknown_slug() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    response = get_watchlist(suburb_slug="unknown-suburb", dal=dal)
    assert response.items == []


def test_service_comparables_empty_state() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    response = get_comparables(query="empty", dal=dal)
    assert response.items == []
    assert response.summary.count == 0
    assert response.narrative.price_position == "insufficient_data"


def test_watchlist_grouping_and_alert_count_summary() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    response = get_watchlist(group_by="strategy", dal=dal)
    assert response.summary.total_entries == len(response.items)
    assert response.summary.alert_counts["high"] >= 1
    assert response.summary.by_status["review"] >= 1
    assert any(group.key == "balanced" for group in response.groups)
    assert response.summary_cards


def test_watchlist_detail_and_alert_filter_flow() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    detail = get_watchlist_detail(suburb_slug="southport-qld-4215", dal=dal)
    high_alerts = get_watchlist_alerts(severity="high", dal=dal)
    assert detail is not None
    assert detail.item.suburb_slug == "southport-qld-4215"
    assert all(alert.severity == "high" for alert in high_alerts.items)


def test_comparables_filter_supports_price_and_distance() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    response = get_comparables(
        query="southport", max_items=5, min_price=890000, max_price=920000, max_distance_km=0.8, dal=dal
    )
    assert response.items
    assert all(item.price >= 890000 and item.price <= 920000 for item in response.items)
    assert all(item.distance_km <= 0.8 for item in response.items)


def test_workflow_snapshots_link_surfaces_across_services() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    suburb = get_suburbs_overview(dal=dal)
    advisor = get_property_advice(query="southport-qld-4215", query_type="slug", dal=dal)
    comps = get_comparables(query="southport-qld-4215", dal=dal)
    watchlist = get_watchlist(suburb_slug="southport-qld-4215", dal=dal)
    assert suburb.workflow_snapshot.next_href.startswith("/advisor")
    assert advisor.workflow_snapshot.next_href.startswith("/comparables")
    assert comps.workflow_snapshot.next_href.startswith("/advisor")
    assert watchlist.workflow_snapshot.primary_suburb_slug == "southport-qld-4215"


def test_postgres_comparables_repository_falls_back_on_connection_error(monkeypatch) -> None:
    repo = PostgresComparableRepository(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )

    def _boom(*args, **kwargs):
        raise psycopg.OperationalError("db unavailable")

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", _boom)
    items = repo.list_by_subject(criteria=ComparableQuery(query="southport", max_items=2))
    assert items
    assert repo.last_source == "fallback_mock"


def test_service_data_source_reports_fallback_when_postgres_unavailable(monkeypatch) -> None:
    dal = DataAccessLayer.create(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )

    def _boom(*args, **kwargs):
        raise psycopg.OperationalError("db unavailable")

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", _boom)
    response = get_comparables(query="southport", max_items=2, dal=dal)
    assert response.data_source.mode == "postgres"
    assert response.data_source.source == "fallback_mock"
    assert response.data_source.is_fallback is True
    assert response.data_source.consistency in {"uniform", "mixed"}


def test_service_data_source_reports_postgres_when_rows_exist(monkeypatch) -> None:
    dal = DataAccessLayer.create(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )

    class _Cursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, *args, **kwargs):
            return None

        def fetchall(self):
            return [("1 Test St", "Southport", "QLD", "4215", 900000, "2025-01-01", 3, 2, {"distance_km": 0.5})]

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor()

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", lambda *args, **kwargs: _Conn())
    response = get_comparables(query="southport", max_items=2, dal=dal)
    assert response.data_source.source == "postgres"
    assert response.data_source.is_fallback is False
    assert "suburbs" in response.data_source.upstream_sources


def test_suburbs_overview_marks_mixed_sources_when_watchlist_falls_back(monkeypatch) -> None:
    dal = DataAccessLayer.create(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )

    class _Cursor:
        def __init__(self, rows):
            self.rows = rows

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, *args, **kwargs):
            return None

        def fetchall(self):
            return self.rows

    class _Conn:
        def __init__(self, rows):
            self.rows = rows

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor(self.rows)

    calls = {"count": 0}

    def _switching_connect(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return _Conn([("Southport", "QLD", "4215")])
        raise psycopg.OperationalError("watchlist unavailable")

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", _switching_connect)
    payload = get_suburbs_overview(dal=dal)
    assert payload.data_source.source == "postgres"
    assert payload.data_source.upstream_sources["watchlist"] == "fallback_mock"
    assert payload.data_source.consistency == "mixed"


def test_watchlist_repository_normalizes_nonstandard_status(monkeypatch) -> None:
    repo = DataAccessLayer.create(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    ).watchlist

    class _Cursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, *args, **kwargs):
            return None

        def fetchall(self):
            return [("Southport", "QLD", "4215", "watch", {"alerts": []})]

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor()

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", lambda *args, **kwargs: _Conn())
    entries = repo.list_entries(criteria=WatchlistQuery())
    assert entries[0].watch_status == "review"


def test_data_source_status_label_for_mock_mode() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    response = get_suburbs_overview(dal=dal)
    assert response.data_source.source == "mock"
    assert response.data_source.status_label == "sample_data"
    assert "Sample fixtures" in response.data_source.investor_note


def test_data_source_status_label_for_fallback_mode(monkeypatch) -> None:
    dal = DataAccessLayer.create(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )

    def _boom(*args, **kwargs):
        raise psycopg.OperationalError("db unavailable")

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", _boom)
    response = get_watchlist(dal=dal)
    assert response.data_source.source == "fallback_mock"
    assert response.data_source.status_label == "fallback"
    assert "Fallback sample payloads" in response.data_source.investor_note


def test_data_source_status_label_for_live_db_mode(monkeypatch) -> None:
    dal = DataAccessLayer.create(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )

    class _Cursor:
        def __init__(self, rows):
            self.rows = rows

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, *args, **kwargs):
            return None

        def fetchall(self):
            return self.rows

    class _Conn:
        def __init__(self, rows):
            self.rows = rows

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor(self.rows)

    calls = {"count": 0}

    def _switching_connect(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return _Conn([("Southport", "QLD", "4215")])
        return _Conn([("Southport", "QLD", "4215", "active", {"alerts": []})])

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", _switching_connect)
    response = get_suburbs_overview(dal=dal)
    assert response.data_source.source == "postgres"
    assert response.data_source.status_label == "live_db"
    assert "Live DB feed" in response.data_source.investor_note


def test_data_source_breakdown_and_fallback_reason_on_db_error(monkeypatch) -> None:
    dal = DataAccessLayer.create(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )

    def _boom(*args, **kwargs):
        raise psycopg.OperationalError("db unavailable")

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", _boom)
    response = get_comparables(query="southport", max_items=2, dal=dal)
    assert response.data_source.source == "fallback_mock"
    assert response.data_source.source_breakdown["fallback_mock"] >= 1
    assert response.data_source.fallback_reason is not None
    assert "Comparables query failed" in response.data_source.fallback_reason


def test_data_source_breakdown_for_mixed_suburb_response(monkeypatch) -> None:
    dal = DataAccessLayer.create(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )

    class _Cursor:
        def __init__(self, rows):
            self.rows = rows

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, *args, **kwargs):
            return None

        def fetchall(self):
            return self.rows

    class _Conn:
        def __init__(self, rows):
            self.rows = rows

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor(self.rows)

    calls = {"count": 0}

    def _switching_connect(*args, **kwargs):
        calls["count"] += 1
        if calls["count"] == 1:
            return _Conn([("Southport", "QLD", "4215")])
        raise psycopg.OperationalError("watchlist unavailable")

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", _switching_connect)
    payload = get_suburbs_overview(dal=dal)
    assert payload.data_source.consistency == "mixed"
    assert payload.data_source.source_breakdown["postgres"] >= 1
    assert payload.data_source.source_breakdown["fallback_mock"] >= 1


def test_property_advice_decision_summary_includes_comp_range() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    response = get_property_advice(query="southport-qld-4215", query_type="slug", dal=dal)
    assert "Subject price anchor" in response.decision_summary
    assert "comp range" in response.decision_summary


def test_postgres_seeded_southport_reads_cover_overview_comparables_and_watchlist(monkeypatch) -> None:
    dal = DataAccessLayer.create(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )

    class _Cursor:
        def __init__(self):
            self.rows = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            q = " ".join(query.split()).lower()
            if "from sales_events se" in q:
                self.rows = [
                    (
                        "12 Nerang St",
                        "Southport",
                        "QLD",
                        "4215",
                        910000,
                        "2025-02-10",
                        3,
                        2,
                        {"distance_km": 0.42, "match_reason": "seeded sale event"},
                    )
                ]
            elif "from suburbs s" in q and "market_metrics" in q:
                self.rows = [("Southport", "QLD", "4215", 935000, 760, 21, "warm")]
            elif "from alert_rules ar" in q:
                self.rows = [
                    (
                        "Southport",
                        "QLD",
                        "4215",
                        "review",
                        {
                            "suburb_slug": "southport-qld-4215",
                            "strategy": "balanced",
                            "watch_status": "review",
                            "notes": "Seeded Southport watchlist row",
                            "target_buy_range_min": 880000,
                            "target_buy_range_max": 940000,
                            "alerts": [
                                {
                                    "id": "seed-alert-1",
                                    "title": "Price drift",
                                    "severity": "high",
                                    "detail": "Comparable median moved 2.1% week-on-week.",
                                    "metric": "median_sale_price",
                                    "observed_at": "2025-02-11T00:00:00Z",
                                }
                            ],
                        },
                    )
                ]
            else:
                self.rows = []

        def fetchall(self):
            return self.rows

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor()

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", lambda *args, **kwargs: _Conn())

    overview = get_suburbs_overview(dal=dal)
    comparables = get_comparables(query="southport-qld-4215", max_items=5, dal=dal)
    detail = get_watchlist_detail(suburb_slug="southport-qld-4215", dal=dal)

    assert overview.data_source.source == "postgres"
    assert overview.items[0].slug == "southport-qld-4215"
    assert overview.items[0].median_price == 935000

    assert comparables.data_source.source == "postgres"
    assert comparables.items
    assert comparables.items[0].address == "12 Nerang St, Southport QLD 4215"
    assert comparables.items[0].match_reason == "seeded sale event"

    assert detail is not None
    assert detail.data_source.source == "postgres"
    assert detail.item.suburb_slug == "southport-qld-4215"
    assert detail.item.alerts[0].severity == "high"


def test_postgres_comparables_keeps_db_source_when_seeded_rows_exist_but_query_has_no_match(monkeypatch) -> None:
    dal = DataAccessLayer.create(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )

    class _Cursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            self.query = " ".join(query.split()).lower()

        def fetchall(self):
            if "from sales_events se" in self.query:
                return [("12 Nerang St", "Southport", "QLD", "4215", 910000, "2025-02-10", 3, 2, {"distance_km": 0.42})]
            return [("Southport", "QLD", "4215")]

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor()

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", lambda *args, **kwargs: _Conn())

    response = get_comparables(query="burleigh-heads-qld-4220", max_items=5, dal=dal)

    assert response.items == []
    assert response.set_quality == "empty"
    assert response.data_source.source == "postgres"
    assert response.data_source.is_fallback is False
