"""FastAPI application factory."""

from __future__ import annotations

import re
import uuid
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import RequestResponseEndpoint

from app import __version__
from app.api.v1 import auth, incidents
from app.config import get_settings
from app.database import database_is_ready, dispose_database
from app.logging import configure_logging
from app.services.errors import ServiceError

_REQUEST_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    yield
    await dispose_database()


def create_app() -> FastAPI:
    settings = get_settings()
    configure_logging(settings.log_level)
    application = FastAPI(
        title="Incident SLA Ledger",
        description=(
            "Auditable incident acknowledgement, resolution, breach, and notification "
            "transitions backed by PostgreSQL."
        ),
        version=__version__,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.app_env != "production" else None,
        redoc_url=None,
        openapi_url=("/api/openapi.json" if settings.app_env != "production" else None),
    )

    if settings.cors_origins:
        application.add_middleware(
            CORSMiddleware,
            allow_origins=settings.cors_origins,
            allow_credentials=False,
            allow_methods=["GET", "POST"],
            allow_headers=["Authorization", "Content-Type", "Idempotency-Key"],
        )

    @application.middleware("http")
    async def request_id(request: Request, call_next: RequestResponseEndpoint) -> Response:
        supplied = request.headers.get("X-Request-ID", "")
        request_id_value = supplied if _REQUEST_ID.fullmatch(supplied) else str(uuid.uuid4())
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id_value
        return response

    @application.exception_handler(ServiceError)
    async def service_error_handler(_: Request, exc: ServiceError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": str(exc)}},
        )

    @application.get("/health/live", tags=["Health"])
    async def live() -> dict[str, str]:
        return {"status": "live", "version": __version__}

    @application.get("/health/ready", tags=["Health"])
    async def ready() -> JSONResponse:
        ready_state = await database_is_ready()
        return JSONResponse(
            status_code=200 if ready_state else 503,
            content={"status": "ready" if ready_state else "not_ready"},
        )

    application.include_router(auth.router, prefix="/api/v1")
    application.include_router(incidents.router, prefix="/api/v1")
    return application


app = create_app()
