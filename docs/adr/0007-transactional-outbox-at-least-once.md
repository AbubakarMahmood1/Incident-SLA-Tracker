# ADR-0007: Publish through a transactional outbox with at-least-once delivery

- **Status:** Accepted
- **Date:** 2026-07-27
- **Decision owners:** Repository maintainer

## Context

Sending email inside the breach transaction couples database locks to network latency and can leave either committed state without a message or a message without committed state. External providers cannot participate in the local transaction.

## Decision

Commit breach event and unique outbox row together. Delivery workers claim bounded rows with expiring leases and `SKIP LOCKED`, increment an attempt number, and update only the matching attempt. Expose a stable deduplication key and describe delivery as at least once.

## Consequences

### Positive

- Database state and publication intent cannot diverge on ordinary rollback.
- Workers can compete without intentionally double-claiming rows.
- Stale workers cannot overwrite newer lease state.

### Negative and limitations

- A crash after provider acceptance but before `sent` can create duplicates.
- An exhausted ambiguous final lease becomes dead and requires operator review.

## Alternatives considered

- Exactly-once claim: rejected because no provider-side atomic acknowledgement exists.
- Send synchronously in the API/evaluator transaction: rejected because network effects are not transactional.

## Verification

Outbox schema, evaluator insert, lease service, stale-attempt tests, operations runbook, and RFC-0003.
