from __future__ import annotations

"""HTTP routes for the PropertyAdvisor MVP API."""

from datetime import datetime, timezone

from fastapi import APIRouter

router = APIRouter(prefix="/api")


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "service": "propertyadvisor-api",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/suburbs/overview")
def suburbs_overview() -> dict:
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": {
            "tracked_suburbs": 3,
            "watchlist_suburbs": 2,
            "data_freshness": "placeholder",
        },
        "items": [
            {
                "slug": "southport-qld-4215",
                "name": "Southport",
                "state": "QLD",
                "median_price": 895000,
                "median_rent": 780,
                "trend": "watching",
                "note": "Replace with market_metrics rollups once DB-backed services are wired.",
            },
            {
                "slug": "burleigh-heads-qld-4220",
                "name": "Burleigh Heads",
                "state": "QLD",
                "median_price": 1350000,
                "median_rent": 950,
                "trend": "steady",
                "note": "Placeholder suburb overview payload for dashboard integration.",
            },
        ],
    }


@router.get("/advisor/property")
def property_advisor_placeholder() -> dict:
    return {
        "property": {
            "address": "12 Example Avenue, Southport QLD 4215",
            "property_type": "house",
            "beds": 4,
            "baths": 2,
        },
        "advice": {
            "recommendation": "watch",
            "confidence": "low",
            "headline": "Initial MVP placeholder awaiting comparable and market-backed logic.",
            "next_steps": [
                "Load latest listing facts",
                "Attach suburb metrics snapshot",
                "Score recent comparables",
            ],
        },
    }


@router.get("/comparables")
def comparables_placeholder() -> dict:
    return {
        "subject": "12 Example Avenue, Southport QLD 4215",
        "set_quality": "placeholder",
        "items": [
            {
                "address": "8 Nearby Street, Southport QLD 4215",
                "price": 910000,
                "distance_km": 0.6,
                "match_reason": "Similar bed/bath count and recent sale date.",
            },
            {
                "address": "17 Sample Road, Southport QLD 4215",
                "price": 875000,
                "distance_km": 0.9,
                "match_reason": "Comparable land profile with slightly lower finish level.",
            },
        ],
    }
