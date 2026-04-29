from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from property_advisor.api.schemas import AlertScanRunResponse

_DEFAULT_LEDGER_PATH = Path('.refresh/alert_scan_runs.json')


def default_alert_scan_ledger_path() -> Path:
    return _DEFAULT_LEDGER_PATH


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _read_records(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text())
    if not isinstance(payload, dict):
        return []
    records = payload.get('runs', [])
    return records if isinstance(records, list) else []


def append_alert_scan_run_record(
    *,
    path: Path,
    mode: str,
    filters: dict[str, object],
    result: AlertScanRunResponse,
    persistence_attempted: bool,
    status: str = 'success',
    error: str | None = None,
) -> dict[str, Any]:
    path.parent.mkdir(parents=True, exist_ok=True)
    records = _read_records(path)
    run_id = f"scan-{_utc_now_iso()}"
    record = {
        'run_id': run_id,
        'timestamp': _utc_now_iso(),
        'mode': mode,
        'filters': filters,
        'status': status,
        'error': error,
        'persistence_attempted': persistence_attempted,
        'counts': result.counts.model_dump(mode='json'),
        'generated_at': result.generated_at.isoformat(),
        'data_mode': result.mode,
        'fallback_detected': result.fallback_detected,
        'fallback_repositories': result.fallback_repositories,
        'regenerate_command': _build_regenerate_command(mode=mode, filters=filters),
    }
    records.append(record)
    path.write_text(json.dumps({'version': 1, 'updated_at': _utc_now_iso(), 'runs': records}, indent=2, sort_keys=True))
    return record


def _build_regenerate_command(*, mode: str, filters: dict[str, object]) -> str:
    command = ['python -m property_advisor.alert_scan', f'--mode {mode}', '--json']
    suburb_slug = filters.get('suburb_slug')
    severity = filters.get('severity')
    limit = filters.get('limit')
    if suburb_slug:
        command.append(f'--suburb-slug {suburb_slug}')
    if severity:
        command.append(f'--severity {severity}')
    if limit is not None:
        command.append(f'--limit {limit}')
    return ' '.join(command)


def get_alert_scan_run_history(path: Path, limit: int = 10) -> list[dict[str, Any]]:
    records = _read_records(path)
    return list(reversed(records))[: max(limit, 0)]
