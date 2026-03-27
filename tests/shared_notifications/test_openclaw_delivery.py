from __future__ import annotations

import json

from shared_notifications.openclaw_delivery import (
    build_sessions_send_params,
    deliver_to_openclaw_session,
    resolve_session_key,
)


SAMPLE_ARTIFACT = {
    "event_type": "completed",
    "status": "completed",
    "project": "PropertyAdvisor",
    "phase": "phase1",
    "round": "round6",
    "slice_id": "southport-qld-4215",
    "summary": "Southport refresh completed",
    "details": {"source_name": "realestate_export"},
    "artifacts": [],
    "created_at": "2026-03-27T12:00:00+00:00",
}


def test_resolve_session_key_prefers_explicit(monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_NOTIFICATION_SESSION_KEY", "env-session")
    assert resolve_session_key("explicit-session") == "explicit-session"


def test_build_sessions_send_params_renders_message() -> None:
    params = build_sessions_send_params(
        artifact=SAMPLE_ARTIFACT,
        session_key="agent:main:test",
        timeout_seconds=0,
    )

    assert params["sessionKey"] == "agent:main:test"
    assert params["timeoutSeconds"] == 0
    assert "PropertyAdvisor notification: Southport refresh completed" in params["message"]


def test_deliver_to_openclaw_session_calls_gateway(monkeypatch) -> None:
    captured = {}

    class Result:
        stdout = json.dumps({"status": "accepted", "runId": "run-123"})

    def fake_run(cmd, capture_output, text, timeout, check):
        captured["cmd"] = cmd
        captured["capture_output"] = capture_output
        captured["text"] = text
        captured["timeout"] = timeout
        captured["check"] = check
        return Result()

    monkeypatch.setattr("shared_notifications.openclaw_delivery.subprocess.run", fake_run)

    result = deliver_to_openclaw_session(
        SAMPLE_ARTIFACT,
        session_key="agent:main:test",
        timeout_seconds=0,
        cli_timeout_seconds=9,
    )

    assert result["status"] == "sent"
    assert result["session_key"] == "agent:main:test"
    assert result["response"]["status"] == "accepted"
    assert captured["cmd"][:4] == ["openclaw", "gateway", "call", "sessions.send"]
    params = json.loads(captured["cmd"][5])
    assert params["sessionKey"] == "agent:main:test"
    assert params["timeoutSeconds"] == 0
    assert captured["timeout"] == 9
