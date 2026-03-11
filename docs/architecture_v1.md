# PropertyAdvisor Architecture v1

## 1. Architectural Intent
Build a practical first version that can ingest property market data, normalize it into a canonical model, compute market and comparable insights, generate property advice snapshots, and serve that to a web application and alerting workflows.

The design favors:
- simple modular services
- Postgres as source of truth
- asynchronous enrichment/jobs
- snapshot tables for historical traceability
- clear separation between raw market events and derived advice

## 2. High-Level System Modules
1. **Data ingestion layer**
   - Imports listing, sales, rental, and suburb data from external sources or batch files.
   - Performs normalization, de-duplication, and address matching.

2. **Core property data service**
   - Manages canonical properties, listings, event history, and suburb records.

3. **Market intelligence engine**
   - Aggregates suburb-level indicators by time period.
   - Produces metrics such as median price, median rent, DOM, listing volume, yield proxy, and trend direction.

4. **Comparables engine**
   - Builds comparable sets for a target property.
   - Scores candidate properties based on distance, recency, property type, bed/bath/parking similarity, land/building area, and price proximity.

5. **Property advisory engine**
   - Generates buy/sell/watch guidance based on current property data, suburb market conditions, comparable evidence, and recent changes.
   - Stores advice snapshots for auditability.

6. **Alerts service**
   - Evaluates watchlists and alert rules.
   - Produces alert events for downstream delivery.

7. **API layer**
   - Serves property pages, suburb dashboards, watchlists, comparables, and advice snapshots.

8. **Web application**
   - Search, property detail, suburb detail, watchlists, and alert settings.

## 3. Suggested Deployment Shape
### MVP
- Monorepo or single backend app
- Postgres database
- Background job runner / scheduler
- HTTP API
- Web frontend

### Logical components
- `api`: REST/JSON endpoints
- `worker`: scheduled ingestion, metrics rollups, comparable generation, advice generation, alerts
- `db`: Postgres
- `web`: frontend client

A single backend codebase with distinct modules is enough for v1.

## 4. Core Data Flow
### A. Data ingestion
1. External source import runs.
2. Incoming records are normalized.
3. Canonical property is found or created.
4. Listing/event records are inserted or updated.
5. Listing snapshots preserve observed state over time.

### B. Market intelligence
1. Scheduled job groups sales, rentals, and listings by suburb and period.
2. Derived metrics are written to `market_metrics`.
3. Downstream advice and alerts can be invalidated/recomputed.

### C. Comparables generation
1. Target property selected.
2. Candidate properties pulled from recent nearby sales/listings.
3. Similarity scoring applied.
4. Top comparable members stored in a `comparable_set`.

### D. Advice generation
1. Property facts + latest listing + suburb metrics + comparables are loaded.
2. Rule-based scoring produces recommendation, confidence, value range, and reasons.
3. Result is stored as a new `property_advice_snapshot`.

### E. Alerts
1. Watchlist and alert rules evaluated on new data arrival or scheduled scan.
2. Matching triggers produce alert events/deliveries.

## 5. Module Responsibilities
### Property data module
Owns:
- properties
- listings
- listing_snapshots
- sales_events
- rental_events
- suburbs

Responsibilities:
- address normalization
- canonical property matching
- preserving history
- lightweight derived attributes on property records

### Market intelligence engine
Owns:
- metric rollups
- trend calculations
- market direction classification

Inputs:
- listings, sales_events, rental_events, suburbs

Outputs:
- `market_metrics`

### Comparables engine
Owns:
- comparable candidate filtering
- similarity scoring
- comparable set creation

Inputs:
- properties, sales_events, listings, suburb context

Outputs:
- `comparable_sets`, `comparable_members`

### Advisory engine
Owns:
- recommendation generation
- confidence scoring
- explanation text/data
- target range calculation

Inputs:
- property facts
- latest listing state
- comparable sets
- market metrics
- recent event history

Outputs:
- `property_advice_snapshots`

### Alerts module
Owns:
- user watch preferences
- trigger evaluation
- alert lifecycle

Inputs:
- watchlists, alert_rules, data changes, advice changes

Outputs:
- alert trigger records or queued notifications (future table/service)

## 6. Initial Recommendation Logic
A first-pass advisory engine should remain transparent and mostly rule-based.

### Buy-side example signals
- Asking price below or within modeled fair range
- Positive suburb momentum
- Healthy comparable support
- Rental yield acceptable for strategy
- Limited red flags in recent trend

### Sell-side example signals
- Current market strength favorable
- Strong recent comparable sales
- Low competing inventory or strong DOM trend
- Asking/list range aligned with evidence

### Output fields
- recommendation: `buy_now | buy_if_below_range | watch | hold | sell_now | sell_if_target_hit | avoid`
- confidence: low / medium / high
- headline summary
- reasons for recommendation
- risks / cautions
- suggested value range

## 7. Comparables Engine Approach
### Candidate filters
- Same suburb first, then nearby suburbs if needed
- Same property type
- Recent activity window (e.g. last 6-12 months for sales)
- Similar bedroom count and land/building size bands

### Ranking inputs
- geographic distance
- recency
- property type match
- bedroom/bathroom/parking difference
- land area/building area variance
- sale/list price distance from target estimate

### Output
- 5-10 primary comparables for MVP
- stored rationale per comparable member
- overall comparable set quality score

## 8. API Surface (MVP)
- `GET /properties/:id`
- `GET /properties/:id/listings`
- `GET /properties/:id/comparables/latest`
- `GET /properties/:id/advice/latest`
- `GET /suburbs/:id`
- `GET /suburbs/:id/metrics`
- `GET /watchlists`
- `POST /watchlists`
- `POST /alert-rules`

## 9. Non-Functional Considerations
- Idempotent ingestion jobs
- Re-runnable metric/advice generation
- DB indexes on address keys, property ids, suburb ids, timestamps, and active listing filters
- Ability to rebuild derived tables from core event tables
- Avoid heavy microservice decomposition early

## 10. Recommended MVP Tech Choices
- Backend: Node.js/TypeScript or Python/FastAPI
- Database: PostgreSQL
- Jobs: cron + app worker / queue
- Frontend: React / Next.js
- Infra: single environment deployment is acceptable initially

## 11. Roadmap Architecture Notes
Later phases can add:
- raw source staging tables
- geospatial indexes and map search
- ML-assisted price/risk models
- notification delivery service
- user accounts and team sharing
- experiment logging and feedback loop for advice quality
