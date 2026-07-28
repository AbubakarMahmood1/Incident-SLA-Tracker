# Definition of Done

The repository is not DONE because a large patch exists or because source-level tests pass. Every required gate below must be observed on the final intended revision.

## 1. Product and claims

- [x] One bounded thesis is stated.
- [x] Unsupported ITSM, E2E, observability, and production-ready claims are removed.
- [x] Non-goals and future RFCs are explicit.
- [x] Final public README wording matches observed local evidence and explicit non-claims.
- [ ] Repository description, topics, and profile entry are updated only after evidence closes.

## 2. Source quality

- [x] Pure domain semantics have deterministic tests.
- [x] Requests reject unknown fields and bounded invalid values.
- [x] Configuration fails closed for database dialect and production JWT secret.
- [x] Ruff format and lint pass using the declared dependency graph.
- [x] Strict MyPy passes using the declared dependency graph.
- [x] Python 3.12 and 3.13 source jobs pass locally.
- [x] uv 0.11.33 lock is committed and `uv pip check` passes.

## 3. PostgreSQL behavior

- [x] Upgrade from base to head succeeds on disposable PostgreSQL.
- [x] Downgrade to base and re-upgrade succeeds on disposable PostgreSQL.
- [x] All PostgreSQL integration tests execute with no skips.
- [x] Event append-only trigger is observed rejecting update/delete.
- [x] Policy, priority, cross-table progress, and breach constraints are observed.
- [x] Same-key concurrent commands converge without partial or poisoned receipts.
- [x] Command/evaluator races preserve one final objective outcome.
- [x] Competing evaluators produce one event and, for an active assignee, one outbox row per objective.
- [x] An unassigned overdue incident records breach evidence without a fabricated notification recipient.
- [x] Stale outbox attempts cannot complete a newer lease.
- [x] Exhausted ambiguous leases become visible dead rows.
- [x] Rollback tests prove no partial aggregate/event/outbox publication.

## 4. API and authentication

- [x] Real database-backed token, create, replay, list, lifecycle, timeline, and negative authorization paths pass.
- [x] Deactivated-user token rejection is observed.
- [x] Reverse-proxy request-size and rate limits are documented as deployment-owned and are not claimed by the supplied Compose topology.
- [x] No secrets, tokens, passwords, recipient addresses, raw provider exceptions, or full outbox payloads appear unexpectedly in tested logs or durable diagnostics.

## 5. Image and deployment

- [x] Image builds from the candidate tree with the locked graph.
- [x] Image runs as the declared non-root UID.
- [x] Compose read-only filesystem, tmpfs, dropped capabilities, and no-new-privileges are observed.
- [x] PostgreSQL is internal and only intended host ports are exposed.
- [x] API and worker restart/recovery behavior is exercised.
- [x] Compose smoke passes from a clean volume.
- [x] Database backup and isolated restore rehearsal succeeds.

## 6. Security, dependencies, and licences

- [x] Dependency vulnerability scan is reviewed.
- [x] Container vulnerability scan is reviewed.
- [x] Third-party runtime licence inventory is recorded and reviewed.
- [x] Repository no-licence status is deliberately retained.
- [x] Controlled SMTP submission and required-STARTTLS refusal are tested.
- [ ] Private vulnerability-reporting path is verified.

## 7. Documentation

- [x] SRS, traceability, C4 source, ADRs, RFCs, contracts, security, operations, testing, claims, and naming documents exist.
- [x] Every SRS requirement maps exactly once and all links resolve in the candidate tree.
- [x] Mermaid diagrams render and pass visual inspection.
- [x] Repository-owned operations steps are rehearsed against the release candidate.
- [x] Claims ledger records the local command set and date; exact pushed revision remains the CI receipt.

## 8. CI and release

- [ ] Final GitHub Actions workflow is green on the final commit with no required test skipped.
- [x] Local release candidate is built from one candidate tree and dependency lock.
- [x] Version 0.2.0 and changelog are deliberate.
- [ ] Retained remote slug, description, topics, vulnerability reporting, and visibility are verified after merge.

## Kill condition

Archive the repository as a documented learning project instead of leaving it publicly almost-complete when any of the following applies after one bounded closure cycle:

- PostgreSQL concurrency cannot prove one breach event and, when a recipient exists, one outbox row per objective;
- idempotency races can repeat or poison commands;
- migration or trigger invariants are too fragile to maintain;
- the owner does not want the ongoing PostgreSQL, Python, image, and dependency maintenance burden;
- scope expands back into an indistinct ITSM clone; or
- external delivery is marketed as exactly once without an accepted provider protocol.

Archival is a valid completion state. The source, ADRs, evidence, and retrospective still preserve the learning.
