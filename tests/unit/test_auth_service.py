from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.services.auth_service import authenticate_user
from app.utils import hash_password


@pytest.mark.asyncio
async def test_invalid_identity_returns_generic_failure_without_querying_database() -> None:
    db = AsyncMock()
    assert await authenticate_user(db, "x" * 321, "not a matching password") is None
    db.scalar.assert_not_awaited()


@pytest.mark.asyncio
async def test_missing_user_returns_generic_failure() -> None:
    db = AsyncMock()
    db.scalar.return_value = None
    assert await authenticate_user(db, "missing-user", "not a matching password") is None


@pytest.mark.asyncio
async def test_active_user_requires_the_correct_password() -> None:
    db = AsyncMock()
    db.scalar.return_value = SimpleNamespace(
        is_active=True,
        password_hash=hash_password("correct horse battery staple"),
    )
    assert await authenticate_user(db, "Alice", "wrong password value") is None
    assert (
        await authenticate_user(db, "Alice", "correct horse battery staple")
        is db.scalar.return_value
    )


@pytest.mark.asyncio
async def test_oversized_username_and_password_do_not_reach_database() -> None:
    db = AsyncMock()
    assert await authenticate_user(db, "u" * 101, "p" * 10000) is None
    db.scalar.assert_not_awaited()
