from __future__ import annotations

import base64
import json
import os
import socket
import struct
import time
import uuid
from pathlib import Path
from urllib.parse import urlparse
from typing import Any, Mapping, Optional

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey, Ed25519PublicKey

from .render import render_openclaw_message

DEFAULT_TIMEOUT_SECONDS = 15
_GATEWAY_TOKEN_ENV_VAR = "OPENCLAW_GATEWAY_TOKEN"
_GATEWAY_URL_ENV_VAR = "OPENCLAW_GATEWAY_URL"
_DEFAULT_GATEWAY_URL = "ws://127.0.0.1:18789"
_SESSION_KEY_ENV_VARS = (
    "OPENCLAW_NOTIFICATION_SESSION_KEY",
    "PROPERTY_ADVISOR_NOTIFICATION_SESSION_KEY",
)
_SESSION_ALIAS_ENV_PREFIX = "OPENCLAW_NOTIFICATION_SESSION_ALIAS_"


def _normalize_alias_key(value: str) -> str:
    return ''.join(ch if ch.isalnum() else '_' for ch in value.strip()).upper()


def resolve_session_key(explicit_session_key: Optional[str] = None) -> Optional[str]:
    if explicit_session_key:
        explicit = explicit_session_key.strip()
        if explicit:
            alias_name = f"{_SESSION_ALIAS_ENV_PREFIX}{_normalize_alias_key(explicit)}"
            alias_value = os.environ.get(alias_name)
            if alias_value and alias_value.strip():
                return alias_value.strip()
            return explicit
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


def _load_openclaw_config() -> dict[str, Any]:
    config_path = Path.home() / ".openclaw" / "openclaw.json"
    if not config_path.exists():
        return {}
    try:
        payload = json.loads(config_path.read_text(encoding="utf-8"))
    except Exception:
        return {}
    return payload if isinstance(payload, dict) else {}


def _resolve_gateway_token() -> Optional[str]:
    env_token = os.environ.get(_GATEWAY_TOKEN_ENV_VAR)
    if env_token and env_token.strip():
        return env_token.strip()

    payload = _load_openclaw_config()
    token = payload.get("gateway", {}).get("auth", {}).get("token")
    if isinstance(token, str) and token.strip():
        return token.strip()
    return None


def _base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def _resolve_gateway_url() -> str:
    env_url = os.environ.get(_GATEWAY_URL_ENV_VAR)
    if env_url and env_url.strip():
        return env_url.strip()

    payload = _load_openclaw_config()
    gateway_cfg = payload.get("gateway", {}) if isinstance(payload.get("gateway"), dict) else {}
    remote_cfg = gateway_cfg.get("remote", {}) if isinstance(gateway_cfg.get("remote"), dict) else {}
    mode = str(gateway_cfg.get("mode") or "local").strip().lower()
    remote_url = str(remote_cfg.get("url") or "").strip()
    if mode == "remote" and remote_url:
        return remote_url

    port = gateway_cfg.get("port")
    tls_cfg = gateway_cfg.get("tls", {}) if isinstance(gateway_cfg.get("tls"), dict) else {}
    tls_enabled = tls_cfg.get("enabled") is True
    if isinstance(port, int) and port > 0:
        scheme = "wss" if tls_enabled else "ws"
        return f"{scheme}://127.0.0.1:{port}"
    return _DEFAULT_GATEWAY_URL


def _load_device_identity() -> Optional[dict[str, Any]]:
    path = Path.home() / ".openclaw" / "identity" / "device.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    return payload if isinstance(payload, dict) else None


def _load_device_auth_token(role: str = "operator") -> Optional[dict[str, Any]]:
    path = Path.home() / ".openclaw" / "identity" / "device-auth.json"
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None
    tokens = payload.get("tokens") if isinstance(payload, dict) else None
    record = tokens.get(role) if isinstance(tokens, dict) else None
    return record if isinstance(record, dict) else None


def _build_device_signature_payload(
    *,
    device_id: str,
    client_id: str,
    client_mode: str,
    role: str,
    scopes: list[str],
    signed_at_ms: int,
    token: str,
    nonce: str,
    platform: str,
    device_family: str = "",
) -> str:
    return "|".join(
        [
            "v3",
            device_id,
            client_id,
            client_mode,
            role,
            ",".join(scopes),
            str(signed_at_ms),
            token,
            nonce,
            platform,
            device_family,
        ]
    )


