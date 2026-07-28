"""Shared pytest configuration."""

import os

import pytest


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """Require explicit opt-in for PostgreSQL tests.

    ``RUN_POSTGRES_TESTS=1`` prevents an accidentally configured or silently skipped database
    suite from being mistaken for evidence.
    """

    if os.getenv("RUN_POSTGRES_TESTS") == "1":
        return
    skip = pytest.mark.skip(reason="set RUN_POSTGRES_TESTS=1 for PostgreSQL tests")
    for item in items:
        if "postgres" in item.keywords:
            item.add_marker(skip)
