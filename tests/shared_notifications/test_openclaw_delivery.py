from __future__ import annotations

import json

from shared_notifications.openclaw_delivery import (
    _DEFAULT_GATEWAY_URL,
    _GATEWAY_TOKEN_ENV_VAR,
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


def test_resolve_session_key_supports_alias_mapping(monkeypatch) -> None:
    monkeypatch.setenv("OPENCLAW_NOTIFICATION_SESSION_ALIAS_TELEGRAM_8590579872", "agent:main:telegram-session")
    assert resolve_session_key("telegram:8590579872") == "agent:main:telegram-session"


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

    def fake_gateway_request(*, method, params, gateway_url, gateway_token, timeout_seconds):
        captured["method"] = method
        captured["params"] = params
        captured["gateway_url"] = gateway_url
        captured["gateway_token"] = gateway_token
        captured["timeout_seconds"] = timeout_seconds
        return {"status": "accepted", "runId": "run-123"}

    monkeypatch.setenv(_GATEWAY_TOKEN_ENV_VAR, "token-123")
    monkeypatch.setattr("shared_notifications.openclaw_delivery._gateway_rpc_request", fake_gateway_request)

    result = deliver_to_openclaw_session(
        SAMPLE_ARTIFACT,
        session_key="agent:main:test",
        timeout_seconds=0,
        cli_timeout_seconds=9,
    )

    assert result["status"] == "sent"
    assert result["session_key"] == "agent:main:test"
    assert result["response"]["status"] == "accepted"
    assert captured["method"] == "sessions.send"
    assert captured["gateway_url"] == _DEFAULT_GATEWAY_URL
    assert captured["gateway_token"] == "token-123"
    assert captured["timeout_seconds"] == 9
    assert captured["params"]["sessionKey"] == "agent:main:test"
    assert captured["params"]["timeoutSeconds"] == 0
    assert "PropertyAdvisor notification: Southport refresh completed" in captured["params"]["message"]
