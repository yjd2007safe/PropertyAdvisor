from __future__ import annotations

import json

from property_advisor.ingest import InMemoryCanonicalStore, run_southport_refresh, verify_southport_demo_slice
from property_advisor.notifications.artifact_consumer import NotificationArtifactConsumer
from property_advisor.pipeline.notification_hooks import PipelineNotificationHooks


def test_pipeline_hooks_emit_required_event_types(tmp_path) -> None:
    hooks = PipelineNotificationHooks(
        project="PropertyAdvisor",
        phase="phase2",
        round="round5",
        slice_id="phase2-round5-notification-artifact-foundation",
        artifact_path=tmp_path / ".dev_pipeline" / "notifications",
        origin={
            "channel": "telegram",
            "chat_id": "123",
            "thread_id": "thread-1",
            "session_key": "session-1",
            "user_id": "user-1",
            "reply_mode": "reply",
        },
        delivery_targets=[
            {"channel": "telegram", "chat_id": "123", "thread_id": "thread-1"},
            {"channel": "session", "session_key": "session-1", "reply_mode": "reply"},
        ],
    )

    hooks.round_started(summary="start")
    hooks.ready_for_evaluation(summary="ready")
    hooks.evaluated(summary="evaluated")
    hooks.evaluation_failed(summary="evaluation failed")
    hooks.delivered(summary="delivered")
    hooks.completed(summary="completed")
    hooks.blocked(summary="blocked")
    hooks.interrupted(summary="interrupted")

    consumer = NotificationArtifactConsumer(base_path=tmp_path / ".dev_pipeline" / "notifications")
    event_types = [artifact["event_type"] for artifact in consumer.read_all()]

    assert event_types == [
        "round_started",
        "ready_for_evaluation",
        "evaluated",
        "evaluation_failed",
        "delivered",
        "completed",
        "blocked",
        "interrupted",
    ]


def test_southport_pipeline_functions_write_local_notification_artifacts(tmp_path, monkeypatch) -> None:
    notification_path = tmp_path / ".dev_pipeline" / "notifications"
    monkeypatch.setattr(
        "property_advisor.ingest._build_southport_notification_hooks",
        lambda: PipelineNotificationHooks(
            project="PropertyAdvisor",
            phase="phase1",
            round="round6",
            slice_id="southport-qld-4215",
            artifact_path=notification_path,
        ),
    )
    monkeypatch.setattr(
        "property_advisor.ingest.collect_southport_row_counts",
        lambda **kwargs: {
            "suburbs": 1,
            "properties": 1,
            "listings": 1,
            "listing_snapshots": 1,
            "sales_events": 1,
            "rental_events": 0,
            "market_metrics": 1,
        },
    )

    input_path = tmp_path / "records.json"
    input_path.write_text(
        json.dumps(
            [
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
            ]
        )
    )

    run_southport_refresh(
        source_name="realestate_export",
        input_path=input_path,
        store=InMemoryCanonicalStore(),
        lock_path=tmp_path / "southport.lock",
        summary_path=tmp_path / "runs.json",
    )
    verify_southport_demo_slice(database_url="postgresql://localhost/propertyadvisor")

    consumer = NotificationArtifactConsumer(base_path=notification_path)
    event_types = [artifact["event_type"] for artifact in consumer.read_all()]

    assert "round_started" in event_types
    assert "completed" in event_types
    assert "ready_for_evaluation" in event_types
    assert "evaluated" in event_types
