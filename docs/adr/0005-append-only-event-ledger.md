# ADR-0005: Append accepted transitions to a protected event ledger

- **Status:** Accepted
- **Date:** 2026-07-27
- **Decision owners:** Repository maintainer

## Context

Mutable aggregate rows show current state but do not explain who changed it, when a contractual breach became effective, or how an implicit acknowledgement occurred.

## Decision

Append one or more ordered events in the same command or breach transaction. PostgreSQL rejects event updates and deletes through a trigger. Events distinguish `occurred_at` from `effective_at`.

## Consequences

### Positive

- Timeline queries can reconstruct accepted transitions.
- Delayed breach observation does not rewrite the contractual effective time.

### Negative and limitations

- The ledger is not cryptographically tamper-evident and a database superuser can alter schema or disable triggers.
- Payload evolution needs contract discipline.

## Alternatives considered

- Rely on application logs: rejected because they are outside the aggregate transaction.
- Full event sourcing: rejected because aggregate rows remain the authoritative read model and replay is not required.

## Verification

Event model, append-only trigger, event response contract, timeline endpoint, and mutation tests.
