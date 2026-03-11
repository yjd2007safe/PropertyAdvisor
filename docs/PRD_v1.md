# PropertyAdvisor PRD v1

## 1. Product Summary
PropertyAdvisor is a residential real-estate decision-support platform for individual buyers, sellers, and small-scale investors. It helps users evaluate whether a property is worth buying, holding, renting, or selling by combining listing data, sales history, rental signals, suburb trends, comparable properties, and generated advisory recommendations.

This product is not a listings portal. It is an advisory layer on top of property and market data.

## 2. Problem Statement
Residential property decisions are slow, high-stakes, and often made with fragmented information:
- Buyers struggle to judge fair value, risk, and competition.
- Sellers struggle to price correctly and time a sale.
- Investors struggle to compare yield, growth, and market conditions across suburbs and individual properties.
- Comparable analysis is usually manual and inconsistent.

Users need a practical tool that converts market data into clear, defensible recommendations.

## 3. Target Users
### Primary
- Owner-occupier buyers
- Individual residential property investors
- Home sellers

### Secondary
- Buyer’s agents / advisers
- Small property research teams

## 4. Product Goals
- Help users make better buy/sell decisions faster.
- Provide transparent reasoning, not black-box scores only.
- Centralize listing, sales, rental, suburb, and advisory data.
- Support repeat monitoring through watchlists and alerts.

## 5. Non-Goals (v1)
- Property transaction execution
- Mortgage broking workflows
- Full CRM for agents
- Nationwide production-grade ingestion from every source on day one
- AVM-level valuation precision for all property types

## 6. Core User Jobs
### Buyer
- Find a property of interest.
- Understand fair value range.
- See comparable sales and active competition.
- Assess suburb trend, downside risk, and rental potential.
- Decide whether to inspect, offer, negotiate, or pass.

### Seller
- Understand likely sale range.
- Identify best timing and pricing strategy.
- Monitor competition and local demand shifts.
- Decide whether to list now, hold, or renovate first.

### Investor
- Compare target suburbs.
- Assess yield, vacancy proxy, momentum, and price trend.
- Monitor properties and market changes over time.
- Decide whether to buy, hold, or sell.

## 7. Core Features
1. **Property profile**
   - Canonical property record
   - Latest active/inactive listing history
   - Sales and rental event history
   - Property facts and derived features

2. **Market intelligence**
   - Suburb-level metrics
   - Supply and demand indicators
   - Median price, rent, days on market, vendor discount, listing volume trends

3. **Comparables engine**
   - Auto-generated comparable sets per property and scenario
   - Ranked comparable members with rationale and distance/feature differences

4. **Property advisory engine**
   - Buy / Hold / Sell / Watch recommendation state
   - Confidence level
   - Evidence summary and key risk factors
   - Suggested action range (e.g. target buy range, suggested list range)

5. **Watchlists and alerts**
   - Save properties and suburbs
   - Alert on price changes, new comparable sales, new listings, rental shifts, and advice changes

6. **Snapshot history**
   - Preserve listing snapshots and advice snapshots for auditability and trend tracking

## 8. Key User Journeys
### Journey A: Buyer evaluates a listing
1. User opens a property page.
2. System shows current listing, value range, comparable sales, suburb conditions, and risks.
3. User reviews advice summary and detailed evidence.
4. User adds property to watchlist.
5. User receives alerts if price, comparables, or advice change.

### Journey B: Seller decides listing strategy
1. User selects owned property.
2. System shows likely sale range and relevant local comparables.
3. System summarizes market momentum and competing inventory.
4. User receives a recommended listing strategy and watch alerts.

### Journey C: Investor scouts a suburb
1. User views suburb dashboard.
2. System surfaces market metrics, trend direction, rent/sale activity, and notable changes.
3. User drills into selected properties.
4. User saves suburb or properties for ongoing monitoring.

## 9. Functional Requirements
### Must Have for MVP
- Create and maintain canonical property records.
- Store listings and listing snapshots.
- Store sales and rental events.
- Store suburb metrics by period.
- Generate comparable sets and comparable member rankings.
- Generate advice snapshots for properties.
- Support watchlists and alert rules.
- Expose core data through internal API endpoints.

### Should Have Soon After MVP
- Manual property search + address matching improvements
- Better confidence scoring and explainability
- Scheduled alert delivery channels (email / push)
- Simple admin tools for data review and reruns

## 10. Quality Requirements
- Clear provenance of recommendations.
- Deterministic first-pass advice generation where possible.
- Fast read performance for property pages (<2s typical API response with cached aggregates).
- Support reprocessing without corrupting historical snapshots.

## 11. Success Metrics
- Time to evaluate a property reduced to <10 minutes.
- % of viewed properties added to watchlists.
- % of advice pages with successful comparable generation.
- Alert open/click rate.
- Repeat weekly active users.

## 12. Risks
- Data quality and address matching issues.
- Incomplete market coverage early on.
- Overstating confidence when comparables are weak.
- Regulatory/compliance concerns if advice is presented too absolutely.

## 13. Product Principles
- Advice should be evidence-led.
- Show the “why”, not just the score.
- Preserve historical states for auditability.
- Start with a practical analyst-style workflow before over-automating.
