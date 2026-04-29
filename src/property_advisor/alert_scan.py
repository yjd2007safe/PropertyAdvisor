from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Iterable

from property_advisor.api.data_access import DataAccessLayer
from property_advisor.api.db import DatabaseConfig, DatabaseSessionFactory, create_session_factory, load_database_config
from property_advisor.api.services import scan_watchlist_alert_events
from property_advisor.operations_ledger import append_alert_scan_run_record, default_alert_scan_ledger_path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="property-advisor-alert-scan",
        description="Scan watchlist evidence alerts and persist alert_events lifecycle updates.",
    )
    parser.add_argument("--suburb-slug")
    parser.add_argument("--severity", choices=["info", "watch", "high"])
    parser.add_argument("--limit", type=int)
    parser.add_argument("--mode", choices=["auto", "mock", "postgres"], default="auto")
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON output.")
    parser.add_argument("--no-ledger", action="store_true", help="Skip writing the local alert scan operations ledger.")
    parser.add_argument("--ledger-path", type=Path, default=default_alert_scan_ledger_path(), help="Override alert scan ledger artifact path.")
    return parser


def _build_dal(mode: str) -> DataAccessLayer:
    if mode == "auto":
        return DataAccessLayer.create(create_session_factory())
    current = load_database_config()
    return DataAccessLayer.create(DatabaseSessionFactory(DatabaseConfig(url=current.url, requested_mode=mode)))


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    dal = _build_dal(args.mode)
    try:
        result = scan_watchlist_alert_events(
            suburb_slug=args.suburb_slug,
            severity=args.severity,
            limit=args.limit,
            dal=dal,
        )
    except Exception as exc:
        if not args.no_ledger:
            placeholder = scan_watchlist_alert_events(suburb_slug=args.suburb_slug, severity=args.severity, limit=0, dal=dal)
            append_alert_scan_run_record(
                path=args.ledger_path,
                mode=args.mode,
                filters={"suburb_slug": args.suburb_slug, "severity": args.severity, "limit": args.limit},
                result=placeholder,
                persistence_attempted=True,
                status="failed",
                error=str(exc),
            )
        raise

    payload = result.model_dump(mode="json")
    if not args.no_ledger:
        append_alert_scan_run_record(
            path=args.ledger_path,
            mode=args.mode,
            filters={"suburb_slug": args.suburb_slug, "severity": args.severity, "limit": args.limit},
            result=result,
            persistence_attempted=True,
            status="success",
        )
    if args.json:
        print(json.dumps(payload, sort_keys=True))
    else:
        counts = payload["counts"]
        print(
            "alert_scan "
            f"entries={counts['entries_scanned']} alerts={counts['alerts_scanned']} persisted={counts['persisted']} "
            f"new={counts['new']} changed={counts['changed']} unchanged={counts['unchanged']}"
        )
        print(json.dumps(payload, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
