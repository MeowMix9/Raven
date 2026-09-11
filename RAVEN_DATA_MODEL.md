# Raven Data Model

> Raven — Configurable Quote & Business Automation Engine

**Status:** Initial Data Model Specification  
**Architecture Contract:** `RAVEN_ARCHITECTURE.md`  
**Related Platform:** Headless Horseman

## Purpose

This document defines the initial persistence model for Raven before application implementation begins. The database must describe Raven's business rather than dictate its user interface.

## Design Principles

1. Pricing is data, not source code.
2. Pricing configuration is effective-dated and auditable.
3. Historical quotes must remain reproducible after configuration changes.
4. Vendors are first-class business entities.
5. Vendor identity is separate from technical integrations.
6. Automated work is represented by observable jobs and runs.
7. Important business changes are recorded as audit events.
8. Money uses exact decimal arithmetic, never binary floating point.
9. Domain logic remains independent of the GUI and persistence implementation.

## Core Entities

```text
users
customers
vendors
products
vendor_products
pricing_profiles
pricing_profile_assignments
pricing_values
pricing_rules
quotes
quote_items
quote_calculations
integrations
jobs
job_runs
audit_events
```

## Relationships

```text
User
 ├── Quotes
 ├── Jobs
 └── Audit Events

Customer
 ├── Quotes
 └── Default Pricing Profile

Vendor
 ├── Vendor Products
 └── Integrations

Product
 ├── Vendor Products
 └── Quote Items

Pricing Profile
 ├── Assignments
 ├── Values
 └── Rules

Quote
 ├── Quote Items
 ├── Quote Calculations
 └── Historical Calculation Snapshot

Integration
 └── Job Runs

Job
 └── Job Runs
```

# User

Authenticated Raven user.

```text
users
-----
id
email
name
identity_reference
status
is_active
created_at
updated_at
last_login_at
```

# Customer

Customer receiving quotes.

```text
customers
---------
id
customer_code
name
status
is_active
default_pricing_profile_id
email
phone
notes
created_at
updated_at
created_by_user_id
updated_by_user_id
```

# Vendor

Supplier, manufacturer, or service provider.

```text
vendors
-------
id
vendor_code
name
status
is_active
contact_name
contact_email
contact_phone
website
notes
created_at
updated_at
created_by_user_id
updated_by_user_id
```

Vendor identity remains independent of technical integration configuration.

# Product

Raven's normalized representation of a product.

```text
products
--------
id
product_code
sku
name
description
category
unit_of_measure
status
is_active
metadata_json
created_at
updated_at
```

Core pricing/query fields remain first-class columns. JSON is reserved for genuinely variable metadata.

# Vendor Product

Maps a Raven product to a vendor's representation.

```text
vendor_products
---------------
id
vendor_id
product_id
vendor_sku
vendor_product_name
vendor_description
status
is_active
lead_time_days
minimum_quantity
metadata_json
created_at
updated_at
```

One Raven product may therefore have different vendor SKUs, costs, lead times, and minimums.

# Pricing Profile

Named container for pricing configuration.

```text
pricing_profiles
----------------
id
profile_code
name
description
profile_type
status
is_active
priority
effective_from
effective_to
version
created_at
updated_at
created_by_user_id
updated_by_user_id
```

Example types: Default, Wholesale, Retail, Customer, Promotional, Custom.

# Pricing Profile Assignment

Determines where and when a pricing profile applies.

```text
pricing_profile_assignments
---------------------------
id
pricing_profile_id
scope_type
scope_id
priority
effective_from
effective_to
is_active
created_at
updated_at
```

Possible scopes:

```text
GLOBAL
CUSTOMER
CUSTOMER_GROUP
VENDOR
PRODUCT
PRODUCT_CATEGORY
```

Profile resolution must be deterministic and data-driven.

# Pricing Value

Configurable parameter used by the pricing engine.

```text
pricing_values
--------------
id
pricing_profile_id
key
value_type
numeric_value
text_value
boolean_value
unit
currency
minimum_quantity
maximum_quantity
effective_from
effective_to
is_active
created_at
updated_at
```

Examples:

```text
base_cost
setup_fee
rush_fee
freight_rate
handling_fee
markup_percent
minimum_charge
margin_target
```

Pricing vocabulary must not be scattered through source code.

