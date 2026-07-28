# ADR-0003: Snapshot SLA policy per incident

- **Status:** Accepted
- **Date:** 2026-07-27
- **Decision owners:** Repository maintainer

## Context

If a configuration change retroactively changes active deadlines, historical decisions become difficult to explain and retries may observe a different contract from the one that existed at creation.

## Decision

At incident creation, persist target seconds, start time, and derived deadlines. Database triggers reject later changes to the policy snapshot and version-1 priority.

## Consequences

### Positive

- Each incident remains explainable under the policy it started with.
- Configuration changes affect new incidents only.

### Negative and limitations

- Correcting an erroneous active policy requires an explicit future rebase design rather than an in-place edit.

## Alternatives considered

- Resolve policy dynamically on every evaluation: rejected because history and retries would drift.
- Permit arbitrary administrator edits: deferred to an RFC with compensating events and authorization.

## Verification

SLA model, initial migration triggers, creation service, and immutability integration tests.
