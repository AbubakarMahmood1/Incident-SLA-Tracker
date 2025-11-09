"""Unit tests for incident service."""

import pytest

from app.models import IncidentPriority, IncidentStatus
from app.schemas import IncidentCreate
from app.services.incident_service import IncidentService


@pytest.mark.asyncio
async def test_create_incident(db_session, test_user):
    """Test creating an incident with automatic SLA assignment."""
    service = IncidentService(db_session)

    incident_data = IncidentCreate(
        title="Test Incident",
        description="This is a test incident",
        priority=IncidentPriority.HIGH,
    )

    incident = await service.create_incident(incident_data, test_user.id)

    assert incident.id is not None
    assert incident.title == "Test Incident"
    assert incident.priority == IncidentPriority.HIGH
    assert incident.status == IncidentStatus.OPEN
    assert incident.reporter_id == test_user.id
    assert incident.sla is not None


@pytest.mark.asyncio
async def test_get_incident(db_session, test_user):
    """Test retrieving an incident by ID."""
    service = IncidentService(db_session)

    # Create incident
    incident_data = IncidentCreate(
        title="Test Incident",
        description="This is a test incident",
        priority=IncidentPriority.MEDIUM,
    )
    created_incident = await service.create_incident(incident_data, test_user.id)

    # Retrieve incident
    retrieved_incident = await service.get_incident(created_incident.id)

    assert retrieved_incident is not None
    assert retrieved_incident.id == created_incident.id
    assert retrieved_incident.title == "Test Incident"


@pytest.mark.asyncio
async def test_list_incidents(db_session, test_user):
    """Test listing incidents with pagination."""
    service = IncidentService(db_session)

    # Create multiple incidents
    for i in range(5):
        incident_data = IncidentCreate(
            title=f"Test Incident {i}",
            description=f"Description {i}",
            priority=IncidentPriority.LOW,
        )
        await service.create_incident(incident_data, test_user.id)

    # List incidents
    incidents, total = await service.list_incidents(skip=0, limit=10)

    assert total >= 5
    assert len(incidents) >= 5


@pytest.mark.asyncio
async def test_update_incident_status(db_session, test_user):
    """Test updating incident status."""
    service = IncidentService(db_session)

    # Create incident
    incident_data = IncidentCreate(
        title="Test Incident",
        description="This is a test incident",
        priority=IncidentPriority.CRITICAL,
    )
    incident = await service.create_incident(incident_data, test_user.id)

    # Update status
    updated_incident = await service.update_status(
        incident.id, IncidentStatus.RESOLVED
    )

    assert updated_incident is not None
    assert updated_incident.status == IncidentStatus.RESOLVED
    assert updated_incident.resolved_at is not None


@pytest.mark.asyncio
async def test_delete_incident(db_session, test_user):
    """Test soft deleting an incident."""
    service = IncidentService(db_session)

    # Create incident
    incident_data = IncidentCreate(
        title="Test Incident",
        description="This is a test incident",
        priority=IncidentPriority.LOW,
    )
    incident = await service.create_incident(incident_data, test_user.id)

    # Delete incident
    deleted = await service.delete_incident(incident.id)

    assert deleted is True

    # Try to retrieve deleted incident
    retrieved_incident = await service.get_incident(incident.id)
    assert retrieved_incident is None  # Soft deleted, so not returned
