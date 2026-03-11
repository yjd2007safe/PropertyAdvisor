from __future__ import annotations

"""Ingestion entry points for external property and market data sources."""

from dataclasses import dataclass
from typing import Any


@dataclass
class IngestJob:
    """Represents a unit of inbound source processing."""

    source_name: str
    payload: dict[str, Any]


def ingest_record(job: IngestJob) -> dict[str, Any]:
    """Return a raw record envelope suitable for normalization."""

    return {
        "source_name": job.source_name,
        "payload": job.payload,
    }