def _build_device_auth(
    *,
    token: str,
    nonce: str,
    client_id: str,
    client_mode: str,
    role: str,
    scopes: list[str],
) -> Optional[dict[str, Any]]:
    identity = _load_device_identity()
    if not identity:
        return None
    private_key_pem = identity.get("privateKeyPem")
    public_key_pem = identity.get("publicKeyPem")
    device_id = identity.get("deviceId")
    if not all(isinstance(value, str) and value.strip() for value in (private_key_pem, public_key_pem, device_id)):
        return None

    private_key = serialization.load_pem_private_key(
        private_key_pem.encode("utf-8"),
        password=None,
        backend=default_backend(),
    )
    public_key = serialization.load_pem_public_key(
        public_key_pem.encode("utf-8"),
        backend=default_backend(),
    )
    if not isinstance(private_key, Ed25519PrivateKey) or not isinstance(public_key, Ed25519PublicKey):
        return None

    signed_at_ms = int(time.time() * 1000)
    payload = _build_device_signature_payload(
        device_id=device_id,
        client_id=client_id,
        client_mode=client_mode,
        role=role,
        scopes=scopes,
        signed_at_ms=signed_at_ms,
        token=token,
        nonce=nonce,
        platform="python",
    )
    signature = private_key.sign(payload.encode("utf-8"))
    public_key_raw = public_key.public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    return {
        "id": device_id,
        "publicKey": _base64url_encode(public_key_raw),
        "signature": _base64url_encode(signature),
        "signedAt": signed_at_ms,
        "nonce": nonce,
    }


def _recv_exact(sock: socket.socket, length: int) -> bytes:
    payload = b""
    while len(payload) < length:
        chunk = sock.recv(length - len(payload))
        if not chunk:
            raise RuntimeError("socket closed while receiving websocket frame")
        payload += chunk
    return payload


def _recv_ws_frame(sock: socket.socket) -> dict[str, Any]:
    header = _recv_exact(sock, 2)
    b1, b2 = header[0], header[1]
    opcode = b1 & 0x0F
    length = b2 & 0x7F
    masked = (b2 & 0x80) != 0
    if length == 126:
        length = struct.unpack("!H", _recv_exact(sock, 2))[0]
    elif length == 127:
        length = struct.unpack("!Q", _recv_exact(sock, 8))[0]
    mask = _recv_exact(sock, 4) if masked else b""
    payload = _recv_exact(sock, length) if length else b""
    if masked:
        payload = bytes(byte ^ mask[index % 4] for index, byte in enumerate(payload))
    return {"opcode": opcode, "payload": payload}


def _send_ws_json(sock: socket.socket, payload: Mapping[str, Any]) -> None:
    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    frame = bytearray([0x81])
    length = len(data)
    if length < 126:
        frame.append(0x80 | length)
    elif length < 65536:
        frame.append(0x80 | 126)
        frame.extend(struct.pack("!H", length))
    else:
        frame.append(0x80 | 127)
        frame.extend(struct.pack("!Q", length))
    mask = os.urandom(4)
    frame.extend(mask)
    frame.extend(bytes(byte ^ mask[index % 4] for index, byte in enumerate(data)))
    sock.sendall(bytes(frame))


def _ws_connect(url: str, *, timeout_seconds: int) -> socket.socket:
    parsed = urlparse(url)
    if parsed.scheme != "ws":
        raise RuntimeError(f"OpenClaw notification delivery currently supports ws:// only, got: {url}")
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 80
    path = parsed.path or "/"
    if parsed.query:
        path = f"{path}?{parsed.query}"

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(timeout_seconds)
    sock.connect((host, port))

    key = base64.b64encode(os.urandom(16)).decode("ascii")
    request = (
        f"GET {path} HTTP/1.1\r\n"
        f"Host: {host}:{port}\r\n"
        "Upgrade: websocket\r\n"
        "Connection: Upgrade\r\n"
        f"Sec-WebSocket-Key: {key}\r\n"
        "Sec-WebSocket-Version: 13\r\n"
        f"Origin: http://{host}:{port}\r\n"
        "\r\n"
    ).encode("utf-8")
    sock.sendall(request)
    response = sock.recv(4096).decode("utf-8", "replace")
    if "101 Switching Protocols" not in response:
        raise RuntimeError(f"websocket upgrade failed: {response.strip() or 'empty response'}")
    return sock


