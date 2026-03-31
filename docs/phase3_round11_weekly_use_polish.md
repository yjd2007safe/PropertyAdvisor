# Phase 3 Round 11: Weekly-use workflow polish

This slice advances **Phase 3 task 7** immediately after workflow acceptance coverage, with a narrow and mergeable product polish scope.

## Scope (this round)

1. Improve loading-state clarity across key workflow surfaces used in weekly review loops.
2. Clean up inconsistent terminology and repeated action labels introduced across recent rounds.
3. Add small repeat-review affordances (saved filter/sort views) only where they materially reduce operator friction.
4. Keep implementation limited to UI workflow polish; no data-model churn or broad redesign.

## What changed

- Added route-specific loading states for:
  - suburb dashboard
  - property advisor
  - comparables
  - watchlist
  - orchestration review
- Normalized handoff copy via shared flow-context helper so advisor/comparables/watchlist present consistent continuation messaging.
- Standardized watchlist action copy from “Save / update watchlist” or “Save” to “Save to watchlist,” and replaced shorthand “Comps” with “Comparables.”
- Added lightweight repeat-review presets:
  - comparables quick weekly filters (nearby shortlist, broader scan, reset)
  - watchlist saved review views (needs review + high alerts, active weekly queue, reset)

## Out of scope (intentionally unchanged)

- No API schema changes.
- No business-logic recommendation changes.
- No broad visual redesign or navigation rewrite.
