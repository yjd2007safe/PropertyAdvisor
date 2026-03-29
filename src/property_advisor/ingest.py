from __future__ import annotations

"""Ingestion entry points and Phase 1 canonical ingest foundations."""

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Optional, Protocol

import os

from property_advisor.market_metrics import generate_suburb_market_metrics
from property_advisor.pipeline.notification_hooks import PipelineNotificationHooks

import psycopg

from shared_notifications.openclaw_delivery import deliver_to_openclaw_session, resolve_session_key


@dataclass
class IngestJob:
    """Represents a unit of inbound source processing."""

    source_name: str
    payload: dict[str, Any]


@dataclass
class IngestRunMetadata:
    source_name: str
    target_slice: str
    started_at: datetime
    input_record_count: int = 0
    inserted_count: int = 0
    updated_count: int = 0
    skipped_count: int = 0
    error_count: int = 0
    sales_events_inserted_count: int = 0
    sales_events_updated_count: int = 0
    rental_events_inserted_count: int = 0
    rental_events_updated_count: int = 0
    market_metrics_inserted_count: int = 0
    market_metrics_updated_count: int = 0

    def as_dict(self) -> dict[str, Any]:
        return {
            "source_name": self.source_name,
            "target_slice": self.target_slice,
            "started_at": self.started_at.isoformat(),
            "input_record_count": self.input_record_count,
            "inserted_count": self.inserted_count,
            "updated_count": self.updated_count,
            "skipped_count": self.skipped_count,
            "error_count": self.error_count,
            "sales_events_inserted_count": self.sales_events_inserted_count,
            "sales_events_updated_count": self.sales_events_updated_count,
            "rental_events_inserted_count": self.rental_events_inserted_count,
            "rental_events_updated_count": self.rental_events_updated_count,
            "market_metrics_inserted_count": self.market_metrics_inserted_count,
            "market_metrics_updated_count": self.market_metrics_updated_count,
        }


@dataclass
class EventUpsertResult:
    sales_inserted: int = 0
    sales_updated: int = 0
    rentals_inserted: int = 0
    rentals_updated: int = 0


@dataclass
class CanonicalListingRecord:
    source_name: str
    source_listing_id: str
    listing_type: str
    status: str
    address_line_1: str
    suburb_name: str
    state_code: Optional[str]
    postcode: Optional[str]
    property_type: str
    bedrooms: Optional[int] = None
    bathrooms: Optional[float] = None
    listing_url: Optional[str] = None
    headline: Optional[str] = None
    description: Optional[str] = None
    asking_price: Optional[float] = None
    rent_price_weekly: Optional[float] = None
    observed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


def ingest_record(job: IngestJob) -> dict[str, Any]:
    """Return a raw record envelope suitable for normalization."""

    return {
        "source_name": job.source_name,
        "payload": job.payload,
    }


def _normalize_status(value: Any, listing_type: str) -> str:
    normalized = str(value or "active").strip().lower().replace(" ", "_")
    mapping = {
        "for_sale": "active",
        "for_rent": "active",
        "new": "active",
        "withdrawn": "withdrawn",
        "leased": "leased",
        "sold": "sold",
        "under_offer": "under_offer",
        "under_contract": "under_offer",
        "off_market": "expired",
    }
    normalized = mapping.get(normalized, normalized)
    valid = {"active", "under_offer", "withdrawn", "sold", "leased", "expired"}
    if normalized not in valid:
        return "active"
    if listing_type == "sale" and normalized == "leased":
        return "expired"
    if listing_type == "rent" and normalized == "sold":
        return "expired"
    return normalized


def _normalize_listing_type(value: Any) -> str:
    normalized = str(value or "sale").strip().lower()
    if normalized in {"sale", "buy"}:
        return "sale"
    if normalized in {"rent", "rental", "lease"}:
        return "rent"
    return "sale"


