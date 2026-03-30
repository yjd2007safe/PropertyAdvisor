# Phase 3 Round 6: Search/query resolution + cross-page handoff quality

This round focuses on context continuity across the core product loop:

- suburb dashboard -> advisor
- advisor -> comparables
- comparables -> watchlist/alerts
- watchlist detail -> advisor/comparables

## What changed

- Added thin client-side handoff context tags (`from`, `intent`) to key links so direct links preserve user intent between pages.
- Improved advisor/comparables query-type inference for direct links by inferring slug vs address when query type is absent.
- Improved watchlist detail deep-link resilience: requesting an unknown `detail_slug` now shows a clear empty state instead of failing the whole page.
- Strengthened API workflow links so major surfaces include entity-specific query params when a suburb slug is known.

## Why this is intentionally narrow

- No routing rewrite.
- Existing API and page surfaces are reused.
- Changes target continuity gaps and weak/missing-context UX dead-ends only.
