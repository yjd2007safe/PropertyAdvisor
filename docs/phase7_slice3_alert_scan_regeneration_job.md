# Phase7 Slice 3 — Alert scan / regeneration job

## Goal

Provide a dedicated, idempotent command for regenerating watchlist evidence alerts and persisting/updating `alert_events` without requiring a read endpoint side effect.

## Entrypoint

Run the scanner as a module:

```bash
python -m property_advisor.alert_scan --json
```

Optional filters:

- `--suburb-slug <slug>`: scan a single watchlist suburb.
- `--severity info|watch|high`: persist only alerts at the chosen severity.
- `--limit <n>`: limit number of watchlist entries scanned.
- `--mode auto|mock|postgres`: force data mode for this run (`auto` default).

## Output contract

`--json` emits one machine-readable object with:

- `generated_at`: UTC timestamp for the scan run.
- `mode`: resolved DAL mode (`mock` or `postgres`).
- `filters`: echo of runtime filters.
- `data_source`: structured source/fallback summary (including upstream source chain).
- `fallback_detected`: true when any repository used fallback mock.
- `fallback_repositories`: repository names currently in fallback.
- `counts`:
  - `entries_scanned`
  - `alerts_scanned`
  - `persisted`
  - `new`
  - `changed`
  - `unchanged`

## Idempotency and lifecycle behavior

- Event identity remains deterministic by `event_key` (suburb + metric + severity + title seed).
- Re-running scan with unchanged evidence increments occurrence/last-seen and reports `unchanged`.
- Re-running after evidence change updates fingerprints and reports `changed`.
- First-seen evidence reports `new`.

## Operational notes

- The command exits non-zero only on operational/runtime failures.
- Thin data and fallback data source situations are returned structurally in JSON output (`data_source`, `fallback_detected`) rather than treated as fatal errors.
