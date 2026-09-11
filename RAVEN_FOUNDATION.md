# Raven Foundation Specification

> Raven — Configurable Quote & Business Automation Engine

**Status:** Foundation Specification
**Architecture Contract:** `RAVEN_ARCHITECTURE.md`
**Data Contract:** `RAVEN_DATA_MODEL.md`
**Related Platform:** Headless Horseman

## Purpose

This document defines the implementation foundation for Raven. It prevents the first coding phase from inventing a different architecture than the established system and data contracts.

## Technology Baseline

### Backend

- Python 3.14+
- FastAPI
- Pydantic v2
- SQLAlchemy 2.x
- Alembic
- PostgreSQL
- pytest
- Ruff

The backend is authoritative for domain behavior and business rules.

### Frontend

- React
- TypeScript
- Tailwind CSS

The frontend consumes the API and must not contain authoritative pricing logic.

### Database

PostgreSQL is the authoritative relational database. SQLite may be used for lightweight unit tests where SQL behavior is compatible, but PostgreSQL behavior must be covered before production use.

## Repository Structure

```text
Raven/
├── backend/
│   ├── raven/
│   │   ├── api/
│   │   ├── auth/
│   │   ├── audit/
│   │   ├── core/
│   │   ├── customers/
│   │   ├── database/
│   │   ├── integrations/
│   │   ├── jobs/
│   │   ├── pricing/
│   │   ├── products/
│   │   ├── quotes/
│   │   ├── vendors/
│   │   └── main.py
│   ├── tests/
│   ├── alembic/
│   ├── alembic.ini
│   ├── pyproject.toml
│   └── .env.example
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   ├── components/
│   │   ├── features/
│   │   ├── layouts/
│   │   ├── pages/
│   │   └── types/
│   ├── package.json
│   └── .env.example
├── docs/
├── scripts/
├── README.md
├── RAVEN_ARCHITECTURE.md
├── RAVEN_DATA_MODEL.md
└── RAVEN_FOUNDATION.md
```

Exact names may evolve, but dependency direction must not.

## Dependency Direction

```text
Frontend
   |
   v
API / Presentation
   |
   v
Application Services
   |
   v
Domain
   |
   +----> Domain Ports / Interfaces
                    |
                    v
               Infrastructure
```

The domain must not depend on FastAPI, SQLAlchemy models, React, HTTP, or a specific database driver.

## Domain and Persistence

SQLAlchemy models are persistence representations, not the entire domain model. Domain objects and services own business behavior.

This separation is especially important for pricing calculations, pricing rule evaluation, quote lifecycle transitions, pricing profile resolution, and historical quote reproduction.

The first implementation does not need elaborate enterprise architecture. It does need boundaries that allow the quote engine to run without an HTTP request or GUI.

## Configuration

Application configuration is environment-driven and typed.

Example variables:

```text
RAVEN_ENV
RAVEN_DATABASE_URL
RAVEN_API_HOST
RAVEN_API_PORT
RAVEN_LOG_LEVEL
RAVEN_SECRET_KEY
RAVEN_CORS_ORIGINS
```

A real `.env` is never committed. `.env.example` contains only safe placeholders.

## Database and Migrations

Alembic is the schema migration authority.

Rules:

1. Schema changes occur through migrations.
2. Generated migrations are reviewed before commit.
3. The application does not silently create production tables at startup.
4. Migrations are deterministic and reversible where practical.
5. Seed data is separate from schema migrations.
6. Money and percentages use exact decimal/numeric types.
7. Timestamps are consistently timezone-aware.

