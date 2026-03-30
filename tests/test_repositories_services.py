import psycopg

from property_advisor.api.data_access import DataAccessLayer
from property_advisor.api.db import DatabaseConfig, DatabaseSessionFactory
from property_advisor.api.repositories import (
    ComparableQuery,
    PostgresComparableRepository,
    PostgresPropertyAdviceRepository,
    PostgresSuburbRepository,
    WatchlistQuery,
    ComparableCandidate,
    ComparableSubject,
    score_comparable_candidates,
    select_comparable_candidates,
)
from property_advisor.api.services import (
    get_comparables,
    get_property_advice,
    get_suburbs_overview,
    get_watchlist,
    get_watchlist_alerts,
    get_watchlist_detail,
    get_watchlist_events,
    upsert_watchlist_action,
)
from property_advisor.api.schemas import WatchlistActionRequest


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
    assert response.inputs.contract_version == "phase2.round3"
    assert response.inputs.required_persisted_inputs["subject_property_identity"] is True
    assert "persisted_comparable_sales" in response.inputs.missing_data_behavior


def test_suburbs_overview_summary_matches_items() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    response = get_suburbs_overview(dal=dal)
    assert response.summary.tracked_suburbs == len(response.items)
    assert response.investor_signals


def test_watchlist_filter_returns_empty_for_unknown_slug() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    response = get_watchlist(suburb_slug="unknown-suburb", dal=dal)
    assert response.items == []


def test_watchlist_action_upsert_feeds_watchlist_context() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    action = upsert_watchlist_action(
        WatchlistActionRequest(suburb_slug="new-suburb-qld-4300", source_surface="comparables"),
        dal=dal,
    )
    response = get_watchlist(suburb_slug="new-suburb-qld-4300", dal=dal)
    assert action.action == "created"
    assert response.summary.total_entries == 1
    assert response.items[0].latest_context is not None
    assert "review_required=" in response.items[0].latest_context.orchestration


def test_service_comparables_empty_state() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    response = get_comparables(query="empty", dal=dal)
    assert response.items == []
    assert response.summary.count == 0
    assert response.narrative.price_position == "insufficient_data"
    assert response.summary.sample_state == "empty"


def test_service_comparables_low_sample_semantics() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    response = get_comparables(query="southport", max_items=2, dal=dal)
    assert response.summary.count == 2
    assert response.summary.sample_state == "low"
    assert response.set_quality == "mvp-sample"


def test_select_comparable_candidates_prefers_same_suburb_same_type_then_recency() -> None:
    subject = ComparableSubject(
        property_id="subject-1",
        address="1 Subject St, Southport QLD 4215",
        suburb_name="Southport",
        state_code="QLD",
        postcode="4215",
        property_type="house",
        bedrooms=3,
        bathrooms=2,
    )
    candidates = [
        ComparableCandidate(
            property_id="c3",
            address="9 Other St, Labrador QLD 4215",
            suburb_name="Labrador",
            suburb_slug="labrador-qld-4215",
            property_type="house",
            sale_price=905000,
            sale_date="2026-02-01",
            bedrooms=3,
            bathrooms=2,
            metadata={},
        ),
        ComparableCandidate(
            property_id="c2",
            address="8 Nearby St, Southport QLD 4215",
            suburb_name="Southport",
            suburb_slug="southport-qld-4215",
            property_type="unit",
            sale_price=880000,
            sale_date="2026-03-01",
            bedrooms=3,
            bathrooms=2,
            metadata={},
        ),
        ComparableCandidate(
            property_id="c1",
            address="7 Match St, Southport QLD 4215",
            suburb_name="Southport",
            suburb_slug="southport-qld-4215",
            property_type="house",
            sale_price=910000,
            sale_date="2026-03-10",
            bedrooms=3,
            bathrooms=2,
            metadata={},
        ),
    ]

    selected = select_comparable_candidates(subject, candidates, max_items=3)
    assert [candidate.property_id for candidate in selected] == ["c1", "c2", "c3"]


