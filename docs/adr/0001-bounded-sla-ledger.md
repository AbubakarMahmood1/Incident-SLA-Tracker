# ADR-0001: Build a bounded SLA ledger, not a general ITSM suite

- **Status:** Accepted
- **Date:** 2026-07-27
- **Decision owners:** Repository maintainer

## Context

The original repository described full CRUD, comments, attachments, broad user management, distributed tasks, email warnings, dashboards, metrics, traces, and E2E coverage. Several of those features did not exist or did not strengthen the central engineering proof. Preserving all of them would make completion broad and claims difficult to verify.

## Decision

Version 1 focuses on incident creation and assignment, acknowledgement, resolution, closure, independent response/resolution objectives, idempotency receipts, an event ledger, and a notification outbox. Comments, attachments, public user management, service catalogs, dashboards, and generic status mutation are excluded.

## Consequences

### Positive

- The project has one reviewable thesis and a bounded completion path.
- Documentation can state non-goals without pretending the repository is a complete ITSM product.

### Negative and limitations

- It is intentionally less feature-complete than commercial or open-source incident platforms.
- Future additions require an RFC showing how they strengthen rather than dilute the proof.

## Alternatives considered

- Retain the original broad feature set: rejected because much of it was unsupported and costly to validate.
- Archive immediately: rejected because the concurrency, deadline, idempotency, and outbox problem has strong backend portfolio value.

## Verification

README scope, API surface, deleted modules, SRS exclusions, and the final evidence matrix.
