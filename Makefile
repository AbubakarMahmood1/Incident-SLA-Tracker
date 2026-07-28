SHELL := /bin/sh
UV ?= uv

.PHONY: install format lint test test-postgres verify-docs audit-dependencies verify-source verify compose-smoke clean

install:
	$(UV) sync --locked --all-extras

format:
	$(UV) run --locked ruff format app tests
	$(UV) run --locked ruff check --fix app tests

lint:
	$(UV) run --locked ruff format --check app tests
	$(UV) run --locked ruff check app tests
	$(UV) run --locked mypy app

# Dependency-available tests; no PostgreSQL claim is implied.
test:
	$(UV) run --locked pytest tests/unit --cov=app.domain --cov=app.config --cov=app.schemas --cov=app.utils.security --cov=app.main --cov-report=term-missing --cov-fail-under=90

test-postgres:
	@test -n "$$TEST_DATABASE_URL" || (echo 'TEST_DATABASE_URL is required' >&2; exit 2)
	RUN_POSTGRES_TESTS=1 $(UV) run --locked pytest -m postgres -v

verify-docs:
	$(UV) run --locked python scripts/verify-docs.py
	$(UV) run --locked python scripts/render-diagrams.py

audit-dependencies:
	./scripts/audit-dependencies.sh

verify-source:
	$(UV) run --locked ./scripts/verify-source.sh

verify:
	$(UV) run --locked ./scripts/verify.sh

compose-smoke:
	./scripts/compose-smoke.sh

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml htmlcov build dist *.egg-info
