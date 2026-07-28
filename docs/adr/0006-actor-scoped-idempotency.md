# ADR-0006: Bind mutation retries to actor, command, and payload

- **Status:** Accepted
- **Date:** 2026-07-27
- **Decision owners:** Repository maintainer

## Context

Clients can lose responses and repeat requests. A key without actor or payload binding can replay a different command, leak another principal's result, or silently accept conflicting input.

## Decision

Require a bounded ASCII `Idempotency-Key` for every mutation. Store a receipt uniquely keyed by actor and key, plus command type, canonical payload hash, incident result, and event sequence. Same input returns the original result; different input conflicts.

## Consequences

### Positive

- Ambiguous HTTP retries do not repeat accepted transitions.
- Keys cannot collide across actors or be repurposed silently.

### Negative and limitations

- Receipts grow over time and need a future retention policy.
- Idempotency covers API commands, not arbitrary database writes or external providers.

## Alternatives considered

- No idempotency: rejected because retry ambiguity is central to the project.
- Global key uniqueness: rejected because actors should not reserve one another's keys.

## Verification

Receipt model and constraint, canonical hash utility, command service, API dependency, and PostgreSQL workflow tests.
