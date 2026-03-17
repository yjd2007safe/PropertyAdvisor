from __future__ import annotations

from datetime import date

from property_advisor.api.db import DatabaseConfig, DatabaseSessionFactory
from property_advisor.api.repositories import PostgresSuburbRepository
from property_advisor.ingest import generate_southport_market_metrics
from property_advisor.market_metrics import generate_suburb_market_metrics


def test_generate_suburb_market_metrics_is_idempotent_for_same_period(monkeypatch) -> None:
    calls = {"upsert": 0}

    class _Cursor:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            self.query = query
            self.params = params
            if "insert into market_metrics" in query:
                calls["upsert"] += 1

        def fetchone(self):
            if "from suburbs" in self.query:
                return ("suburb-southport",)
            if "insert into market_metrics" in self.query:
                return (calls["upsert"] == 1,)
            return None

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor()

        def commit(self):
            return None

    monkeypatch.setattr("property_advisor.market_metrics.psycopg.connect", lambda *args, **kwargs: _Conn())

    first = generate_suburb_market_metrics(
        database_url="postgresql://localhost/propertyadvisor",
        suburb_name="Southport",
        state_code="QLD",
        postcode="4215",
        target_slice="southport-qld-4215",
        metric_period="monthly",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
    )
    second = generate_suburb_market_metrics(
        database_url="postgresql://localhost/propertyadvisor",
        suburb_name="Southport",
        state_code="QLD",
        postcode="4215",
        target_slice="southport-qld-4215",
        metric_period="monthly",
        period_start=date(2025, 1, 1),
        period_end=date(2025, 1, 31),
    )

    assert first.inserted is True
    assert second.inserted is False
    assert first.suburb_id == "suburb-southport"
    assert calls["upsert"] == 2


def test_generate_southport_market_metrics_wraps_generator(monkeypatch) -> None:
    class _Result:
        target_slice = "southport-qld-4215"
        suburb_id = "suburb-southport"
        metric_period = "monthly"
        period_start = date(2025, 2, 1)
        period_end = date(2025, 2, 28)
        inserted = True

    monkeypatch.setattr("property_advisor.ingest.generate_suburb_market_metrics", lambda **kwargs: _Result())

    payload = generate_southport_market_metrics(
        database_url="postgresql://localhost/propertyadvisor",
        period_start=date(2025, 2, 1),
        period_end=date(2025, 2, 28),
    )

    assert payload["target_slice"] == "southport-qld-4215"
    assert payload["inserted"] is True


def test_postgres_suburb_overview_prefers_latest_market_metrics_rows(monkeypatch) -> None:
    repo = PostgresSuburbRepository(
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
            return [
                ("Southport", "QLD", "4215", 930000, 740, 24, "warm"),
                ("Unknownville", "QLD", "4999", None, None, None, None),
            ]

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor()

    monkeypatch.setattr("property_advisor.api.repositories.psycopg.connect", lambda *args, **kwargs: _Conn())
    items = repo.list_overview()

    southport = next(item for item in items if item.slug == "southport-qld-4215")
    unknown = next(item for item in items if item.slug == "unknownville-qld-4999")

    assert southport.median_price == 930000
    assert southport.median_rent == 740
    assert southport.trend == "improving"
    assert "market_metrics" in southport.note

    assert unknown.median_price == 0
    assert "fallback values" in unknown.note
