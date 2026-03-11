"""Normalization helpers for PropertyAdvisor's canonical property model."""

from typing import Any


def normalize_property(raw_record: dict[str, Any]) -> dict[str, Any]:
    """Map a raw inbound record into a minimal canonical shape."""

    payload = raw_record.get("payload", {})

    return {
        "source_name": raw_record.get("source_name"),
        "external_id": payload.get("external_id"),
        "address": payload.get("address"),
        "city": payload.get("city"),
        "state": payload.get("state"),
        "postal_code": payload.get("postal_code"),
        "property_type": payload.get("property_type"),
        "beds": payload.get("beds"),
        "baths": payload.get("baths"),
        "square_feet": payload.get("square_feet"),
        "status": payload.get("status"),
    }
