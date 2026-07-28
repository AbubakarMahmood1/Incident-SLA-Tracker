# ADR-0008: Use explicit one-way commands instead of generic status updates

- **Status:** Accepted
- **Date:** 2026-07-27
- **Decision owners:** Repository maintainer

## Context

A generic status endpoint permits invalid jumps, makes authorization unclear, and cannot reliably determine which events, timestamps, or SLA consequences accompany a change.

## Decision

Expose create, assign, acknowledge, resolve, and close commands. Assignment is permitted only while an incident is open or acknowledged. Version 1 permits `open -> acknowledged -> resolved -> closed`, plus `open -> resolved` with an explicit implicit-acknowledgement event. Reopen and arbitrary status edits are excluded.

## Consequences

### Positive

- Every transition has one authorization and invariant path.
- Events and timestamps are not inferred from arbitrary patch payloads.

### Negative and limitations

- Corrections and reopen require a future, explicit design.
- The workflow is deliberately less flexible than a general ticket system.

## Alternatives considered

- PATCH status: rejected because it hides domain semantics.
- Full configurable state machine: rejected as unnecessary complexity for version 1.

## Verification

Domain functions, route surface, lifecycle database check, and workflow tests.
