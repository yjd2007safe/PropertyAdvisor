from property_advisor.advisory import build_advisory_snapshot
from property_advisor.alerts import evaluate_alerts
from property_advisor.comparables import build_comparable_set
from property_advisor.ingest import IngestJob, ingest_record
from property_advisor.market_metrics import summarize_days_on_market
from property_advisor.normalize import normalize_property


def test_domain_scaffold_smoke_flow() -> None:
    raw = ingest_record(
        IngestJob(
            source_name="sample_feed",
            payload={
                "external_id": "listing-123",
                "address": "10 Market St",
                "city": "Austin",
                "state": "TX",
                "postal_code": "78701",
                "property_type": "single_family",
                "beds": 3,
                "baths": 2,
                "square_feet": 1800,
                "status": "active",
            },
        )
    )

    normalized = normalize_property(raw)
    comparables = build_comparable_set(normalized, [normalized])
    market = summarize_days_on_market([12, 18, 21])
    advisory = build_advisory_snapshot(normalized, comparables, market)

    assert advisory["property"]["external_id"] == "listing-123"
    assert evaluate_alerts(advisory) == []
