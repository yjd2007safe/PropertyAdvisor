# Phase 3 — Product UX / Workflow Enhancement Tasks

## Objective

Turn the data-capable advisory MVP into a practical repeated-use product flow: discover signal, inspect property, validate evidence, decide action, and monitor changes.

## Entry condition

Phase 2 provides stable persisted metrics, comparables, advice snapshots, and meaningful confidence/rationale fields.

## Ordered task list

### 1. Tighten the end-to-end workflow map
**Tasks**
1. Define the primary user loops explicitly:
   - suburb screening
   - property review
   - comparable validation
   - watchlist decision
   - alert follow-up
2. Audit current routes and UI states against those loops.
3. Remove dead-end navigation and duplicate next-step prompts.

**Dependencies**
- stable Phase 2 outputs

**Success criteria**
- each major page has a clear user purpose and next action
- workflow snapshot links are consistent across surfaces

### 2. Improve search, query resolution, and handoff quality
**Tasks**
1. Strengthen address/suburb query resolution UX.
2. Make route params and direct links robust for real suburb/property identifiers.
3. Add empty states for unmatched/weakly matched queries.
4. Ensure moving between suburb → advisor → comparables preserves context.

**Dependencies**
- Phase 1 canonical identifiers stable

**Success criteria**
- users can reliably land on the intended entity from common query forms
- cross-page handoff no longer drops context

### 3. Upgrade evidence presentation
**Tasks**
1. Show freshness/source/confidence clearly on each evidence block.
2. Present comparables in a decision-friendly layout:
   - rank
   - distance
   - recency
   - feature differences
   - rationale
3. Present advisory rationale and risks as structured evidence, not generic prose.
4. Surface data gaps honestly when sample depth is weak.

**Dependencies**
- Phase 2 data semantics stable

**Success criteria**
- the user can understand why a recommendation exists without reading code
- weak evidence is visible instead of hidden

### 4. Make watchlists operational
**Tasks**
1. Improve watchlist CRUD and status updates for real user actions.
2. Add practical states such as review, active, paused, archived if needed.
3. Let users save or move properties/suburbs into watchlists from major pages.
4. Show latest advisory/comparable/market changes inside watchlist detail.

**Dependencies**
- Phases 1-2 identifiers and evidence outputs

**Success criteria**
- watchlist becomes the action hub, not a placeholder page
- repeated weekly review is supported

### 5. Add alert/event visibility
**Tasks**
1. Create a readable alert/event timeline or status panel.
2. Show what changed, when, and which entity it affects.
3. Distinguish advisory changes, comparable changes, and market shifts.
4. Add basic acknowledge/dismiss/archive behavior if it simplifies repeated use.

**Dependencies**
- Phase 2 alert generation signals available

**Success criteria**
- users can tell what deserves follow-up without rechecking everything manually

### 6. Add operator-grade transparency and controls
**Tasks**
1. Show data mode, source provenance, and freshness at page level where useful.
2. Add internal/admin-only debug affordances if needed:
   - latest refresh time
   - snapshot count
   - fallback indicators
   - low-confidence warnings
3. Make fallback-to-mock behavior obvious in non-production states.

**Dependencies**
- Phases 1-2 provenance metadata available

**Success criteria**
- operators can trust what they are seeing and diagnose thin-data states quickly

### 7. Polish for weekly product use
**Tasks**
1. Improve loading states and page responsiveness.
2. Clean up terminology across dashboard, advisor, comparables, watchlist, and alerts.
3. Reduce clutter and duplicate summaries.
4. Add basic saved filters/sorts where they materially help repeated review.

**Dependencies**
- core workflow stable

**Success criteria**
- product feels cohesive for repeated internal use
- major actions can be completed quickly without hunting for controls

### 8. Expand acceptance coverage around real workflows
**Tasks**
1. Add end-to-end smoke coverage for the main user journeys.
2. Add UI assertions for data freshness, confidence, and next-step messaging.
3. Include thin-data and empty-state journeys, not only happy paths.

**Dependencies**
- Tasks 1-7

**Success criteria**
- workflow regressions are caught automatically
- UI remains aligned with advisory semantics as logic evolves

## Recommended auto_dev round breakdown

1. workflow/navigation cleanup
2. evidence presentation and confidence/freshness UI
3. watchlist action loop improvements
4. alert/event visibility
5. end-to-end workflow acceptance coverage

## Phase 3 done when

- a user can move from market signal to property decision confidently inside the app
- the app communicates evidence quality, freshness, and next actions clearly
- watchlist and alerts support an ongoing review workflow instead of one-off demos
