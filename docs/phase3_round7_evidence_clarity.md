# Phase 3 Round 7: Evidence presentation and decision clarity

This slice upgrades how recommendation evidence is communicated in the existing advisor and comparables workflow surfaces, without changing API contracts or routing.

## What changed

- Advisor now includes an **Evidence quality** panel that surfaces freshness, strength, sample depth, agreement, model version, confidence reasons, section-level status, and thin-evidence indicators.
- Comparables now includes an **Evidence quality** panel that surfaces sample state, set quality metadata, quality score, algorithm version, plus a thin-evidence warning when depth is low.
- Comparables table now highlights decision readability by adding rank, score, and per-row rationale metadata in-line with match reasons.

## Why this remains narrow

- No workflow shell changes, no route rewrites, and no broad styling redesign.
- Existing advisory/comparables API semantics are reused.
- Scope is limited to interpreting recommendation quality and evidence strength more clearly where users already inspect decisions.
