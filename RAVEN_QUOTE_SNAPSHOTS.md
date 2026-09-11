# Raven Quote Calculation Snapshots

## Purpose

A quote must remain historically correct after pricing configuration changes.

If a quote was calculated with a 25% markup and the active pricing profile is later changed to 30%, the existing quote must continue to represent the 25% calculation.

Raven therefore treats the calculation snapshot as an immutable historical record rather than recalculating historical quotes from current configuration.

## Snapshot contents

A `CalculationSnapshot` records:

- pricing profile ID
- pricing profile version when available
- calculation effective date
- resolved pricing values
- applied pricing rule IDs
- normalized rule actions
- line calculations
- subtotal cost
- total cost
- total price
- gross profit
- gross margin
- calculation trace
- calculation engine version

The snapshot contains copies of configuration data rather than references to live SQLAlchemy models or mutable rule dictionaries.

## Immutability

Snapshot domain objects use frozen dataclasses and tuples. Nested rule configuration is recursively copied into immutable tuple structures when the snapshot is created.

This prevents later mutation of a pricing rule or configuration object from silently changing the historical calculation.

## Persistence format

`CalculationSnapshot.to_dict()` produces a JSON-compatible representation.

Decimal values are serialized as strings rather than floating-point numbers. This preserves exact monetary and percentage values and avoids binary floating-point conversion.

The serialized snapshot is intended to be stored with the quote and treated as historical data.

## Historical reproducibility

A future pricing change must not rewrite a prior snapshot.

The snapshot is the authoritative record of what Raven used when the quote was calculated. Current pricing configuration is used only when calculating or recalculating a quote.

The calculation engine version is recorded so a historical quote can be distinguished from a result produced by a later engine implementation.

## Future extensions

The snapshot will eventually include additional quote-specific context such as:

- vendor and vendor-product values
- raw-goods supplier
- supply responsibility
- product options
- customer-specific data used by rules
- freight/handling inputs
- other resolved external data required to reproduce the quote

These should be added as explicit snapshot data, not live references.

## Principle

> Current configuration calculates new quotes. The snapshot explains old quotes.
