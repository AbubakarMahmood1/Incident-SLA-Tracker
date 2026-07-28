# RFC-0002: Multi-Tenant Authorization

- **Status:** Draft
- **Created:** 2026-07-27
- **Target version:** Unscheduled

## Summary

Introduce tenant isolation, team membership, and policy-aware roles without weakening current actor-scoped idempotency or leaking incident data through queries, receipts, events, or outbox payloads.

## Motivation

The current model is suitable for one controlled deployment. Adding a `tenant_id` column to a few tables would not be sufficient: every unique key, foreign key, query, admin capability, worker batch, and notification path must become tenant-safe.

## Proposed direction

- Make tenant identity part of users, incidents, policies, events, receipts, and outbox rows.
- Replace global administrators with tenant-scoped roles; reserve platform administration for operator-only paths.
- Scope idempotency uniqueness by tenant and actor.
- Consider PostgreSQL row-level security as defence in depth, not as a substitute for service authorization.
- Add cross-tenant negative tests for every endpoint and worker query.

## Risks

- Accidental global queries
- Cross-tenant identifier inference
- Shared email addresses or usernames
- Worker batches that lock or publish the wrong tenant's rows
- Migration of existing unscoped records

## Acceptance criteria

No implementation begins until the data model, migration, authorization matrix, RLS decision, negative-test matrix, and operational tenant lifecycle are approved.
