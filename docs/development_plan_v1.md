# PropertyAdvisor Development Plan v1

## 1. Goal
Turn the architecture package into a buildable MVP in a controlled sequence, prioritizing reliable data foundations before UI polish.

## 2. Delivery Principles
- Ship an internal-first working slice early.
- Keep logic explainable and testable.
- Favor batch jobs and snapshots over premature real-time complexity.
- Build only what the first advisory workflow needs.

## 3. Suggested Build Order
### Phase 1: Foundation
**Outputs**
- project skeleton
- DB migrations from `schema_v1.sql`
- seed data path
- basic API app + worker app

**Tasks**
- set up backend framework
- set up migration tooling
- define repository/service structure
- add healthcheck and logging
- add config management

### Phase 2: Core property data
**Outputs**
- CRUD/read services for properties, suburbs, listings, events
- property search by address/suburb

**Tasks**
- property normalization helpers
- ingest/import scripts
- property detail API
- listing history API

### Phase 3: Market intelligence engine
**Outputs**
- suburb metric rollup jobs
- suburb metrics API

**Tasks**
- aggregate sales, rental, and listing activity by period
- compute first-pass demand/supply/temperature fields
- add tests for metric calculations

### Phase 4: Comparables engine
**Outputs**
- comparable generation job
- latest comparable set API

**Tasks**
- candidate selection query
- similarity scoring rules
- comparable quality scoring
- persisted rationale strings/data

### Phase 5: Advisory engine
**Outputs**
- advice snapshot generation job
- latest advice API

**Tasks**
- define rule-based recommendation model
- calculate value/rent guidance ranges
- store rationale, risks, and confidence
- add regression tests for recommendation scenarios

### Phase 6: Watchlists and alerts
**Outputs**
- watchlist APIs
- alert rule APIs
- rule evaluation worker

**Tasks**
- watchlist CRUD
- trigger evaluation on changed data
- record triggered events or deliveries

### Phase 7: Frontend MVP
**Outputs**
- property page
- suburb page
- watchlist page

**Tasks**
- read-only internal UX first
- evidence-first layout
- recommendation + comparables + trend summaries

## 4. Recommended Code Structure
### Backend
- `src/modules/properties`
- `src/modules/listings`
- `src/modules/events`
- `src/modules/suburbs`
- `src/modules/market-intelligence`
- `src/modules/comparables`
- `src/modules/advisory`
- `src/modules/watchlists`
- `src/modules/alerts`
- `src/jobs`

### Frontend
- `web/app/properties/[id]`
- `web/app/suburbs/[id]`
- `web/app/watchlists`

## 5. Initial API Priorities
1. `GET /properties/:id`
2. `GET /properties/:id/advice/latest`
3. `GET /properties/:id/comparables/latest`
4. `GET /suburbs/:id/metrics`
5. `POST /watchlists`
6. `POST /alert-rules`

## 6. Testing Strategy
### Unit tests
- address normalization
- metric calculations
- comparable scoring
- recommendation rules

### Integration tests
- ingestion to canonical property linking
- property detail read model
- suburb metric rollups
- advice snapshot generation

### Seed/demo data
Prepare a small, representative suburb/property dataset so the full workflow can be demoed end-to-end early.

## 7. Suggested Milestones
### Milestone 1
Database + property/suburb/listing/event read model working.

### Milestone 2
Suburb metrics and comparable generation working.

### Milestone 3
Advice snapshots working for internal users.

### Milestone 4
Watchlists and alerts working.

### Milestone 5
Internal MVP UI ready for evaluation.

## 8. Key Open Decisions
- initial target geography and data coverage
- ingestion source mix and legality/compliance
- backend stack choice (TypeScript vs Python)
- auth/user model timing
- whether alert event history needs its own table in next schema revision

## 9. Recommended Next Step After This Package
Implement the backend foundation first:
1. choose stack
2. convert schema to migrations
3. create seed/demo dataset
4. build property + suburb read APIs
5. add first metric rollup job

That sequence gets the product from concept to a testable advisory backbone quickly.
