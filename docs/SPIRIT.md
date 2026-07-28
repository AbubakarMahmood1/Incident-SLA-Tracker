# Project Spirit

## One-sentence thesis

Incident SLA Ledger demonstrates that a small incident lifecycle can remain deterministic, attributable, and retry-safe when deadline evaluation, API commands, and notification publication compete over the same PostgreSQL state.

## What makes it worth keeping

The project is not differentiated by FastAPI, SQLAlchemy, JWT, or Docker. Those are implementation tools. Its portfolio value comes from the failure boundaries it makes explicit:

- two SLA objectives are independent and cannot suppress one another;
- a delayed scheduler records the contractual deadline rather than rewriting history to the observation time;
- mutation retries are bound to actor, command, and payload;
- policy values are snapshotted rather than retroactively changed;
- accepted transitions create durable history in the same transaction;
- breach publication uses a transactional outbox; and
- external delivery is described honestly as at least once.

A reviewer should be able to inspect the domain functions, migration constraints, service transactions, and PostgreSQL tests and see the same semantics expressed at each layer.

## Product boundary

The bounded product supports:

1. owner-provisioned authenticated users;
2. incident creation and assignment;
3. acknowledgement, resolution, and closure;
4. response and resolution deadline evaluation;
5. append-only transition history;
6. actor-scoped idempotent commands; and
7. durable breach-notification publication.

Everything else must justify itself against this thesis. Comments, attachments, service catalogs, broad user administration, dashboards, tracing infrastructure, queues, and elaborate alerting are not automatically valuable merely because mature ITSM products contain them.

## Honesty rules

- “Source-ready” means the source-level design and dependency-available checks are coherent. It does not mean deployed, production-ready, or fully verified.
- “Append-only” means PostgreSQL rejects update and delete operations on event rows through the installed trigger. It does not mean cryptographically tamper-evident or resistant to a database superuser.
- “Idempotent” applies only to commands carrying the same key, actor, command type, and canonical payload.
- “At least once” permits duplicates after ambiguous provider outcomes; consumers receive a deduplication key.
- “PostgreSQL-authoritative time” applies to normal uninjected execution. Test clocks are deliberate evidence fixtures.
- A configured CI workflow is not a green CI result until it runs on the final commit.

## Success condition

The project earns a public portfolio position when its final source passes:

- strict source checks on supported Python versions;
- migration upgrade, downgrade, and re-upgrade against disposable PostgreSQL;
- real concurrency and trigger tests;
- image build and Compose smoke;
- dependency and image review; and
- a green final GitHub Actions run.

## Kill condition

Archive the repository as a documented learning project if any of these remains true after a focused closure pass:

- competing evaluators can create duplicate objective evidence;
- a failed command can leave state without its event or receipt result;
- policy or history invariants cannot be enforced and tested in PostgreSQL;
- notification semantics are advertised as exactly once without a provider-side idempotency protocol;
- the project expands back into an unbounded ITSM clone; or
- the maintenance cost of Python, PostgreSQL, image, and concurrency evidence exceeds its portfolio value.
