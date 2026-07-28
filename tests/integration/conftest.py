"""PostgreSQL integration fixtures.

These fixtures intentionally fail when explicitly enabled without a database. They never fall
back to SQLite or an in-memory ORM substitute because the evidence depends on PostgreSQL locks,
JSONB, triggers, and conflict handling.
"""

from __future__ import annotations

import os
import subprocess
from collections.abc import AsyncIterator

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.models import User
from app.utils import hash_password


@pytest.fixture(scope="session")
def postgres_url() -> str:
    url = os.getenv("TEST_DATABASE_URL", "")
    if not url:
        pytest.fail("TEST_DATABASE_URL is required when RUN_POSTGRES_TESTS=1")
    if not url.startswith("postgresql+psycopg://"):
        pytest.fail("TEST_DATABASE_URL must use postgresql+psycopg://")
    env = os.environ.copy()
    env["DATABASE_URL"] = url
    env["APP_ENV"] = "test"
    env["JWT_SECRET"] = "integration-test-secret-that-is-long-enough"
    subprocess.run(
        ["alembic", "upgrade", "head"],
        check=True,
        env=env,
        capture_output=True,
        text=True,
    )
    return url


@pytest.fixture
async def db(postgres_url: str) -> AsyncIterator[AsyncSession]:
    engine = create_async_engine(postgres_url, pool_pre_ping=True)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with engine.begin() as connection:
        await connection.execute(
            text(
                "TRUNCATE outbox_messages, command_receipts, incident_events, slas, "
                "incidents, users RESTART IDENTITY CASCADE"
            )
        )
    async with factory() as session:
        yield session
        await session.rollback()
    await engine.dispose()


@pytest.fixture
async def users(db: AsyncSession) -> dict[str, User]:
    reporter = User(
        username="reporter",
        email="reporter@example.com",
        display_name="Reporter",
        password_hash=hash_password("reporter password 123"),
    )
    assignee = User(
        username="assignee",
        email="assignee@example.com",
        display_name="Assignee",
        password_hash=hash_password("assignee password 123"),
    )
    outsider = User(
        username="outsider",
        email="outsider@example.com",
        display_name="Outsider",
        password_hash=hash_password("outsider password 123"),
    )
    admin = User(
        username="admin",
        email="admin@example.com",
        display_name="Admin",
        password_hash=hash_password("administrator password 123"),
        is_admin=True,
    )
    async with db.begin():
        db.add_all([reporter, assignee, outsider, admin])
    return {
        "reporter": reporter,
        "assignee": assignee,
        "outsider": outsider,
        "admin": admin,
    }