# Pricing Rule

Conditional pricing behavior.

```text
pricing_rules
-------------
id
pricing_profile_id
name
description
priority
condition_group_json
action_json
effective_from
effective_to
is_enabled
created_at
updated_at
created_by_user_id
updated_by_user_id
```

Conceptually:

```text
IF conditions are true
THEN perform actions
```

Rule ordering and conflict behavior must be deterministic and tested.

# Quote

Customer-facing quoting transaction and historical record.

```text
quotes
------
id
quote_number
customer_id
created_by_user_id
pricing_profile_id
status
quote_date
expiration_date
currency
subtotal
adjustments
total_cost
total_price
gross_profit
gross_margin_percent
notes
calculation_snapshot_json
calculation_engine_version
created_at
updated_at
```

Initial statuses:

```text
DRAFT
CALCULATED
REVIEWED
APPROVED
SENT
ACCEPTED
REJECTED
EXPIRED
CANCELLED
```

Status transitions belong to domain logic, not arbitrary GUI updates.

# Quote Item

Individual quoted line item.

```text
quote_items
-----------
id
quote_id
line_number
product_id
vendor_product_id
vendor_id
description
quantity
unit_of_measure
unit_cost
unit_price
extended_cost
extended_price
discount_amount
markup_amount
margin_amount
options_json
calculation_snapshot_json
created_at
updated_at
```

A quote item retains the values used for that quote even if current product, vendor, or pricing configuration changes later.

# Quote Calculation

Calculation detail supporting explainability and historical reproduction.

```text
quote_calculations
------------------
id
quote_id
quote_item_id
calculation_type
sequence
input_json
output_json
rule_ids_json
pricing_profile_id
engine_version
created_at
```

Possible stages:

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

# Integration

Technical connection belonging to a vendor.

```text
integrations
------------
id
vendor_id
name
integration_type
purpose
status
configuration_json
connection_reference
timeout_seconds
rate_limit_per_minute
is_enabled
last_success_at
last_error_at
last_error_message
created_at
updated_at
created_by_user_id
updated_by_user_id
```

Possible types:

```text
REST_API
SOAP_API
FTP
SFTP
EDI
EMAIL
FILE
MANUAL
```

Sensitive connection material must not be stored in ordinary business records, source code, logs, exports, or normal API responses. `connection_reference` represents a future secure credential abstraction.

# Job

Requested automated work.

```text
jobs
----
id
job_type
name
status
priority
source
vendor_id
integration_id
requested_by_user_id
schedule_reference
input_reference_json
created_at
updated_at
next_run_at
```

Example types:

```text
VENDOR_SYNC
PRODUCT_IMPORT
PRICE_IMPORT
QUOTE_RECALCULATION
FILE_EXPORT
NOTIFICATION
CUSTOM
```

# Job Run

One execution attempt of a job.

```text
job_runs
--------
id
job_id
status
attempt_number
started_at
completed_at
worker_reference
input_reference_json
result_reference_json
error_code
error_message
created_at
```

Statuses:

```text
QUEUED
RUNNING
SUCCEEDED
FAILED
CANCELLED
RETRYING
```

A job can have multiple attempts without destroying execution history. This maps naturally to the Headless Horseman worker model.

# Audit Event

Immutable record of a meaningful business or system change.

```text
audit_events
------------
id
event_type
entity_type
entity_id
actor_type
actor_id
action
before_json
after_json
metadata_json
created_at
```

Possible actors:

```text
USER
SYSTEM
JOB
API
HORSEMAN
```

Audit records must never contain sensitive connection material.

# Pricing Resolution

Pricing selection must be data-driven rather than hardcoded around specific customers or vendors.

```text
Quote Request
     |
     v
Find applicable Pricing Profile Assignments
     |
     v
Filter by effective date
     |
     v
Order by scope specificity + priority
     |
     v
Select active profile
     |
     v
Load Pricing Values + Rules
     |
     v
Evaluate rules
     |
     v
Calculate quote
```

The exact precedence algorithm must be deterministic and covered by tests.

# Historical Quote Reproducibility

If a quote is created with one vendor cost and markup, later pricing changes must not alter that historical quote.

The calculation snapshot should capture at minimum:

