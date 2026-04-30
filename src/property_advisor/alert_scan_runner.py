from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from typing import Iterable, Sequence

from property_advisor.alert_scan import main as alert_scan_main


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="property-advisor-alert-scan-runner",
        description="Local wrapper for one-shot or foreground-loop alert scan execution.",
    )
    parser.add_argument("--mode", choices=["auto", "mock", "postgres"], default="auto")
    parser.add_argument("--suburb-slug")
    parser.add_argument("--severity", choices=["info", "watch", "high"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--ledger-path")
    parser.add_argument("--interval-minutes", type=float, help="If set, run in a foreground loop at this interval.")
    parser.add_argument("--max-cycles", type=int, help="Optional safety/testing cap for number of loop cycles.")
    return parser


def _build_scan_argv(args: argparse.Namespace) -> list[str]:
    scan_args: list[str] = ["--json", "--mode", args.mode]
    if args.suburb_slug:
        scan_args.extend(["--suburb-slug", args.suburb_slug])
    if args.severity:
        scan_args.extend(["--severity", args.severity])
    if args.limit is not None:
        scan_args.extend(["--limit", str(args.limit)])
    if args.ledger_path:
        scan_args.extend(["--ledger-path", args.ledger_path])
    return scan_args


def _render_cycle_summary(cycle: int, payload: dict, scan_command: str) -> None:
    counts = payload.get("counts", {})
    now = datetime.now(timezone.utc).isoformat()
    print(
        f"[cycle {cycle}] {now} entries={counts.get('entries_scanned', 0)} alerts={counts.get('alerts_scanned', 0)} "
        f"persisted={counts.get('persisted', 0)} new={counts.get('new', 0)} changed={counts.get('changed', 0)} "
        f"unchanged={counts.get('unchanged', 0)}"
    )
    print(f"[cycle {cycle}] regenerate_command={scan_command}")


def _run_cycle(cycle: int, scan_argv: Sequence[str]) -> int:
    from io import StringIO
    import contextlib

    output = StringIO()
    with contextlib.redirect_stdout(output):
        code = alert_scan_main(scan_argv)
    text = output.getvalue().strip()
    if code != 0:
        print(text)
        return code
    payload = json.loads(text)
    _render_cycle_summary(cycle, payload, f"python -m property_advisor.alert_scan {' '.join(scan_argv)}")
    return 0


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    if args.interval_minutes is not None and args.interval_minutes <= 0:
        parser.error("--interval-minutes must be > 0 when provided")
    if args.max_cycles is not None and args.max_cycles <= 0:
        parser.error("--max-cycles must be > 0 when provided")

    scan_argv = _build_scan_argv(args)
    scan_command = f"python -m property_advisor.alert_scan {' '.join(scan_argv)}"

    if args.interval_minutes is None:
        print("[runner] one-shot mode")
        print(f"[runner] scan_command={scan_command}")
        return _run_cycle(1, scan_argv)

    cycle = 0
    interval_seconds = args.interval_minutes * 60
    print("[runner] foreground loop mode")
    print(f"[runner] interval_minutes={args.interval_minutes}")
    print(f"[runner] scan_command={scan_command}")

    while True:
        cycle += 1
        code = _run_cycle(cycle, scan_argv)
        if code != 0:
            return code
        if args.max_cycles is not None and cycle >= args.max_cycles:
            print(f"[runner] reached max_cycles={args.max_cycles}; exiting")
            return 0
        next_run = datetime.now(timezone.utc).timestamp() + interval_seconds
        next_run_at = datetime.fromtimestamp(next_run, tz=timezone.utc).isoformat()
        print(f"[runner] next_run_at={next_run_at}")
        time.sleep(interval_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
