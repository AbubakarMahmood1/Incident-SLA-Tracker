"""Incident API endpoints."""

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_active_user
from app.database import get_db
from app.models import IncidentPriority, IncidentStatus, User
from app.schemas import (
    IncidentAssign,
    IncidentCreate,
    IncidentListResponse,
    IncidentResponse,
    IncidentStatusUpdate,
    IncidentUpdate,
    IncidentWithDetails,
)
from app.services.incident_service import IncidentService

router = APIRouter()


@router.post("/incidents", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
async def create_incident(
    incident_data: IncidentCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IncidentResponse:
    """Create a new incident.

    Args:
        incident_data: Incident creation data
        current_user: Current authenticated user
        db: Database session

    Returns:
        IncidentResponse: Created incident
    """
    service = IncidentService(db)
    incident = await service.create_incident(incident_data, current_user.id)
    return IncidentResponse.model_validate(incident)


@router.get("/incidents", response_model=IncidentListResponse)
async def list_incidents(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    status: IncidentStatus | None = None,
    priority: IncidentPriority | None = None,
    assignee_id: UUID | None = None,
    reporter_id: UUID | None = None,
    search: str | None = None,
) -> IncidentListResponse:
    """List incidents with filters and pagination.

    Args:
        current_user: Current authenticated user
        db: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        status: Filter by status
        priority: Filter by priority
        assignee_id: Filter by assignee
        reporter_id: Filter by reporter
        search: Search in title and description

    Returns:
        IncidentListResponse: Paginated list of incidents
    """
    service = IncidentService(db)
    incidents, total = await service.list_incidents(
        skip=skip,
        limit=limit,
        status=status,
        priority=priority,
        assignee_id=assignee_id,
        reporter_id=reporter_id,
        search=search,
    )

    return IncidentListResponse(
        items=[IncidentResponse.model_validate(inc) for inc in incidents],
        total=total,
        page=skip // limit + 1,
        page_size=limit,
        pages=(total + limit - 1) // limit if total > 0 else 0,
    )


@router.get("/incidents/{incident_id}", response_model=IncidentWithDetails)
async def get_incident(
    incident_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IncidentWithDetails:
    """Get incident by ID.

    Args:
        incident_id: Incident ID
        current_user: Current authenticated user
        db: Database session

    Returns:
        IncidentWithDetails: Incident details

    Raises:
        HTTPException: If incident not found
    """
    service = IncidentService(db)
    incident = await service.get_incident(incident_id)

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    return IncidentWithDetails.model_validate(incident)


@router.patch("/incidents/{incident_id}", response_model=IncidentResponse)
async def update_incident(
    incident_id: UUID,
    incident_data: IncidentUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IncidentResponse:
    """Update an incident.

    Args:
        incident_id: Incident ID
        incident_data: Update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        IncidentResponse: Updated incident

    Raises:
        HTTPException: If incident not found
    """
    service = IncidentService(db)
    incident = await service.update_incident(incident_id, incident_data)

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    return IncidentResponse.model_validate(incident)


@router.post("/incidents/{incident_id}/assign", response_model=IncidentResponse)
async def assign_incident(
    incident_id: UUID,
    assign_data: IncidentAssign,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IncidentResponse:
    """Assign an incident to a user.

    Args:
        incident_id: Incident ID
        assign_data: Assignment data
        current_user: Current authenticated user
        db: Database session

    Returns:
        IncidentResponse: Updated incident

    Raises:
        HTTPException: If incident not found
    """
    service = IncidentService(db)
    incident = await service.assign_incident(incident_id, assign_data.assignee_id)

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    return IncidentResponse.model_validate(incident)


@router.post("/incidents/{incident_id}/status", response_model=IncidentResponse)
async def update_incident_status(
    incident_id: UUID,
    status_data: IncidentStatusUpdate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> IncidentResponse:
    """Update incident status.

    Args:
        incident_id: Incident ID
        status_data: Status update data
        current_user: Current authenticated user
        db: Database session

    Returns:
        IncidentResponse: Updated incident

    Raises:
        HTTPException: If incident not found
    """
    service = IncidentService(db)
    incident = await service.update_status(incident_id, status_data.status)

    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )

    return IncidentResponse.model_validate(incident)


@router.delete("/incidents/{incident_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_incident(
    incident_id: UUID,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> None:
    """Delete an incident (soft delete).

    Args:
        incident_id: Incident ID
        current_user: Current authenticated user
        db: Database session

    Raises:
        HTTPException: If incident not found
    """
    service = IncidentService(db)
    deleted = await service.delete_incident(incident_id)

    if not deleted:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Incident not found",
        )


@router.get("/incidents/stats/summary")
async def get_incident_stats(
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    user_id: UUID | None = None,
) -> dict:
    """Get incident statistics.

    Args:
        current_user: Current authenticated user
        db: Database session
        user_id: Optional user ID to filter stats

    Returns:
        dict: Statistics
    """
    service = IncidentService(db)
    stats = await service.get_incident_stats(user_id)
    return stats
