# PropertyAdvisor MVP Scope

## 1. MVP Outcome
Deliver a usable internal-first product that can:
- represent residential properties canonically
- track listing, sale, and rental history
- compute basic suburb market metrics
- generate comparable sets
- generate explainable property advice snapshots
- support watchlists and alert rules

## 2. In Scope
### Data foundation
- Canonical property records
- Suburb records
- Listings + listing snapshots
- Sales events
- Rental events

### Decision-support features
- Property detail view with latest advice snapshot
- Comparable sales/listings section
- Suburb market summary
- Value range / recommendation summary
- Watchlists
- Rule-based alerts

### System capabilities
- Scheduled ingestion jobs
- Scheduled market metric rollups
- Scheduled comparable generation
- Scheduled advice generation
- API endpoints for property/suburb/watchlist reads

## 3. Explicitly Out of Scope
- Automated purchase/sale execution
- Mortgage servicing or lender integrations
- Full document vault
- Consumer-ready mobile app
- Advanced personalization engine
- Agent CRM and pipeline management
- Real-time nationwide ingestion coverage
- Fully automated valuation model across all stock

## 4. MVP User Stories
### Buyer
- As a buyer, I can view a property’s current listing and recent comparable sales.
- As a buyer, I can see a suggested buy range and reasons.
- As a buyer, I can save a property and be alerted to price or advice changes.

### Seller
- As a seller, I can view an estimated sale range and recent local comparables.
- As a seller, I can monitor market conditions in my suburb.

### Investor
- As an investor, I can compare suburb-level price/rent conditions.
- As an investor, I can assess rental history and yield proxy for a property.

## 5. MVP Screens / Surfaces
- Property search/select page
- Property detail page
- Suburb detail page
- Watchlist page
- Admin/research job status page (basic, optional but useful)

## 6. Core Rules for v1
- Prefer evidence-backed summaries over excessive automation.
- If comparable quality is weak, say so explicitly.
- Keep recommendation categories small and understandable.
- Preserve historical snapshots rather than overwriting judgments.

## 7. MVP Acceptance Criteria
- A property can be created and linked to listing/sales/rental history.
- A suburb can show at least one time-series market metric set.
- A comparable set can be generated and persisted for a property.
- An advice snapshot can be generated and retrieved for a property.
- A user can add a property to a watchlist and define at least one alert rule.

## 8. Suggested First Target Geography
Start with one metro region or state where data quality is manageable. Expand after:
- address normalization is stable
- comparable generation is reliable
- alert volume is under control

## 9. Release Strategy
### Phase 0
Internal analyst/research use only.

### Phase 1
Invite-only early users.

### Phase 2
Public beta after data quality and advice consistency improve.
