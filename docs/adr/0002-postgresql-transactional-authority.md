# ADR-0002: Use PostgreSQL as transactional and time authority

- **Status:** Accepted
- **Date:** 2026-07-27
- **Decision owners:** Repository maintainer

## Context

The system must coordinate API commands, competing evaluators, idempotency receipts, event rows, and notification publication. A separate Redis/Celery control plane increased operational surface without owning a unique guarantee. Independent application clocks could also disagree around deadlines.

## Decision

Use PostgreSQL for aggregate row locks, `SKIP LOCKED` batches, command-receipt conflicts, event and outbox transactions, and the effective clock for normal execution. Run evaluator and delivery loops as ordinary processes against the same database.

## Consequences

### Positive

- State and coordination share one commit boundary.
- Multi-node deadline decisions use one clock authority.
- The local topology is smaller and easier to prove.

### Negative and limitations

- PostgreSQL availability and lock behavior become central dependencies.
- Very high scheduling throughput may eventually justify a separate broker, but version 1 does not claim that scale.

## Alternatives considered

- Celery plus Redis: rejected for version 1 because it added moving parts without eliminating the need for PostgreSQL transactions.
- Application system clocks: rejected for normal execution because node skew can alter deadline decisions.

## Verification

Service transactions, `clock_timestamp()` queries, PostgreSQL integration tests, and Compose without Redis.
