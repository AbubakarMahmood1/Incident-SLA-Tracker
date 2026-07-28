# Operations Runbook

## Operational status

This runbook describes intended operation of the supplied source and Compose topology. It is not evidence that the system has been operated under production load. Every environment must supply its own TLS, secret management, backups, monitoring, and incident response.

## Process roles

- **Migration process:** applies Alembic revisions and exits.
- **API process:** serves commands, queries, liveness, and readiness.
- **Worker process:** alternates bounded SLA evaluation and outbox delivery cycles.
- **PostgreSQL:** owns state, locks, clock, constraints, history, receipts, and outbox.

Run migrations as a controlled deployment step before starting a new application revision. The API never calls `create_all()`.

## Startup sequence

1. Provision PostgreSQL and a least-privileged application/migration identity.
2. Load validated environment variables and secrets.
3. Back up the database before a destructive or irreversible migration.
4. Run `alembic upgrade head`.
5. Start API and worker processes.
6. Verify `/health/live` and `/health/ready`.
7. Run a synthetic create/replay/read smoke test.
8. Inspect worker logs and outbox state.

## Health interpretation

- Liveness confirms the API process can answer a trivial request.
- Readiness confirms a database connection and `SELECT 1` at that moment.
- Neither endpoint proves evaluator freshness, outbox delivery, SMTP acceptance, or business correctness.

A production deployment should add external checks for worker heartbeat/freshness and dead outbox growth rather than treating API readiness as whole-system health.

## Worker operation

One cycle evaluates a bounded number of overdue incident/SLA rows and then delivers a bounded number of outbox rows. Multiple workers may run because both paths use row locks and `SKIP LOCKED`.

Useful one-shot commands:

```bash
incident-sla-worker evaluate-once
incident-sla-worker deliver-once
```

The default loop logs cycle summaries and continues after a failed cycle. Repeated failures require operator action; an infinite retry loop is not a recovery plan.

## Inspecting outbox state

```sql
SELECT status, count(*)
FROM outbox_messages
GROUP BY status
ORDER BY status;

SELECT id, deduplication_key, topic, attempts, available_at,
       claimed_at, sent_at, left(coalesce(last_error, ''), 500) AS last_error
FROM outbox_messages
WHERE status IN ('processing', 'dead')
ORDER BY available_at, id;
```

Interpretation:

- `pending`: eligible at or after `available_at`.
- `processing`: leased; do not manually reset before the configured lease expires unless the worker is known dead.
- `sent`: the transport call returned successfully; this is not proof the recipient consumed it.
- `dead`: exhausted or ambiguous final attempt requiring review.

## Dead-message recovery

1. Determine whether the provider may already have accepted the message.
2. Search provider logs using the deduplication key when supported.
3. Correct credentials, transport, or payload issues.
4. Decide explicitly whether redelivery risk is acceptable.
5. In one audited transaction, reset only selected rows to `pending`, clear `claimed_at`, and choose an `available_at`.
6. Preserve or externally record the previous error and operator decision.

Do not bulk reset all dead rows without understanding duplicate risk.

## Ambiguous delivery

A worker can crash after external acceptance but before `sent` is committed. On lease expiry, redelivery may occur. Operators should treat the deduplication key as the correlation identifier and never infer exactly-once behavior from one database row.

## SLA evaluator delay

A delayed evaluator records:

- breach column and `effective_at`: contractual deadline;
- event `occurred_at` and payload `detected_at`: observation time.

Investigate worker delay separately. Do not edit breach timestamps to hide it.

## Policy changes

Environment policy changes apply only to newly created incidents. Existing snapshots and priority are immutable in version 1.

If a policy was configured incorrectly:

- do not update active deadlines directly;
- document the affected incidents;
- use a future compensating rebase design from RFC-0001; or
- restore/correct in a controlled maintenance procedure with explicit provenance if this is still a pre-release dataset.

## Migration procedure

Before upgrade:

```bash
alembic current
alembic history --verbose
```

Generate and review offline SQL when useful:

```bash
alembic upgrade head --sql > migration.sql
```

Apply:

```bash
alembic upgrade head
```

The verification gate also tests `downgrade base` followed by re-upgrade on a disposable database. That does not mean downgrading a populated production database is always safe. Review each revision and backup first.

## Backup and restore

`scripts/compose-smoke.sh` performs a disposable local rehearsal that:

- logical backup creation;
- restore into an isolated database;
- Alembic revision consistency;
- event sequence and trigger presence;
- aggregate/SLA consistency queries;
- outbox state counts; and
- restored incident lookup; and
- restored append-only trigger rejection.

Backups contain usernames, email addresses, incident content, and notification payloads. Protect and expire them accordingly.

## Consistency probes

```sql
-- Every incident has exactly one SLA snapshot.
SELECT i.id
FROM incidents i
LEFT JOIN slas s ON s.incident_id = i.id
WHERE s.id IS NULL;

-- Mirrored progress timestamps agree.
SELECT i.id
FROM incidents i
JOIN slas s ON s.incident_id = i.id
WHERE i.acknowledged_at IS DISTINCT FROM s.acknowledged_at
   OR i.resolved_at IS DISTINCT FROM s.resolved_at;

-- Breach evidence uses contractual deadlines.
SELECT incident_id
FROM slas
WHERE (response_breached_at IS NOT NULL
       AND response_breached_at <> response_deadline)
   OR (resolution_breached_at IS NOT NULL
       AND resolution_breached_at <> resolution_deadline);
```

All should return no rows.

## Clock discipline

Normal decisions query PostgreSQL `clock_timestamp()` inside transactions. Keep the database host synchronized and monitor drift. Injected fixed clocks exist only in tests and must not be wired into a deployed process.

## Logging and personal data

JSON logs may contain incident and event identifiers, error classes, and correlation keys. The console transport intentionally omits recipient and full notification payload. Durable outbox diagnostics retain only an error class and, for SMTP response failures, a sanitized response code; raw provider exception text is not stored. Other application failures can still expose operational context, so define retention and access before using real data.

## Rollback boundary

Application rollback is safe only when the previous code understands the current schema. Database downgrade may delete all version-1 tables because the initial revision has no predecessor. On any populated environment, prefer restoring a verified backup or forward-fixing unless a reviewed rollback plan says otherwise.
