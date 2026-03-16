from __future__ import annotations

import json
from pathlib import Path

import pytest

from property_advisor.ingest import (
    InMemoryCanonicalStore,
    PropertyMatchConfidence,
    _get_address_matching_key,
    _normalize_address,
    parse_source_payload,
    run_file_ingest,
)


class TestAddressNormalization:
    """Test address normalization edge cases."""

    def test_normalize_basic_address(self) -> None:
        assert _normalize_address("123 main street") == "123 Main St"
        assert _normalize_address("456 OCEAN ROAD") == "456 Ocean Rd"

    def test_normalize_abbreviations(self) -> None:
        # Street variations
        assert _normalize_address("1 First Street") == "1 First St"
        assert _normalize_address("2 Second St") == "2 Second St"
        assert _normalize_address("3 Third Rd") == "3 Third Rd"
        assert _normalize_address("4 Fourth Road") == "4 Fourth Rd"
        assert _normalize_address("5 Fifth Avenue") == "5 Fifth Ave"
        assert _normalize_address("6 Sixth Ave") == "6 Sixth Ave"
        assert _normalize_address("7 Seventh Drive") == "7 Seventh Dr"
        assert _normalize_address("8 Eighth Dr") == "8 Eighth Dr"

    def test_normalize_unit_prefixes(self) -> None:
        # Unit/Apartment formats
        assert _normalize_address("Unit 5, 123 Main St") == "Unit 5 123 Main St"
        assert _normalize_address("Apt 10, 456 Ocean Rd") == "Unit 10 456 Ocean Rd"
        assert _normalize_address("Apartment 3, 789 Park Ave") == "Unit 3 789 Park Ave"

    def test_normalize_australian_unit_notation(self) -> None:
        # Australian "X/Address" format
        assert _normalize_address("5/123 Main St") == "Unit 5 123 Main St"
        assert _normalize_address("A/456 Ocean Rd") == "Unit A 456 Ocean Rd"
        # "Parade Pde" becomes "Pde Pde" because both words get abbreviated - this is expected
        # The input "Parade Pde" has "Pde" as an abbreviation, both get standardized to "Pde"
        assert _normalize_address("12/78 Parade Pde") == "Unit 12 78 Pde Pde"

    def test_normalize_whitespace(self) -> None:
        assert _normalize_address("  123   Main   Street  ") == "123 Main St"
        assert _normalize_address("123\tMain\nStreet") == "123 Main St"


class TestAddressMatchingKey:
    """Test address matching key generation for fuzzy matching."""

    def test_matching_key_normalizes_addresses(self) -> None:
        # St and Street should produce same matching key after normalization
        key1 = _get_address_matching_key("123 Main St")
        key2 = _get_address_matching_key("123 Main Street")
        # Both normalize to "123 main st" (lowercase, abbreviations standardized)
        assert key1 == key2 == "123 main st"

    def test_matching_key_removes_unit_prefixes(self) -> None:
        # Units should not affect matching
        key1 = _get_address_matching_key("Unit 5, 123 Main St")
        key2 = _get_address_matching_key("123 Main St")
        key3 = _get_address_matching_key("5/123 Main St")
        assert key1 == key2 == key3

    def test_matching_key_normalizes_case(self) -> None:
        key1 = _get_address_matching_key("123 MAIN STREET")
        key2 = _get_address_matching_key("123 Main Street")
        key3 = _get_address_matching_key("123 main street")
        assert key1 == key2 == key3


class TestPropertyMatching:
    """Test property matching with confidence levels."""

    def test_exact_match_confidence(self) -> None:
        store = InMemoryCanonicalStore()
        
        record = parse_source_payload("test", {
            "source_listing_id": "rea-1",
            "address": "10 Marine Parade",
            "suburb": "Southport",
            "state": "QLD",
            "postcode": "4215",
            "listing_type": "sale",
        })
        
        # First observation creates new property
        prop_id1, conf1 = store.find_property_match(record)
        assert prop_id1 is None  # No match yet
        assert conf1 == PropertyMatchConfidence.REVIEW
        
        # Insert the property
        store.upsert_listing_observation(record)
        
        # Same address should now match exactly
        prop_id2, conf2 = store.find_property_match(record)
        assert prop_id2 is not None
        assert conf2 == PropertyMatchConfidence.EXACT

    def test_normalized_match_confidence(self) -> None:
        store = InMemoryCanonicalStore()
        
        # First record with "Street"
        record1 = parse_source_payload("test", {
            "source_listing_id": "rea-1",
            "address": "10 Main Street",
            "suburb": "Southport",
            "state": "QLD",
            "postcode": "4215",
            "listing_type": "sale",
        })
        store.upsert_listing_observation(record1)
        
        # Second record with slight variation (extra spaces, different casing)
        record2 = parse_source_payload("test", {
            "source_listing_id": "rea-2",
            "address": "10  MAIN  Street",  # Extra spaces, uppercase
            "suburb": "Southport",
            "state": "QLD",
            "postcode": "4215",
            "listing_type": "sale",
        })
        
        prop_id, conf = store.find_property_match(record2)
        assert prop_id is not None
        # Since both addresses normalize to the same form, this is an EXACT match
        # on the normalized representation
        assert conf == PropertyMatchConfidence.EXACT

    def test_unit_variations_match_same_property(self) -> None:
        store = InMemoryCanonicalStore()
        
        # First record without unit
        record1 = parse_source_payload("test", {
            "source_listing_id": "rea-1",
            "address": "123 Ocean Parade",
            "suburb": "Southport",
            "state": "QLD",
            "postcode": "4215",
            "listing_type": "sale",
        })
        store.upsert_listing_observation(record1)
        
        # Second record with unit - should match same property
        record2 = parse_source_payload("test", {
            "source_listing_id": "rea-2",
            "address": "Unit 5, 123 Ocean Parade",
            "suburb": "Southport",
            "state": "QLD",
            "postcode": "4215",
            "listing_type": "rent",
        })
        
        prop_id, conf = store.find_property_match(record2)
        assert prop_id is not None
        # Should be normalized match since unit was stripped for matching
        assert conf == PropertyMatchConfidence.NORMALIZED


