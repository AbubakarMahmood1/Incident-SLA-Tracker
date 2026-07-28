# Requirements Traceability

This matrix maps every accepted requirement to implementation, tests, and the strongest evidence observed on the 2026-07-28 local candidate. Exact-commit GitHub Actions and repository-setting receipts are recorded in [CLAIMS-AND-EVIDENCE.md](CLAIMS-AND-EVIDENCE.md).

| Requirement | Implementation | Test or verification asset | Current evidence |
|---|---|---|---|
| FR-001 | `app/config.py` | `tests/unit/test_config.py` | Observed in unit tests |
| FR-002 | `app/config.py` | `tests/unit/test_config.py` | Observed in unit tests |
| FR-003 | `app/config.py` | `tests/unit/test_config.py` | Observed for direct and environment loading |
| FR-004 | `app/main.py` | `tests/unit/test_app.py` | Observed through ASGI test client |
| FR-005 | `app/main.py; app/database.py` | `tests/unit/test_app.py; tests/integration/test_api_postgres.py; scripts/compose-smoke.sh` | Liveness plus failed and successful PostgreSQL readiness observed |
| FR-006 | `app/cli.py; app/utils/security.py` | `tests/unit/test_cli.py; scripts/compose-smoke.sh` | Prompt/stdin paths and real CLI/database provisioning observed |
| FR-007 | `app/api/v1/auth.py; app/services/auth_service.py` | `tests/unit/test_security.py; tests/integration/test_api_postgres.py; scripts/compose-smoke.sh` | Crypto and database-backed token endpoint observed |
| FR-008 | `app/api/v1/auth.py; app/api/deps.py` | `tests/integration/test_api_postgres.py` | Bearer authentication and deactivated-user rejection observed |
| FR-009 | `app/utils/security.py; app/api/deps.py` | `tests/unit/test_security.py` | Observed for required claims, audience, expiry, and signature path |
| FR-010 | `app/services/incident_service.py` | `tests/integration/test_postgres_workflow.py` | PostgreSQL creation transaction observed |
| FR-011 | `app/schemas/incident.py; app/api/deps.py` | `tests/unit/test_schemas.py; tests/unit/test_security.py` | Observed in unit tests |
| FR-012 | `app/services/incident_service.py` | `tests/integration/test_postgres_workflow.py` | Immutable snapshot persistence observed |
| FR-013 | `app/domain/sla.py; app/services/incident_service.py` | `tests/unit/test_domain_sla.py; tests/integration/test_postgres_workflow.py` | Domain calculation and persistence observed |
| FR-014 | `app/services/incident_service.py` | `tests/integration/test_postgres_workflow.py` | PostgreSQL clock path observed |
| FR-015 | `app/services/incident_service.py; app/models/event.py` | `tests/integration/test_postgres_workflow.py` | Atomic incident/SLA/event creation observed |
| FR-016 | `app/api/deps.py; app/api/v1/incidents.py` | `tests/integration/test_api_postgres.py; scripts/compose-smoke.sh` | Endpoint idempotency-key enforcement observed |
| FR-017 | `app/models/idempotency.py; app/services/incident_service.py` | `tests/integration/test_postgres_workflow.py; tests/integration/test_idempotency_concurrency.py` | Durable actor-scoped receipts observed |
| FR-018 | `app/services/incident_service.py; app/utils/security.py` | `tests/unit/test_security.py; tests/integration/test_postgres_workflow.py; tests/integration/test_api_postgres.py` | Canonical replay and conflict behavior observed |
| FR-019 | `app/services/incident_service.py` | `tests/integration/test_postgres_workflow.py; scripts/compose-smoke.sh` | Stable replay observed in PostgreSQL and Compose |
| FR-020 | `app/services/incident_service.py` | `tests/integration/test_idempotency_concurrency.py` | Same-key commit and rollback races observed |
| FR-021 | `app/services/incident_service.py` | `tests/integration/test_postgres_workflow.py` | Authorization and lifecycle transaction observed |
| FR-022 | `app/api/v1/incidents.py; app/domain/sla.py` | `tests/unit/test_domain_sla.py` | Route surface and domain transitions observed |
| FR-023 | `app/services/incident_service.py` | `tests/integration/test_postgres_workflow.py; tests/integration/test_api_postgres.py` | One-way lifecycle and API paths observed |
| FR-024 | `app/domain/sla.py` | `tests/unit/test_domain_sla.py` | Observed at the deadline boundary |
| FR-025 | `app/domain/sla.py; app/services/sla_service.py` | `tests/unit/test_domain_sla.py; tests/integration/test_postgres_workflow.py` | Domain decision and transactional persistence observed |
| FR-026 | `app/services/incident_service.py` | `tests/integration/test_postgres_workflow.py` | Resolution transition observed |
| FR-027 | `app/domain/sla.py; app/services/incident_service.py` | `tests/unit/test_domain_sla.py; tests/integration/test_postgres_workflow.py` | Independent event ordering observed |
| FR-028 | `app/domain/sla.py` | `tests/unit/test_domain_sla.py; tests/integration/test_postgres_workflow.py` | Direct resolution and implicit acknowledgement observed |
| FR-029 | `app/domain/sla.py; app/services/incident_service.py` | `tests/unit/test_domain_sla.py; tests/integration/test_api_postgres.py` | Authorization and persisted transition observed |
| FR-030 | `app/domain/sla.py; app/models/sla.py` | `tests/unit/test_domain_sla.py; tests/integration/test_boundary_races.py` | Boundary semantics under concurrency observed |
| FR-031 | `app/domain/sla.py; app/models/sla.py; alembic/versions/0001_initial_ledger.py` | `tests/unit/test_domain_sla.py; tests/integration/test_postgres_workflow.py` | Domain and live constraint execution observed |
| FR-032 | `app/services/sla_service.py; app/models/event.py` | `tests/unit/test_domain_sla.py; tests/integration/test_postgres_workflow.py` | Breach decision and event persistence observed |
| FR-033 | `app/services/sla_service.py` | `tests/integration/test_worker_concurrency.py; tests/integration/test_boundary_races.py` | Evaluator concurrency and command races observed |
| FR-034 | `app/services/sla_service.py; app/models/outbox.py` | `tests/integration/test_worker_concurrency.py` | Atomic event/outbox publication observed |
| FR-035 | `alembic/versions/0001_initial_ledger.py` | `tests/integration/test_postgres_workflow.py` | Event append-only trigger observed |
| FR-036 | `alembic/versions/0001_initial_ledger.py` | `tests/integration/test_postgres_workflow.py` | Policy/priority immutability triggers observed |
| FR-037 | `alembic/versions/0001_initial_ledger.py` | `tests/integration/test_postgres_workflow.py` | SLA deletion guard observed |
| FR-038 | `alembic/versions/0001_initial_ledger.py` | `tests/integration/test_postgres_workflow.py` | Deferred cross-table consistency trigger observed |
| FR-039 | `app/services/incident_service.py` | `tests/integration/test_api_postgres.py` | Actor-scoped visibility observed |
| FR-040 | `app/services/incident_service.py; app/api/v1/incidents.py` | `tests/integration/test_api_postgres.py` | Database list and detail query behavior observed |
| FR-041 | `app/services/incident_service.py` | `tests/integration/test_postgres_workflow.py` | Escaped PostgreSQL search behavior observed |
| FR-042 | `app/services/sla_service.py` | `tests/integration/test_postgres_workflow.py; tests/integration/test_worker_concurrency.py` | Assigned and unassigned breach transactions observed |
| FR-043 | `app/services/sla_service.py; app/models/outbox.py` | `tests/integration/test_worker_concurrency.py` | Unique publication under competing evaluators observed |
| FR-044 | `app/services/outbox_service.py` | `tests/integration/test_worker_concurrency.py` | Lease claim and recovery observed |
| FR-045 | `app/services/outbox_service.py` | `tests/integration/test_worker_concurrency.py` | Stale attempt rejection observed |
| FR-046 | `app/services/outbox_service.py; app/models/outbox.py` | `tests/integration/test_worker_concurrency.py` | Pending, processing, sent, retry, and dead transitions observed |
| FR-047 | `app/services/outbox_service.py` | `tests/unit/test_outbox_transport.py; tests/integration/test_worker_concurrency.py` | Console privacy and bounded durable diagnostics observed |
| FR-048 | `app/services/outbox_service.py` | `tests/unit/test_smtp_transport.py` | Controlled SMTP delivery and required-STARTTLS failure observed |
| NFR-001 | `pyproject.toml; .python-version; .github/workflows/ci.yml` | `scripts/verify-source.sh` | Python 3.12 and 3.13 source gates observed locally |
| NFR-002 | `tests/integration/conftest.py; app/models` | `tests/integration` | Real PostgreSQL gate observed with no fallback |
| NFR-003 | `app/services/incident_service.py; app/services/sla_service.py` | `tests/integration/test_idempotency_concurrency.py; tests/integration/test_boundary_races.py` | Rollback and race behavior observed |
| NFR-004 | `app/domain/sla.py; app/utils/time.py; app/services` | `tests/unit/test_domain_sla.py; tests/integration/test_postgres_workflow.py` | Domain and persisted UTC values observed |
| NFR-005 | `app/services/incident_service.py; app/services/sla_service.py; app/services/outbox_service.py` | `tests/integration` | Live PostgreSQL clock paths observed |
| NFR-006 | `app/domain/sla.py` | `tests/unit/test_domain_sla.py` | Observed |
| NFR-007 | `scripts/verify-source.sh; pyproject.toml` | `tests/unit` | Observed above 90 percent in audit environment |
| NFR-008 | `tests/conftest.py; tests/integration/conftest.py` | `tests/integration` | Explicit database-required gate executes with no skip |
| NFR-009 | `scripts/verify.sh; alembic` | `tests/integration` | Upgrade/downgrade/re-upgrade cycle observed |
| NFR-010 | `Dockerfile; docker-compose.yml` | `scripts/compose-smoke.sh` | Non-root/read-only runtime controls observed |
| NFR-011 | `docker-compose.yml` | `scripts/compose-smoke.sh` | Internal database and loopback-only API exposure observed |
| NFR-012 | `.gitignore; .dockerignore` | `scripts/verify-source.sh; Trivy source scan` | Packaging exclusions and secret scan observed |
| NFR-013 | `app/utils/security.py` | `tests/unit/test_security.py` | Observed |
| NFR-014 | `app/utils/security.py` | `tests/unit/test_security.py` | Observed |
| NFR-015 | `app/logging.py; app/services/outbox_service.py` | `tests/unit/test_app.py; tests/unit/test_outbox_transport.py` | JSON structure and transport redaction observed |
| NFR-016 | `app/config.py; app/schemas; app/api/v1/incidents.py; app/services/outbox_service.py` | `tests/unit/test_config.py; tests/unit/test_schemas.py; tests/integration/test_worker_concurrency.py` | Request/config bounds and durable error minimization observed |
| NFR-017 | `app/main.py; app/database.py` | `tests/unit/test_app.py; tests/integration/test_api_postgres.py; scripts/compose-smoke.sh` | Failure and success modes observed |
| NFR-018 | `pyproject.toml; uv.lock; docs/DEPENDENCIES-AND-LICENCES.md` | `scripts/audit-dependencies.sh; uv pip check` | Locked graph, audit, and licence inventory observed |
| NFR-019 | `docs/SRS.md; docs/TRACEABILITY.md` | `scripts/verify-docs.py` | ID bijection and local links observed |
| NFR-020 | `README.md; docs/CLAIMS-AND-EVIDENCE.md` | `documentation review` | Implemented in source wording |
| NFR-021 | `alembic; app/main.py` | `scripts/verify.sh` | Offline SQL and live migration cycle observed |
| NFR-022 | `tests/integration/test_worker_concurrency.py` | `PostgreSQL integration gate` | Competing evaluators and workers observed |
| NFR-023 | `docs/OPERATIONS.md` | `scripts/compose-smoke.sh` | Restart and isolated backup/restore rehearsal observed |
| NFR-024 | `tests/integration; app/services/outbox_service.py` | `fake/console transport selection` | No real provider calls in tests |

## Interpretation

- **Observed** means the named command or test executed with its authoritative dependency on the local candidate.
- GitHub Actions and repository settings are external evidence classes and were verified separately from the local candidate.

Requirement closure status is summarized in [CLAIMS-AND-EVIDENCE.md](CLAIMS-AND-EVIDENCE.md).
