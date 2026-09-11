# Raven Architecture

> Raven — Configurable Quote & Business Automation Engine

**Status:** Initial Architecture  
**Repository:** `MeowMix9/Raven`  
**Related Platform:** Headless Horseman

---

## Core Principles

Raven is intended to become a configurable business system rather than a hardcoded quoting calculator.

- **Configuration over hardcoding.** Pricing, vendor behavior, business rules, and operational parameters should be represented as data wherever practical.
- **Pricing is data, not source code.** The existing spreadsheet is seed/default data; users must be able to modify pricing through the application without changing code.
- **Pricing profiles and versioned rules.** Rules should support effective dates, priorities, enabled state, and audit history.
- **Quote engine independent of GUI.** The calculation engine must be callable from the UI, API, CLI, jobs, or Headless Horseman.
- **Vendors are first-class entities.** Vendor identity and business configuration are separate from technical integrations.
- **Integrations are abstracted.** A vendor may have multiple API, FTP, SFTP, EDI, email, or file integrations.
- **Credentials are separate and secure.** Secrets must never be embedded in source, ordinary configuration, logs, quote records, or exports.
- **Automation is first-class.** Synchronization, imports, exports, validation, notifications, and recalculation should be representable as jobs/workflows.
- **Auditability.** Historical quotes must remain reproducible after pricing changes.
- **API-first.** The GUI should consume the same domain services available to automation clients.
- **Headless Horseman compatibility.** Reusable concepts should be implemented in a way that can eventually be shared with Horseman.

---

## High-Level Architecture

```text
Raven UI
    |
    v
Raven API
    |
    +--------------------+
    |                    |
    v                    v
Quote Engine        Integration Engine
    |                    |
    v                    v
Pricing / Rules      Vendor Connectors
    |                    |
    +---------+----------+
              |
              v
         Jobs / Workflows
              |
              v
           Database
```

The GUI is a client of the API/domain services rather than the location of business logic.

---

## Major Domains

A likely structure is:

```text
raven/
├── core/
├── quotes/
├── pricing/
├── vendors/
├── integrations/
├── customers/
├── products/
├── automation/
├── audit/
├── auth/
└── api/
```

Dependency direction should remain:

```text
UI -> API -> Domain Services -> Core / Infrastructure
```

---

## Quote Domain

A quote should retain enough information to understand what was quoted and why.

Potential fields:

- Quote ID
- Customer
- Quote date
- Expiration date
- Salesperson/user
- Products/items
- Quantities
- Options
- Pricing profile
- Vendor selections
- Calculated costs
- Sell price
- Margin
- Status
- Notes
- Calculation snapshot
- Audit history

### Quote lifecycle

```text
Draft -> Calculated -> Reviewed -> Approved -> Sent -> Accepted / Rejected / Expired
```

A quote must retain its calculation inputs/snapshot so historical quotes do not silently change when pricing configuration changes.

Successful customer-facing quotes may display the branding phrase **“Quoth the Raven.”** This is presentation only and must never participate in calculation logic.

---

## Pricing Domain

Pricing components should be configurable rather than hardcoded. Potential components include:

- Base Cost
- Material Cost
- Labor Cost
- Setup Cost
- Decoration Cost
- Freight
- Handling
- Vendor Cost
- Markup
- Margin
- Discount
- Rush Fee
- Minimum Charge
- Additional Charges

### Pricing profiles

Profiles may include Default, Customer-specific, Wholesale, Retail, Promotional, and Custom.

### Pricing rules

Rules should support conditions, operators, values, actions, priorities, effective dates, and enabled/disabled state.

Conceptual calculation flow:

```text
QuoteRequest
    -> Load Pricing Profile
    -> Load Pricing Rules
    -> Resolve Products
    -> Resolve Vendors
    -> Calculate Costs
    -> Apply Markups
    -> Apply Discounts
    -> Apply Minimums / Fees
    -> Calculate Margin
    -> QuoteResult
```

The engine should be callable from the Raven UI, API, CLI, scheduled jobs, Headless Horseman, and external applications.

---

## Vendor Domain

Vendor identity, business configuration, and technical integrations remain distinct.

```text
Vendor
├── Identity
│   ├── Name
│   ├── Code
│   ├── Contact Information
│   └── Status
│
├── Business Configuration
│   ├── Products
│   ├── Pricing
│   ├── Lead Times
│   ├── Minimums
│   └── Rules
│
└── Integrations
    ├── API
    ├── FTP
    ├── SFTP
    ├── EDI
    ├── Email
    └── File
```

