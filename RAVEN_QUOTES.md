# Raven Quote Domain

## Purpose

The quote domain represents a customer-facing quote independently of the database, API, GUI, spreadsheet, or vendor integrations.

Raven separates **quote state** from **quote calculation**.

## Calculation boundary

`CalculateQuote` orchestrates pricing profile resolution, pricing value resolution, rule retrieval, rule evaluation, calculation pipeline execution, and immutable calculation snapshot creation.

The service does not contain pricing constants and does not implement presentation concerns.

## Immutable calculation snapshots

Once a quote is calculated, the historical calculation must not depend on mutable pricing configuration. If a markup changes from 25% to 30% tomorrow, an existing quote calculated at 25% must still represent the 25% calculation.

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

The snapshot is immutable in the domain model. Decimal monetary and percentage values are serialized as strings rather than binary floating-point numbers.

## Quote item price semantics

A quote item distinguishes **cost** from **sell price**. Raven must not copy cost into a sell-price field merely because the persistence schema contains both fields.

Quote items therefore carry:

- `unit_cost` / `extended_cost`
- `unit_price` / `extended_price`
- `discount_amount`
- `markup_amount`
- `margin_amount`

The current calculation pipeline produces authoritative quote-level totals and a calculation trace. It does not invent a per-line allocation of a quote-level price. Allocating a global markup, minimum, discount, or charge across lines is a business rule and must be explicitly defined.

For that reason, persistence requires explicit line sell prices for a calculated quote. Draft quotes may temporarily use cost as a display fallback when no sell price has been entered. This is a persistence safeguard, not pricing logic.

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

The repository translates between the domain model and persistence models. SQLAlchemy entities never cross back into the domain layer.

Normalized quote columns are projections for filtering, reporting, sorting, and ordinary application queries. `calculation_snapshot_json` is the historical calculation authority.

`quote_calculations` stores trace entries in a queryable form for operational reporting and future audit tooling. It does not replace the immutable snapshot.

Saving a quote is transactional: the quote row, its items, and its calculation trace are persisted through the same repository/session boundary.

## Quote rehydration

When a persisted quote is loaded, the repository reconstructs the domain `Quote` and its `CalculationSnapshot` from durable data. The resulting domain object does not need access to current pricing configuration to understand its historical calculation.

## Quote items and supply responsibility

Quote items carry business identity and supply information needed to reproduce the quote. Vendor/product references are optional because some quote lines may represent services, charges, or customer-supplied goods.

Raw-goods responsibility must be represented as data rather than hardcoded behavior. This supports values such as:

- Raven Supplied
- Customer Supplied
- Contract Supplied
- Vendor Supplied

Output formatting can then automatically identify contract-supplied goods without special-case code for an individual company.

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

## Design rule

A quote is a business document with a calculation attached to it, not merely the output of a calculator.

The calculation engine remains reusable by APIs, GUI workflows, imports, scheduled jobs, and Headless Horseman automation.
