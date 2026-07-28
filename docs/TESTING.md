# Testing and Evidence Strategy

## Principle

A test asset is not evidence until it executes against the dependency whose semantics matter. Pure Python tests establish domain and validation behavior. They do not establish PostgreSQL locks, deferred triggers, migrations, image execution, SMTP behavior, or GitHub Actions status.

## Test layers

### 1. Pure domain and validation

Runs without PostgreSQL:

- deadline boundary and outcome transitions;
- independent response/resolution breaches;
- implicit acknowledgement on direct resolution;
- timezone and invariant rejection;
- policy validation;
- idempotency-key grammar and canonical hashing;
- Argon2 and JWT behavior;
- settings fail-closed rules;
- Unicode and strict request schemas; and
- ASGI liveness and readiness-failure behavior.

Command:

```bash
python -m pytest tests/unit
```

The source verification script applies a branch-aware coverage gate only to the dependency-available core modules. It does not inflate the number by pretending database services were exercised.

### 2. PostgreSQL integration

Requires an explicitly supplied disposable database and `RUN_POSTGRES_TESTS=1`. There is no SQLite fallback.

Coverage includes:

- migration-installed constraints and triggers;
- create/replay/conflicting idempotency behavior;
- authorization and one-way lifecycle;
- event ordering;
- late command producing two independent breaches;
- event and policy immutability;
- incident/SLA cross-table consistency;
- competing evaluator workers;
- command/evaluator races at both objective boundaries;
- concurrent same-key commit and rollback recovery;
- database-backed API authentication and authorization;
- unique outbox publication;
- stale lease completion;
- cancellation after transport send and before database mark;
- provider failure retry-to-dead with bounded diagnostics; and
- terminal handling of an exhausted ambiguous lease.

Command:

```bash
export TEST_DATABASE_URL='postgresql+psycopg://.../disposable_database'
RUN_POSTGRES_TESTS=1 python -m pytest -m postgres -v
```

### 3. Migration cycle

`./scripts/verify.sh` performs:

1. source checks;
2. upgrade to head;
3. PostgreSQL tests;
4. downgrade to base;
5. re-upgrade to head; and
6. PostgreSQL tests again.

This is disposable-schema evidence, not a claim that downgrading real populated data is harmless.

### 4. Container and Compose smoke

`./scripts/compose-smoke.sh` builds the image, applies migrations, starts API and worker, provisions a synthetic administrator, authenticates, creates an incident twice with one idempotency key, checks the stable result, restarts database and application processes, and rehearses a logical backup into an isolated restored database.

The smoke gate inspects:

- non-root UID;
- read-only filesystem;
- dropped capabilities and no-new-privileges;
- PostgreSQL internal network placement;
- healthy restart behavior;
- backup count and Alembic revision parity;
- restored aggregate readability and event-trigger enforcement; and
- no committed secrets.

### 5. CI evidence

The workflow defines Python 3.12/3.13 source jobs, PostgreSQL migration/concurrency evidence, and container smoke. The workflow is not considered passing until observed on the final commit.

## Required failure scenarios before DONE

- Command rollback leaves no partial aggregate, event, or receipt result.
- Two identical requests racing on one actor/key converge on one result.
- The first claimant rolling back does not permanently poison the key.
- Two evaluator workers produce one event and, for an active assignee, one outbox row per objective.
- An unassigned overdue incident records breach evidence without fabricating an outbox recipient.
- A command racing an evaluator produces the same final breach outcomes.
- A stale outbox worker cannot overwrite a later attempt.
- Provider failure retries, reaches dead state, and retains bounded diagnostics.
- An ambiguous final lease is visible to operators.
- Direct event mutation, policy edit, priority edit, progress drift, and SLA deletion fail in PostgreSQL.
- Migration downgrade/re-upgrade is reproducible on a disposable database.

All listed repository-owned scenarios are exercised by the unit, PostgreSQL, migration, SMTP, or Compose gates. Production-provider acceptance, deployment proxy policy, load behavior, and final exact-commit CI remain separate evidence classes.

## Security checks

The local candidate gate includes:

- dependency vulnerability scan;
- container vulnerability scan;
- licence-policy review;
- secret-pattern scan;
- malformed and expired JWT tests;
- authorization negative matrix;
- CORS and input-bound tests;
- SMTP submission and STARTTLS-refusal behavior against a controlled test server; and
- log review for recipient, title, token, password, and payload leakage.

## Performance evidence

No throughput or latency claim is currently made. A future benchmark must publish hardware, software versions, dataset, connection pool, incident distribution, worker count, warm-up, repetitions, percentiles, database settings, and raw results. A single local requests-per-second number is not accepted as portfolio evidence.

## Diagram and documentation checks

- Render every Mermaid block and inspect labels and edges.
- Resolve every repository-local Markdown link.
- Ensure every SRS ID occurs exactly once in SRS and traceability.
- Ensure ADR/RFC indexes cover every record.
- Reject claims that have no evidence state.
