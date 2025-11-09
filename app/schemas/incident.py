"""Incident schemas for request/response validation."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.models.incident import IncidentPriority, IncidentStatus


class IncidentBase(BaseModel):
    """Base incident schema."""

    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1)
    priority: IncidentPriority = Field(default=IncidentPriority.MEDIUM)


class IncidentCreate(IncidentBase):
    """Schema for creating an incident."""

    pass


class IncidentUpdate(BaseModel):
    """Schema for updating an incident."""

    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1)
    status: IncidentStatus | None = None
    priority: IncidentPriority | None = None
    assignee_id: UUID | None = None


class IncidentInDB(IncidentBase):
    """Schema for incident in database."""

    id: UUID
    status: IncidentStatus
    reporter_id: UUID
    assignee_id: UUID | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    closed_at: datetime | None
    deleted_at: datetime | None

    class Config:
        from_attributes = True


class IncidentResponse(IncidentInDB):
    """Schema for incident response."""

    pass


class IncidentWithDetails(IncidentInDB):
    """Schema for incident with related details."""

    reporter: "UserResponse" | None = None
    assignee: "UserResponse" | None = None
    sla: "SLAResponse | None" = None
    comments_count: int = 0
    attachments_count: int = 0

    class Config:
        from_attributes = True


class IncidentListResponse(BaseModel):
    """Schema for paginated incident list."""

    items: list[IncidentResponse]
    total: int
    page: int
    page_size: int
    pages: int


class IncidentStatusUpdate(BaseModel):
    """Schema for updating incident status."""

    status: IncidentStatus


class IncidentAssign(BaseModel):
    """Schema for assigning incident."""

    assignee_id: UUID


# Import to avoid circular import issues
from app.schemas.sla import SLAResponse  # noqa: E402
from app.schemas.user import UserResponse  # noqa: E402

IncidentWithDetails.model_rebuild()
