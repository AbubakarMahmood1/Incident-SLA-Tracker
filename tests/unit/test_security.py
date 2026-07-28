from datetime import UTC, datetime, timedelta
from uuid import uuid4

import jwt
import pytest

from app.config import Settings
from app.utils import (
    TokenError,
    canonical_request_hash,
    create_access_token,
    decode_access_token,
    hash_password,
    normalize_identity,
    validate_idempotency_key,
    verify_password,
)


def settings(**overrides) -> Settings:
    return Settings(
        app_env="test",
        jwt_secret="x" * 40,
        database_url="postgresql+psycopg://u:p@localhost/db",
        **overrides,
    )


def test_password_round_trip() -> None:
    encoded = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", encoded)
    assert not verify_password("incorrect horse battery staple", encoded)


@pytest.mark.parametrize("length", [0, 1, 11, 257])
def test_password_length_is_bounded(length: int) -> None:
    with pytest.raises(ValueError):
        hash_password("a" * length)


def test_token_round_trip() -> None:
    user_id = uuid4()
    token = create_access_token(user_id=user_id, settings=settings())
    assert decode_access_token(token, settings=settings()) == user_id


def test_token_rejects_wrong_audience() -> None:
    user_id = uuid4()
    token = create_access_token(user_id=user_id, settings=settings())
    with pytest.raises(TokenError):
        decode_access_token(token, settings=settings(jwt_audience="other"))


def test_token_requires_claims() -> None:
    config = settings()
    token = jwt.encode({"sub": str(uuid4())}, config.jwt_secret, algorithm="HS256")
    with pytest.raises(TokenError):
        decode_access_token(token, settings=config)


def test_expired_token_is_rejected() -> None:
    config = settings()
    now = datetime.now(UTC)
    token = jwt.encode(
        {
            "sub": str(uuid4()),
            "iss": config.jwt_issuer,
            "aud": config.jwt_audience,
            "iat": now - timedelta(hours=2),
            "nbf": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
            "jti": str(uuid4()),
        },
        config.jwt_secret,
        algorithm="HS256",
    )
    with pytest.raises(TokenError):
        decode_access_token(token, settings=config)


@pytest.mark.parametrize(
    "key",
    [
        "request-123",
        "01HZX2R3S4T5V6W7X8Y9",
        "actor:command:0001",
        "abc_def.ghi-jkl",
    ],
)
def test_idempotency_key_accepts_bounded_ascii(key: str) -> None:
    assert validate_idempotency_key(key) == key


@pytest.mark.parametrize(
    "key",
    ["short", " contains-space", "contains space", "é" * 8, "a" * 129, "!invalid!!"],
)
def test_idempotency_key_rejects_ambiguous_values(key: str) -> None:
    with pytest.raises(ValueError):
        validate_idempotency_key(key)


def test_request_hash_is_canonical_for_mapping_order() -> None:
    first = canonical_request_hash("command", {"b": 2, "a": 1})
    second = canonical_request_hash("command", {"a": 1, "b": 2})
    assert first == second


def test_request_hash_binds_command_and_payload() -> None:
    baseline = canonical_request_hash("create", {"a": 1})
    assert baseline != canonical_request_hash("update", {"a": 1})
    assert baseline != canonical_request_hash("create", {"a": 2})


def test_identity_normalization_is_compatibility_normalized_casefolded_and_trimmed() -> None:
    assert normalize_identity("  Alice.Example  ") == "alice.example"
    assert normalize_identity("ＡＬＩＣＥ") == "alice"  # noqa: RUF001


@pytest.mark.parametrize("value", ["", "   ", "name\nadmin", "a" * 321])
def test_identity_normalization_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_identity(value)
