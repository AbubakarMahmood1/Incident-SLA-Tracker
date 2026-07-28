"""Authentication service."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.utils import normalize_identity, verify_password

# A non-secret Argon2 hash used only to keep missing/invalid-user authentication on the same
# password-verification path as existing users.
_DUMMY_PASSWORD_HASH = (
    "$argon2id$v=19$m=65536,t=3,p=4$BOsoJPqdg/ts8wxienX5uQ"
    "$Ue/oemYasdjPWjS0KpqHccD7wZrlbsjTxEbPxWrGbBY"
)


async def authenticate_user(db: AsyncSession, username: str, password: str) -> User | None:
    bounded_password = password if len(password) <= 256 else "invalid oversized password"
    try:
        normalized = normalize_identity(username)
        if len(normalized) > 100:
            raise ValueError("username exceeds the stored identity bound")
    except ValueError:
        verify_password(bounded_password, _DUMMY_PASSWORD_HASH)
        return None

    user = await db.scalar(select(User).where(User.username == normalized))
    encoded = user.password_hash if user is not None else _DUMMY_PASSWORD_HASH
    password_matches = verify_password(bounded_password, encoded)
    if len(password) > 256:
        password_matches = False
    if user is None or not user.is_active or not password_matches:
        return None
    return user