### Vendor management UI

The GUI should eventually provide vendor lists and details with sections for General information, Products, Pricing, Lead Times, Integrations, Files, Rules, Activity, and Test Connection.

---

## Integration Architecture

```text
Vendor
   |
   v
Integration Configuration
   |
   v
Connector
   |
   v
Protocol / Service
```

Potential connector types:

- REST API
- SOAP API
- FTP
- SFTP
- HTTP/HTTPS
- EDI
- Email
- File Import/Export
- Manual

A conceptual connector interface:

```python
class VendorConnector:
    def connect(self): ...
    def test_connection(self): ...
    def authenticate(self): ...
    def list_products(self): ...
    def retrieve_data(self): ...
    def submit_data(self): ...
    def disconnect(self): ...
```

Actual interfaces should be capability-based rather than forcing every connector to implement unsupported operations.

Individual implementations could include `RESTConnector`, `FTPConnector`, `SFTPConnector`, `EDIConnector`, `EmailConnector`, and `FileConnector`.

### Integration configuration

API integrations may contain a base URL, authentication type, API-key reference, OAuth configuration, headers, timeout, and rate limits. FTP/SFTP integrations may contain host, port, username, credential reference, remote path, file format, and protocol-specific options.

### Secrets

Credentials must never be committed to Git, stored in ordinary configuration files, written to logs, included in normal API responses, or included in quote exports. They should be referenced through a dedicated secure credential abstraction.

### Multiple integrations per vendor

One vendor may have multiple independent integrations:

```text
Vendor A
├── Product API
├── Inventory SFTP
├── Order API
└── Invoice FTP
```

An integration record should conceptually contain ID, Vendor, Name, Type, Purpose, Configuration, Credentials Reference, Status, Last Successful Connection, Last Error, and Enabled state.

---

## Vendor Synchronization and Jobs

Example workflow:

```text
Vendor file arrives
    -> Retrieve
    -> Parse
    -> Transform
    -> Validate
    -> Update vendor/product data
    -> Recalculate affected quotes
    -> Record audit event
```

A job/run record may contain Vendor, Integration, Action, Input/reference, Started timestamp, Completed timestamp, Status, Result/reference, and Error.

The job model should map naturally to Headless Horseman jobs/workers.

---

## Headless Horseman Integration

Raven should be a specialized business application that can eventually participate as a module within Headless Horseman.

```text
Headless Horseman
    |
    +-- Automation Modules
          |
          +-- Raven Module
          +-- Takedown Module
          +-- Other Modules
          |
          +-- Shared Services
```

Shared concepts should include, where appropriate:

- Jobs
- Workers
- Connectors
- Credentials
- Integrations
- Workflows
- Rules
- Transformations
- Audit logs
- Storage
- Notifications
- Scheduling
- APIs

Raven should avoid Raven-only abstractions when a Horseman-compatible abstraction makes sense.

Example automation:

```text
New vendor file
    -> Import
    -> Transform
    -> Validate
    -> Update pricing
    -> Recalculate quotes
    -> Create exceptions
    -> Notify user
```

Another example:

```text
New quote
    -> Calculate
    -> Check margin
    -> If below threshold:
         Create exception
         Notify reviewer
    -> Otherwise approve/send
```

---

## API Surface

Potential resources:

```text
/api/quotes
/api/quotes/calculate
/api/pricing-profiles
/api/pricing-rules
/api/vendors
/api/vendors/{id}/integrations
/api/integrations
/api/products
/api/customers
/api/jobs
/api/audit
```

Routes may evolve, but API capabilities should map to domain concepts rather than GUI screens.

---

## Database Model Candidates

Initial entities may include:

```text
users
customers
vendors
vendor_integrations
credentials
products
pricing_profiles
pricing_rules
quotes
quote_items
quote_calculations
jobs
job_runs
audit_events
```

Relationships:

```text
Vendor
  ├── Integrations
  │      └── Credentials Reference
  ├── Products
  └── Pricing Rules

Customer
  └── Pricing Profile

Pricing Profile
  └── Pricing Rules

Quote
  ├── Customer
  ├── Products
  ├── Vendor
  ├── Pricing Profile
  └── Calculation Snapshot
```

---

