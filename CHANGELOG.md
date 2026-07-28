# Changelog

All notable repository-level changes are recorded here. This portfolio project does not currently publish packaged releases.

## 0.2.0 - 2026-07-28

### Changed

- Reframed the project as the bounded Incident SLA Ledger rather than a broad ITSM clone.
- Made PostgreSQL the sole transaction, lock, clock, idempotency, event, SLA, and outbox authority.
- Split response and resolution objectives and preserved contractual deadline evidence.
- Replaced Celery and Redis with bounded `SKIP LOCKED` evaluator and outbox workers.
- Added owner-provisioned authentication, explicit authorization, actor-scoped idempotency, and one-way lifecycle commands.
- Added a locked Python 3.12/3.13 toolchain, hardened Alpine image, Compose evidence topology, and supply-chain checks.
- Added SRS, traceability, C4 views, ADRs, RFCs, contracts, security, operations, test strategy, and claims governance.

### Verified Locally

- Unit, branch-coverage, strict Ruff, and strict MyPy gates.
- PostgreSQL migrations, constraints, triggers, command races, evaluator races, and outbox lease behavior.
- Database-backed API authentication and authorization matrix.
- Controlled SMTP submission and STARTTLS refusal without plaintext fallback.
- Non-root read-only container controls, restart behavior, and isolated backup/restore.
- Locked dependency audit, source/image scanning, documentation validation, and Mermaid rendering.

### Boundaries

- No production-readiness, exactly-once external delivery, cryptographic tamper evidence, or performance claim is added.
- No repository software licence is granted.
