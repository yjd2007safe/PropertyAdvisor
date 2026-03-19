from __future__ import annotations

import json
from pathlib import Path

import pytest

from property_advisor.ingest import InMemoryCanonicalStore, parse_source_payload, run_file_ingest, run_southport_refresh
from property_advisor.ingest import collect_southport_row_counts, run_southport_backfill_and_verify, verify_southport_demo_slice


def test_parse_source_payload_requires_identity_and_location() -> None:
    try:
        parse_source_payload(source_name="feed", payload={"address": "10 Test St"})
        assert False, "expected ValueError"
    except ValueError as exc:
        assert "required fields" in str(exc)


def test_run_file_ingest_tracks_insert_and_update_counts(tmp_path: Path) -> None:
    payload = [
        {
            "source_listing_id": "rea-1",
            "address": "10 Marine Parade",
            "suburb": "Southport",
            "state": "qld",
            "postcode": "4215",
            "status": "active",
            "listing_type": "sale",
            "asking_price": 800000,
        }
    ]
    input_path = tmp_path / "records.json"
    input_path.write_text(json.dumps(payload))

    store = InMemoryCanonicalStore()

    first = run_file_ingest(
        source_name="realestate_export",
        target_slice="southport-qld-4215",
        input_path=input_path,
        store=store,
    )
    second = run_file_ingest(
        source_name="realestate_export",
        target_slice="southport-qld-4215",
        input_path=input_path,
        store=store,
    )

    assert first.inserted_count == 1
    assert first.updated_count == 0
    assert second.inserted_count == 0
    assert second.updated_count == 1
    assert len(store.listings) == 1
    assert len(store.listing_snapshots) == 2


def test_run_file_ingest_skips_invalid_records(tmp_path: Path) -> None:
    payload = [
        {
            "source_listing_id": "rea-1",
            "address": "10 Marine Parade",
            "suburb": "Southport",
        },
        {
            "source_listing_id": "rea-2",
            "address": "",
            "suburb": "Southport",
        },
    ]
    input_path = tmp_path / "records.json"
    input_path.write_text(json.dumps(payload))

    result = run_file_ingest(
        source_name="realestate_export",
        target_slice="southport-qld-4215",
        input_path=input_path,
        store=InMemoryCanonicalStore(),
    )

    assert result.input_record_count == 2
    assert result.inserted_count == 1
    assert result.skipped_count == 1


def test_event_persistence_is_idempotent(tmp_path: Path) -> None:
    payload = [
        {
            "source_listing_id": "rea-sale-1",
            "address": "10 Marine Parade",
            "suburb": "Southport",
            "state": "QLD",
            "postcode": "4215",
            "listing_type": "sale",
            "status": "sold",
            "sold_price": 910000,
            "sold_date": "2024-01-10",
            "sale_event_id": "sale-evt-1",
        },
        {
            "source_listing_id": "rea-rent-1",
            "address": "12 Marine Parade",
            "suburb": "Southport",
            "state": "QLD",
            "postcode": "4215",
            "listing_type": "rent",
            "status": "leased",
            "leased_rent_weekly": 700,
            "leased_date": "2024-01-11",
            "rental_event_id": "rent-evt-1",
        },
    ]
    input_path = tmp_path / "events.json"
    input_path.write_text(json.dumps(payload))

    store = InMemoryCanonicalStore()
    first = run_file_ingest(
        source_name="realestate_export",
        target_slice="southport-qld-4215",
        input_path=input_path,
        store=store,
    )
    second = run_file_ingest(
        source_name="realestate_export",
        target_slice="southport-qld-4215",
        input_path=input_path,
        store=store,
    )

    assert first.sales_events_inserted_count == 1
    assert first.rental_events_inserted_count == 1
    assert second.sales_events_inserted_count == 0
    assert second.sales_events_updated_count == 1
    assert second.rental_events_inserted_count == 0
    assert second.rental_events_updated_count == 1
    assert len(store.sales_events) == 1
    assert len(store.rental_events) == 1


def test_run_southport_refresh_records_summary_and_blocks_active_lock(tmp_path: Path) -> None:
    input_path = tmp_path / "records.json"
    input_path.write_text(json.dumps([
        {
            "source_listing_id": "rea-1",
            "address": "10 Marine Parade",
            "suburb": "Southport",
            "state": "QLD",
            "postcode": "4215",
            "listing_type": "sale",
            "status": "sold",
            "sold_price": 900000,
        }
    ]))

    summary_path = tmp_path / "runs.json"
    lock_path = tmp_path / "southport.lock"
    store = InMemoryCanonicalStore()

    run_southport_refresh(
        source_name="realestate_export",
        input_path=input_path,
        store=store,
        lock_path=lock_path,
        summary_path=summary_path,
    )
    run_southport_refresh(
        source_name="realestate_export",
        input_path=input_path,
        store=store,
        lock_path=lock_path,
        summary_path=summary_path,
    )

    runs = json.loads(summary_path.read_text())
    assert len(runs) == 2
    assert runs[1]["artifact_type"] == "southport_refresh_run_summary"
    assert runs[1]["proof_slice_evidence"]["ingest"]["sales_events_inserted_count"] == 0
    assert runs[1]["proof_slice_evidence"]["ingest"]["sales_events_updated_count"] == 1
    assert runs[1]["production_readiness"]["broader_production_status"] == "not_yet_complete"
    assert "proof_slice_evidence" in runs[1]["operator_summary"]

    lock_path.write_text("active")
    with pytest.raises(RuntimeError):
        run_southport_refresh(
            source_name="realestate_export",
            input_path=input_path,
            store=store,
            lock_path=lock_path,
            summary_path=summary_path,
        )


