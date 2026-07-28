import pytest
from pydantic import ValidationError

from app.config import Settings
from app.domain import IncidentPriority

BASE = {
    "app_env": "test",
    "jwt_secret": "x" * 40,
    "database_url": "postgresql+psycopg://u:p@localhost/db",
}


def test_cors_origins_parse_from_csv() -> None:
    config = Settings(**BASE, cors_origins="https://a.example, https://b.example")
    assert config.cors_origins == ["https://a.example", "https://b.example"]


def test_cors_origins_parse_from_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    for key, value in BASE.items():
        monkeypatch.setenv(key.upper(), str(value))
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example, https://b.example")
    assert Settings().cors_origins == ["https://a.example", "https://b.example"]


def test_non_postgresql_url_is_rejected() -> None:
    with pytest.raises(ValidationError, match=r"postgresql\+psycopg"):
        Settings(**{**BASE, "database_url": "sqlite:///tmp.db"})


def test_production_rejects_placeholder_secret() -> None:
    with pytest.raises(ValidationError, match="JWT_SECRET"):
        Settings(
            **{
                **BASE,
                "app_env": "production",
                "jwt_secret": "replace-with-at-least-32-random-bytes",
            }
        )


def test_smtp_requires_host_and_sender() -> None:
    with pytest.raises(ValidationError, match="SMTP_HOST"):
        Settings(**BASE, outbox_transport="smtp", smtp_host="")
    with pytest.raises(ValidationError, match="SMTP_FROM"):
        Settings(**BASE, outbox_transport="smtp", smtp_host="smtp.example.com")


def test_smtp_rejects_invalid_sender_and_partial_credentials() -> None:
    with pytest.raises(ValidationError, match="SMTP_FROM"):
        Settings(
            **BASE,
            outbox_transport="smtp",
            smtp_host="smtp.example.com",
            smtp_from="not-an-email",
        )
    with pytest.raises(ValidationError, match="configured together"):
        Settings(
            **BASE,
            outbox_transport="smtp",
            smtp_host="smtp.example.com",
            smtp_from="alerts@example.com",
            smtp_username="mailer",
        )


def test_policy_map_contains_every_priority() -> None:
    config = Settings(**BASE)
    assert set(config.sla_policies) == set(IncidentPriority)


def test_resolution_target_cannot_precede_response_target() -> None:
    with pytest.raises(ValidationError, match="resolution_minutes"):
        Settings(
            **BASE,
            sla_high_response_minutes=120,
            sla_high_resolution_minutes=60,
        )


@pytest.mark.parametrize(
    "origin",
    [
        "*",
        "https://example.test/path",
        "https://user:password@example.com",
        "ftp://example.test",
        "https://example.test?query=1",
    ],
)
def test_cors_origins_reject_non_origins(origin: str) -> None:
    with pytest.raises(ValidationError, match="CORS origins"):
        Settings(**BASE, cors_origins=origin)


def test_cors_origins_are_deduplicated_after_normalization() -> None:
    with pytest.raises(ValidationError, match="unique"):
        Settings(**BASE, cors_origins="https://example.test/,https://example.test")
