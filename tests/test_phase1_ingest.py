from __future__ import annotations

import json
from pathlib import Path

from property_advisor.ingest import InMemoryCanonicalStore, parse_source_payload, run_file_ingest


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
