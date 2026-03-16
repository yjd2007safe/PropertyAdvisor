from __future__ import annotations

"""Ingestion entry points and Phase 1 canonical ingest foundations."""

import argparse
import json
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional, Protocol

import psycopg


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
        }


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


class PropertyMatchConfidence:
    """Confidence levels for property matching."""
    EXACT = "exact"           # Exact address match (case-insensitive)
    NORMALIZED = "normalized"  # Normalized form matches (St/Street equivalent)
    REVIEW = "review"         # Low confidence, needs manual review


class CanonicalStore(Protocol):
    def upsert_listing_observation(self, record: CanonicalListingRecord) -> str:
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
            if outcome == "inserted":
                metadata.inserted_count += 1
            else:
                metadata.updated_count += 1
        except ValueError:
            metadata.skipped_count += 1
        except Exception:
            metadata.error_count += 1
            raise

    return metadata


def build_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Phase 1 ingest MVP for canonical suburb/property/listing upsert.")
    parser.add_argument("--source-name", required=True)
    parser.add_argument("--target-slice", required=True)
    parser.add_argument("--input", required=True, help="Path to JSON payload list")
    parser.add_argument("--database-url", default=None, help="Optional Postgres URL. If omitted, uses in-memory dry run")
    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_cli_parser().parse_args(argv)
    store: CanonicalStore
    if args.database_url:
        store = PostgresCanonicalStore(database_url=args.database_url)
    else:
        store = InMemoryCanonicalStore()

    result = run_file_ingest(
        source_name=args.source_name,
        target_slice=args.target_slice,
        input_path=Path(args.input),
        store=store,
    )
    print(json.dumps(result.as_dict(), indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