def test_verify_southport_demo_slice_reports_minimum_failures(monkeypatch) -> None:
    monkeypatch.setattr(
        "property_advisor.ingest.collect_southport_row_counts",
        lambda **kwargs: {
            "suburbs": 1,
            "properties": 1,
            "listings": 1,
            "listing_snapshots": 1,
            "sales_events": 0,
            "rental_events": 0,
            "market_metrics": 0,
        },
    )

    result = verify_southport_demo_slice(
        database_url="postgresql://localhost/propertyadvisor",
        expected_minimums={"sales_events": 1},
    )

    assert result["proof_slice_evidence"]["meets_minimums"] is False
    assert result["proof_slice_evidence"]["minimum_failures"] == ["sales_events"]
    assert result["proof_slice_evidence"]["has_outcome_history"] is False
    assert result["production_readiness"]["proof_slice_status"] == "needs_attention"
    assert result["production_readiness"]["broader_production_status"] == "not_yet_complete"


def test_collect_southport_row_counts_queries_canonical_tables(monkeypatch) -> None:
    class _Cursor:
        query = ""

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, query, params=None):
            self.query = query

        def fetchone(self):
            return (1, 2, 3, 4, 5, 6, 7)

    class _Conn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def cursor(self):
            return _Cursor()

    monkeypatch.setattr("property_advisor.ingest.psycopg.connect", lambda *args, **kwargs: _Conn())
    counts = collect_southport_row_counts(database_url="postgresql://localhost/propertyadvisor")

    assert counts == {
        "suburbs": 1,
        "properties": 2,
        "listings": 3,
        "listing_snapshots": 4,
        "sales_events": 5,
        "rental_events": 6,
        "market_metrics": 7,
    }


def test_run_southport_backfill_and_verify_writes_report(tmp_path: Path, monkeypatch) -> None:
    input_path = tmp_path / "records.json"
    input_path.write_text(json.dumps([{"source_listing_id": "rea-1", "address": "10 Marine Parade", "suburb": "Southport"}]))
    summary_path = tmp_path / "runs.json"
    verification_path = tmp_path / "verification.json"

    monkeypatch.setattr(
        "property_advisor.ingest.run_southport_refresh",
        lambda **kwargs: {"artifact_type": "southport_refresh_run_summary", "target_slice": "southport-qld-4215", "operator_summary": {"headline": "refresh ok"}, "production_readiness": {"proof_slice_ready": True}, "proof_slice_evidence": {"ingest": {"inserted_count": 1}}},
    )
    monkeypatch.setattr(
        "property_advisor.ingest.verify_southport_demo_slice",
        lambda **kwargs: {"artifact_type": "southport_verification_report", "target_slice": "southport-qld-4215", "operator_summary": {"headline": "verification ok"}, "production_readiness": {"proof_slice_ready": True, "broader_production_status": "not_yet_complete"}, "proof_slice_evidence": {"meets_minimums": True, "row_counts": {"suburbs": 1}}},
    )

    result = run_southport_backfill_and_verify(
        source_name="realestate_export",
        input_path=input_path,
        database_url="postgresql://localhost/propertyadvisor",
        summary_path=summary_path,
        verification_path=verification_path,
    )

    assert result["proof_slice_evidence"]["verification"]["proof_slice_evidence"]["meets_minimums"] is True
    assert verification_path.exists()
    persisted = json.loads(verification_path.read_text())
    assert persisted["target_slice"] == "southport-qld-4215"
    assert persisted["artifact_type"] == "southport_backfill_verification_report"
    assert persisted["operator_summary"]["proof_slice_ready"] is True


def test_run_southport_refresh_artifact_separates_proof_slice_from_readiness(tmp_path: Path) -> None:
    input_path = tmp_path / "records.json"
    input_path.write_text(json.dumps([{
        "source_listing_id": "rea-1",
        "address": "10 Marine Parade",
        "suburb": "Southport",
        "state": "QLD",
        "postcode": "4215",
        "listing_type": "sale",
    }]))

    result = run_southport_refresh(
        source_name="realestate_export",
        input_path=input_path,
        store=InMemoryCanonicalStore(),
        summary_path=tmp_path / "runs.json",
    )

    assert result["scope"]["proof_slice_boundary"]["geography"]["suburb"] == "Southport"
    assert result["proof_slice_evidence"]["ingest"]["inserted_count"] == 1
    assert result["proof_slice_evidence"]["market_metrics"] is None
    assert result["production_readiness"]["proof_slice_ready"] is True
    assert result["production_readiness"]["broader_production_status"] == "not_yet_complete"
    assert any("whole-product production readiness" in note for note in result["production_readiness"]["notes"])
    assert result["operator_summary"]["safe_rerun_steps"][0].startswith("Confirm DATABASE_URL")


def test_verify_southport_demo_slice_artifact_contract_v2(monkeypatch) -> None:
    monkeypatch.setattr(
        "property_advisor.ingest.collect_southport_row_counts",
        lambda **kwargs: {
            "suburbs": 1,
            "properties": 2,
            "listings": 3,
            "listing_snapshots": 4,
            "sales_events": 1,
            "rental_events": 0,
            "market_metrics": 1,
        },
    )

    result = verify_southport_demo_slice(database_url="postgresql://localhost/propertyadvisor")

    assert result["artifact_contract_version"] == 2
    assert result["proof_slice_evidence"]["row_counts"]["sales_events"] == 1
    assert result["proof_slice_evidence"]["has_outcome_history"] is True
    assert result["operator_summary"]["proof_slice_ready"] is True
    assert result["scope"]["fallback_or_demo_only"]
