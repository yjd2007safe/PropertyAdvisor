from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from .openclaw_bridge import OpenClawNotificationBridge


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="propertyadvisor-openclaw-bridge",
        description="Replay PropertyAdvisor notification artifacts into an OpenClaw session.",
    )
    parser.add_argument("--artifact-path", default=".dev_pipeline/notifications")
    parser.add_argument("--state-path")
    parser.add_argument("--delivery-log-path")
    parser.add_argument("--session-key")
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--event-types",
        help="Comma-separated event types to deliver. Defaults to high-value notification events.",
    )
    parser.add_argument("--dry-run", action="store_true")
    return parser


def _parse_event_types(value: str | None) -> list[str] | None:
    if value is None:
        return None
    parsed = [part.strip() for part in value.split(",") if part.strip()]
    return parsed or None


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    bridge = OpenClawNotificationBridge(
        artifact_path=Path(args.artifact_path),
        state_path=Path(args.state_path) if args.state_path else None,
        delivery_log_path=Path(args.delivery_log_path) if args.delivery_log_path else None,
        session_key=args.session_key,
        event_types=_parse_event_types(args.event_types),
    )
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
    print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
