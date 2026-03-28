from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path
from typing import Any, Mapping, Optional

from .render import render_openclaw_message

DEFAULT_TIMEOUT_SECONDS = 15
_GATEWAY_TOKEN_ENV_VAR = "OPENCLAW_GATEWAY_TOKEN"
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


def _resolve_gateway_token() -> Optional[str]:
    env_token = os.environ.get(_GATEWAY_TOKEN_ENV_VAR)
    if env_token and env_token.strip():
        return env_token.strip()

    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        return None

    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return None

    token = payload.get("gateway", {}).get("auth", {}).get("token")
    if isinstance(token, str) and token.strip():
        return token.strip()
    return None


def _build_agent_command(*, artifact: Mapping[str, Any], session_key: str, timeout_seconds: int) -> list[str]:
    return [
        "openclaw",
        "agent",
        "--to",
        session_key,
        "--message",
        render_openclaw_message(artifact),
        "--timeout",
        str(timeout_seconds),
        "--json",
    ]


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
    command = _build_agent_command(
        artifact=artifact,
        session_key=resolved_session_key,
        timeout_seconds=timeout_seconds,
    )
    env = os.environ.copy()
    gateway_token = _resolve_gateway_token()
    if gateway_token:
        env.setdefault(_GATEWAY_TOKEN_ENV_VAR, gateway_token)

    result = subprocess.run(
        command,
        capture_output=True,
        text=True,
        timeout=cli_timeout_seconds,
        check=True,
        env=env,
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
