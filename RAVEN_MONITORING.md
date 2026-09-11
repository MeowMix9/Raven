# Raven Monitoring & Alerts

## Purpose

Raven must be able to detect when an external dependency becomes unavailable, remains unavailable, or recovers. Monitoring is a first-class capability and must not be embedded inside quote calculations or individual vendor integrations.

## Design Principles

1. **Monitoring is configuration-driven.** Targets, schedules, thresholds, and alert destinations are data, not hardcoded behavior.
2. **Recovery matters.** Raven alerts on meaningful state transitions, including recovery after an outage.
3. **Avoid alert storms.** Consecutive-failure and consecutive-success thresholds prevent repeated notifications for transient conditions.
4. **Checks are capability-based.** HTTP/API checks are only one implementation; FTP, SFTP, database, and other integration health checks can use the same monitoring model.
5. **Monitoring is independent of pricing.** A vendor being unavailable must not alter pricing calculations implicitly.
6. **History is retained.** Check results and state transitions provide an auditable availability history.
7. **Notifications are abstracted.** Monitoring produces alert events; notification channels determine how those events are delivered.
8. **Horseman-compatible.** Scheduled checks map naturally to Headless Horseman Jobs and JobRuns.

## Conceptual Flow

```text
Monitor Configuration
        |
        v
Scheduled Job
        |
        v
Health Check
        |
        v
Health Result
        |
        v
State Evaluator
        |
        +---- no transition ----> Record Result
        |
        +---- transition -------> Alert Event
                                      |
                                      v
                              Notification Channel
```

## Monitor

A monitor represents a configured health check target.

Conceptual fields:

- `id`
- `name`
- `description`
- `target_type`
- `target_reference`
- `check_type`
- `configuration_json`
- `schedule`
- `timeout_seconds`
- `retry_policy_json`
- `failure_threshold`
- `recovery_threshold`
- `is_enabled`
- `current_state`
- `last_checked_at`
- `last_success_at`
- `last_failure_at`
- timestamps

The target reference must not contain credentials. Secrets belong to the credential/integration layer.

## Target Types

Initial target types should support the architecture without requiring every connector immediately:

- `HTTP`
- `API`
- `FTP`
- `SFTP`
- `DATABASE`
- `INTEGRATION`
- `CUSTOM`

The implementation should allow additional target types without changing the state machine.

## Check Types

Potential checks include:

- availability/reachability
- HTTP status
- response-time threshold
- response-body validation
- authentication validation
- connector-specific health check
- custom health assertion

A check returns a normalized health result rather than exposing protocol-specific details to the state evaluator.

## Health Result

A normalized result should contain enough information to diagnose a failure without storing secrets:

- `monitor_id`
- `checked_at`
- `success`
- `status`
- `response_time_ms`
- `error_code`
- `error_message`
- `metadata_json`

Sensitive response bodies, authorization headers, passwords, tokens, and credentials must never be persisted in health results or alerts.

## State Machine

```text
UNKNOWN
   |
   +-- success ------------------> HEALTHY
   |
   +-- failure ------------------> DEGRADED

HEALTHY
   |
   +-- failures >= threshold ---> DOWN
   |
   +-- transient failure -------> HEALTHY

DEGRADED
   |
   +-- success ------------------> HEALTHY
   +-- failures >= threshold ---> DOWN

DOWN
   |
   +-- successes >= threshold --> RECOVERED
                                      |
                                      v
                                   HEALTHY
```

`RECOVERED` may be represented as a transition/event rather than a persistent state. The persistent monitor state returns to `HEALTHY` after the recovery event is emitted.

The exact state transition policy must be deterministic and covered by unit tests.

## Alert Events

Meaningful events include:

- `MONITOR_DEGRADED`
- `MONITOR_DOWN`
- `MONITOR_RECOVERED`
- `MONITOR_DISABLED`
- `MONITOR_CONFIGURATION_ERROR`

The alert event should identify the monitor, transition, timestamp, and relevant non-sensitive diagnostic information.

## Alert Policy

Alerting should be configurable independently from checking.

Conceptual policy:

- enabled/disabled
- events to notify
- notification destinations
- minimum severity
- cooldown/deduplication behavior
- escalation behavior

Example:

```text
Creative Goods API

Check: every 5 minutes
Expected: HTTP 200
Timeout: 15 seconds
Failure threshold: 2
Recovery threshold: 1

DOWN notification: Email + Webhook
RECOVERED notification: Email + Webhook
```

## Notification Abstraction

Monitoring should emit a domain-level notification request. Channel implementations handle delivery.

Potential channels:

- Email
- Webhook
- n8n
- Slack
- Microsoft Teams
- SMS
- In-app notification
- Headless Horseman notification service

The monitoring subsystem must not contain provider-specific delivery code.

## Jobs and Horseman

A scheduled monitor maps naturally to the Horseman execution model:

```text
Monitor
   |
   v
Job
   |
   v
JobRun
   |
   v
Connector / Health Check
   |
   v
Health Result
   |
   v
State Transition
   |
   v
Alert Event
```

Raven may implement a lightweight local scheduler during early development, but the domain contracts should remain compatible with the Horseman Job/JobRun model.

## Database Direction

Likely entities:

- `monitors`
- `monitor_checks`
- `monitor_state_transitions`
- `alert_policies`
- `notification_destinations`
- `notification_events`

The exact schema should be introduced when monitoring implementation begins. Do not prematurely add all monitoring tables to the Phase 1 pricing migration.

## Operational Requirements

Monitoring should provide:

- current state
- last check
- last successful check
- last failed check
- consecutive failure count
- consecutive success count
- response time
- recent state transitions
- alert history

The UI should eventually expose a concise health dashboard while preserving detailed history for troubleshooting.

## Example Recovery Scenario

```text
10:00  API check succeeds       HEALTHY
10:05  API check times out      DEGRADED
10:10  API check times out      DOWN -> ALERT
10:15  API check times out      DOWN (no duplicate alert)
10:20  API responds             RECOVERED -> ALERT
10:25  API responds             HEALTHY
```

## Non-Goals

Monitoring is not responsible for:

- changing quote prices because a vendor is unavailable
- silently substituting vendors
- modifying pricing rules
- storing credentials
- acting as a full observability platform
- replacing application logs or infrastructure monitoring

Vendor availability may eventually participate in an explicitly configured business rule, but that must be an intentional rule and never an implicit side effect of monitoring.

## Architectural Relationship

Raven evolves from a quote engine into a configurable business automation system:

```text
Configuration
     |
     +--> Pricing
     +--> Vendors
     +--> Integrations
     +--> Monitoring
     +--> Notifications
     +--> Jobs
     |
     v
Automation
```

Monitoring is therefore part of Raven's reusable infrastructure rather than a feature attached only to a particular vendor or API.
