"""SLA schemas for request/response validation."""

from datetime import datetime, timedelta
from uuid import UUID

from pydantic import BaseModel

from app.models.sla import SLAStatus


class SLABase(BaseModel):
    """Base SLA schema."""

    response_deadline: datetime
    resolution_deadline: datetime


class SLACreate(SLABase):
    """Schema for creating an SLA."""

    incident_id: UUID


class SLAUpdate(BaseModel):
    """Schema for updating an SLA."""

    status: SLAStatus | None = None
    response_at: datetime | None = None


class SLAInDB(SLABase):
    """Schema for SLA in database."""

    id: UUID
    incident_id: UUID
    status: SLAStatus
    response_at: datetime | None
    paused_at: datetime | None
    paused_duration: timedelta
    breach_notified_at: datetime | None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SLAResponse(SLAInDB):
    """Schema for SLA response."""

    is_response_breached: bool = False
    is_resolution_breached: bool = False
    time_remaining: timedelta | None = None

    class Config:
        from_attributes = True


class SLAPauseRequest(BaseModel):
    """Schema for pausing SLA."""

    pass


class SLAResumeRequest(BaseModel):
    """Schema for resuming SLA."""

    pass
