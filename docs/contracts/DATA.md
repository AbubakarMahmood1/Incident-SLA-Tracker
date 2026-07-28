# Data and Event Contract

## PostgreSQL is part of the contract

The schema intentionally uses PostgreSQL UUID, JSONB, identity columns, PL/pgSQL triggers, transactional DDL, row locks, and `SKIP LOCKED`. SQLite and in-memory ORM behavior are not accepted substitutes for persistence evidence.

## Tables

### `users`

Owner-provisioned principals with normalized unique username and email, Argon2 password hash, active flag, and administrator flag. Version 1 has no public user-lifecycle API.

### `incidents`

The current aggregate read model:

- immutable version-1 priority;
- one-way status;
- reporter and optional assignee;
- acknowledgement, resolution, and closure timestamps; and
- monotonically increasing revision.

A check constraint binds allowed status/timestamp combinations.

### `slas`

One row per incident containing:

- immutable target seconds;
- immutable start and derived deadlines;
- progress timestamps mirrored from the incident aggregate;
- response-breach deadline, if breached; and
- resolution-breach deadline, if breached.

The duplicated progress timestamps are deliberate local denormalization for evaluator queries. Deferred constraint triggers reject disagreement with the incident row and reject an incident without its SLA snapshot.

A breach timestamp must equal its contractual deadline. Detection latency belongs in the event, not in the breach column.

### `incident_events`

Globally ordered accepted-transition history:

- identity `sequence` primary key;
- stable UUID `event_id`;
- incident and optional actor;
- enumerated event type;
- `occurred_at` observation time;
- `effective_at` contractual time;
- bounded source label; and
- JSONB payload.

`effective_at <= occurred_at` is enforced. A trigger rejects updates and deletes. This is an append-only application ledger, not a cryptographic transparency log.

Event types:

```text
incident.created
incident.assigned
incident.acknowledged
incident.resolved
incident.closed
sla.response_breached
sla.resolution_breached
```

### `command_receipts`

Durable mutation idempotency:

- actor UUID;
- bounded client key;
- command type;
- SHA-256 of canonical command and payload;
- resulting incident UUID; and
- resulting event sequence.

Unique key: `(actor_id, idempotency_key)`.

Receipts currently have no automated retention policy. Deleting them carelessly weakens retry behavior and is an open operational decision.

### `outbox_messages`

Publication intent tied to one event:

- unique stable deduplication key;
- topic, recipient, and JSONB payload;
- state: `pending`, `processing`, `sent`, or `dead`;
- attempt number;
- availability, lease, and sent timestamps; and
- bounded retained error text.

State/timestamp consistency is enforced by a check constraint. A stale worker may complete only the attempt number it claimed.

## Lifecycle contract

```text
open -> acknowledged -> resolved -> closed
   \-----------------> resolved
```

The direct open-to-resolved path creates both an implicit acknowledgement event and a resolution event. Reopen and correction are not represented in version 1.

## Objective contract

For each objective:

- action at or before deadline: `met`;
- no action and authoritative time at or before deadline: `pending`;
- no action and authoritative time after deadline: `breached`;
- action after a persisted breach: remains `breached`.

Response and resolution are evaluated independently.

## Transaction boundaries

### Incident command

One transaction contains the actor-scoped receipt claim, aggregate lock, due-breach evaluation when applicable, state mutation, event append, and receipt result.

### Evaluator batch

One bounded transaction locks due incident/SLA rows with `SKIP LOCKED`, persists objective breach evidence, appends events, and inserts unique outbox rows only when an active assignee supplies the recipient. An unassigned breach remains durable evidence and does not create a fabricated fallback notification.

### Delivery

Claiming rows is a short database transaction. Network delivery happens outside it. Marking sent or failed is another attempt-scoped transaction. This is why the transport is at least once.

## Deletion and retention

Version 1 exposes no incident-deletion endpoint. Event triggers and receipt references make casual deletion intentionally difficult. A legally compliant retention/anonymization design would require an RFC because it must reconcile personal data with audit history.