The first migration implements the Phase 1 entities in `RAVEN_DATA_MODEL.md`:

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
audit_events
```

`integrations`, `jobs`, and `job_runs` may follow with their feature work, but their interfaces must remain architecturally compatible from the beginning.

## Database Conventions

- UUID primary keys for externally meaningful entities.
- Foreign keys for actual relationships.
- Explicit unique constraints for business identifiers.
- `created_at` and `updated_at` on mutable business records.
- Decimal/numeric columns for money and percentages.
- JSON/JSONB only where the data model explicitly permits variable structure.
- Indexes based on real query patterns.

Business identifiers such as quote numbers, vendor codes, customer codes, and product codes are not substitutes for primary keys.

## API Boundary

FastAPI provides the HTTP boundary. API handlers translate requests into application/domain services rather than implementing business calculations directly.

Initial endpoints:

```text
GET /health
GET /api/v1/health
```

Domain endpoints are added incrementally:

```text
/api/v1/customers
/api/v1/vendors
/api/v1/products
/api/v1/pricing-profiles
/api/v1/pricing-rules
/api/v1/quotes
```

Quote calculation eventually gets a dedicated application operation such as:

```text
POST /api/v1/quotes/calculate
```

The exact public API contract is defined when each domain is implemented.

## Application Services

Application services coordinate use cases, for example:

```text
CreateCustomer
CreateVendor
CreateProduct
ResolvePricingProfile
CalculateQuote
CreateQuote
RecalculateQuote
TransitionQuoteStatus
RecordAuditEvent
```

They coordinate repositories, domain services, and external ports without becoming a dumping ground for arbitrary business logic.

## Repository Interfaces

Persistence access should be hidden behind interfaces where that boundary protects meaningful domain independence.

Examples include quote repositories and pricing repositories. SQLAlchemy implementations belong in infrastructure.

Do not create abstractions merely for ceremony. Protect the boundaries that matter: pricing, quotes, integrations, and external systems.

## Money and Numeric Handling

Money is high-risk business logic.

The implementation must:

- Use Python `Decimal` for monetary arithmetic.
- Use PostgreSQL `NUMERIC/DECIMAL` for monetary persistence.
- Never use binary floating point for money.
- Make currency explicit.
- Centralize rounding behavior.
- Test rounding at relevant calculation boundaries.

The frontend displays authoritative monetary values returned by the backend.

## Pricing Engine Boundary

The pricing engine is the primary domain boundary:

```text
QuoteRequest
      |
      v
Pricing Resolver
      |
      v
Resolved Pricing Context
      |
      v
Rule Evaluator
      |
      v
Calculation Pipeline
      |
      v
