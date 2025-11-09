"""Application configuration using Pydantic Settings."""

from typing import List

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(default="incident-sla-tracker")
    app_env: str = Field(default="development")
    debug: bool = Field(default=False)
    secret_key: str = Field(default="change-this-secret-key")
    algorithm: str = Field(default="HS256")
    access_token_expire_minutes: int = Field(default=30)

    # Server
    host: str = Field(default="0.0.0.0")
    port: int = Field(default=8000)

    # Database
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/incident_tracker"
    )
    test_database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/incident_tracker_test"
    )
    database_pool_size: int = Field(default=10)
    database_max_overflow: int = Field(default=20)

    # Redis/Celery
    redis_url: str = Field(default="redis://localhost:6379/0")
    celery_broker_url: str = Field(default="redis://localhost:6379/0")
    celery_result_backend: str = Field(default="redis://localhost:6379/1")

    # Email
    smtp_host: str = Field(default="smtp.gmail.com")
    smtp_port: int = Field(default=587)
    smtp_user: str = Field(default="")
    smtp_password: str = Field(default="")
    email_from: str = Field(default="noreply@incident-tracker.com")
    email_from_name: str = Field(default="Incident SLA Tracker")

    # SLA Defaults (in hours)
    sla_critical_response: int = Field(default=1)
    sla_critical_resolution: int = Field(default=4)
    sla_high_response: int = Field(default=4)
    sla_high_resolution: int = Field(default=24)
    sla_medium_response: int = Field(default=8)
    sla_medium_resolution: int = Field(default=72)
    sla_low_response: int = Field(default=24)
    sla_low_resolution: int = Field(default=168)

    # OpenTelemetry
    otel_exporter_otlp_endpoint: str = Field(default="http://localhost:4317")
    otel_service_name: str = Field(default="incident-sla-tracker")
    otel_traces_exporter: str = Field(default="otlp")
    otel_metrics_exporter: str = Field(default="otlp")
    otel_logs_exporter: str = Field(default="otlp")

    # File Upload
    upload_dir: str = Field(default="./uploads")
    max_upload_size: int = Field(default=10485760)  # 10MB
    allowed_extensions: str = Field(
        default="pdf,png,jpg,jpeg,gif,txt,doc,docx,xls,xlsx"
    )

    # CORS
    cors_origins: str = Field(default="http://localhost:3000,http://localhost:8000")

    # Logging
    log_level: str = Field(default="INFO")
    log_format: str = Field(default="json")

    @field_validator("cors_origins")
    @classmethod
    def parse_cors_origins(cls, v: str) -> List[str]:
        """Parse comma-separated CORS origins."""
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",") if origin.strip()]
        return v

    @field_validator("allowed_extensions")
    @classmethod
    def parse_allowed_extensions(cls, v: str) -> List[str]:
        """Parse comma-separated file extensions."""
        if isinstance(v, str):
            return [ext.strip().lower() for ext in v.split(",") if ext.strip()]
        return v

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.app_env == "development"

    @property
    def is_production(self) -> bool:
        """Check if running in production mode."""
        return self.app_env == "production"

    def get_sla_deadlines(self, priority: str) -> dict[str, int]:
        """Get SLA response and resolution deadlines for a priority level.

        Args:
            priority: Priority level (critical, high, medium, low)

        Returns:
            Dictionary with response_hours and resolution_hours
        """
        priority_lower = priority.lower()

        if priority_lower == "critical":
            return {
                "response_hours": self.sla_critical_response,
                "resolution_hours": self.sla_critical_resolution,
            }
        elif priority_lower == "high":
            return {
                "response_hours": self.sla_high_response,
                "resolution_hours": self.sla_high_resolution,
            }
        elif priority_lower == "medium":
            return {
                "response_hours": self.sla_medium_response,
                "resolution_hours": self.sla_medium_resolution,
            }
        elif priority_lower == "low":
            return {
                "response_hours": self.sla_low_response,
                "resolution_hours": self.sla_low_resolution,
            }
        else:
            # Default to medium
            return {
                "response_hours": self.sla_medium_response,
                "resolution_hours": self.sla_medium_resolution,
            }


# Global settings instance
settings = Settings()
