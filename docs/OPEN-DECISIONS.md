# Open Decisions and Deferred Work

This file holds unresolved work that does not belong in current claims. Items should be removed, converted to an ADR/RFC, or closed with evidence rather than accumulating indefinitely.

## Closed in the 0.2.0 candidate

- uv 0.11.33 and `uv.lock` are the accepted dependency authority.
- The repository deliberately retains no software licence.
- PostgreSQL migration, constraint, trigger, idempotency, boundary-race, API, and worker tests execute against the real database.
- Ruff, strict MyPy, Python 3.12/3.13, dependency, image, Compose, backup/restore, SMTP, logging, and diagram gates execute locally.
- The existing GitHub slug is deliberately retained for link stability.
- Exact-commit GitHub Actions and private vulnerability reporting remain external repository-setting gates, not missing source work.

## Architectural decisions awaiting RFC outcome

- Business calendars, pauses, and policy correction: RFC-0001.
- Multi-tenant identity and authorization: RFC-0002.
- Provider receipts and stronger deduplication: RFC-0003.
- Collaboration modules or external integration: RFC-0004.

## Operational policy decisions

- Command-receipt retention and whether old keys may ever be reused.
- Event and outbox retention/anonymization for real personal data.
- Dead-message review ownership and response target.
- Whether a future accepted RFC should route unassigned breach alerts to an explicit escalation policy; version 1 records the breach but creates no fallback recipient.
- Supported PostgreSQL minor versions and upgrade cadence.
- Supported Python patch versions and dependency-update cadence.
- JWT secret rotation procedure without refresh tokens.
- Whether console transport should remain available outside development.
- Production reverse-proxy body, connection, and rate limits.
- Production TLS termination, secret storage, monitoring, backup retention, and incident-response ownership.

## Deliberately deferred improvements

- Metrics and tracing may be added only after concrete operational questions are identified. A decorative dashboard stack is not a release requirement.
- A browser UI is not needed to prove the backend thesis.
- Generic CRUD, reopen, deletion, comments, and attachments do not return without an accepted RFC.
