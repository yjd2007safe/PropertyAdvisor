# Phase 6 Round 7: Evidence-driven watchlist alert surfacing

## Why this slice

Phase 6 review execution packets finished the workflow/review loop hardening, but the remaining product leverage was still in evidence production rather than UI-only polish. This slice closes the long-standing placeholder in `property_advisor.alerts` and turns advisory evidence into explicit watchlist alert signals.

## What changed

- Implemented deterministic `evaluate_alerts(advisory_snapshot)` rule logic for:
  - recommendation/fallback risk;
  - low-confidence and insufficient evidence;
  - target-range or pricing tension via comparable position;
  - weak comparable sample depth;
  - stale evidence;
  - material demand/supply shifts;
  - explicit evidence conflict.
- Wired alert evaluation into watchlist entry enrichment so advisory/comparable context produces additive watchlist alerts without schema migration.
- Updated watchlist events text to clearly distinguish evidence-driven alerts from generic watchlist status events.
- Updated watchlist alerts surface to include enriched/evidence-driven alerts.

## Alert semantics after this slice

Watchlist alerts are now a mixed stream:

1. **Baseline watchlist alerts** from stored watchlist entries.
2. **Evidence-driven advisory alerts** generated from the latest advisory snapshot + comparable/market context.

Evidence-driven alerts keep existing watchlist shape compatibility (`severity`, `title`, `detail`, `metric`, `observed_at`) so existing consumers keep working, while alert titles/details now make it clear when an alert is advisory-evidence derived.

## Product impact

This slice makes the advisory/watchlist path data-producing and evidence-driven as intended in phase planning: recommendations now carry explicit risk/quality/freshness signals into the action queue instead of relying on static placeholder behavior.
