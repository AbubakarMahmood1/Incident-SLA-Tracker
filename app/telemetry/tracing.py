"""OpenTelemetry tracing configuration."""

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.celery import CeleryInstrumentor
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor

from app.config import settings


def setup_telemetry() -> None:
    """Set up OpenTelemetry instrumentation for the application."""
    # Create resource with service information
    resource = Resource.create(
        {
            "service.name": settings.otel_service_name,
            "service.version": "0.1.0",
            "deployment.environment": settings.app_env,
        }
    )

    # Set up tracer provider
    tracer_provider = TracerProvider(resource=resource)

    # Configure OTLP exporter
    otlp_exporter = OTLPSpanExporter(
        endpoint=settings.otel_exporter_otlp_endpoint,
        insecure=True,  # Use insecure for local development
    )

    # Add span processor
    tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    # Set global tracer provider
    trace.set_tracer_provider(tracer_provider)


def instrument_app(app: "FastAPI") -> None:  # type: ignore # noqa: F821
    """Instrument FastAPI application with OpenTelemetry.

    Args:
        app: FastAPI application instance
    """
    # Instrument FastAPI
    FastAPIInstrumentor.instrument_app(app)


def instrument_sqlalchemy(engine: "Engine") -> None:  # type: ignore # noqa: F821
    """Instrument SQLAlchemy engine with OpenTelemetry.

    Args:
        engine: SQLAlchemy engine
    """
    SQLAlchemyInstrumentor().instrument(engine=engine.sync_engine)


def instrument_celery() -> None:
    """Instrument Celery with OpenTelemetry."""
    CeleryInstrumentor().instrument()


def get_tracer(name: str) -> trace.Tracer:
    """Get a tracer instance.

    Args:
        name: Tracer name (typically module name)

    Returns:
        trace.Tracer: Tracer instance
    """
    return trace.get_tracer(name)
