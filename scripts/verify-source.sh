#!/bin/sh
set -eu

python3 -m compileall -q app tests alembic
python3 -m ruff format --check app tests
python3 -m ruff check app tests
python3 -m mypy app
python3 scripts/verify-docs.py
python3 scripts/render-diagrams.py
python3 -m pytest tests/unit \
  --cov=app.domain \
  --cov=app.config \
  --cov=app.schemas \
  --cov=app.utils.security \
  --cov=app.main \
  --cov-report=term-missing \
  --cov-fail-under=90
