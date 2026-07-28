"""Password hashing, JWT validation, and canonical request hashing."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from jwt.types import Options

from app.config import Settings

_PASSWORD_HASHER = PasswordHasher()
_IDEMPOTENCY_KEY = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{7,127}$")


class TokenError(ValueError):
    """Raised when an access token cannot be trusted."""


def normalize_identity(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    if not normalized or len(normalized) > 320:
        raise ValueError("identity value is empty or too long")
    if any(ord(char) < 32 or ord(char) == 127 for char in normalized):
        raise ValueError("identity value contains control characters")
    return normalized


def hash_password(password: str) -> str:
    if len(password) < 12 or len(password) > 256:
        raise ValueError("password length must be between 12 and 256 characters")
    return _PASSWORD_HASHER.hash(password)


def verify_password(password: str, encoded: str) -> bool:
    try:
        return _PASSWORD_HASHER.verify(encoded, password)
    except (VerifyMismatchError, InvalidHashError):
        return False


def create_access_token(
    *, user_id: uuid.UUID, settings: Settings, now: datetime | None = None
) -> str:
    issued_at = now or datetime.now(UTC)
    if issued_at.tzinfo is None or issued_at.utcoffset() is None:
        raise ValueError("token clock must be timezone-aware")
    expires_at = issued_at + timedelta(minutes=settings.access_token_expire_minutes)
    payload = {
        "sub": str(user_id),
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": issued_at,
        "nbf": issued_at,
        "exp": expires_at,
        "jti": str(uuid.uuid4()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def decode_access_token(token: str, *, settings: Settings) -> uuid.UUID:
    options: Options = {"require": ["sub", "iss", "aud", "iat", "nbf", "exp", "jti"]}
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=["HS256"],
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            options=options,
        )
        return uuid.UUID(str(payload["sub"]))
    except (jwt.PyJWTError, KeyError, TypeError, ValueError) as exc:
        raise TokenError("invalid access token") from exc


def validate_idempotency_key(value: str) -> str:
    if not _IDEMPOTENCY_KEY.fullmatch(value):
        raise ValueError(
            "Idempotency-Key must be 8-128 characters using letters, digits, '.', '_', ':', or '-'"
        )
    return value


def canonical_request_hash(command_type: str, payload: Any) -> str:
    canonical = json.dumps(
        {"command": command_type, "payload": payload},
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    ).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()
