"""Main FastAPI application."""

from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.config import settings
from app.database import close_db, engine, init_db
from app.telemetry import instrument_app, instrument_sqlalchemy, setup_telemetry

# Set up OpenTelemetry
setup_telemetry()


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Application lifespan events.

    Args:
        app: FastAPI application instance

    Yields:
        None
    """
    # Startup
    await init_db()

    # Instrument SQLAlchemy
    instrument_sqlalchemy(engine)

    yield
    # Shutdown
    await close_db()


# Create FastAPI application
app = FastAPI(
    title="Incident & SLA Tracker",
    description="Production-ready FastAPI application for incident and SLA tracking",
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# Instrument FastAPI with OpenTelemetry
instrument_app(app)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Root endpoint
@app.get("/", tags=["Root"])
async def root() -> dict:
    """Root endpoint.

    Returns:
        dict: Welcome message
    """
    return {
        "message": "Incident & SLA Tracker API",
        "version": "0.1.0",
        "docs": "/api/docs",
    }


# Health check endpoint
@app.get("/health", tags=["Health"])
async def health_check() -> JSONResponse:
    """Health check endpoint.

    Returns:
        JSONResponse: Health status
    """
    return JSONResponse(
        content={
            "status": "healthy",
            "service": "incident-sla-tracker",
            "environment": settings.app_env,
        }
    )


# Import and include routers
from app.api.v1 import incidents  # noqa: E402

app.include_router(incidents.router, prefix="/api/v1", tags=["Incidents"])