def test_select_comparable_candidates_applies_feature_bands_and_recency() -> None:
    subject = ComparableSubject(
        property_id="subject-1",
        address="1 Subject St, Southport QLD 4215",
        suburb_name="Southport",
        state_code="QLD",
        postcode="4215",
        property_type="house",
        bedrooms=3,
        bathrooms=2,
    )
    candidates = [
        ComparableCandidate(
            property_id="keep",
            address="7 Match St, Southport QLD 4215",
            suburb_name="Southport",
            suburb_slug="southport-qld-4215",
            property_type="house",
            sale_price=910000,
            sale_date="2026-02-10",
            bedrooms=4,
            bathrooms=2,
            metadata={},
        ),
        ComparableCandidate(
            property_id="old",
            address="6 Old St, Southport QLD 4215",
            suburb_name="Southport",
            suburb_slug="southport-qld-4215",
            property_type="house",
            sale_price=870000,
            sale_date="2024-01-10",
            bedrooms=3,
            bathrooms=2,
            metadata={},
        ),
        ComparableCandidate(
            property_id="wide-band",
            address="5 Wide St, Southport QLD 4215",
            suburb_name="Southport",
            suburb_slug="southport-qld-4215",
            property_type="house",
            sale_price=950000,
            sale_date="2026-02-12",
            bedrooms=6,
            bathrooms=4,
            metadata={},
        ),
    ]

    selected = select_comparable_candidates(subject, candidates, max_items=5)
    assert [candidate.property_id for candidate in selected] == ["keep"]


def test_score_comparable_candidates_exposes_rationale_and_orders_by_similarity() -> None:
    subject = ComparableSubject(
        property_id="subject-1",
        address="1 Subject St, Southport QLD 4215",
        suburb_name="Southport",
        state_code="QLD",
        postcode="4215",
        property_type="house",
        bedrooms=3,
        bathrooms=2,
    )
    candidates = [
        ComparableCandidate(
            property_id="near-best",
            address="2 Near St, Southport QLD 4215",
            suburb_name="Southport",
            suburb_slug="southport-qld-4215",
            property_type="house",
            sale_price=905000,
            sale_date="2026-03-10",
            bedrooms=3,
            bathrooms=2,
            metadata={"distance_km": 0.4, "subject_price": 900000},
        ),
        ComparableCandidate(
            property_id="far-weaker",
            address="9 Far St, Labrador QLD 4215",
            suburb_name="Labrador",
            suburb_slug="labrador-qld-4215",
            property_type="unit",
            sale_price=980000,
            sale_date="2025-05-10",
            bedrooms=4,
            bathrooms=3,
            metadata={"distance_km": 7.2, "subject_price": 900000},
        ),
    ]

    scored = score_comparable_candidates(subject, candidates, max_items=5)

    assert [item.candidate.property_id for item in scored] == ["near-best", "far-weaker"]
    assert scored[0].similarity_score > scored[1].similarity_score
    assert scored[0].rationale["same_suburb"] is True
    assert "price_relevance_score" in scored[0].rationale
    assert scored[1].rationale["same_property_type"] is False


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


def test_watchlist_events_prioritizes_recent_actionable_changes() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    response = get_watchlist_events(limit=8, dal=dal)
    assert response.total <= 8
    assert all(item.follow_up_href.startswith("/") for item in response.items)
    if response.items:
        categories = {item.category for item in response.items}
        assert "watchlist" in categories or "alert" in categories
        assert categories <= {"watchlist", "alert", "advisory", "orchestration"}


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


def test_workflow_links_preserve_entity_context_for_cross_page_handoffs() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    advisor = get_property_advice(query="southport-qld-4215", query_type="slug", dal=dal)
    comps = get_comparables(query="southport-qld-4215", dal=dal)
    watchlist = get_watchlist(suburb_slug="southport-qld-4215", dal=dal)

    advisor_links = {item.label: item.href for item in advisor.workflow_links}
    comp_links = {item.label: item.href for item in comps.workflow_links}
    watchlist_links = {item.label: item.href for item in watchlist.workflow_links}

    assert advisor_links["Comparables"].endswith("?query=southport-qld-4215")
    assert comp_links["Property advisor"].endswith("?query=southport-qld-4215&query_type=slug")
    assert watchlist_links["Watchlist"].endswith("?detail_slug=southport-qld-4215&suburb_slug=southport-qld-4215")


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
        def __init__(self):
            self.query = ""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, *args, **kwargs):
            self.query = " ".join(query.split()).lower()

        def fetchall(self):
            if "from properties p" in self.query:
                return [("subject-1", "1 Test St", "Southport", "QLD", "4215", "house", 3, 2)]
            return [("comp-1", "2 Test St", "Southport", "QLD", "4215", "house", 900000, "2026-01-01", 3, 2, {"distance_km": 0.5})]

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