def _recv_ws_json(sock: socket.socket, *, ignore_events: bool = False) -> dict[str, Any]:
    while True:
        frame = _recv_ws_frame(sock)
        opcode = frame["opcode"]
        if opcode == 0x8:
            raise RuntimeError("gateway websocket closed the connection")
        if opcode != 0x1:
            continue
        text = frame["payload"].decode("utf-8", "replace")
        payload = json.loads(text)
        if ignore_events and payload.get("type") == "event":
            continue
        return payload


def _gateway_rpc_request(
    *,
    method: str,
    params: Mapping[str, Any],
    gateway_url: str,
    gateway_token: str,
    timeout_seconds: int,
) -> Mapping[str, Any]:
    sock = _ws_connect(gateway_url, timeout_seconds=timeout_seconds)
    try:
        challenge = _recv_ws_json(sock)
        nonce = ((challenge.get("payload") or {}).get("nonce")) if challenge.get("event") == "connect.challenge" else None
        if not isinstance(nonce, str) or not nonce.strip():
            raise RuntimeError(f"gateway connect challenge missing nonce: {challenge}")

        role = "operator"
        scopes = ["operator.admin", "operator.write", "operator.read"]
        client_id = "gateway-client"
        client_mode = "backend"
        device_auth_record = _load_device_auth_token(role)
        auth_token = (
            device_auth_record.get("token")
            if isinstance(device_auth_record, dict) and isinstance(device_auth_record.get("token"), str) and device_auth_record.get("token", "").strip()
            else gateway_token
        )
        device_auth = _build_device_auth(
            token=auth_token,
            nonce=nonce,
            client_id=client_id,
            client_mode=client_mode,
            role=role,
            scopes=scopes,
        )
        connect_request = {
            "type": "req",
            "id": f"connect-{uuid.uuid4()}",
            "method": "connect",
            "params": {
                "minProtocol": 3,
                "maxProtocol": 3,
                "client": {
                    "id": client_id,
                    "displayName": "PropertyAdvisor notification bridge",
                    "version": "propertyadvisor-notify",
                    "platform": "python",
                    "mode": client_mode,
                },
                "caps": [],
                "auth": {
                    "token": auth_token,
                    **({"deviceToken": auth_token} if auth_token != gateway_token or device_auth is not None else {}),
                },
                "role": role,
                "scopes": scopes,
                **({"device": device_auth} if device_auth is not None else {}),
            },
        }
        _send_ws_json(sock, connect_request)
        connect_response = _recv_ws_json(sock, ignore_events=True)
        if connect_response.get("type") != "res" or connect_response.get("id") != connect_request["id"]:
            raise RuntimeError(f"unexpected gateway connect response: {connect_response}")
        if connect_response.get("ok") is not True:
            raise RuntimeError((connect_response.get("error") or {}).get("message") or "gateway connect failed")

        request_id = f"request-{uuid.uuid4()}"
        _send_ws_json(
            sock,
            {
                "type": "req",
                "id": request_id,
                "method": method,
                "params": dict(params),
            },
        )
        while True:
            response = _recv_ws_json(sock)
            if response.get("type") == "event":
                continue
            if response.get("type") != "res" or response.get("id") != request_id:
                continue
            if response.get("ok") is not True:
                raise RuntimeError((response.get("error") or {}).get("message") or f"gateway {method} failed")
            payload = response.get("payload")
            return payload if isinstance(payload, Mapping) else {"payload": payload}
    finally:
        try:
            sock.close()
        except Exception:
            pass


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
    gateway_token = _resolve_gateway_token()
    if not gateway_token:
        raise RuntimeError("OpenClaw notification delivery requires a gateway token.")

    payload = _gateway_rpc_request(
        method="sessions.send",
        params=params,
        gateway_url=_resolve_gateway_url(),
        gateway_token=gateway_token,
        timeout_seconds=cli_timeout_seconds,
    )

    return {
        "status": "sent",
        "channel": "openclaw-session",
        "session_key": resolved_session_key,
        "response": dict(payload),
    }
