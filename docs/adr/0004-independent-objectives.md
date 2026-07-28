# ADR-0004: Persist response and resolution outcomes independently

- **Status:** Accepted
- **Date:** 2026-07-27
- **Decision owners:** Repository maintainer

## Context

A single SLA status and one notification timestamp cannot correctly represent two objectives. Recording a response breach could suppress a later resolution breach, while a delayed evaluator could misidentify which target failed.

## Decision

Persist acknowledgement, resolution, response-breach, and resolution-breach evidence separately. A breach timestamp is the objective deadline; detection time is recorded on the event payload and event occurrence.

## Consequences

### Positive

- Each objective has a stable, explainable outcome.
- Both objectives can breach in one delayed evaluation without overwriting one another.

### Negative and limitations

- The data model contains more explicit fields and invariants.
- Version 1 supports exactly two fixed objectives rather than arbitrary policy stages.

## Alternatives considered

- One composite status: rejected because it loses information.
- Generic objective table: deferred because two explicit objectives are easier to review and sufficient for the bounded thesis.

## Verification

Pure domain tests, SLA columns and checks, evaluator service, and competing-worker tests.
