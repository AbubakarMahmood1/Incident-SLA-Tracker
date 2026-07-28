# Incident SLA Ledger

**Deterministic incident acknowledgement, resolution, breach, and notification evidence backed by PostgreSQL.**

> Portfolio status: **locally verified release candidate; operation under production load is not claimed.**

Incident SLA Ledger is a deliberately bounded backend systems project. It is not a miniature IT service-management suite. Its purpose is to make a small set of incident transitions explainable under retries, delayed workers, and competing processes:

- snapshot a response and resolution policy when an incident is created;
- require explicit, one-way lifecycle commands;
- distinguish response and resolution objectives rather than compressing them into one status;
- use the contractual deadline as the effective breach instant and record detection latency separately;
- bind mutating retries to an actor-scoped idempotency key and canonical payload hash;
- append every accepted state transition to an event ledger; and
- publish breach notifications for active assignees through a durable PostgreSQL outbox with **at-least-once** delivery semantics.

The repository intentionally does **not** claim production readiness, exactly-once notification delivery, cryptographic tamper evidence, a complete ITSM feature set, or operation under production load.

## Why this project exists

The interesting problem is not CRUD. It is preserving one coherent answer when any of the following happens:

- two evaluator workers inspect the same overdue incident;
- a client retries a command after losing the HTTP response;
- a command arrives after one or both objectives have already expired;
- a delivery worker sends a notification and crashes before acknowledging it;
- an old worker finishes after another worker has reclaimed its lease; or
- a policy changes after an incident has already started.

The design keeps PostgreSQL as the transactional authority for aggregate locks, idempotency receipts, immutable policy snapshots, event history, breach decisions, and outbox publication. Redis and Celery are not required for this bounded proof.

## Current bounded scope

### Implemented in source

- Authenticated reporters, assignees, and administrators
- Owner-operated CLI user creation; no public registration flow
- Incident create, assign, acknowledge, resolve, close, list, detail, and timeline endpoints
- Explicit lifecycle: `open -> acknowledged -> resolved -> closed`
- Direct `open -> resolved` transition with an explicit implicit-acknowledgement event
- Immutable priority and SLA policy snapshot in version 1
- Separate response and resolution deadlines and breach evidence
- PostgreSQL-authoritative command and worker timestamps
- Actor-scoped idempotency receipts for every mutation
- Append-only incident-event rows protected by a database trigger
- Deferred database checks that keep incident and SLA progress timestamps aligned
- `FOR UPDATE SKIP LOCKED` evaluator and outbox leases
- Console and SMTP outbox transports
- JSON logs, liveness, and database-backed readiness
- Alembic migrations, a non-root image, Compose, and GitHub Actions definitions

### Explicit non-goals for version 1

- Comments, attachments, service catalogs, teams, queues, or public user management
- Reopening incidents, priority changes, pauses, business calendars, or deadline rebasing
- Multi-tenancy or a general-purpose RBAC engine
- Exactly-once external side effects
- A browser frontend
- Built-in TLS termination, secret management, metrics backend, or distributed tracing stack
- Claims that email providers consumed a message exactly once

Potential expansions are kept in [RFCs](docs/rfc/README.md) rather than being advertised as existing features.

## Core semantics

### Deadline boundary

An objective is met when its action occurs **at or before** its deadline. It becomes breached only when the authoritative time is later than that deadline.

For a delayed evaluator:

- `effective_at` = the contractual deadline;
- `occurred_at` / `detected_at` = when the worker or command observed the breach.

This preserves the contract while making scheduler latency visible.

### Independent objectives

Response and resolution outcomes are persisted independently. A response breach cannot suppress a later resolution breach, and a successful acknowledgement cannot erase an already-recorded response breach.

### Idempotency

Every mutation requires an `Idempotency-Key` header. The durable receipt is scoped by authenticated actor and binds:

- command type;
- canonical request payload hash; and
- resulting incident and event sequence.

Reusing the same key with the same command and payload returns the original aggregate. Reusing it for different input returns a conflict. This does not make unrelated commands idempotent and does not deduplicate requests across actors.

### Outbox delivery

Breach evidence is always committed. When the incident has an active assignee, the corresponding outbox row is committed in that same database transaction. Version 1 does not invent a fallback recipient for unassigned incidents. Delivery is lease-based and **at least once**:

- downstream consumers receive a stable deduplication key;
- expired leases may be reclaimed;
- stale workers cannot mark a newer attempt complete; and
- an exhausted ambiguous final lease is moved to `dead` rather than remaining stuck forever.

A worker crash after an external provider accepts a message but before the database records `sent` can still produce a duplicate. That is a stated boundary, not hidden behind an exactly-once claim.

## Architecture at a glance

```mermaid
flowchart LR
    User[Reporter / assignee / administrator]
    API[FastAPI command and query API]
    Worker[SLA evaluator and outbox worker]
    DB[(PostgreSQL\naggregate + ledger + receipts + outbox)]
    Transport[Console or SMTP transport]

    User -->|JWT + idempotency key| API
    API -->|single command transaction| DB
    Worker -->|row locks + database clock| DB
    Worker -->|at-least-once envelope| Transport
```

The complete C4 set is in [docs/architecture](docs/architecture/README.md).

## API summary

