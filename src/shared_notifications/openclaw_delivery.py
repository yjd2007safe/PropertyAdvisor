from __future__ import annotations

import json
import os
import subprocess
from typing import Any, Mapping, Optional

from .render import render_openclaw_message

DEFAULT_TIMEOUT_SECONDS = 15
_SESSION_KEY_ENV_VARS = (
    "OPENCLAW_NOTIFICATION_SESSION_KEY",
    "PROPERTY_ADVISOR_NOTIFICATION_SESSION_KEY",
)


def resolve_session_key(explicit_session_key: Optional[str] = None) -> Optional[str]:
    if explicit_session_key:
        return explicit_session_key.strip() or None
    for name in _SESSION_KEY_ENV_VARS:
        value = os.environ.get(name)
        if value and value.strip():
            return value.strip()
    return None


def build_sessions_send_params(*, artifact: Mapping[str, Any], session_key: str, timeout_seconds: int = 0) -> dict[str, Any]:
    return {
        "sessionKey": session_key,
        "message": render_openclaw_message(artifact),
        "timeoutSeconds": timeout_seconds,
    }


def deliver_to_openclaw_session(
    artifact: Mapping[str, Any],
    *,
    session_key: Optional[str] = None,
    timeout_seconds: int = 0,
    cli_timeout_seconds: int = DEFAULT_TIMEOUT_SECONDS,
) -> Mapping[str, Any]:
    resolved_session_key = resolve_session_key(session_key)
    if not resolved_session_key:
        raise RuntimeError(
            "OpenClaw notification delivery requires OPENCLAW_NOTIFICATION_SESSION_KEY "
            "or PROPERTY_ADVISOR_NOTIFICATION_SESSION_KEY."
        )

    params = build_sessions_send_params(
        artifact=artifact,
        session_key=resolved_session_key,
        timeout_seconds=timeout_seconds,
    )
    result = subprocess.run(
        [
            "openclaw",
            "gateway",
            "call",
            "sessions.send",
            "--params",
            json.dumps(params, ensure_ascii=False),
            "--json",
        ],
        capture_output=True,
        text=True,
        timeout=cli_timeout_seconds,
        check=True,
    )

    payload: dict[str, Any]
    stdout = result.stdout.strip()
    if stdout:
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError:
            payload = {"raw": stdout}
    else:
        payload = {}

    return {
        "status": "sent",
        "channel": "openclaw-session",
        "session_key": resolved_session_key,
        "response": payload,
    }