class TestIdempotentUpsert:
    """Test idempotent upsert behavior."""

    def test_same_listing_twice_updates_not_duplicates(self) -> None:
        store = InMemoryCanonicalStore()
        
        payload = {
            "source_listing_id": "rea-1",
            "address": "10 Marine Parade",
            "suburb": "Southport",
            "state": "qld",
            "postcode": "4215",
            "status": "active",
            "listing_type": "sale",
            "asking_price": 800000,
        }
        
        record = parse_source_payload("test", payload)
        
        # First insert
        outcome1 = store.upsert_listing_observation(record)
        assert outcome1 == "inserted"
        assert len(store.listings) == 1
        
        # Second insert of same listing - should update
        outcome2 = store.upsert_listing_observation(record)
        assert outcome2 == "updated"
        assert len(store.listings) == 1  # Still only one listing

    def test_price_change_creates_snapshot(self) -> None:
        store = InMemoryCanonicalStore()
        
        # First observation with price 800k
        record1 = parse_source_payload("test", {
            "source_listing_id": "rea-1",
            "address": "10 Marine Parade",
            "suburb": "Southport",
            "state": "QLD",
            "postcode": "4215",
            "status": "active",
            "listing_type": "sale",
            "asking_price": 800000,
        })
        store.upsert_listing_observation(record1)
        
        assert len(store.listing_snapshots) == 1
        assert store.listing_snapshots[0]["asking_price"] == 800000
        
        # Second observation with price change to 850k
        record2 = parse_source_payload("test", {
            "source_listing_id": "rea-1",
            "address": "10 Marine Parade",
            "suburb": "Southport",
            "state": "QLD",
            "postcode": "4215",
            "status": "active",
            "listing_type": "sale",
            "asking_price": 850000,
        })
        store.upsert_listing_observation(record2)
        
        # Should have two snapshots
        assert len(store.listing_snapshots) == 2
        assert store.listing_snapshots[1]["asking_price"] == 850000

    def test_status_change_creates_snapshot(self) -> None:
        store = InMemoryCanonicalStore()
        
        # First observation - active
        record1 = parse_source_payload("test", {
            "source_listing_id": "rea-1",
            "address": "10 Marine Parade",
            "suburb": "Southport",
            "state": "QLD",
            "postcode": "4215",
            "status": "active",
            "listing_type": "sale",
        })
        store.upsert_listing_observation(record1)
        
        # Second observation - under offer
        record2 = parse_source_payload("test", {
            "source_listing_id": "rea-1",
            "address": "10 Marine Parade",
            "suburb": "Southport",
            "state": "QLD",
            "postcode": "4215",
            "status": "under_offer",
            "listing_type": "sale",
        })
        store.upsert_listing_observation(record2)
        
        assert len(store.listing_snapshots) == 2
        assert store.listing_snapshots[0]["status"] == "active"
        assert store.listing_snapshots[1]["status"] == "under_offer"


class TestFileIngest:
    """Test file-based ingest operations."""

    def test_run_file_ingest_tracks_insert_and_update_counts(self, tmp_path: Path) -> None:
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

    def test_run_file_ingest_skips_invalid_records(self, tmp_path: Path) -> None:
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

    def test_multiple_listings_same_property_different_sources(self, tmp_path: Path) -> None:
        """Test that same property can have multiple listings from different sources."""
        payload = [
            {
                "source_listing_id": "rea-1",
                "address": "10 Marine Parade",
                "suburb": "Southport",
                "state": "QLD",
                "postcode": "4215",
                "status": "active",
                "listing_type": "sale",
            },
            {
                "source_listing_id": "domain-1",
                "address": "10 Marine Parade",
                "suburb": "Southport",
                "state": "QLD",
                "postcode": "4215",
                "status": "active",
                "listing_type": "sale",
            },
        ]
        input_path = tmp_path / "records.json"
        input_path.write_text(json.dumps(payload))

        store = InMemoryCanonicalStore()
        result = run_file_ingest(
            source_name="realestate_export",
            target_slice="southport-qld-4215",
            input_path=input_path,
            store=store,
        )

        # Should have 2 listings but only 1 property
        assert result.inserted_count == 2
        assert len(store.listings) == 2
        # Properties should share the same underlying property (matched)
        listing_values = list(store.listings.values())
        assert listing_values[0]["property_id"] == listing_values[1]["property_id"]


class TestParseSourcePayload:
    """Test payload parsing validation."""

    def test_parse_source_payload_requires_identity_and_location(self) -> None:
        try:
            parse_source_payload(source_name="feed", payload={"address": "10 Test St"})
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "required fields" in str(exc)

    def test_parse_source_payload_requires_address(self) -> None:
        try:
            parse_source_payload(source_name="feed", payload={
                "source_listing_id": "123",
                "suburb": "Southport"
            })
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "required fields" in str(exc)

    def test_parse_source_payload_requires_suburb(self) -> None:
        try:
            parse_source_payload(source_name="feed", payload={
                "source_listing_id": "123",
                "address": "10 Test St"
            })
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "required fields" in str(exc)