| Method | Path | Purpose | Idempotency key |
|---|---|---|---|
| `POST` | `/api/v1/auth/token` | Exchange owner-provisioned credentials for a bearer token | No |
| `POST` | `/api/v1/incidents` | Create an incident and immutable SLA snapshot | Required |
| `GET` | `/api/v1/incidents` | List incidents visible to the actor | No |
| `GET` | `/api/v1/incidents/{id}` | Read one visible incident | No |
| `POST` | `/api/v1/incidents/{id}/assign` | Administrator assignment | Required |
| `POST` | `/api/v1/incidents/{id}/acknowledge` | Assignee/admin response transition | Required |
| `POST` | `/api/v1/incidents/{id}/resolve` | Assignee/admin resolution transition | Required |
| `POST` | `/api/v1/incidents/{id}/close` | Reporter/admin closure transition | Required |
| `GET` | `/api/v1/incidents/{id}/events` | Read the append-only timeline | No |
| `GET` | `/health/live` | Process liveness | No |
| `GET` | `/health/ready` | PostgreSQL readiness | No |

See [the API contract](docs/contracts/API.md) for request, response, access, and error semantics.

## Local setup

### Requirements

- Python 3.12 or 3.13
- uv 0.11.33
- PostgreSQL with permissions to create the schema and triggers
- Docker with the Compose plugin for the container smoke path

`uv.lock` is the authoritative cross-platform dependency graph for local checks, CI, and image builds. Commands use `--locked` so dependency declarations cannot silently rewrite it.

### Python environment

```bash
uv sync --locked --all-extras
cp .env.example .env
uv run --locked alembic upgrade head
```

Create an initial user through the owner-operated CLI:

```bash
uv run --locked incident-sla create-user \
  --username admin \
  --email admin@example.com \
  --display-name 'Local Admin' \
  --admin
```

The command prompts twice without putting the password in the process argument list. For controlled automation, pipe one line and add `--password-stdin`.

Run the API and worker:

```bash
uv run --locked uvicorn app.main:app --reload
uv run --locked incident-sla-worker run
```

Development API documentation is exposed at `/api/docs`. It is disabled when `APP_ENV=production`.

### Compose path

```bash
./scripts/compose-smoke.sh
```

The Compose topology keeps PostgreSQL internal and publishes only the API on host loopback through a separate edge bridge. The worker alone joins the explicit egress network used by an SMTP transport. Compose is evidence topology rather than a production egress firewall; enforce stricter API network policy in the chosen deployment.

## Example command

```bash
TOKEN='replace-with-access-token'

curl --fail --silent \
  -X POST http://127.0.0.1:8000/api/v1/incidents \
  -H "Authorization: Bearer $TOKEN" \
  -H 'Content-Type: application/json' \
  -H 'Idempotency-Key: create-payments-20260727-001' \
  -d '{
    "title": "Payments returning 503",
    "description": "Checkout cannot authorize new payments",
    "priority": "critical"
  }'
```

The same actor may repeat this exact command with the same key and receive the original result. Changing the payload while reusing the key returns `409 idempotency_conflict`.

## Verification

Dependency-available source checks:

```bash
./scripts/verify-source.sh
```

Authoritative PostgreSQL path:

```bash
export TEST_DATABASE_URL='postgresql+psycopg://incident:incident@127.0.0.1:5432/incident_sla_test'
./scripts/verify.sh
```

Container path:

```bash
./scripts/compose-smoke.sh
```

Dependency and documentation gates:

```bash
./scripts/audit-dependencies.sh
python scripts/verify-docs.py
python scripts/render-diagrams.py --output /tmp/incident-sla-diagrams --render
```

The 2026-07-28 local candidate run observed 135 unit tests, the configured 90% branch-aware coverage gate, both Python 3.12 and 3.13 source gates, 22 PostgreSQL integration tests on both sides of a migration downgrade/re-upgrade cycle, a locked dependency audit, strict source and image scans, five rendered Mermaid diagrams, and the full Compose smoke including an isolated backup/restore rehearsal. The merged implementation and maintenance-policy commits also passed the exact-commit GitHub Actions gate recorded in [Claims and Evidence](docs/CLAIMS-AND-EVIDENCE.md).

## Documentation map

- [Spirit and bounded thesis](docs/SPIRIT.md)
- [Software requirements specification](docs/SRS.md)
- [Requirements traceability](docs/TRACEABILITY.md)
- [C4 architecture views](docs/architecture/README.md)
- [Architecture decision records](docs/adr/README.md)
- [Requests for comments](docs/rfc/README.md)
- [API contract](docs/contracts/API.md)
- [Data contract](docs/contracts/DATA.md)
- [Security and trust boundaries](docs/SECURITY.md)
- [Operations runbook](docs/OPERATIONS.md)
- [Testing strategy](docs/TESTING.md)
- [Claims and evidence](docs/CLAIMS-AND-EVIDENCE.md)
- [Definition of done and kill condition](docs/DEFINITION-OF-DONE.md)
- [Product naming](docs/PRODUCT-NAMING.md)
- [Documentation governance](docs/DOCUMENTATION-GOVERNANCE.md)
- [Open decisions](docs/OPEN-DECISIONS.md)
- [Runtime dependency and licence inventory](docs/DEPENDENCIES-AND-LICENCES.md)
- [Changelog](CHANGELOG.md)

## Repository status and licence

This repository is an evidence-oriented portfolio project, not a hosted service offering. The owner has deliberately retained **no repository software licence** for this release candidate; normal copyright restrictions therefore apply. Third-party packages keep their own terms, recorded separately in [Runtime Dependencies and Licences](docs/DEPENDENCIES-AND-LICENCES.md).