def _normalize_text(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


# Address abbreviation mapping for normalization
_ADDRESS_ABBREVIATIONS = {
    # Street types
    "street": "St",
    "st": "St",
    "road": "Rd",
    "rd": "Rd",
    "avenue": "Ave",
    "ave": "Ave",
    "av": "Ave",
    "drive": "Dr",
    "dr": "Dr",
    "court": "Ct",
    "ct": "Ct",
    "lane": "Ln",
    "ln": "Ln",
    "place": "Pl",
    "pl": "Pl",
    "parade": "Pde",
    "pde": "Pde",
    "terrace": "Tce",
    "tce": "Tce",
    "highway": "Hwy",
    "hwy": "Hwy",
    "boulevard": "Blvd",
    "blvd": "Blvd",
    "crescent": "Cres",
    "cres": "Cres",
    "circuit": "Cct",
    "cct": "Cct",
    "close": "Cl",
    "cl": "Cl",
    "grove": "Gr",
    "gr": "Gr",
    "heights": "Hts",
    "hts": "Hts",
    "expressway": "Expy",
    "expy": "Expy",
    # Unit/Apartment indicators
    "apartment": "Apt",
    "apt": "Apt",
    "unit": "Unit",
    "flat": "Unit",
    "suite": "Ste",
    "ste": "Ste",
    "level": "Lvl",
    "lvl": "Lvl",
    "shop": "Shop",
    "lot": "Lot",
    # Directions
    "north": "N",
    "n": "N",
    "south": "S",
    "s": "S",
    "east": "E",
    "e": "E",
    "west": "W",
    "w": "W",
}


def _normalize_address(value: Any) -> str:
    """Normalize address with abbreviation standardization.
    
    Handles:
    - Whitespace normalization
    - Abbreviation standardization (St/Street, Rd/Road, etc.)
    - Unit/Apartment number extraction (preserved but standardized format)
    - Title casing
    """
    import re
    
    if not value:
        return ""
    
    text = str(value).strip()
    
    # Extract unit number if present (e.g., "Unit 5, 123 Main St" or "5/123 Main St")
    unit_prefix = ""
    
    # Check for "Unit X, " or "Apt X, " prefix
    unit_match = re.match(r'^(unit|apt|apartment|flat|suite|ste|shop|lot)\s*(\w+)[,\s]+(.+)$', text, re.IGNORECASE)
    if unit_match:
        unit_prefix = f"Unit {unit_match.group(2)} "
        text = unit_match.group(3)
    else:
        # Check for "X/123" format (Australian unit notation) - but only if it looks like a unit number
        # (starts with digit or single letter, followed by slash and then a street number)
        slash_match = re.match(r'^([0-9]+|[A-Za-z])/(\d+\s+.+)$', text)
        if slash_match:
            unit_prefix = f"Unit {slash_match.group(1)} "
            text = slash_match.group(2)
    
    # Normalize whitespace
    text = " ".join(text.split())
    
    # Standardize abbreviations - only replace full words at end of address
    # Process from end to avoid double-expansion (e.g., "Parade Pde" -> "Pde Pde")
    words = text.split()
    normalized_words = []
    
    for i, word in enumerate(words):
        lower_word = word.lower().rstrip(",.")
        # Only abbreviate if it's a street type at the end or a unit indicator
        if lower_word in _ADDRESS_ABBREVIATIONS:
            # Check if this word was already processed as an abbreviation
            # (avoid double-expansion by checking if result would be different)
            abbrev = _ADDRESS_ABBREVIATIONS[lower_word]
            if abbrev.lower() != lower_word:
                normalized_words.append(abbrev)
            else:
                normalized_words.append(word)
        else:
            normalized_words.append(word)
    
    text = " ".join(normalized_words)
    
    # Apply title case
    text = text.title()
    
    # Add unit prefix back if present
    if unit_prefix:
        text = unit_prefix + text
    
    return text


def _get_address_matching_key(address: str) -> str:
    """Generate a normalized matching key for address comparison.
    
    This removes unit numbers and standardizes format for fuzzy matching.
    All abbreviations are expanded to their full form for consistent matching.
    """
    import re
    
    # First normalize the address to standardize abbreviations
    normalized = _normalize_address(address)
    text = normalized.lower()
    
    # Remove unit prefixes like "unit 5 " or "5/123 " (Australian notation)
    text = re.sub(r'^(unit|apt|apartment|flat|suite|ste|shop|lot)\s*\w+\s+', '', text)
    
    # Normalize whitespace and punctuation
    text = re.sub(r'[\s,\.]+', ' ', text).strip()
    
    return text


def _normalize_suburb(value: Any) -> str:
    return " ".join(str(value or "").split()).title()


def _normalize_state(value: Any) -> Optional[str]:
    text = _normalize_text(value)
    return text.upper() if text else None


def _normalize_postcode(value: Any) -> Optional[str]:
    text = _normalize_text(value)
    if not text:
        return None
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits[:4] if digits else None


def parse_source_payload(source_name: str, payload: dict[str, Any]) -> CanonicalListingRecord:
    listing_type = _normalize_listing_type(payload.get("listing_type"))
    source_listing_id = _normalize_text(payload.get("source_listing_id") or payload.get("external_id"))
    address_line_1 = _normalize_address(payload.get("address") or payload.get("address_line_1"))
    suburb_name = _normalize_suburb(payload.get("suburb") or payload.get("city"))

    if not source_listing_id or not address_line_1 or not suburb_name:
        raise ValueError("record missing one of required fields: source_listing_id/external_id, address, suburb/city")

    return CanonicalListingRecord(
        source_name=source_name,
        source_listing_id=source_listing_id,
        listing_type=listing_type,
        status=_normalize_status(payload.get("status"), listing_type=listing_type),
        address_line_1=address_line_1,
        suburb_name=suburb_name,
        state_code=_normalize_state(payload.get("state") or payload.get("state_code")),
        postcode=_normalize_postcode(payload.get("postcode") or payload.get("postal_code")),
        property_type=_normalize_text(payload.get("property_type")) or "house",
        bedrooms=payload.get("beds") or payload.get("bedrooms"),
        bathrooms=payload.get("baths") or payload.get("bathrooms"),
        listing_url=_normalize_text(payload.get("listing_url")),
        headline=_normalize_text(payload.get("headline")),
        description=_normalize_text(payload.get("description")),
        asking_price=payload.get("asking_price"),
        rent_price_weekly=payload.get("rent_price_weekly"),
    )


def _parse_event_date(value: Any) -> Optional[date]:
    if value in (None, ""):
        return None
    text = str(value).strip()
    if not text:
        return None
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        return None


def _extract_sale_event(raw: dict[str, Any], *, source_name: str, property_id: str, listing_id: str) -> Optional[dict[str, Any]]:
    status = _normalize_status(raw.get("status"), _normalize_listing_type(raw.get("listing_type")))
    sold_price = raw.get("sold_price") or raw.get("sale_price")
    sold_date = _parse_event_date(raw.get("sold_date") or raw.get("sale_date"))
    if status != "sold" and sold_price is None and sold_date is None:
        return None

    source_event_id = _normalize_text(raw.get("sale_event_id") or raw.get("source_event_id"))
    if not source_event_id:
        source_event_id = f"sale:{source_name}:{_normalize_text(raw.get('source_listing_id') or raw.get('external_id')) or listing_id}"

    return {
        "property_id": property_id,
        "listing_id": listing_id,
        "sale_date": sold_date or datetime.now(timezone.utc).date(),
        "sale_price": sold_price,
        "sale_method": _normalize_text(raw.get("sale_method")),
        "days_on_market": raw.get("days_on_market"),
        "source_name": source_name,
        "source_event_id": source_event_id,
        "metadata": {"raw": raw},
    }


def _extract_rental_event(raw: dict[str, Any], *, source_name: str, property_id: str, listing_id: str) -> Optional[dict[str, Any]]:
    status = _normalize_status(raw.get("status"), _normalize_listing_type(raw.get("listing_type")))
    weekly_rent = raw.get("leased_price_weekly") or raw.get("leased_rent_weekly") or raw.get("rent_price_weekly")
    lease_date = _parse_event_date(raw.get("leased_date") or raw.get("lease_date"))
    if status != "leased" and weekly_rent is None and lease_date is None:
        return None

    source_event_id = _normalize_text(raw.get("rental_event_id") or raw.get("lease_event_id") or raw.get("source_event_id"))
    if not source_event_id:
        source_event_id = f"rent:{source_name}:{_normalize_text(raw.get('source_listing_id') or raw.get('external_id')) or listing_id}"

    return {
        "property_id": property_id,
        "listing_id": listing_id,
        "lease_date": lease_date or datetime.now(timezone.utc).date(),
        "weekly_rent": weekly_rent,
        "days_on_market": raw.get("days_on_market"),
        "source_name": source_name,
        "source_event_id": source_event_id,
        "metadata": {"raw": raw},
    }


class PropertyMatchConfidence:
    """Confidence levels for property matching."""
    EXACT = "exact"           # Exact address match (case-insensitive)
    NORMALIZED = "normalized"  # Normalized form matches (St/Street equivalent)
    REVIEW = "review"         # Low confidence, needs manual review


class CanonicalStore(Protocol):
    def upsert_listing_observation(self, record: CanonicalListingRecord) -> str:
        ...

    def upsert_outcome_events(self, *, raw_payload: dict[str, Any], record: CanonicalListingRecord) -> EventUpsertResult:
        ...

    def find_property_match(
        self,
        record: CanonicalListingRecord
    ) -> tuple[Optional[str], str]:
        """Find matching property_id and return confidence level.

        Returns: (property_id or None, confidence level)
        """
        ...


class InMemoryCanonicalStore:
    """Test-friendly canonical store with idempotent listing upsert behavior."""

    def __init__(self) -> None:
        self.suburbs: dict[tuple[str, Optional[str], Optional[str]], str] = {}
        # Properties stored by normalized key for matching
        self.properties: dict[str, dict[str, Any]] = {}  # key -> {id, address, suburb, state, postcode}
        self.listings: dict[tuple[str, str], dict[str, Any]] = {}
        self.listing_snapshots: list[dict[str, Any]] = []
        self.sales_events: dict[tuple[str, str], dict[str, Any]] = {}
        self.rental_events: dict[tuple[str, str], dict[str, Any]] = {}
        self._property_counter = 0

    def _make_property_key(self, address: str, suburb: str, state: Optional[str], postcode: Optional[str]) -> str:
        """Create a matching key for property lookup."""
        return f"{address.lower().strip()}|{suburb.lower().strip()}|{state or ''}|{postcode or ''}"

    def find_property_match(
        self, 
        record: CanonicalListingRecord
    ) -> tuple[Optional[str], str]:
        """Find matching property with confidence scoring.
        
        Matching strategy:
        1. EXACT: Exact normalized address match
        2. NORMALIZED: Address matching key matches (handles St/Street variations)
        3. REVIEW: No confident match found
        """
        # Try exact match first
        exact_key = self._make_property_key(
            record.address_line_1, 
            record.suburb_name, 
            record.state_code, 
            record.postcode
        )
        if exact_key in self.properties:
            return self.properties[exact_key]["id"], PropertyMatchConfidence.EXACT
        
        # Try normalized match (handles abbreviations)
        matching_key = _get_address_matching_key(record.address_line_1)
        norm_key = self._make_property_key(
            matching_key,
            record.suburb_name,
            record.state_code,
            record.postcode
        )
        
        for key, prop in self.properties.items():
            stored_matching_key = _get_address_matching_key(prop["address"])
            if (stored_matching_key == matching_key and 
                prop["suburb"].lower() == record.suburb_name.lower() and
                prop["state"] == record.state_code and
                prop["postcode"] == record.postcode):
                return prop["id"], PropertyMatchConfidence.NORMALIZED
        
        return None, PropertyMatchConfidence.REVIEW

    def upsert_listing_observation(self, record: CanonicalListingRecord) -> str:
        suburb_key = (record.suburb_name, record.state_code, record.postcode)
        suburb_id = self.suburbs.setdefault(suburb_key, f"suburb-{len(self.suburbs) + 1}")

        # Find existing property or create new one
        property_id, confidence = self.find_property_match(record)
        
        if property_id is None:
            self._property_counter += 1
            property_id = f"property-{self._property_counter}"
            prop_key = self._make_property_key(
                record.address_line_1,
                record.suburb_name,
                record.state_code,
                record.postcode
            )
            self.properties[prop_key] = {
                "id": property_id,
                "address": record.address_line_1,
                "suburb": record.suburb_name,
                "state": record.state_code,
                "postcode": record.postcode,
                "confidence": confidence,
            }

        listing_key = (record.source_name, record.source_listing_id)
        current = self.listings.get(listing_key)
        if current is None:
            self.listings[listing_key] = {
                "id": f"listing-{len(self.listings) + 1}",
                "suburb_id": suburb_id,
                "property_id": property_id,
                "status": record.status,
                "asking_price": record.asking_price,
                "rent_price_weekly": record.rent_price_weekly,
                "first_seen_at": record.observed_at,
                "last_seen_at": record.observed_at,
            }
            change_type = "inserted"
        else:
            current["status"] = record.status
            current["asking_price"] = record.asking_price
            current["rent_price_weekly"] = record.rent_price_weekly
            current["last_seen_at"] = record.observed_at
            change_type = "updated"

        self.listing_snapshots.append(
            {
                "listing_id": self.listings[listing_key]["id"],
                "observed_at": record.observed_at,
                "status": record.status,
                "asking_price": record.asking_price,
                "headline": record.headline,
                "description": record.description,
            }
        )
        return change_type

    def upsert_outcome_events(self, *, raw_payload: dict[str, Any], record: CanonicalListingRecord) -> EventUpsertResult:
        listing_key = (record.source_name, record.source_listing_id)
        listing = self.listings.get(listing_key)
        if listing is None:
            return EventUpsertResult()

        sale_event = _extract_sale_event(raw_payload, source_name=record.source_name, property_id=listing["property_id"], listing_id=listing["id"])
        rental_event = _extract_rental_event(raw_payload, source_name=record.source_name, property_id=listing["property_id"], listing_id=listing["id"])
        result = EventUpsertResult()

        if sale_event is not None:
            key = (sale_event["source_name"], sale_event["source_event_id"])
            if key in self.sales_events:
                self.sales_events[key].update(sale_event)
                result.sales_updated = 1
            else:
                self.sales_events[key] = sale_event
                result.sales_inserted = 1

        if rental_event is not None:
            key = (rental_event["source_name"], rental_event["source_event_id"])
            if key in self.rental_events:
                self.rental_events[key].update(rental_event)
                result.rentals_updated = 1
            else:
                self.rental_events[key] = rental_event
                result.rentals_inserted = 1

        return result



class PostgresCanonicalStore:
    def __init__(self, database_url: str):
        self.database_url = database_url

    def find_property_match(
        self, 
        record: CanonicalListingRecord
    ) -> tuple[Optional[str], str]:
        """Find matching property in postgres with confidence scoring.
        
        Matching strategy:
        1. EXACT: Exact normalized_address match
        2. NORMALIZED: matching_key matches (handles St/Street variations)
        3. REVIEW: No confident match found
        """
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                # Try exact match first using normalized_address
                normalized_address = f"{record.address_line_1.lower()}|{record.suburb_name.lower()}|{record.state_code or ''}|{record.postcode or ''}"
                cur.execute(
                    """
                    SELECT id FROM properties 
                    WHERE normalized_address = %s
                    ORDER BY created_at ASC
                    LIMIT 1
                    """,
                    (normalized_address,)
                )
                result = cur.fetchone()
                if result:
                    return result[0], PropertyMatchConfidence.EXACT
                
                # Try normalized match using matching_key
                matching_key = _get_address_matching_key(record.address_line_1)
                cur.execute(
                    """
                    SELECT id FROM properties 
                    WHERE matching_key = %s
                      AND suburb_name = %s
                      AND (state_code = %s OR (state_code IS NULL AND %s IS NULL))
                      AND (postcode = %s OR (postcode IS NULL AND %s IS NULL))
                    ORDER BY created_at ASC
                    LIMIT 1
                    """,
                    (matching_key, record.suburb_name, record.state_code, record.state_code,
                     record.postcode, record.postcode)
                )
                result = cur.fetchone()
                if result:
                    return result[0], PropertyMatchConfidence.NORMALIZED
                
                return None, PropertyMatchConfidence.REVIEW

    def upsert_listing_observation(self, record: CanonicalListingRecord) -> str:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    insert into suburbs (country_code, state_code, suburb_name, postcode)
                    values ('AU', %s, %s, %s)
                    on conflict (country_code, state_code, suburb_name, postcode)
                    do update set updated_at = now()
                    returning id
                    """,
                    (record.state_code, record.suburb_name, record.postcode),
                )
                suburb_id = cur.fetchone()[0]

                # Find or create property with confidence tracking
                property_id, confidence = self.find_property_match(record)
                
                if property_id is None:
                    normalized_address = f"{record.address_line_1.lower()}|{record.suburb_name.lower()}|{record.state_code or ''}|{record.postcode or ''}"
                    matching_key = _get_address_matching_key(record.address_line_1)
                    
                    cur.execute(
                        """
                        insert into properties (
                            suburb_id, address_line_1, suburb_name, state_code, postcode,
                            normalized_address, matching_key, property_type, bedrooms, bathrooms, 
                            source_confidence
                        )
                        values (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                        on conflict do nothing
                        """,
                        (
                            suburb_id,
                            record.address_line_1,
                            record.suburb_name,
                            record.state_code,
                            record.postcode,
                            normalized_address,
                            matching_key,
                            record.property_type,
                            record.bedrooms,
                            record.bathrooms,
                            confidence,
                        ),
                    )

                    cur.execute(
                        """
                        select id from properties
                        where normalized_address = %s
                        order by created_at asc
                        limit 1
                        """,
                        (normalized_address,),
                    )
                    property_id = cur.fetchone()[0]

                cur.execute(
                    """
                    insert into listings (
                        property_id, source_name, source_listing_id, listing_type, status,
                        listing_url, first_seen_at, last_seen_at, asking_price, rent_price_weekly,
                        headline, description
                    )
                    values (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s,
                        %s, %s
                    )
                    on conflict (source_name, source_listing_id)
                    do update set
                        property_id = excluded.property_id,
                        status = excluded.status,
                        listing_url = excluded.listing_url,
                        last_seen_at = excluded.last_seen_at,
                        asking_price = excluded.asking_price,
                        rent_price_weekly = excluded.rent_price_weekly,
                        headline = excluded.headline,
                        description = excluded.description,
                        off_market_at = case
                            when excluded.status in ('sold', 'leased', 'withdrawn', 'expired') then excluded.last_seen_at
                            else listings.off_market_at
                        end,
                        updated_at = now()
                    returning id, (xmax = 0) as inserted
                    """,
                    (
                        property_id,
                        record.source_name,
                        record.source_listing_id,
                        record.listing_type,
                        record.status,
                        record.listing_url,
                        record.observed_at,
                        record.observed_at,
                        record.asking_price,
                        record.rent_price_weekly,
                        record.headline,
                        record.description,
                    ),
                )
                listing_id, inserted = cur.fetchone()

                cur.execute(
                    """
                    insert into listing_snapshots (
                        listing_id, observed_at, status, asking_price, rent_price_weekly,
                        headline, description, metadata
                    ) values (%s, %s, %s, %s, %s, %s, %s, '{}'::jsonb)
                    """,
                    (
                        listing_id,
                        record.observed_at,
                        record.status,
                        record.asking_price,
                        record.rent_price_weekly,
                        record.headline,
                        record.description,
                    ),
                )
            conn.commit()
        return "inserted" if inserted else "updated"


    def upsert_outcome_events(self, *, raw_payload: dict[str, Any], record: CanonicalListingRecord) -> EventUpsertResult:
        with psycopg.connect(self.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select id, property_id from listings
                    where source_name = %s and source_listing_id = %s
                    limit 1
                    """,
                    (record.source_name, record.source_listing_id),
                )
                listing_row = cur.fetchone()
                if listing_row is None:
                    return EventUpsertResult()
                listing_id, property_id = listing_row

                result = EventUpsertResult()
                sale_event = _extract_sale_event(raw_payload, source_name=record.source_name, property_id=property_id, listing_id=listing_id)
                if sale_event is not None:
                    cur.execute(
                        """
                        insert into sales_events (
                            property_id, listing_id, sale_date, sale_price, sale_method,
                            days_on_market, source_name, source_event_id, metadata
                        )
                        values (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        on conflict (source_name, source_event_id)
                        do update set
                            property_id = excluded.property_id,
                            listing_id = excluded.listing_id,
                            sale_date = excluded.sale_date,
                            sale_price = excluded.sale_price,
                            sale_method = excluded.sale_method,
                            days_on_market = excluded.days_on_market,
                            metadata = excluded.metadata
                        returning (xmax = 0)
                        """,
                        (
                            sale_event["property_id"],
                            sale_event["listing_id"],
                            sale_event["sale_date"],
                            sale_event["sale_price"],
                            sale_event["sale_method"],
                            sale_event["days_on_market"],
                            sale_event["source_name"],
                            sale_event["source_event_id"],
                            json.dumps(sale_event["metadata"]),
                        ),
                    )
                    if cur.fetchone()[0]:
                        result.sales_inserted = 1
                    else:
                        result.sales_updated = 1

                rental_event = _extract_rental_event(raw_payload, source_name=record.source_name, property_id=property_id, listing_id=listing_id)
                if rental_event is not None:
                    cur.execute(
                        """
                        insert into rental_events (
                            property_id, listing_id, lease_date, weekly_rent,
                            days_on_market, source_name, source_event_id, metadata
                        )
                        values (%s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                        on conflict (source_name, source_event_id)
                        do update set
                            property_id = excluded.property_id,
                            listing_id = excluded.listing_id,
                            lease_date = excluded.lease_date,
                            weekly_rent = excluded.weekly_rent,
                            days_on_market = excluded.days_on_market,
                            metadata = excluded.metadata
                        returning (xmax = 0)
                        """,
                        (
                            rental_event["property_id"],
                            rental_event["listing_id"],
                            rental_event["lease_date"],
                            rental_event["weekly_rent"],
                            rental_event["days_on_market"],
                            rental_event["source_name"],
                            rental_event["source_event_id"],
                            json.dumps(rental_event["metadata"]),
                        ),
                    )
                    if cur.fetchone()[0]:
                        result.rentals_inserted = 1
                    else:
                        result.rentals_updated = 1
            conn.commit()
        return result


@dataclass
class RefreshRunSummary:
    target_slice: str
    started_at: datetime
    completed_at: datetime
    input_path: str
    lock_path: str
    ingest: dict[str, Any]


DEFAULT_SOUTHPORT_ROW_COUNT_MINIMUMS: dict[str, int] = {
    "suburbs": 1,
    "properties": 1,
    "listings": 1,
    "listing_snapshots": 1,
    "sales_events": 0,
    "rental_events": 0,
    "market_metrics": 0,
}

SOUTHPORT_SLICE_ID = "southport-qld-4215"
SOUTHPORT_PROOF_SLICE_BOUNDARY = {
    "geography": {"suburb": "Southport", "state": "QLD", "postcode": "4215", "country": "AU"},
    "included_real_data_tables": [
        "suburbs",
        "properties",
        "listings",
        "listing_snapshots",
        "sales_events",
        "rental_events",
        "market_metrics",
    ],
    "excluded_broader_production_capabilities": [
        "additional suburbs or postcodes",
        "broad-market completeness checks",
        "operator-independent source acquisition",
        "frontend-wide postgres cutover",
        "non-Southport demo validation",
    ],
}
SOUTHPORT_REAL_DATA_BACKED_NOW = [
    "Canonical suburb/property/listing persistence for Southport, QLD 4215",
    "Listing snapshot history for repeat refreshes on the frozen Southport slice",
    "Sales/rental outcome event persistence when the payload includes sold/leased fields",
    "First-pass Southport market metric persistence when --database-url is provided",
    "Row-count verification for the canonical Southport proof-slice tables",
]
SOUTHPORT_FALLBACK_OR_DEMO_ONLY = [
    "Payload completeness and market coverage remain operator-supplied rather than guaranteed by the pipeline",
    "Broader production readiness outside Southport still depends on later slice expansion and read-path hardening",
    "Demo verification confirms minimum evidence for the frozen slice, not full-market completeness or SLA-backed operations",
]
SOUTHPORT_SAFE_RERUN_STEPS = [
    "Confirm DATABASE_URL points at the intended environment before writing",
    "Run refresh-southport with the canonical payload for Southport only",
    "Review the appended refresh artifact for ingest counts and market_metrics status",
    "Run backfill-verify-southport or verify-southport-demo to confirm proof-slice evidence still meets minimums",
]


def _build_southport_notification_hooks() -> PipelineNotificationHooks:
    session_key = resolve_session_key()
    delivery_targets = []
    origin = {
        "channel": "local_pipeline",
        "session_key": session_key or "southport-demo-pipeline",
        "reply_mode": "reply" if session_key else "artifact_only",
    }
    delivery_handler = None
    if session_key:
        delivery_targets.append(
            {
                "channel": "openclaw-session",
                "session_key": session_key,
                "reply_mode": "reply",
            }
        )
        timeout_seconds = int(os.environ.get("OPENCLAW_NOTIFICATION_TIMEOUT_SECONDS", "0") or "0")
        delivery_handler = lambda artifact: deliver_to_openclaw_session(
            artifact,
            session_key=session_key,
            timeout_seconds=timeout_seconds,
        )

    return PipelineNotificationHooks(
        project="PropertyAdvisor",
        phase="phase1",
        round="round6",
        slice_id=SOUTHPORT_SLICE_ID,
        origin=origin,
        delivery_targets=delivery_targets,
        delivery_handler=delivery_handler,
    )


def _isoformat_utc(value: datetime) -> str:
    return value.astimezone(timezone.utc).isoformat()


def _build_southport_scope_descriptor() -> dict[str, Any]:
    return {
        "slice_id": SOUTHPORT_SLICE_ID,
        "proof_slice_boundary": SOUTHPORT_PROOF_SLICE_BOUNDARY,
        "real_data_backed_now": SOUTHPORT_REAL_DATA_BACKED_NOW,
        "fallback_or_demo_only": SOUTHPORT_FALLBACK_OR_DEMO_ONLY,
    }


def _build_southport_operator_readiness(*, proof_slice_ready: bool, has_market_metrics: bool, has_outcome_history: bool | None = None) -> dict[str, Any]:
    proof_slice_status = "ready" if proof_slice_ready else "needs_attention"
    notes = [
        "Proof-slice evidence covers only the frozen Southport slice and should not be read as whole-product production readiness.",
        "Broader production readiness still requires additional slices, feed coverage, and postgres-backed read-path rollout beyond this artifact.",
    ]
    if not has_market_metrics:
        notes.append("Market metrics are skipped when refresh runs without --database-url, so evidence remains ingest-only for that run.")
    if has_outcome_history is False:
        notes.append("Outcome-history evidence is currently absent in row counts; sold/leased rows depend on source payload coverage.")
    return {
        "proof_slice_status": proof_slice_status,
        "proof_slice_ready": proof_slice_ready,
        "broader_production_status": "not_yet_complete",
        "notes": notes,
    }


def _build_refresh_operator_summary(*, ingest: dict[str, Any], market_metrics: Optional[dict[str, Any]], proof_slice_ready: bool) -> dict[str, Any]:
    market_metrics_status = "persisted" if market_metrics else "skipped_no_database"
    return {
        "headline": f"Southport refresh completed for proof slice {SOUTHPORT_SLICE_ID}",
        "proof_slice_evidence": [
            f"Listings inserted={ingest['inserted_count']} updated={ingest['updated_count']} skipped={ingest['skipped_count']} errors={ingest['error_count']}",
            f"Outcome events sales(inserted={ingest['sales_events_inserted_count']}, updated={ingest['sales_events_updated_count']}) rentals(inserted={ingest['rental_events_inserted_count']}, updated={ingest['rental_events_updated_count']})",
            f"Market metrics status: {market_metrics_status}",
        ],
        "production_readiness_boundary": SOUTHPORT_FALLBACK_OR_DEMO_ONLY,
        "safe_rerun_steps": SOUTHPORT_SAFE_RERUN_STEPS,
        "proof_slice_ready": proof_slice_ready,
    }


def _build_verification_operator_summary(*, row_counts: dict[str, int], failures: list[str], proof_slice_ready: bool, has_outcome_history: bool) -> dict[str, Any]:
    headline_status = "passed" if proof_slice_ready else "needs attention"
    return {
        "headline": f"Southport proof-slice verification {headline_status}",
        "proof_slice_evidence": [
            "Row counts: " + ", ".join(f"{table}={count}" for table, count in row_counts.items()),
            f"Outcome history present: {'yes' if has_outcome_history else 'no'}",
            f"Minimum failures: {', '.join(failures) if failures else 'none'}",
        ],
        "production_readiness_boundary": SOUTHPORT_FALLBACK_OR_DEMO_ONLY,
        "safe_rerun_steps": SOUTHPORT_SAFE_RERUN_STEPS,
        "proof_slice_ready": proof_slice_ready,
    }


def run_southport_refresh(
    *,
    source_name: str,
    input_path: Path,
    store: CanonicalStore,
    lock_path: Path = Path(".refresh-southport.lock"),
    summary_path: Optional[Path] = None,
    database_url: Optional[str] = None,
    metric_period: str = "monthly",
    metric_period_start: Optional[date] = None,
    metric_period_end: Optional[date] = None,
) -> dict[str, Any]:
    started_at = datetime.now(timezone.utc)
    notification_hooks = _build_southport_notification_hooks()
    if lock_path.exists():
        notification_hooks.blocked(
            summary=f"Southport refresh blocked for {SOUTHPORT_SLICE_ID}",
            details={
                "lock_path": str(lock_path),
                "source_name": source_name,
            },
        )
        raise RuntimeError(
            f"refresh lock exists at {lock_path}. Remove it if no run is active, then rerun."
        )

    notification_hooks.round_started(
        summary=f"Southport refresh started for {SOUTHPORT_SLICE_ID}",
        details={
            "input_path": str(input_path),
            "lock_path": str(lock_path),
            "source_name": source_name,
        },
    )
    lock_path.write_text(started_at.isoformat())
    try:
        ingest_result = run_file_ingest(
            source_name=source_name,
            target_slice=SOUTHPORT_SLICE_ID,
            input_path=input_path,
            store=store,
        )
        metrics_result: Optional[dict[str, Any]] = None
        if database_url:
            period_start = metric_period_start or date(started_at.year, started_at.month, 1)
            period_end = metric_period_end or started_at.date()
            metrics_result = generate_southport_market_metrics(
                database_url=database_url,
                period_start=period_start,
                period_end=period_end,
                metric_period=metric_period,
            )
            if metrics_result["inserted"]:
                ingest_result.market_metrics_inserted_count += 1
            else:
                ingest_result.market_metrics_updated_count += 1

        completed_at = datetime.now(timezone.utc)
        summary = RefreshRunSummary(
            target_slice=SOUTHPORT_SLICE_ID,
            started_at=started_at,
            completed_at=completed_at,
            input_path=str(input_path),
            lock_path=str(lock_path),
            ingest=ingest_result.as_dict(),
        )
        summary_dict = {
            "artifact_type": "southport_refresh_run_summary",
            "artifact_contract_version": 2,
            "target_slice": summary.target_slice,
            "scope": _build_southport_scope_descriptor(),
            "run": {
                "started_at": _isoformat_utc(summary.started_at),
                "completed_at": _isoformat_utc(summary.completed_at),
                "duration_seconds": round((completed_at - started_at).total_seconds(), 3),
                "input_path": summary.input_path,
                "lock_path": summary.lock_path,
                "source_name": source_name,
            },
            "proof_slice_evidence": {
                "ingest": summary.ingest,
                "market_metrics": metrics_result,
            },
            "production_readiness": _build_southport_operator_readiness(
                proof_slice_ready=summary.ingest["error_count"] == 0,
                has_market_metrics=metrics_result is not None,
            ),
            "operator_summary": _build_refresh_operator_summary(
                ingest=summary.ingest,
                market_metrics=metrics_result,
                proof_slice_ready=summary.ingest["error_count"] == 0,
            ),
        }
        if summary_path is not None:
            history: list[dict[str, Any]] = []
            if summary_path.exists():
                history = json.loads(summary_path.read_text())
                if not isinstance(history, list):
                    history = []
            history.append(summary_dict)
            summary_path.parent.mkdir(parents=True, exist_ok=True)
            summary_path.write_text(json.dumps(history, indent=2))
        notification_hooks.completed(
            summary=f"Southport refresh completed for {SOUTHPORT_SLICE_ID}",
            details={
                "source_name": source_name,
                "input_path": str(input_path),
                "summary_path": str(summary_path) if summary_path is not None else None,
            },
            artifacts=[
                {
                    "type": "southport_refresh_run_summary",
                    "path": str(summary_path) if summary_path is not None else None,
                }
            ],
        )
        return summary_dict
    except KeyboardInterrupt:
        notification_hooks.interrupted(
            summary=f"Southport refresh interrupted for {SOUTHPORT_SLICE_ID}",
            details={
                "source_name": source_name,
                "input_path": str(input_path),
            },
        )
        raise
    finally:
        if lock_path.exists():
            lock_path.unlink()


def collect_southport_row_counts(*, database_url: str) -> dict[str, int]:
    """Collect row counts for the canonical phase-1 tables in the Southport slice."""

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                with southport_suburbs as (
                  select id
                  from suburbs
                  where lower(suburb_name) = lower('Southport')
                    and coalesce(upper(state_code), '') = 'QLD'
                    and coalesce(postcode, '') = '4215'
                ),
                southport_properties as (
                  select p.id
                  from properties p
                  join southport_suburbs s on s.id = p.suburb_id
                ),
                southport_listings as (
                  select l.id
                  from listings l
                  join southport_properties p on p.id = l.property_id
                )
                select
                  (select count(*)::int from southport_suburbs) as suburbs,
                  (select count(*)::int from southport_properties) as properties,
                  (select count(*)::int from southport_listings) as listings,
                  (select count(*)::int from listing_snapshots ls join southport_listings l on l.id = ls.listing_id) as listing_snapshots,
                  (select count(*)::int from sales_events se join southport_properties p on p.id = se.property_id) as sales_events,
                  (select count(*)::int from rental_events re join southport_properties p on p.id = re.property_id) as rental_events,
                  (select count(*)::int from market_metrics mm join southport_suburbs s on s.id = mm.suburb_id) as market_metrics
                """
            )
            row = cur.fetchone()

    return {
        "suburbs": row[0],
        "properties": row[1],
        "listings": row[2],
        "listing_snapshots": row[3],
        "sales_events": row[4],
        "rental_events": row[5],
        "market_metrics": row[6],
    }


def verify_southport_demo_slice(
    *,
    database_url: str,
    expected_minimums: Optional[dict[str, int]] = None,
) -> dict[str, Any]:
    """Verify the demo slice has enough persisted rows to support phase-1 handoff."""

    notification_hooks = _build_southport_notification_hooks()
    notification_hooks.ready_for_evaluation(
        summary=f"Southport verification ready for evaluation for {SOUTHPORT_SLICE_ID}",
        details={
            "database_url_supplied": bool(database_url),
            "expected_minimums": expected_minimums or {},
        },
    )
    row_counts = collect_southport_row_counts(database_url=database_url)
    minimums = {**DEFAULT_SOUTHPORT_ROW_COUNT_MINIMUMS, **(expected_minimums or {})}
    failures = [table for table, minimum in minimums.items() if row_counts.get(table, 0) < minimum]
    has_outcome_history = row_counts["sales_events"] > 0 or row_counts["rental_events"] > 0
    proof_slice_ready = len(failures) == 0

    report = {
        "artifact_type": "southport_verification_report",
        "artifact_contract_version": 2,
        "target_slice": SOUTHPORT_SLICE_ID,
        "scope": _build_southport_scope_descriptor(),
        "proof_slice_evidence": {
            "row_counts": row_counts,
            "minimums": minimums,
            "meets_minimums": proof_slice_ready,
            "minimum_failures": failures,
            "has_outcome_history": has_outcome_history,
        },
        "production_readiness": _build_southport_operator_readiness(
            proof_slice_ready=proof_slice_ready,
            has_market_metrics=row_counts["market_metrics"] > 0,
            has_outcome_history=has_outcome_history,
        ),
        "operator_summary": _build_verification_operator_summary(
            row_counts=row_counts,
            failures=failures,
            proof_slice_ready=proof_slice_ready,
            has_outcome_history=has_outcome_history,
        ),
    }
    if proof_slice_ready:
        notification_hooks.evaluated(
            summary=f"Southport verification passed for {SOUTHPORT_SLICE_ID}",
            details={
                "minimum_failures": failures,
                "row_counts": row_counts,
            },
        )
    else:
        notification_hooks.evaluation_failed(
            summary=f"Southport verification needs attention for {SOUTHPORT_SLICE_ID}",
            details={
                "minimum_failures": failures,
                "row_counts": row_counts,
            },
        )
    return report


def run_southport_backfill_and_verify(
    *,
    source_name: str,
    input_path: Path,
    database_url: str,
    lock_path: Path = Path(".refresh-southport.lock"),
    summary_path: Optional[Path] = None,
    verification_path: Optional[Path] = None,
) -> dict[str, Any]:
    """Run the full refresh + metrics + row-count verification pipeline for Southport."""

    notification_hooks = _build_southport_notification_hooks()
    refresh = run_southport_refresh(
        source_name=source_name,
        input_path=input_path,
        store=PostgresCanonicalStore(database_url),
        lock_path=lock_path,
        summary_path=summary_path,
        database_url=database_url,
    )
    verification = verify_southport_demo_slice(database_url=database_url)
    report = {
        "artifact_type": "southport_backfill_verification_report",
        "artifact_contract_version": 2,
        "target_slice": SOUTHPORT_SLICE_ID,
        "scope": _build_southport_scope_descriptor(),
        "proof_slice_evidence": {
            "refresh": refresh,
            "verification": verification,
        },
        "production_readiness": verification["production_readiness"],
        "operator_summary": {
            "headline": f"Southport backfill + verification completed for {SOUTHPORT_SLICE_ID}",
            "proof_slice_evidence": [
                refresh["operator_summary"]["headline"],
                verification["operator_summary"]["headline"],
            ],
            "production_readiness_boundary": SOUTHPORT_FALLBACK_OR_DEMO_ONLY,
            "safe_rerun_steps": SOUTHPORT_SAFE_RERUN_STEPS,
            "proof_slice_ready": verification["production_readiness"]["proof_slice_ready"],
        },
    }
    if verification_path is not None:
        verification_path.parent.mkdir(parents=True, exist_ok=True)
        verification_path.write_text(json.dumps(report, indent=2))
    notification_hooks.completed(
        summary=f"Southport backfill and verification completed for {SOUTHPORT_SLICE_ID}",
        details={
            "source_name": source_name,
            "verification_path": str(verification_path) if verification_path is not None else None,
        },
        artifacts=[
            {
                "type": "southport_backfill_verification_report",
                "path": str(verification_path) if verification_path is not None else None,
            }
        ],
    )
    return report

def run_file_ingest(
    *,
    source_name: str,
    target_slice: str,
    input_path: Path,
    store: CanonicalStore,
) -> IngestRunMetadata:
    payload = json.loads(input_path.read_text())
    records = payload if isinstance(payload, list) else [payload]

    metadata = IngestRunMetadata(source_name=source_name, target_slice=target_slice, started_at=datetime.now(timezone.utc))

    for raw in records:
        metadata.input_record_count += 1
        try:
            record = parse_source_payload(source_name=source_name, payload=raw)
            outcome = store.upsert_listing_observation(record)
            event_result = store.upsert_outcome_events(raw_payload=raw, record=record)
            if outcome == "inserted":
                metadata.inserted_count += 1
            else:
                metadata.updated_count += 1
            metadata.sales_events_inserted_count += event_result.sales_inserted
            metadata.sales_events_updated_count += event_result.sales_updated
            metadata.rental_events_inserted_count += event_result.rentals_inserted
            metadata.rental_events_updated_count += event_result.rentals_updated
        except ValueError:
            metadata.skipped_count += 1
        except Exception:
            metadata.error_count += 1
            raise

    return metadata



def generate_southport_market_metrics(*, database_url: str, period_start: date, period_end: date, metric_period: str = "monthly") -> dict[str, Any]:
    """Generate first-pass market metrics for the frozen Southport demo slice."""

    result = generate_suburb_market_metrics(
        database_url=database_url,
        suburb_name="Southport",
        state_code="QLD",
        postcode="4215",
        target_slice="southport-qld-4215",
        metric_period=metric_period,
        period_start=period_start,
        period_end=period_end,
    )
    return {
        "target_slice": result.target_slice,
        "suburb_id": result.suburb_id,
        "metric_period": result.metric_period,
        "period_start": result.period_start.isoformat(),
        "period_end": result.period_end.isoformat(),
        "inserted": result.inserted,
    }

def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase 1 ingest + refresh orchestration for Southport (QLD 4215).")
    subparsers = parser.add_subparsers(dest="command")

    ingest_parser = subparsers.add_parser("ingest", help="Run ingest for a provided target slice and input payload")
    ingest_parser.add_argument("--source-name", required=True)
    ingest_parser.add_argument("--target-slice", required=True)
    ingest_parser.add_argument("--input", required=True, help="Path to JSON payload list")
    ingest_parser.add_argument("--database-url", default=None, help="Optional Postgres URL. If omitted, uses in-memory dry run")

    refresh_parser = subparsers.add_parser("refresh-southport", help="Run repeatable refresh for southport-qld-4215 with lock file safety")
    refresh_parser.add_argument("--source-name", required=True)
    refresh_parser.add_argument("--input", required=True, help="Path to JSON payload list")
    refresh_parser.add_argument("--database-url", default=None, help="Optional Postgres URL. If omitted, uses in-memory dry run")
    refresh_parser.add_argument("--lock-path", default=".refresh-southport.lock", help="Lock file path used to block overlapping runs")
    refresh_parser.add_argument("--summary-path", default=".refresh/runs/southport_refresh_runs.json", help="JSON file where run summaries are appended")

    verify_parser = subparsers.add_parser("verify-southport-demo", help="Validate canonical Southport row counts for demo readiness")
    verify_parser.add_argument("--database-url", required=True)

    backfill_parser = subparsers.add_parser("backfill-verify-southport", help="Run Southport refresh and emit a verification report")
    backfill_parser.add_argument("--source-name", required=True)
    backfill_parser.add_argument("--input", required=True, help="Path to JSON payload list")
    backfill_parser.add_argument("--database-url", required=True)
    backfill_parser.add_argument("--lock-path", default=".refresh-southport.lock")
    backfill_parser.add_argument("--summary-path", default=".refresh/runs/southport_refresh_runs.json")
    backfill_parser.add_argument("--verification-path", default=".refresh/runs/southport_demo_verification.json")

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv and argv[0].startswith("--"):
        argv = ["ingest", *argv]
    args = build_cli_parser().parse_args(argv if argv else None)
    command = args.command or "ingest"

    if command == "ingest":
        store: CanonicalStore = PostgresCanonicalStore(args.database_url) if args.database_url else InMemoryCanonicalStore()
        result = run_file_ingest(
            source_name=args.source_name,
            target_slice=args.target_slice,
            input_path=Path(args.input),
            store=store,
        )
        print(json.dumps(result.as_dict(), indent=2))
        return 0

    if command == "refresh-southport":
        store = PostgresCanonicalStore(args.database_url) if args.database_url else InMemoryCanonicalStore()
        result = run_southport_refresh(
            source_name=args.source_name,
            input_path=Path(args.input),
            store=store,
            lock_path=Path(args.lock_path),
            summary_path=Path(args.summary_path),
            database_url=args.database_url,
        )
        print(json.dumps(result, indent=2))
        return 0

    if command == "verify-southport-demo":
        result = verify_southport_demo_slice(database_url=args.database_url)
        print(json.dumps(result, indent=2))
        return 0

    if command == "backfill-verify-southport":
        result = run_southport_backfill_and_verify(
            source_name=args.source_name,
            input_path=Path(args.input),
            database_url=args.database_url,
            lock_path=Path(args.lock_path),
            summary_path=Path(args.summary_path),
            verification_path=Path(args.verification_path),
        )
        print(json.dumps(result, indent=2))
        return 0

    raise ValueError(f"unknown command: {command}")


if __name__ == "__main__":
    raise SystemExit(main())
