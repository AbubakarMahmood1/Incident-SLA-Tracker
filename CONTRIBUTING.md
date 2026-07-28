# Contributing

This repository prioritizes a small, evidence-bearing SLA ledger over feature count.

## Before changing behavior

1. Read [docs/SPIRIT.md](docs/SPIRIT.md) and [docs/SRS.md](docs/SRS.md).
2. Confirm the change strengthens the bounded thesis.
3. Use an RFC for a material new capability or contract change.
4. Use an ADR when an architectural choice is accepted.
5. Update requirements, traceability, tests, claims, and operations together.

## Local checks

```bash
uv sync --locked --all-extras
uv run --locked ./scripts/verify-source.sh
```

PostgreSQL changes also require:

```bash
export TEST_DATABASE_URL='postgresql+psycopg://.../disposable_test_database'
uv run --locked ./scripts/verify.sh
```

Container changes require `./scripts/compose-smoke.sh`.

## Pull requests

A pull request should state:

- problem and bounded scope;
- affected requirement and ADR/RFC identifiers;
- failure modes considered;
- tests and evidence run;
- migration and rollback impact; and
- claims that must change.

Do not submit generated caches, `.env`, credentials, real incident data, database dumps, or screenshots containing secrets.
