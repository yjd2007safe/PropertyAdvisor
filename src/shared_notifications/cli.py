from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Iterable

from .artifact_writer import NotificationArtifactWriter
from .relay import NotificationRelay

DEFAULT_ARTIFACT_PATH = Path(".dev_pipeline/notifications")


def _json_type(expected: type | tuple[type, ...], arg_name: str):
    def _parse(value: str) -> Any:
        try:
            payload = json.loads(value)
        except json.JSONDecodeError as exc:
            raise argparse.ArgumentTypeError(f"{arg_name} must be valid JSON: {exc}") from exc
        if not isinstance(payload, expected):
            expected_name = (
                expected.__name__
                if isinstance(expected, type)
                else " or ".join(t.__name__ for t in expected)
            )
            raise argparse.ArgumentTypeError(f"{arg_name} must be a JSON {expected_name}")
        return payload

    return _parse


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="shared-notifications",
        description="Shared notification runtime CLI.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    emit_parser = subparsers.add_parser("emit", help="Emit a notification artifact.")
    emit_parser.add_argument("--project", required=True)
    emit_parser.add_argument("--phase", required=True)
    emit_parser.add_argument("--round", required=True)
    emit_parser.add_argument("--slice-id", required=True)
    emit_parser.add_argument("--event-type", required=True)
    emit_parser.add_argument("--status", required=True)
    emit_parser.add_argument("--summary", required=True)
    emit_parser.add_argument("--artifact-path")
    emit_parser.add_argument("--details-json", type=_json_type(dict, "--details-json"))
    emit_parser.add_argument("--artifacts-json", type=_json_type(list, "--artifacts-json"))
    emit_parser.add_argument("--origin-json", type=_json_type(dict, "--origin-json"))
    emit_parser.add_argument(
        "--delivery-targets-json",
        type=_json_type(list, "--delivery-targets-json"),
    )
    emit_parser.add_argument("--event-id")
    emit_parser.add_argument("--created-at")
    emit_parser.set_defaults(func=_handle_emit)

    replay_parser = subparsers.add_parser("replay", help="Replay pending notification artifacts.")
    replay_parser.add_argument("--artifact-path", default=str(DEFAULT_ARTIFACT_PATH))
    replay_parser.add_argument("--delivery-log-path")
    replay_parser.add_argument("--state-path")
    replay_parser.set_defaults(func=_handle_replay)

    return parser


def _handle_emit(args: argparse.Namespace) -> int:
    artifact_path = Path(args.artifact_path) if args.artifact_path else DEFAULT_ARTIFACT_PATH
    writer = NotificationArtifactWriter(artifact_path)
    artifact, path = writer.write_event(
        event_type=args.event_type,
        project=args.project,
        phase=args.phase,
        round=args.round,
        slice_id=args.slice_id,
        status=args.status,
        summary=args.summary,
        details=args.details_json,
        artifacts=args.artifacts_json,
        origin=args.origin_json,
        delivery_targets=args.delivery_targets_json,
        event_id=args.event_id,
        created_at=args.created_at,
    )
    _print_json(
        {
            "status": "ok",
            "artifact_path": str(path),
            "artifact": artifact,
        }
    )
    return 0


def _handle_replay(args: argparse.Namespace) -> int:
    artifact_path = Path(args.artifact_path)
    delivery_log_path = Path(args.delivery_log_path) if args.delivery_log_path else None
    state_path = Path(args.state_path) if args.state_path else None

    relay = NotificationRelay(
        artifact_path=artifact_path,
        delivery_log_path=delivery_log_path,
        state_path=state_path,
    )
    delivered = relay.replay_pending()
    resolved_delivery_log_path = delivery_log_path or artifact_path / "delivery_log.jsonl"
    resolved_state_path = state_path or artifact_path / ".consumer_state.json"

    _print_json(
        {
            "status": "ok",
            "artifact_path": str(artifact_path),
            "delivery_log_path": str(resolved_delivery_log_path),
            "state_path": str(resolved_state_path),
            "replayed_count": len(delivered),
            "delivered_event_ids": [record["event_id"] for record in delivered],
        }
    )
    return 0


def _print_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, sort_keys=True))


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
