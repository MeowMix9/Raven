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
6. Return of an explainable calculation result.

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
        v
QuoteCalculationResult
```

The service does not contain pricing constants and does not implement presentation concerns.

## Calculation snapshots

Once a quote is calculated, the result must remain historically reproducible even if pricing configuration changes later.

The persisted snapshot should preserve, at minimum:

- pricing profile ID/version
- effective pricing values used
- applicable rule IDs and actions
- vendor/product values used by the calculation
- quantities and options
- calculation engine version
- line costs
- total cost
- total price
- gross profit
- gross margin
- calculation trace

The database representation may use JSON for the immutable snapshot, while the normalized quote tables remain authoritative for searchable business entities.

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
