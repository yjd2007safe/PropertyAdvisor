from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from .openclaw_bridge import OpenClawNotificationBridge


def _common_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--artifact-path", default=".dev_pipeline/notifications")
    parser.add_argument("--state-path")
    parser.add_argument("--delivery-log-path")
    parser.add_argument("--session-key")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--event-types",
        help="Comma-separated event types to include. Defaults to high-value notification events.",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="openclaw-notification-bridge",
        description="Replay shared notification artifacts into an OpenClaw session.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    collect_parser = subparsers.add_parser("collect", help="Collect pending notification records.")
    _common_args(collect_parser)
    collect_parser.set_defaults(func=_handle_collect)

    ack_parser = subparsers.add_parser("ack", help="Mark a pending notification as delivered.")
    _common_args(ack_parser)
    ack_parser.add_argument("--event-id", required=True)
    ack_parser.add_argument("--status", default="sent")
    ack_parser.add_argument("--delivery-result-json")
    ack_parser.set_defaults(func=_handle_ack)

    fail_parser = subparsers.add_parser("fail", help="Record a delivery failure without acking state.")
    _common_args(fail_parser)
    fail_parser.add_argument("--event-id", required=True)
    fail_parser.add_argument("--error", required=True)
    fail_parser.set_defaults(func=_handle_fail)

    replay_parser = subparsers.add_parser("replay", help="Replay artifacts using the configured sender.")
    _common_args(replay_parser)
    replay_parser.add_argument("--dry-run", action="store_true")
    replay_parser.set_defaults(func=_handle_replay)

    return parser


def _parse_event_types(value: str | None) -> list[str] | None:
    if value is None:
        return None
    parsed = [part.strip() for part in value.split(",") if part.strip()]
    return parsed or None


def _build_bridge(args: argparse.Namespace) -> OpenClawNotificationBridge:
    return OpenClawNotificationBridge(
        artifact_path=Path(args.artifact_path),
        state_path=Path(args.state_path) if args.state_path else None,
        delivery_log_path=Path(args.delivery_log_path) if args.delivery_log_path else None,
        session_key=args.session_key,
        event_types=_parse_event_types(args.event_types),
    )


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True))


def _find_pending_artifact(bridge: OpenClawNotificationBridge, event_id: str) -> dict[str, Any]:
    for artifact in bridge.collect_pending():
        if artifact["event_id"] == event_id:
            return artifact
    raise SystemExit(f"pending event_id not found: {event_id}")


def _handle_collect(args: argparse.Namespace) -> int:
    bridge = _build_bridge(args)
    records = bridge.build_pending_records(limit=args.limit)
    payload = {
        "status": "ok",
        "artifact_path": str(bridge.artifact_path),
        "state_path": str(bridge.state_path),
        "delivery_log_path": str(bridge.delivery_log_path),
        "session_key": bridge.session_key,
        "record_count": len(records),
        "records": [
            {
                "event_id": record["event_id"],
                "event_type": record["event_type"],
                "session_key": record["session_key"],
                "message": record["message"],
                "created_at": record["created_at"],
            }
            for record in records
        ],
    }
    _print_json(payload)
    return 0


def _handle_ack(args: argparse.Namespace) -> int:
    bridge = _build_bridge(args)
    artifact = _find_pending_artifact(bridge, args.event_id)
    delivery_result = json.loads(args.delivery_result_json) if args.delivery_result_json else None
    record = bridge.mark_delivered(
        artifact=artifact,
        session_key=args.session_key or bridge.session_key,
        delivery_result=delivery_result,
        status=args.status,
    )
    _print_json({"status": "ok", "record": record})
    return 0


def _handle_fail(args: argparse.Namespace) -> int:
    bridge = _build_bridge(args)
    artifact = _find_pending_artifact(bridge, args.event_id)
    record = bridge.mark_failed(
        artifact=artifact,
        session_key=args.session_key or bridge.session_key,
        error=args.error,
    )
    _print_json({"status": "ok", "record": record})
    return 0


def _handle_replay(args: argparse.Namespace) -> int:
    bridge = _build_bridge(args)
    records = bridge.replay_pending(limit=args.limit, dry_run=args.dry_run)
    payload = {
        "status": "ok",
        "artifact_path": str(bridge.artifact_path),
        "state_path": str(bridge.state_path),
        "delivery_log_path": str(bridge.delivery_log_path),
        "session_key": bridge.session_key,
        "record_count": len(records),
        "sent_count": sum(1 for record in records if record["status"] == "sent"),
        "dry_run_count": sum(1 for record in records if record["status"] == "dry-run"),
        "failed_count": sum(1 for record in records if record["status"] == "failed"),
        "event_ids": [record["event_id"] for record in records],
    }
    _print_json(payload)
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
