# Architecture Decision Records

Accepted ADRs are retained as the historical explanation for architecturally significant choices. A superseded record is not deleted; a later ADR links to it and changes its status.

| ADR | Status | Decision |
|---|---|---|
| [0001](0001-bounded-sla-ledger.md) | Accepted | Build a bounded SLA ledger, not a general ITSM suite |
| [0002](0002-postgresql-transactional-authority.md) | Accepted | Use PostgreSQL as transactional and time authority |
| [0003](0003-immutable-policy-snapshots.md) | Accepted | Snapshot SLA policy per incident |
| [0004](0004-independent-objectives.md) | Accepted | Persist response and resolution outcomes independently |
| [0005](0005-append-only-event-ledger.md) | Accepted | Append accepted transitions to a protected event ledger |
| [0006](0006-actor-scoped-idempotency.md) | Accepted | Bind mutation retries to actor, command, and payload |
| [0007](0007-transactional-outbox-at-least-once.md) | Accepted | Publish through a transactional outbox with at-least-once delivery |
| [0008](0008-explicit-one-way-lifecycle.md) | Accepted | Use explicit one-way commands instead of generic status updates |
| [0009](0009-documentation-governance.md) | Accepted | Use SRS, C4, ADR, and RFC proportionally; omit KEP machinery |

Use [the template](TEMPLATE.md) for new records.