Quote Calculation Result
```

It must not care whether it was called by the UI, API, CLI, a scheduled job, Headless Horseman, or another application.

## Pricing Configuration Rule

No business pricing constants may be hidden in Python source.

This is forbidden:

```python
MARKUP = 0.35
RUSH_FEE = 25.00
MINIMUM_CHARGE = 100.00
```

Those values belong in configurable pricing data. Spreadsheet values become seed records, not source constants.

## Quote Snapshot

A calculated quote captures the effective inputs needed to explain the result later, including as applicable:

```text
pricing profile/version
pricing values
pricing rules used
vendor/product values
quantities
options
calculation stages
engine version
currency/rounding context
resulting monetary values
```

The snapshot is historical evidence. Editing current pricing never rewrites a previous quote snapshot.

## Audit and Logging

Audit meaningful changes to pricing, rules, vendors, integrations, quotes, quote status, important customer/product changes, and automated work.

Do not audit every HTTP request by default.

Use structured logging with stable identifiers. Logs and audit records must never contain passwords, API keys, tokens, private keys, or credential material.

## Error Handling

Initial error categories:

```text
VALIDATION_ERROR
NOT_FOUND
CONFLICT
CALCULATION_ERROR
CONFIGURATION_ERROR
INTEGRATION_ERROR
AUTHENTICATION_ERROR
AUTHORIZATION_ERROR
INTERNAL_ERROR
```

API responses should be safe and useful; detailed diagnostics belong in appropriate server-side logs.

## Testing Foundation

```text
backend/tests/
├── unit/
│   ├── pricing/
│   ├── quotes/
│   └── core/
├── integration/
│   ├── database/
│   └── api/
└── fixtures/
```

Foundation tests must verify application startup, typed configuration, database connectivity, clean migrations, health endpoints, decimal handling, importable domain/application modules, and operation without external vendor credentials.

Pricing behavior receives its comprehensive test suite in Phase 2.

## Transactions

Application use cases define meaningful transaction boundaries. Creating a quote and its calculation snapshot should be atomic from the application's perspective.

Avoid arbitrary commits inside low-level repository methods when doing so prevents coherent rollback of multi-step operations.

## Authentication Boundary

Authentication belongs in the foundation, but full authorization/RBAC is deferred. The initial user model supports identity reference and active state while keeping authentication and authorization as separate concerns.

## Frontend Boundary

The frontend may render forms, perform usability validation, manage UI state, and request calculations. It must not become the authoritative pricing engine.

The backend must recalculate before a quote is persisted or approved.

## Headless Horseman Compatibility

Keep clean extension points for future shared concepts:

```text
Job
JobRun
Connector
CredentialReference
AuditEvent
StorageReference
Workflow
Rule
```

Do not copy Horseman implementation code merely because concepts are similar. Establish compatible interfaces first; extract shared libraries only after the boundary is proven.

## Local Development

The intended workflow is:

```text
1. Create Python environment.
2. Install backend dependencies.
3. Configure environment variables.
4. Start PostgreSQL.
5. Run Alembic migrations.
6. Start FastAPI.
7. Run backend tests.
8. Start frontend development server.
9. Run frontend checks/build.
```

Docker/Compose may provide repeatable PostgreSQL development, but domain tests should not require Docker.

## CI Expectations

CI should eventually enforce:

```text
Backend formatting/linting
Backend tests
Migration validation
Frontend type checking
Frontend linting
Frontend tests/build
```

External vendor credentials are never required by ordinary pull-request CI.

## Implementation Sequence

### Foundation 1 — Project Skeleton

Create backend/frontend structure and development configuration.

### Foundation 2 — Database Infrastructure

Create SQLAlchemy infrastructure, Alembic configuration, database sessions, and the initial migration.

### Foundation 3 — Core Domain Types

Introduce identifiers, timestamps, money/decimal handling, statuses, and domain errors.

### Foundation 4 — Initial Entities

Implement the Phase 1 entities from `RAVEN_DATA_MODEL.md`.

### Foundation 5 — Application/API Boundary

Implement health checks, dependency injection, API versioning, error handling, and foundational endpoints.

### Foundation 6 — Tests and CI

Establish automated tests and quality gates.

### Foundation 7 — Pricing Engine

Only after the foundation is stable should actual pricing logic begin.

## Explicit Non-Goals

Do not build these during foundation:

- Full quote GUI.
- Full dashboard.
- Vendor connection implementations.
- Complex workflow designer.
- Customer portal.
- Billing/payment processing.
- Tax engine.
- Full CRM.
- Full inventory management.
- Advanced RBAC.
- Production credential management.
- Premature multi-tenant infrastructure.

## Acceptance Criteria

The foundation is complete when:

1. Backend/frontend structure is clear.
2. Configuration is typed and environment-driven.
3. PostgreSQL is the authoritative database target.
4. Alembic owns schema migrations.
5. Phase 1 entities migrate cleanly.
6. Money uses exact decimal arithmetic.
7. Domain/application boundaries are established.
8. The API has a versioned boundary and health endpoint.
9. No business pricing is hardcoded.
10. Tests run without external vendor credentials.
11. Secrets are excluded from Git and logs.
12. CI validates the foundation.
13. The quote engine can be implemented independently of the GUI.
14. The structure leaves a clean path toward Headless Horseman compatibility.

## Architectural Contract

`RAVEN_ARCHITECTURE.md` defines system architecture. `RAVEN_DATA_MODEL.md` defines persistence semantics. `RAVEN_FOUNDATION.md` defines implementation boundaries.

If implementation pressure conflicts with these documents, stop and resolve the architectural conflict rather than silently bypassing the contract.

> **Build the foundation once. Build the business on top of it.**

**Quoth the Raven.**