def test_property_advice_explicitly_marks_missing_comparables_in_input_contract() -> None:
    dal = DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=None, requested_mode="mock")))
    response = get_property_advice(query="empty", query_type="auto", dal=dal)
    assert response.comparable_snapshot.price_position == "insufficient_data"
    assert response.inputs.optional_persisted_inputs["persisted_comparable_sales"] is False


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
            if "from properties p" in q:
                self.rows = [("subject-1", "10 Sample Ave", "Southport", "QLD", "4215", "house", 3, 2)]
            elif "from sales_events se" in q:
                self.rows = [
                    (
                        "comp-1",
                        "12 Nerang St",
                        "Southport",
                        "QLD",
                        "4215",
                        "house",
                        910000,
                        "2026-02-10",
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
    assert comparables.items[0].match_reason.startswith("seeded sale event")

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
            if "from properties p" in self.query:
                return []
            if "from sales_events se" in self.query:
                return [("comp-1", "12 Nerang St", "Southport", "QLD", "4215", "house", 910000, "2026-02-10", 3, 2, {"distance_km": 0.42})]
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

    assert response.items
    assert response.data_source.source == "fallback_mock"
    assert response.data_source.is_fallback is True


def test_postgres_comparable_generation_is_idempotent_for_same_version(monkeypatch) -> None:
    dal = DataAccessLayer.create(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )
    state = {"set_id": None, "member_inserts": 0, "member_deletes": 0}

    class _Cursor:
        def __init__(self):
            self.query = ""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            self.query = " ".join(query.split()).lower()
            self.params = params
            if self.query.startswith("delete from comparable_members"):
                state["member_deletes"] += 1
            elif self.query.startswith("insert into comparable_members"):
                state["member_inserts"] += 1
            elif self.query.startswith("insert into comparable_sets"):
                state["set_id"] = params[0]

        def fetchone(self):
            if "from properties p" in self.query:
                return ("subject-1", "10 Sample Ave", "Southport", "QLD", "4215", "house", 3, 2)
            if "from comparable_sets" in self.query:
                return (state["set_id"],) if state["set_id"] else None
            return None

        def fetchall(self):
            if "from sales_events se" in self.query:
                return [
                    ("comp-1", "12 Nerang St", "Southport", "QLD", "4215", "house", 910000, "2026-03-10", 3, 2, {"distance_km": 0.42, "subject_price": 900000}),
                    ("comp-2", "14 Queen St", "Southport", "QLD", "4215", "house", 895000, "2026-03-03", 3, 2, {"distance_km": 0.66, "subject_price": 900000}),
                ]
            if "join comparable_members cm" in self.query:
                return []
            return []

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor()

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", lambda *args, **kwargs: _Conn())

    first = dal.comparables.generate_comparable_set(ComparableQuery(query="southport-qld-4215", max_items=5))
    second = dal.comparables.generate_comparable_set(ComparableQuery(query="southport-qld-4215", max_items=5))

    assert first.set_id == second.set_id
    assert first.algorithm_version == "phase2.round2.v1"
    assert state["member_deletes"] == 1
    assert state["member_inserts"] == 4


def test_service_comparables_prefers_latest_persisted_set_when_available(monkeypatch) -> None:
    dal = DataAccessLayer.create(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )

    class _Cursor:
        def __init__(self):
            self.query = ""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            self.query = " ".join(query.split()).lower()

        def fetchone(self):
            if "from properties p" in self.query:
                return ("subject-1", "10 Sample Ave", "Southport", "QLD", "4215", "house", 3, 2)
            return None

        def fetchall(self):
            if "join comparable_members cm" in self.query:
                return [
                    (
                        "set-1",
                        "phase2.round2.v1",
                        "2026-03-19T00:00:00+00:00",
                        0.812,
                        '{"quality_label": "high"}',
                        "comp-1",
                        "12 Nerang St",
                        "Southport",
                        "QLD",
                        "4215",
                        910000,
                        0.42,
                        '{"same_suburb": true, "price_delta_pct": 1.1}',
                        "persisted high-confidence comparable",
                        0.88,
                        "2026-03-10",
                        3,
                        2,
                    )
                ]
            return []

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor()

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", lambda *args, **kwargs: _Conn())

    response = get_comparables(query="southport-qld-4215", max_items=5, dal=dal)

    assert response.set_quality == "persisted-high"
    assert response.summary.algorithm_version == "phase2.round2.v1"
    assert response.summary.quality_score == 0.812
    assert response.items[0].score == 0.88
    assert response.items[0].rationale["same_suburb"] is True


def test_postgres_property_advice_snapshot_generation_persists_deterministically(monkeypatch) -> None:
    repo = PostgresPropertyAdviceRepository(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )
    state = {"existing_id": "advice-1", "updates": 0, "inserts": 0}

    class _Cursor:
        def __init__(self):
            self.query = ""
            self.params = None
            self.rows = []

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            self.query = " ".join(query.split()).lower()
            self.params = params
            if "from properties p" in self.query:
                self.rows = [("prop-1", "10 Sample Ave", "Southport", "QLD", "4215", "house", 3, 2, "sub-1")]
            elif "from listings l" in self.query:
                self.rows = [("listing-1", "active", 905000, None, "2026-03-18T00:00:00+00:00", "active", 905000, 21)]
            elif "from market_metrics" in self.query:
                self.rows = [("metric-1", 920000, 760, 24, 61.0, 47.0, "warm", "2026-03-15")]
            elif "from comparable_sets cs" in self.query and "left join comparable_members" in self.query:
                self.rows = [
                    ("set-1", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.82, '{"quality_label": "high"}', "comp-1"),
                    ("set-1", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.82, '{"quality_label": "high"}', "comp-2"),
                    ("set-1", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.82, '{"quality_label": "high"}', "comp-3"),
                ]
            elif "from property_advice_snapshots" in self.query and "select id" in self.query:
                self.rows = [(state["existing_id"],)]
            elif self.query.startswith("update property_advice_snapshots"):
                state["updates"] += 1
                self.rows = []
            elif self.query.startswith("insert into property_advice_snapshots"):
                state["inserts"] += 1
                self.rows = []
            else:
                self.rows = []

        def fetchall(self):
            return self.rows

        def fetchone(self):
            return self.rows[0] if self.rows else None

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor()

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", lambda *args, **kwargs: _Conn())

    first = repo.generate_snapshot("southport-qld-4215", query_type="slug")
    second = repo.generate_snapshot("southport-qld-4215", query_type="slug")

    assert first is not None
    assert second is not None
    assert first.advice.evidence_summary is not None
    assert first.advice.evidence_summary.optional_inputs["comparable_set"] is True
    assert first.advice.recommendation == second.advice.recommendation
    assert state["updates"] == 2
    assert state["inserts"] == 0


def test_postgres_property_advice_read_prefers_latest_persisted_snapshot(monkeypatch) -> None:
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

        def fetchone(self):
            if "from property_advice_snapshots pas" in self.query:
                return (
                    "10 Sample Ave", "Southport", "QLD", "4215", "house", 3, 2,
                    "consider", "medium", "Persisted snapshot says proceed carefully.",
                    {
                        "decision_summary": "Persisted snapshot summary",
                        "summary": "Persisted snapshot says proceed carefully.",
                        "stance": "consider",
                        "rationale_bullets": ["Persisted comp depth is acceptable."],
                        "warnings": ["Listing facts are one cycle old."],
                        "fallback_notes": [],
                        "confidence_reasons": ["Comparable set quality is strong."],
                        "fallback_state": "none",
                        "fallback_reasons": [],
                        "limitations": [],
                        "freshness": "fresh",
                        "sample_depth": "moderate",
                        "evidence_agreement": "aligned",
                        "evidence_summary": {
                            "contract_version": "phase2.round4",
                            "algorithm_version": "phase2.round3.v1",
                            "freshness_status": "fresh",
                            "required_inputs": {"property_facts": True},
                            "optional_inputs": {"listing_facts": True},
                            "sections": [],
                            "warnings": ["Listing facts are one cycle old."],
                            "fallback_notes": [],
                            "limitations": [],
                            "confidence_reasons": ["Comparable set quality is strong."],
                            "fallback_state": "none",
                            "fallback_reasons": [],
                            "sample_depth": "moderate",
                            "evidence_agreement": "aligned",
                            "evidence_strength": "strong",
                        },
                    },
                    "phase2.round3.v1",
                )
            return None

        def fetchall(self):
            return []

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor()

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", lambda *args, **kwargs: _Conn())

    response = get_property_advice(query="southport-qld-4215", query_type="slug", dal=dal)

    assert response.data_source.source == "postgres"
    assert response.advice.recommendation == "consider"
    assert response.advice.evidence_summary is not None
    assert response.advice.evidence_summary.algorithm_version == "phase2.round3.v1"
    assert response.decision_summary == "Persisted snapshot summary"
    assert response.advice.fallback_state == "none"
    assert response.advice.sample_depth == "moderate"
    assert response.advice.evidence_agreement == "aligned"


def test_postgres_property_advice_snapshot_generation_marks_low_evidence_and_missing_data(monkeypatch) -> None:
    repo = PostgresPropertyAdviceRepository(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )

    class _Cursor:
        def __init__(self):
            self.rows = []
            self.query = ""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            self.query = " ".join(query.split()).lower()
            if "from properties p" in self.query:
                self.rows = [("prop-2", "11 Sparse Ave", "Southport", "QLD", "4215", None, None, None, "sub-1")]
            elif "from listings l" in self.query:
                self.rows = []
            elif "from market_metrics" in self.query:
                self.rows = [("metric-1", 920000, 760, 24, None, None, "balanced", "2025-10-01")]
            elif "from comparable_sets cs" in self.query and "left join comparable_members" in self.query:
                self.rows = [("set-2", "phase2.round2.v1", "2025-10-01T00:00:00+00:00", 0.4, '{"quality_label": "low"}', "comp-1")]
            elif "from property_advice_snapshots" in self.query and "select id" in self.query:
                self.rows = []
            else:
                self.rows = []

        def fetchall(self):
            return self.rows

        def fetchone(self):
            return self.rows[0] if self.rows else None

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor()

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", lambda *args, **kwargs: _Conn())

    response = repo.generate_snapshot("southport-qld-4215", query_type="slug")

    assert response is not None
    assert response.advice.confidence == "low"
    assert response.advice.recommendation == "watch"
    assert any("Comparable evidence is weak" in item for item in response.advice.warnings)
    assert any("Listing facts are missing" in item for item in response.advice.warnings)
    assert any("Key property attributes" in item for item in response.advice.warnings)
    assert response.advice.fallback_state == "low_sample"
    assert "Comparable sample depth is below the minimum preferred threshold." in response.advice.fallback_reasons
    assert response.advice.freshness == "stale"


def test_postgres_property_advice_snapshot_generation_high_confidence_on_strong_evidence(monkeypatch) -> None:
    repo = PostgresPropertyAdviceRepository(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )

    class _Cursor:
        def __init__(self):
            self.rows = []
            self.query = ""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            self.query = " ".join(query.split()).lower()
            if "from properties p" in self.query:
                self.rows = [("prop-9", "9 Strong Ave", "Southport", "QLD", "4215", "house", 4, 2, "sub-1")]
            elif "from listings l" in self.query:
                self.rows = [("listing-9", "active", 880000, None, "2026-03-18T00:00:00+00:00", "active", 880000, 12)]
            elif "from market_metrics" in self.query:
                self.rows = [("metric-9", 920000, 760, 24, 70.0, 44.0, "warm", "2026-03-15")]
            elif "from comparable_sets cs" in self.query and "left join comparable_members" in self.query:
                self.rows = [
                    ("set-9", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.86, '{"quality_label": "high"}', "comp-1"),
                    ("set-9", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.86, '{"quality_label": "high"}', "comp-2"),
                    ("set-9", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.86, '{"quality_label": "high"}', "comp-3"),
                    ("set-9", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.86, '{"quality_label": "high"}', "comp-4"),
                    ("set-9", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.86, '{"quality_label": "high"}', "comp-5"),
                ]
            elif "from property_advice_snapshots" in self.query and "select id" in self.query:
                self.rows = []
            else:
                self.rows = []

        def fetchall(self):
            return self.rows

        def fetchone(self):
            return self.rows[0] if self.rows else None

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor()

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", lambda *args, **kwargs: _Conn())

    response = repo.generate_snapshot("southport-qld-4215", query_type="slug")

    assert response is not None
    assert response.advice.recommendation == "consider"
    assert response.advice.confidence == "high"
    assert response.advice.fallback_state == "none"
    assert response.advice.sample_depth == "high"
    assert response.advice.evidence_agreement == "aligned"


def test_postgres_property_advice_snapshot_generation_marks_conflicting_evidence(monkeypatch) -> None:
    repo = PostgresPropertyAdviceRepository(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )

    class _Cursor:
        def __init__(self):
            self.rows = []
            self.query = ""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            self.query = " ".join(query.split()).lower()
            if "from properties p" in self.query:
                self.rows = [("prop-3", "13 Mixed Ave", "Southport", "QLD", "4215", "house", 4, 2, "sub-1")]
            elif "from listings l" in self.query:
                self.rows = [("listing-3", "active", 885000, None, "2026-03-18T00:00:00+00:00", "active", 885000, 19)]
            elif "from market_metrics" in self.query:
                self.rows = [("metric-3", 920000, 760, 24, 40.0, 61.0, "balanced", "2026-03-15")]
            elif "from comparable_sets cs" in self.query and "left join comparable_members" in self.query:
                self.rows = [
                    ("set-3", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.83, '{"quality_label": "high"}', "comp-1"),
                    ("set-3", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.83, '{"quality_label": "high"}', "comp-2"),
                    ("set-3", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.83, '{"quality_label": "high"}', "comp-3"),
                    ("set-3", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.83, '{"quality_label": "high"}', "comp-4"),
                ]
            elif "from property_advice_snapshots" in self.query and "select id" in self.query:
                self.rows = []
            else:
                self.rows = []

        def fetchall(self):
            return self.rows

        def fetchone(self):
            return self.rows[0] if self.rows else None

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor()

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", lambda *args, **kwargs: _Conn())

    response = repo.generate_snapshot("southport-qld-4215", query_type="slug")

    assert response is not None
    assert response.advice.recommendation == "consider"
    assert response.advice.fallback_state == "conflicting_evidence"
    assert response.advice.evidence_agreement == "conflicting"
    assert response.advice.confidence in {"low", "medium"}


def test_postgres_property_advice_snapshot_generation_keeps_negative_recommendation_with_strong_evidence(monkeypatch) -> None:
    repo = PostgresPropertyAdviceRepository(
        DatabaseSessionFactory(DatabaseConfig(url="postgresql://localhost/propertyadvisor", requested_mode="postgres"))
    )

    class _Cursor:
        def __init__(self):
            self.rows = []
            self.query = ""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            self.query = " ".join(query.split()).lower()
            if "from properties p" in self.query:
                self.rows = [("prop-4", "14 Expensive Ave", "Southport", "QLD", "4215", "house", 4, 2, "sub-1")]
            elif "from listings l" in self.query:
                self.rows = [("listing-4", "active", 995000, None, "2026-03-18T00:00:00+00:00", "active", 995000, 14)]
            elif "from market_metrics" in self.query:
                self.rows = [("metric-4", 920000, 760, 24, 48.0, 49.0, "balanced", "2026-03-15")]
            elif "from comparable_sets cs" in self.query and "left join comparable_members" in self.query:
                self.rows = [
                    ("set-4", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.88, '{"quality_label": "high"}', "comp-1"),
                    ("set-4", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.88, '{"quality_label": "high"}', "comp-2"),
                    ("set-4", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.88, '{"quality_label": "high"}', "comp-3"),
                    ("set-4", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.88, '{"quality_label": "high"}', "comp-4"),
                    ("set-4", "phase2.round2.v1", "2026-03-17T00:00:00+00:00", 0.88, '{"quality_label": "high"}', "comp-5"),
                ]
            elif "from property_advice_snapshots" in self.query and "select id" in self.query:
                self.rows = []
            else:
                self.rows = []

        def fetchall(self):
            return self.rows

        def fetchone(self):
            return self.rows[0] if self.rows else None

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor()

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", lambda *args, **kwargs: _Conn())

    response = repo.generate_snapshot("southport-qld-4215", query_type="slug")

    assert response is not None
    assert response.advice.recommendation == "pass"
    assert response.advice.confidence == "high"
    assert response.advice.fallback_state == "none"
    assert response.advice.confidence_reasons
