from __future__ import annotations

import json
from pathlib import Path

import pytest

from property_advisor.ingest import InMemoryCanonicalStore, parse_source_payload, run_file_ingest, run_southport_refresh


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
    assert runs[1]["ingest"]["sales_events_inserted_count"] == 0
    assert runs[1]["ingest"]["sales_events_updated_count"] == 1

    lock_path.write_text("active")
    with pytest.raises(RuntimeError):
        run_southport_refresh(
            source_name="realestate_export",
            input_path=input_path,
            store=store,
            lock_path=lock_path,
            summary_path=summary_path,
        )
