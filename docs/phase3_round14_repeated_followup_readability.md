# Phase 3 Round 14: Repeated follow-up readability + review ergonomics

This slice advances the next narrow Phase 3 polish step after weekly review default cues, focused on reducing repeated weekly re-check friction across existing surfaces only.

## Scope (this round)

1. Improve repeated follow-up readability with clearer, less repetitive action copy.
2. Tighten weekly-review default behavior consistency on current pages.
3. Add lightweight emphasis cues for rapid change scanning during repeated reviews.

## What changed

- **Watchlist default consistency fix**: when no explicit `group_by` is provided, the page now actually loads data grouped by `strategy` (matching the UI default cue) and reset view returns to this weekly default.
- **Follow-up wording polish**: workflow helper copy now uses concise "Follow-up" phrasing and de-duplicates repeated action labels.
- **Watchlist event follow-up labels**: labels are now clearer and action-first (`Review suburb detail`, `Refresh advisor view`, `Check advisor recommendation`) to reduce repeated "open/run follow-up" wording.
- **Comparables change emphasis cue**: when viewing by most recent sale, the page now adds a compact cue that newest sales are surfaced first for weekly re-checks.

## Out of scope

- No schema/model changes.
- No API contract redesign.
- No new pages or navigation changes.
