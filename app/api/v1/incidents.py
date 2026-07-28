"""Access-controlled incident commands and queries."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_idempotency_key
from app.config import Settings, get_settings
from app.database import get_db
from app.domain import IncidentPriority, IncidentStatus
from app.models import User
from app.schemas import (
    IncidentAssign,
    IncidentCreate,
    IncidentEventResponse,
    IncidentListResponse,
    IncidentResponse,
    IncidentTimelineResponse,
)
from app.services.incident_service import IncidentService

router = APIRouter(prefix="/incidents", tags=["Incidents"])


def service(
    db: AsyncSession,
    settings: Settings,
) -> IncidentService:
    return IncidentService(db, settings=settings)


@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    data: IncidentCreate,
    actor: Annotated[User, Depends(get_current_user)],
    idempotency_key: Annotated[str, Depends(get_idempotency_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IncidentResponse:
    incident = await service(db, settings).create_incident(
        data=data, actor=actor, idempotency_key=idempotency_key
    )
    return IncidentResponse.model_validate(incident)


@router.get("", response_model=IncidentListResponse)
async def list_incidents(
    actor: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=50, ge=1, le=200),
    status_filter: IncidentStatus | None = Query(default=None, alias="status"),
    priority: IncidentPriority | None = None,
    search: str | None = Query(default=None, max_length=255),
) -> IncidentListResponse:
    rows, total = await service(db, settings).list_incidents(
        actor=actor,
        offset=offset,
        limit=limit,
        status=status_filter,
        priority=priority,
        search=search,
    )
    return IncidentListResponse(
        items=[IncidentResponse.model_validate(row) for row in rows],
        total=total,
        offset=offset,
        limit=limit,
    )


@router.get("/{incident_id}", response_model=IncidentResponse)
async def get_incident(
    incident_id: UUID,
    actor: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IncidentResponse:
    row = await service(db, settings).get_incident(incident_id=incident_id, actor=actor)
    return IncidentResponse.model_validate(row)


@router.post("/{incident_id}/assign", response_model=IncidentResponse)
async def assign_incident(
    incident_id: UUID,
    data: IncidentAssign,
    actor: Annotated[User, Depends(get_current_user)],
    idempotency_key: Annotated[str, Depends(get_idempotency_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IncidentResponse:
    row = await service(db, settings).assign_incident(
        incident_id=incident_id,
        assignee_id=data.assignee_id,
        actor=actor,
        idempotency_key=idempotency_key,
    )
    return IncidentResponse.model_validate(row)


@router.post("/{incident_id}/acknowledge", response_model=IncidentResponse)
async def acknowledge_incident(
    incident_id: UUID,
    actor: Annotated[User, Depends(get_current_user)],
    idempotency_key: Annotated[str, Depends(get_idempotency_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IncidentResponse:
    row = await service(db, settings).acknowledge_incident(
        incident_id=incident_id,
        actor=actor,
        idempotency_key=idempotency_key,
    )
    return IncidentResponse.model_validate(row)


@router.post("/{incident_id}/resolve", response_model=IncidentResponse)
async def resolve_incident(
    incident_id: UUID,
    actor: Annotated[User, Depends(get_current_user)],
    idempotency_key: Annotated[str, Depends(get_idempotency_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IncidentResponse:
    row = await service(db, settings).resolve_incident(
        incident_id=incident_id,
        actor=actor,
        idempotency_key=idempotency_key,
    )
    return IncidentResponse.model_validate(row)


@router.post("/{incident_id}/close", response_model=IncidentResponse)
async def close_incident(
    incident_id: UUID,
    actor: Annotated[User, Depends(get_current_user)],
    idempotency_key: Annotated[str, Depends(get_idempotency_key)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IncidentResponse:
    row = await service(db, settings).close_incident(
        incident_id=incident_id,
        actor=actor,
        idempotency_key=idempotency_key,
    )
    return IncidentResponse.model_validate(row)


@router.get("/{incident_id}/events", response_model=IncidentTimelineResponse)
async def get_timeline(
    incident_id: UUID,
    actor: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> IncidentTimelineResponse:
    events = await service(db, settings).timeline(incident_id=incident_id, actor=actor)
    return IncidentTimelineResponse(
        incident_id=incident_id,
        events=[IncidentEventResponse.model_validate(event) for event in events],
    )
