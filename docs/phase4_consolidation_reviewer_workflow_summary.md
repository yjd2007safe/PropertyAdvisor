# Phase 4 Consolidation: Reviewer workflow capability consolidation

This consolidation round gathers the reviewer workflow capabilities added across Phase4 Round4-Round7 into a clearer, more stable, and easier-to-maintain capability layer.

## Goal

Consolidate the reviewer workflow so the product, service layer, schema layer, and UI express the same reviewer workflow concepts with less drift and better documentation.

## Scope

- summarize the reviewer workflow capability that now exists across Round4-Round7
- align terminology and field intent across backend/service, schemas, and UI where small inconsistencies remain
- improve structural clarity without broad workflow redesign
- preserve the user-visible behavior unless a small consistency fix is clearly beneficial

## Success criteria

- a reviewer workflow summary doc exists and reflects the current capability set accurately
- reviewer workflow terminology is more consistent across service/schema/UI boundaries
- any narrow structural cleanup remains mergeable and low-risk
- tests and web build still pass

## Constraints

- no broad redesign of orchestration workflow
- no new task system, scoring engine, or unrelated product expansion
- no ingestion/database/infra expansion unless strictly required by the consolidation slice
