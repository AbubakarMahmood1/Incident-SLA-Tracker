# Software Requirements Specification

## 1. Purpose

This SRS defines the bounded version-1 behavior of Incident SLA Ledger. Its structure uses stable requirement identifiers, explicit interfaces, verification mappings, and change control. It is informed by common requirements-engineering practice, including ISO/IEC/IEEE 29148 terminology, but it does not reproduce the standard or claim audited conformance.

## 2. Scope

The system records incidents, snapshots response and resolution objectives, accepts a one-way set of lifecycle commands, evaluates overdue objectives, appends transition evidence, and publishes breach notifications through a durable outbox. PostgreSQL is the transactional authority.

### 2.1 Actors

- **Reporter:** creates an incident, reads it, and may close it after resolution.
- **Assignee:** reads an assigned incident and may acknowledge or resolve it.
- **Administrator:** may read all incidents, assign them, and perform lifecycle commands.
- **Evaluator worker:** detects response and resolution breaches.
- **Delivery worker:** leases and delivers outbox envelopes.
- **Repository owner/operator:** provisions users, applies migrations, configures secrets, and operates recovery.

### 2.2 Exclusions

Version 1 excludes public registration, password reset, refresh tokens, comments, attachments, service catalogs, teams, reopen, priority changes, SLA pauses, business calendars, multi-tenancy, a browser UI, native TLS termination, exactly-once external delivery, and a bundled observability platform.

## 3. Definitions

- **Response objective:** time from incident start until acknowledgement.
- **Resolution objective:** time from incident start until resolution.
- **Contractual deadline:** immutable timestamp derived from the policy snapshot.
- **Detection time:** when a command or worker observed that a deadline had passed.
- **Command receipt:** actor-scoped durable idempotency record.
- **Event ledger:** ordered append-only record of accepted transitions.
- **Outbox:** database rows representing external notifications to be delivered at least once.

## 4. Assumptions and constraints

- PostgreSQL features such as JSONB, constraint triggers, row locks, and `SKIP LOCKED` are part of the design.
- Host clocks should be synchronized, but normal deadline decisions use PostgreSQL time to avoid application-node skew.
- Operators control user provisioning and database credentials.
- SMTP behavior and provider deduplication are outside the local transaction boundary.
- The event ledger is append-only under ordinary database roles; it is not a cryptographic transparency log.

## 5. Functional requirements

### FR-001

The process shall load configuration from environment variables and reject database URLs that do not use the PostgreSQL psycopg dialect.

### FR-002

Production mode shall reject placeholder or shorter-than-32-character JWT secrets.

### FR-003

Configured CORS entries shall be unique exact HTTP or HTTPS origins without wildcards, credentials, paths, queries, or fragments.

### FR-004

The API shall expose a liveness endpoint that does not require database access.

### FR-005

The API shall expose a readiness endpoint that succeeds only when a PostgreSQL probe succeeds.

### FR-006

An owner-operated CLI shall create normalized local users and reject duplicate username or email identities.

### FR-007

The token endpoint shall issue a bearer token only for an active user with a valid password.

### FR-008

Authentication failures shall use a generic response that does not distinguish unknown users from invalid passwords.

### FR-009

Protected endpoints shall reject tokens with invalid signature, issuer, audience, subject, lifetime, or required claims.

### FR-010

A non-administrator shall see an incident only when they are its reporter or current assignee. Principal summaries shall expose only identifier, username, and display name rather than email or administrator status.

### FR-011

Incident command payloads shall reject unknown fields and normalize, bound, and validate text and identifiers.

### FR-012

Creating an incident shall bind the authenticated actor as its reporter.

### FR-013

Creating an incident shall snapshot the configured response and resolution targets and derive immutable deadlines.

### FR-014

Normal command execution shall obtain its effective timestamp from PostgreSQL inside the command transaction.

### FR-015

Creating an incident shall append an incident.created event in the same transaction.

### FR-016

Every mutating incident endpoint shall require a syntactically bounded Idempotency-Key.

### FR-017

A command receipt shall scope an idempotency key to the authenticated actor.

### FR-018

Reusing a key for a different command type or canonical payload shall return an idempotency conflict.

### FR-019

Reusing a completed key for the same actor, command, and payload shall return the original incident result without repeating the transition.

### FR-020

Only an administrator shall assign an open or acknowledged incident, and the assignee shall be an active user.

### FR-021

A successful assignment shall append an event containing the previous and new assignee identifiers.

### FR-022

Lifecycle changes shall occur only through explicit acknowledge, resolve, and close commands rather than a generic status update.

### FR-023

Only the current assignee or an administrator shall acknowledge an incident.

### FR-024

An acknowledgement at or before the response deadline shall meet the response objective.

### FR-025

An acknowledgement after the response deadline shall preserve a response breach at the contractual deadline before recording acknowledgement.

### FR-026

Only the current assignee or an administrator shall resolve an incident.

### FR-027

Resolving an open incident shall atomically record an explicit implicit-acknowledgement event before the resolution event.

### FR-028

A resolution at or before the resolution deadline shall meet that objective; a later resolution shall preserve a breach at the deadline.

### FR-029

Only a reporter or administrator shall close an incident, and only a resolved incident may be closed.

### FR-030

Response and resolution objective state shall be stored and evaluated independently.

### FR-031

