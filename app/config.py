"""Validated application configuration."""

from __future__ import annotations

from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import EmailStr, Field, TypeAdapter, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

from app.domain import IncidentPriority, SLAPolicy

_PLACEHOLDER_SECRETS = {
    "change-me",
    "change-this-secret-key",
    "replace-with-at-least-32-random-bytes",
    "secret",
}


class Settings(BaseSettings):
    """Configuration loaded from environment variables and an optional ``.env`` file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    app_name: str = "incident-sla-ledger"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    jwt_secret: str = "replace-with-at-least-32-random-bytes"
    jwt_issuer: str = "incident-sla-ledger"
    jwt_audience: str = "incident-sla-api"
    access_token_expire_minutes: int = Field(default=30, ge=5, le=1440)

    database_url: str = "postgresql+psycopg://incident:incident@localhost:5432/incident_sla"
    database_pool_size: int = Field(default=5, ge=1, le=50)
    database_max_overflow: int = Field(default=5, ge=0, le=100)
    database_statement_timeout_ms: int = Field(default=5000, ge=250, le=120000)

    cors_origins: Annotated[list[str], NoDecode] = Field(default_factory=list)

    sla_critical_response_minutes: int = Field(default=15, ge=1, le=525600)
    sla_critical_resolution_minutes: int = Field(default=240, ge=1, le=525600)
    sla_high_response_minutes: int = Field(default=60, ge=1, le=525600)
    sla_high_resolution_minutes: int = Field(default=1440, ge=1, le=525600)
    sla_medium_response_minutes: int = Field(default=240, ge=1, le=525600)
    sla_medium_resolution_minutes: int = Field(default=4320, ge=1, le=525600)
    sla_low_response_minutes: int = Field(default=1440, ge=1, le=525600)
    sla_low_resolution_minutes: int = Field(default=10080, ge=1, le=525600)

    worker_poll_seconds: float = Field(default=5.0, ge=0.25, le=3600)
    worker_batch_size: int = Field(default=100, ge=1, le=1000)
    outbox_max_attempts: int = Field(default=8, ge=1, le=100)
    outbox_lease_seconds: int = Field(default=120, ge=10, le=86400)
    outbox_transport: Literal["console", "smtp"] = "console"

    smtp_host: str = ""
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_starttls: bool = True
    smtp_username: str = ""
    smtp_password: str = ""
    smtp_from: str = ""

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("cors_origins")
    @classmethod
    def validate_origins(cls, values: list[str]) -> list[str]:
        normalized: list[str] = []
        for value in values:
            candidate = value.strip().rstrip("/")
            parsed = urlsplit(candidate)
            try:
                port = parsed.port
            except ValueError as exc:
                raise ValueError("CORS origin contains an invalid port") from exc
            hostname = parsed.hostname
            canonical = f"{parsed.scheme}://{parsed.netloc}"
            if (
                parsed.scheme not in {"http", "https"}
                or not parsed.netloc
                or not hostname
                or any(char.isspace() for char in candidate)
                or candidate != canonical
                or parsed.username is not None
                or parsed.password is not None
                or "*" in candidate
                or (port is not None and not 1 <= port <= 65535)
            ):
                raise ValueError(
                    "CORS origins must be exact http(s) origins without paths, "
                    "credentials, queries, fragments, or wildcards"
                )
            normalized.append(candidate)
        if len(normalized) != len(set(normalized)):
            raise ValueError("CORS origins must be unique")
        return normalized

    @field_validator("database_url")
    @classmethod
    def require_postgresql_psycopg(cls, value: str) -> str:
        if not value.startswith("postgresql+psycopg://"):
            raise ValueError("DATABASE_URL must use postgresql+psycopg://")
        return value

    @model_validator(mode="after")
    def validate_security_and_policy(self) -> Settings:
        if self.app_env == "production" and (
            self.jwt_secret in _PLACEHOLDER_SECRETS or len(self.jwt_secret) < 32
        ):
            raise ValueError(
                "production JWT_SECRET must be non-placeholder and at least 32 characters"
            )
        if self.outbox_transport == "smtp":
            if not self.smtp_host:
                raise ValueError("SMTP_HOST is required when OUTBOX_TRANSPORT=smtp")
            if not self.smtp_from:
                raise ValueError("SMTP_FROM is required when OUTBOX_TRANSPORT=smtp")
            try:
                TypeAdapter(EmailStr).validate_python(self.smtp_from)
            except ValueError as exc:
                raise ValueError("SMTP_FROM must be a valid email address") from exc
            if bool(self.smtp_username) != bool(self.smtp_password):
                raise ValueError("SMTP_USERNAME and SMTP_PASSWORD must be configured together")

        for policy in self.sla_policies.values():
            policy.validate()
        return self

    @property
    def sla_policies(self) -> dict[IncidentPriority, SLAPolicy]:
        return {
            IncidentPriority.CRITICAL: SLAPolicy(
                response_minutes=self.sla_critical_response_minutes,
                resolution_minutes=self.sla_critical_resolution_minutes,
            ),
            IncidentPriority.HIGH: SLAPolicy(
                response_minutes=self.sla_high_response_minutes,
                resolution_minutes=self.sla_high_resolution_minutes,
            ),
            IncidentPriority.MEDIUM: SLAPolicy(
                response_minutes=self.sla_medium_response_minutes,
                resolution_minutes=self.sla_medium_resolution_minutes,
            ),
            IncidentPriority.LOW: SLAPolicy(
                response_minutes=self.sla_low_response_minutes,
                resolution_minutes=self.sla_low_resolution_minutes,
            ),
        }


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return the process-wide validated settings instance."""

    return Settings()
