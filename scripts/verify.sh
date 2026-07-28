#!/bin/sh
set -eu

: "${TEST_DATABASE_URL:?TEST_DATABASE_URL is required for authoritative verification}"

./scripts/verify-source.sh
DATABASE_URL="$TEST_DATABASE_URL" alembic upgrade head
RUN_POSTGRES_TESTS=1 python3 -m pytest -m postgres -v
DATABASE_URL="$TEST_DATABASE_URL" alembic downgrade base
DATABASE_URL="$TEST_DATABASE_URL" alembic upgrade head
RUN_POSTGRES_TESTS=1 python3 -m pytest -m postgres -v
