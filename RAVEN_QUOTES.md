# Raven Quote Domain

## Purpose

The quote domain represents a customer-facing quote independently of the database, API, GUI, spreadsheet, or vendor integrations.

Raven separates **quote state** from **quote calculation**.

```text
Quote
  |
  +-- Customer
  +-- Items
  +-- Pricing Profile
  +-- Status
  +-- Dates
  +-- Currency
  +-- Notes
  |
  +-- Calculation Snapshot
        |
        +-- Costs
        +-- Price
        +-- Profit
        +-- Margin
        +-- Applied Rules
        +-- Calculation Trace
        +-- Engine Version
```

## Lifecycle

```text
DRAFT
  -> CALCULATED
  -> REVIEWED
  -> APPROVED
  -> SENT
  -> ACCEPTED

Alternative terminal states:
  REJECTED
  EXPIRED
```

Lifecycle transitions belong to the quote domain/application layer rather than the frontend.

## Calculation boundary

`CalculateQuote` is the application service that orchestrates:

1. Pricing profile resolution.
2. Pricing value resolution.
3. Pricing rule retrieval.
4. Rule evaluation using quote context.
5. Calculation pipeline execution.
6. Immutable calculation snapshot creation.
7. Return of an explainable calculation result and snapshot.

```text
QuoteCalculationRequest
        |
        v
    CalculateQuote
        |
        +--> PricingResolver
        |
        +--> PricingRepository.get_rules()
        |
        +--> PricingRuleEvaluator
        |
        +--> PricingCalculationPipeline
        |
        +--> CalculationSnapshot
        |
        v
QuoteCalculationResult
```

The service does not contain pricing constants and does not implement presentation concerns.

## Immutable calculation snapshots

Once a quote is calculated, the historical calculation must not depend on mutable pricing configuration. If a markup changes from 25% to 30% tomorrow, an existing quote calculated at 25% must still represent the 25% calculation.

Raven therefore creates a `CalculationSnapshot` at the calculation boundary. The snapshot contains value copies, not references to live configuration objects.

The snapshot preserves, at minimum:

- pricing profile ID/version
- effective pricing values used
- applicable rule IDs and action payloads
- quantities and options represented by the calculation
- calculation engine version
- line costs
- total cost
- total price
- gross profit
- gross margin
- calculation trace

The snapshot is immutable in the domain model. Nested rule/action structures are converted to immutable tuples so later mutation of the source configuration cannot change the historical record.

`CalculationSnapshot.to_dict()` produces a JSON-compatible persistence representation. Decimal monetary and percentage values are serialized as strings rather than binary floating-point numbers.

## Persistence boundary

The quote domain depends on the `QuoteRepository` protocol rather than SQLAlchemy or PostgreSQL.

```text
Quote Domain
     |
     v
QuoteRepository
     |
     v
SqlAlchemyQuoteRepository
     |
     +--> quotes
     +--> quote_items
     +--> quote_calculations
```

The repository is responsible for translating between the domain model and persistence models. SQLAlchemy entities never cross back into the domain layer.

The persistence strategy deliberately uses two representations of calculation data:

1. **Normalized columns** on `quotes` and `quote_items` for filtering, reporting, sorting, and ordinary application queries.
2. **`calculation_snapshot_json`** for the immutable historical calculation record.

The JSON snapshot is the historical calculation authority. Normalized totals are queryable projections of that snapshot, not an alternate calculation engine.

`quote_calculations` stores trace entries in a queryable form for operational reporting and future audit tooling. It does not replace the immutable snapshot.

Saving a quote is transactional: the quote row, its items, and its calculation trace are persisted through the same repository/session boundary.

## Quote rehydration

When a persisted quote is loaded, the repository reconstructs the domain `Quote` and its `CalculationSnapshot` from durable data. The resulting domain object does not need access to the current pricing profile, rules, or pricing values to understand its historical calculation.

That means this remains valid even after configuration changes:

```text
2026-09-11
Markup = 25%
Quote calculated
       |
       v
Immutable snapshot
       |
       +----------------------+
                              |
2026-10-01                   |
Markup changed to 30%         |
                              v
                    Existing quote still = 25%
```

## Quote items

Quote items carry business identity and supply information needed to reproduce the quote. Vendor/product references are optional because some quote lines may represent services, charges, or customer-supplied goods.

Raw-goods responsibility must be represented as data rather than hardcoded behavior. This supports values such as:

- Raven Supplied
- Customer Supplied
- Contract Supplied
- Vendor Supplied

Output formatting can then automatically identify contract-supplied goods without special-case code for an individual company.

## Design rule

A quote is a business document with a calculation attached to it, not merely the output of a calculator.

The calculation engine remains reusable by APIs, GUI workflows, imports, scheduled jobs, and Headless Horseman automation.