A persisted breach timestamp shall equal the relevant contractual deadline.

### FR-032

A breach event shall separately record when the worker or command detected the overdue objective.

### FR-033

The evaluator shall select due aggregates with PostgreSQL row locks and SKIP LOCKED batch coordination.

### FR-034

Competing evaluators shall produce at most one event and one outbox record per incident objective.

### FR-035

PostgreSQL shall reject updates and deletes of incident-event ledger rows.

### FR-036

PostgreSQL shall reject changes to an incident's SLA policy snapshot and derived deadlines.

### FR-037

PostgreSQL shall reject incident-priority changes in version 1.

### FR-038

Deferred database checks shall reject missing SLA snapshots or disagreement between incident and SLA progress timestamps.

### FR-039

The timeline endpoint shall return events in ascending global sequence order.

### FR-040

Incident listing shall apply actor visibility, bounded pagination, stable ordering, and optional status and priority filters.

### FR-041

Text search shall treat percent, underscore, and escape characters as literal input rather than wildcard syntax.

### FR-042

Every new breach event shall be committed even when no active assignee exists. When an active assignee supplies a valid recipient, the corresponding notification outbox row shall be committed in the same transaction; version 1 shall not invent a fallback recipient.

### FR-043

Each breach outbox record shall carry a stable per-incident, per-objective deduplication key.

### FR-044

Outbox workers shall claim eligible rows in bounded SKIP LOCKED batches using expiring leases.

### FR-045

A stale delivery attempt shall not mark a newer reclaimed attempt sent or failed.

### FR-046

Failed delivery shall use bounded exponential delay and eventually enter a terminal dead state.

### FR-047

The console transport shall avoid logging recipient addresses, titles, or full payloads by default.

### FR-048

The SMTP transport shall place the stable deduplication key in the outgoing message and shall not be described as exactly once.

## 6. Non-functional requirements

### NFR-001

The supported source baseline shall be Python 3.12 and 3.13.

### NFR-002

Authoritative persistence tests shall use PostgreSQL and shall never fall back to SQLite or an in-memory ORM substitute.

### NFR-003

Each accepted command shall commit aggregate state, receipt result, and events atomically.

### NFR-004

All domain, command, event, deadline, lease, and delivery timestamps shall be timezone-aware.

### NFR-005

Normal multi-process execution shall use PostgreSQL as the shared time authority; injected clocks are test-only evidence fixtures.

### NFR-006

Pure lifecycle and deadline functions shall be deterministic and independent of I/O.

### NFR-007

The dependency-available core test selection shall maintain at least 90 percent branch-aware coverage.

### NFR-008

PostgreSQL tests shall require explicit opt-in and shall fail, rather than silently substitute, when their database is unavailable.

### NFR-009

The authoritative database gate shall verify upgrade, downgrade to base, re-upgrade, and repeated integration execution.

### NFR-010

The runtime image shall execute as a non-root user with a read-only filesystem, temporary writable storage, dropped capabilities, and no-new-privileges in Compose.

### NFR-011

PostgreSQL shall remain on an internal Compose network; only the API port and an explicit worker egress path shall be exposed.

### NFR-012

Source-ready deliverables shall exclude secrets, local environment files, caches, bytecode, databases, and generated test output.

### NFR-013

Passwords shall be stored with Argon2 and bounded before hashing.

### NFR-014

JWTs shall bind subject, issuer, audience, issued-at, not-before, expiry, and unique token identifier claims.

### NFR-015

Application logs shall be structured JSON and shall avoid default breach-notification payload disclosure.

### NFR-016

Public request fields, pagination, search, identifiers, error text, and retained delivery errors shall have explicit bounds.

### NFR-017

Readiness shall fail closed when PostgreSQL is unreachable while liveness remains independent.

### NFR-018

A public release shall include an owner-reviewed dependency lock and successful dependency consistency check.

### NFR-019

Every accepted requirement shall have a stable identifier and a code, test, or evidence mapping.

### NFR-020

Public documentation shall distinguish implemented source, observed evidence, pending gates, non-goals, and future RFCs.

### NFR-021

Schema changes shall be represented by Alembic migrations rather than application-startup create_all behavior.

### NFR-022

Concurrency evidence shall cover competing SLA evaluators and stale outbox lease completion.

### NFR-023

Operations documentation shall include dead-message inspection, migration rollback boundaries, backups, and ambiguous-delivery recovery.

### NFR-024

Integration tests shall use disposable data and shall not call real external notification providers.

## 7. External interfaces

The HTTP interface is defined in [contracts/API.md](contracts/API.md). The relational and event contracts are defined in [contracts/DATA.md](contracts/DATA.md). Configuration keys are exemplified in [../.env.example](../.env.example).

## 8. Acceptance

A requirement is not considered closed merely because code exists. Closure requires the corresponding evidence in [TRACEABILITY.md](TRACEABILITY.md) and [CLAIMS-AND-EVIDENCE.md](CLAIMS-AND-EVIDENCE.md). PostgreSQL-specific requirements require the real integration gate rather than a source-only substitute.

## 9. Change control

- Clarifications that preserve behavior may update this SRS directly.
- Architecturally significant accepted choices require an ADR.
- Proposed scope or contract changes require an RFC before implementation.
- Superseded requirement IDs are retained and marked rather than silently reused.
