# Product and Repository Naming

## Decision

- **Retained GitHub repository slug:** `Incident-SLA-Tracker`
- **Display name:** Incident SLA Ledger
- **Python package:** `incident-sla-ledger`
- **Import package:** `app` for this bounded pass
- **CLI commands:** `incident-sla` and `incident-sla-worker`

## Why the names differ

“Ledger” communicates the repository's strongest property: durable, ordered evidence for SLA decisions and retries. The existing GitHub slug remains understandable, already has inbound links and repository history, and a cosmetic remote rename would create maintenance without changing the implementation or public display name.

“Ledger” is not a claim of blockchain, cryptographic immutability, accounting compliance, or tamper-proof storage. Here it means that accepted transitions are appended to an ordered PostgreSQL event history and cannot be casually edited through ordinary application roles.

## Why not use a fanciful brand

A startup-style name would add collision and explanation cost without improving portfolio signal. A descriptive slug lets a reviewer infer the domain and the distinguishing mechanism immediately.

## Remote metadata sequence

After authoritative gates pass:

1. update the repository description to the evidence-backed thesis;
2. replace stale Celery/Redis/observability topics with the implemented architecture;
3. retain the existing remote slug and visibility;
4. update portfolio references only if their claims are stale; and
5. avoid renaming internal imports merely for cosmetic symmetry unless a separate refactor has value.

Recommended description:

> Auditable incident SLA transitions with PostgreSQL idempotency, independent deadline evidence, and an at-least-once transactional outbox.

The description is a bounded thesis, not a production-readiness claim.
