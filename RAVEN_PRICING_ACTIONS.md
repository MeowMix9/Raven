# Raven Pricing Action Contract

> **Status:** Domain contract  
> **Related:** `RAVEN_ARCHITECTURE.md`, `RAVEN_DATA_MODEL.md`, `RAVEN_FOUNDATION.md`

## Purpose

Pricing rules determine **when** configured behavior applies. Pricing actions determine **what** the calculation engine should do when a rule matches.

The action contract exists to keep business pricing values out of source code while still giving the calculation pipeline a deterministic vocabulary.

## Core Rule

Action **types** are part of Raven's domain vocabulary. Action **values** are configuration.

For example, this is valid:

```json
{
  "type": "apply_markup",
  "target": "unit_price",
  "value_key": "markup_percent"
}
```

The action type is defined by Raven; `markup_percent` and its actual value live in pricing configuration.

This is also valid for a temporary or explicitly configured literal:

```json
{
  "type": "apply_markup",
  "target": "unit_price",
  "value": "0.25"
}
```

A business pricing value should normally use `value_key` so the value remains editable through pricing configuration.

## Supported Action Types

### `set_value`

Set a target value directly.

```json
{
  "type": "set_value",
  "target": "unit_price",
  "value": "12.50"
}
```

### `add_amount`

Add an absolute amount to a target monetary/numeric value.

```json
{
  "type": "add_amount",
  "target": "unit_price",
  "value_key": "handling_fee"
}
```

### `subtract_amount`

Subtract an absolute amount.

### `multiply`

Multiply a numeric target by a configured factor.

```json
{
  "type": "multiply",
  "target": "unit_price",
  "value": "1.10"
}
```

### `add_percent`

Increase a target by a percentage represented as a decimal ratio.

```text
0.25 = 25%
0.10 = 10%
```

### `subtract_percent`

Decrease a target by a percentage represented as a decimal ratio.

### `apply_markup`

Semantic pricing operation for applying a markup percentage to a target.

```json
{
  "type": "apply_markup",
  "target": "unit_price",
  "value_key": "markup_percent"
}
```

### `apply_discount`

Semantic pricing operation for applying a discount percentage to a target.

```json
{
  "type": "apply_discount",
  "target": "unit_price",
  "value_key": "wholesale_discount_percent"
}
```

### `add_charge`

Add an absolute charge that can be represented as a distinct calculation line.

```json
{
  "type": "add_charge",
  "value_key": "rush_fee",
  "label": "Rush fee",
  "currency": "USD"
}
```

`label` is required because the resulting charge must be explainable in the quote calculation.

### `set_minimum`

Establish a minimum for a target value.

```json
{
  "type": "set_minimum",
  "target": "total_price",
  "value_key": "minimum_charge"
}
```

## Action Schema

All actions contain:

```text
 type       required string
 target     required for target-based actions
 value      optional literal operand
 value_key  optional pricing configuration reference
 label      optional except add_charge, where required
 currency   optional three-letter currency code
```

An action must provide **exactly one operand source** when its type requires a value:

```text
value
OR
value_key
```

Never both.

## Operand Rules

### Literal values

Literal numeric values are normalized to `Decimal` before calculation.

### Pricing value references

`value_key` refers to a resolved `PricingValue` from the active pricing context.

This is the preferred mechanism for ordinary business pricing.

Example:

```text
Pricing Value
key: markup_percent
value: 0.25

Rule Action
value_key: markup_percent
```

The action does not know that the configured value is currently 25%. It only knows which configuration value to consume.

## Composition

Actions are executed in rule priority order.

For example:

```text
Rule 100: apply_markup  -> +25%
Rule  90: add_charge    -> +$15
Rule  80: apply_discount -> -10%
```

The calculation pipeline owns the arithmetic and determines which calculation stage each action affects.

The action contract itself does not perform pricing arithmetic.

## Calculation Stages

Actions should eventually map to explicit calculation stages such as:

```text
BASE_COST
MATERIAL
LABOR
SETUP
DECORATION
FREIGHT
HANDLING
VENDOR_COST
MARKUP
DISCOUNT
RUSH_FEE
MINIMUM
OTHER
```

This preserves explainability and allows the quote calculation record to show how a final number was produced.

## No Hidden Business Constants

The following is acceptable:

```python
if action.type == "apply_markup":
    price = price * (Decimal("1") + operand)
```

The operation is domain behavior; the operand is configuration.

The following is forbidden:

```python
price = price * Decimal("1.35")
```

The 35% value belongs in `PricingValue`, not source code.

Likewise, this is forbidden:

```python
rush_fee = Decimal("25.00")
```

The amount belongs in configuration.

## Error Handling

Invalid actions must fail deterministically before calculation.

Examples:

- unknown action type
- missing required target
- missing required operand
- both `value` and `value_key` supplied
- invalid numeric operand
- invalid currency
- missing charge label

An invalid configured rule should produce a configuration/calculation error rather than silently changing the quote.

## Auditability

A calculated quote should retain enough information to explain each applied action:

```text
rule ID
rule priority
action type
target
operand source
resolved operand value
calculation stage
result before action
result after action
```

Historical quote snapshots must preserve the resolved operand values used at calculation time.

## UI Implications

The future Pricing Rule editor should not expose raw JSON as the primary user experience.

A user should be able to select:

```text
WHEN
  Quantity >= 100

THEN
  Apply Markup
  Target: Unit Price
  Value: Markup Percent
```

The UI translates that configuration into the domain action contract.

Advanced users may eventually have access to structured/JSON configuration, but the normal workflow should be form-driven.

## Future Extension

New action types may be added when real business requirements justify them.

Potential future actions include:

- `set_margin_target`
- `choose_vendor`
- `set_vendor`
- `add_percentage_charge`
- `round_to_increment`
- `set_lead_time`
- `create_exception`
- `require_approval`
- `notify`

These should not be added merely because they are possible. Each new action must have a clear domain contract, deterministic behavior, tests, and an appropriate calculation/audit representation.

## Architectural Principle

> **Rules decide when. Actions describe what. Configuration supplies the values. The calculation pipeline performs the arithmetic.**

This separation keeps Raven configurable today and automatable by Headless Horseman tomorrow.

**Quoth the Raven.**