- Pricing profile identity/version.
- Effective pricing values.
- Rules used.
- Vendor/product values used.
- Quantities.
- Options.
- Calculation engine version.
- Resulting monetary values.

The normalized current configuration remains the source for future quotes. The quote snapshot is the source for historical explanation and reproduction.

# Monetary Rules

Use exact decimal/numeric storage for money and percentages.

```text
Money amount -> DECIMAL
Percentage   -> DECIMAL
Quantity     -> DECIMAL where fractional quantities are valid
```

Currency must be explicit. Rounding rules belong in the pricing engine and must be tested centrally.

Never use binary floating-point values for monetary calculations.

# JSON Rules

JSON is appropriate for:

- Integration protocol configuration.
- Variable product/vendor metadata.
- Rule conditions/actions.
- Historical quote snapshots.
- Job input/output references.
- Audit before/after state.

JSON is not a substitute for relationships Raven needs to query or enforce. IDs such as `customer_id`, `vendor_id`, `product_id`, `quote_id`, `pricing_profile_id`, `integration_id`, and `job_id` remain first-class fields.

# Deletion Policy

Records referenced by historical quotes or audit events should normally be deactivated rather than physically deleted.

Candidates for deactivation include Customers, Vendors, Products, Vendor Products, Pricing Profiles, Pricing Rules, Integrations, and Users.

Quotes should generally not be physically deleted through ordinary application behavior. Cancellation or archival should preserve history.

# Multi-Tenant Readiness

The first deployment may be single-tenant, but the model should avoid assumptions that prevent future organizations/tenants.

A future `organizations` entity can introduce `organization_id` on major business entities when multi-tenancy becomes an actual requirement. It should not be added prematurely unless needed by the first implementation.

# Initial Indexing Candidates

```text
users.email
customers.customer_code
vendors.vendor_code
products.product_code
products.sku
vendor_products.vendor_id + vendor_sku
pricing_profiles.profile_code
pricing_profile_assignments.scope_type + scope_id
pricing_rules.pricing_profile_id + priority
quotes.quote_number
quotes.customer_id
quotes.status
quotes.quote_date
quote_items.quote_id
integrations.vendor_id
integrations.status
jobs.status
jobs.next_run_at
job_runs.job_id
job_runs.status
audit_events.entity_type + entity_id
audit_events.created_at
```

Indexes should be validated against real query patterns during implementation.

# Integrity Rules

The database and domain layer should enforce important invariants where practical:

- Quote numbers are unique.
- Product codes are unique within organization scope.
- Vendor codes are unique within organization scope.
- Vendor products reference existing vendors and products.
- Quote items reference existing quotes.
- Normal quote quantities are greater than zero.
- Monetary values use decimal storage.
- Effective date ranges are valid.
- Disabled pricing rules cannot affect new calculations.
- Historical quote snapshots are not changed by current pricing edits.

# Deferred Domains

Do not prematurely complicate the first implementation with full CRM hierarchy, tax, payment processing, invoicing, full inventory management, advanced workflow design, attachment storage, full tenant management, fine-grained RBAC, or an external customer portal. These can be added when actual requirements justify them.

# Phase 1 Implementation Boundary

The first database migration should implement:

```text
User
Customer
Vendor
Product
VendorProduct
PricingProfile
PricingProfileAssignment
PricingValue
PricingRule
Quote
QuoteItem
QuoteCalculation
AuditEvent
```

Integration, Job, and JobRun persistence can follow as integration and automation features are implemented, provided their domain interfaces are respected from the beginning.

# Architectural Contract

1. No hardcoded business pricing values.
2. Pricing configuration can be edited without source changes.
3. Pricing supports effective dates and deterministic rule resolution.
4. Historical quotes remain stable after pricing changes.
5. Vendors support multiple products and integrations.
6. Vendor technical integrations remain separate from vendor identity.
7. Sensitive connection material is handled by a secure mechanism.
8. Money uses exact decimal arithmetic.
9. Automated work is observable through jobs and runs.
10. Meaningful business changes are auditable.
11. The quote engine remains callable independently of the GUI.
12. The model remains compatible with future Headless Horseman integration.

## Final Principle

> **Raven should be a configurable business system, not a calculator disguised as an application.**

Business Logic becomes Configuration.  
Configuration becomes Automation.  
Automation becomes Reusable Infrastructure.

**Quoth the Raven.**