## UI Direction

Primary navigation should eventually include:

```text
Dashboard
Quotes
Pricing
Products
Customers
Vendors
Integrations
Automation
Reports
Settings
```

### Pricing UI

Users must be able to inspect and modify pricing parameters without editing source code. The UI should distinguish defaults, overrides, customer-specific values, vendor-specific values, effective-dated values, and currently active values.

### Vendor UI

The vendor area should provide both business configuration and technical integration management without conflating them. A user should be able to configure a vendor's API/FTP/SFTP/etc. connection from the GUI and test it without editing configuration files.

---

## Spreadsheet as Seed Data

The existing pricing spreadsheet is not the application architecture. Its values become initial/default configuration.

Future pricing changes should happen through GUI configuration, API, import/export, or automation.

Possible formats include CSV, Excel, JSON, and API-based import/export.

The spreadsheet is therefore **seed data**, not business logic.

---

## Auditability and Historical Reproducibility

Pricing changes over time. Historical quotes must not change because a user edited today's pricing.

When a quote is calculated, Raven should preserve the relevant calculation inputs and/or a calculation snapshot sufficient to reproduce the result.

Audit records should capture meaningful changes to pricing profiles, pricing rules, vendor configuration, integrations, quote calculations, quote status, user actions, and automated jobs.

---

## Testing Strategy

The pricing engine should have deterministic tests covering tiers, markups, margins, discounts, minimums, fees, rounding, effective dates, rule priority/conflicts, missing/invalid data, edge quantities, vendor-specific pricing, and customer-specific pricing.

Integration testing should cover connector configuration, connection testing, authentication failure, retrieval, submission, timeouts, rate limiting, invalid responses, file parsing, and job failure/retry behavior.

Quote testing should cover draft creation, calculation, recalculation, snapshot persistence, status transitions, and historical reproducibility.

Security testing should ensure secrets never leak through API responses, logs, exports, or audit records.

---

## Implementation Order

### Phase 1 — Foundation

- Project structure
- Configuration
- Database
- Domain models
- Migrations
- Core abstractions
- Initial tests

### Phase 2 — Pricing

- Pricing profiles
- Pricing rules
- Pricing engine
- Rule evaluation
- Calculation tests

### Phase 3 — Quotes

- Quote model
- Quote items
- Calculation
- Historical snapshots
- Quote API
- Quote UI foundation

### Phase 4 — Vendors

- Vendor model
- Vendor management
- Products
- Vendor pricing
- Integration model
- Credential abstraction
- Connection testing

### Phase 5 — Data Synchronization

- Imports
- API synchronization
- FTP/SFTP synchronization
- Jobs
- Audit events
- Error handling/retries

### Phase 6 — GUI

- Dashboard
- Quote interface
- Pricing configuration
- Vendor management
- Integration management
- Reports

### Phase 7 — Automation

- Workflows
- Schedules
- Triggers
- Notifications
- Horseman integration

---

## Architectural Decisions

1. **Pricing is configurable.** Raven will not hardcode business pricing values. Current spreadsheet values are initial defaults/seed data.
2. **Pricing is versionable.** Pricing changes must be auditable and historical quotes must remain reproducible.
3. **Vendors are first-class entities.** Vendor management is part of Raven's core business domain.
4. **Vendor integrations are separate from vendor identity.** A vendor may have multiple technical integrations.
5. **Protocols are abstracted.** REST, FTP, SFTP, EDI, email, and file integrations belong behind connector abstractions.
6. **Credentials are referenced, not embedded.** Secrets belong in a dedicated secure credential mechanism.
7. **Jobs are first-class entities.** Synchronization and automation work should be observable, auditable, and compatible with future workers.
8. **API-first.** The GUI is a client of the Raven API/domain services.
9. **Horseman-compatible architecture.** Raven should reuse or align with Headless Horseman concepts wherever practical.
10. **Spreadsheet is seed data.** It is an initial data source, not the pricing engine.
11. **Customer-facing branding.** A successful quote may display **“Quoth the Raven.”** as a presentation element.

---

## Final Architectural Principle

> **Raven should be a configurable business system, not a calculator disguised as an application.**

The intended evolution is:

```text
Business Logic becomes Configuration.
Configuration becomes Automation.
Automation becomes Reusable Infrastructure.
```

That infrastructure should ultimately be capable of living inside, or being shared with, Headless Horseman.
