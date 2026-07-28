# Claims and Evidence Ledger

## Status vocabulary

- **Observed locally:** executed against the 2026-07-28 candidate tree with the named dependency.
- **Pending external:** requires an exact-commit receipt outside the local environment.
- **Boundary:** implemented behavior is intentionally narrower than the possible claim.
- **Rejected:** wording must not be used for the current system.

## Current ledger

| Claim | Status | Evidence or reason |
|---|---|---|
| Pure SLA, validation, authentication, and API-isolation semantics behave as documented | Observed locally | 135 unit tests pass on the locked Python 3.13 graph |
| Selected dependency-available core exceeds 90% branch-aware coverage | Observed locally | `scripts/verify-source.sh` coverage gate |
| Python 3.12 and 3.13 source, formatting, lint, and strict typing gates pass | Observed locally | Locked source gate on both interpreters |
| Migration upgrade, downgrade, and re-upgrade succeed | Observed locally | `scripts/verify.sh` against disposable PostgreSQL |
| Twenty-two PostgreSQL integration tests pass before and after the migration cycle | Observed locally | Real PostgreSQL tests with no SQLite fallback and no skips |
| Actor-scoped idempotency converges under commit and rollback races | Observed locally | Concurrent create and rollback-retry tests |
| API commands and evaluators converge at response and resolution boundaries | Observed locally | Command-first and evaluator-first PostgreSQL race tests |
| Event, policy, priority, progress, and SLA constraints reject forbidden mutation | Observed locally | Migration-installed trigger and deferred-constraint tests |
| Competing evaluators publish each breach once | Observed locally | `SKIP LOCKED` concurrency tests; outbox publication remains conditional on an active assignee |
| Outbox leases resist stale completion and recover after cancellation | Observed locally | Stale-attempt, final-lease, and send-before-mark cancellation tests |
| Provider failures retry to dead with bounded durable diagnostics | Observed locally | Durable state records error type and sanitized SMTP response code, not raw exception text |
| Database-backed token, authorization, visibility, lifecycle, timeline, and deactivation paths pass | Observed locally | PostgreSQL API matrix |
| Controlled SMTP submission works and STARTTLS refusal does not fall back to plaintext | Observed locally | Local SMTP transport tests |
| Image builds and runs with the declared non-root/read-only controls | Observed locally | Pinned Alpine image and Compose runtime inspection |
| Compose smoke, restart recovery, idempotent replay, and isolated backup/restore pass | Observed locally | `scripts/compose-smoke.sh` |
| Dependency graph is reproducibly locked and internally consistent | Observed locally | uv 0.11.33, `uv.lock`, locked sync/export, and `uv pip check` |
| Locked Python dependencies have no known audited vulnerabilities | Observed locally | `scripts/audit-dependencies.sh` with pip-audit 2.10.1 |
| Source and final Alpine image have no detected HIGH/CRITICAL Trivy findings | Observed locally | Trivy 0.72.0 strict scans |
| Runtime dependency licences are inventoried | Observed locally | `DEPENDENCIES-AND-LICENCES.md`; repository no-licence status retained |
| Five Mermaid diagrams render and pass visual inspection | Observed locally | Pinned Mermaid CLI render plus PNG inspection |
| GitHub Actions is green on the final commit | Pending external | Requires the pushed exact-commit workflow receipt |
| Private vulnerability reporting is enabled | Pending external | Requires GitHub repository setting verification |
| SMTP submission works with an arbitrary production provider | Boundary | Controlled server behavior is observed; provider-specific trust and acceptance remain deployment-owned |
| External delivery is exactly once | Rejected | Provider outcome cannot share the PostgreSQL commit |
| The event ledger is cryptographically tamper-proof | Rejected | Trigger-protected append-only rows are not a transparency log |
| The project is production-ready | Rejected | No production deployment, load evidence, SLO, TLS/secret platform, monitoring, or operational ownership exists |
| The project is a complete ITSM platform | Rejected | Deliberately bounded non-goals |
| The API has comprehensive E2E browser coverage | Rejected | No browser product or executed E2E suite |
| Prometheus, Grafana, and distributed tracing are supplied | Rejected | Decorative unintegrated stack removed from scope |

## Local evidence receipt

Date: **2026-07-28**

```bash
./scripts/verify-source.sh
TEST_DATABASE_URL='postgresql+psycopg://.../disposable_database' ./scripts/verify.sh
./scripts/compose-smoke.sh
./scripts/audit-dependencies.sh
python scripts/verify-docs.py
python scripts/render-diagrams.py --output /tmp/incident-sla-diagrams --render
```

Scanner and image commands are pinned in `.github/workflows/ci.yml`. The exact pushed commit and workflow run remain the external gate rather than being inferred from these local results.

## Public wording allowed after exact-commit CI

> Auditable incident SLA transition service with observed PostgreSQL concurrency, migration, idempotency, and at-least-once outbox behavior.

Even after closure, avoid “production-ready,” “exactly once,” “tamper-proof,” and unqualified performance claims.
