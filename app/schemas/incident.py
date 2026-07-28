"""Incident command and query schemas."""

from __future__ import annotations

import unicodedata
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.domain import IncidentPriority, IncidentStatus, ObjectiveOutcome
from app.schemas.auth import UserSummary


def _clean_text(value: str, *, field: str) -> str:
    normalized = unicodedata.normalize("NFC", value).strip()
    if not normalized:
        raise ValueError(f"{field} must not be blank")
    if any(unicodedata.category(char) in {"Cc", "Cs"} for char in normalized):
        raise ValueError(f"{field} contains control or surrogate characters")
    return normalized


class IncidentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=255)
    description: str = Field(min_length=1, max_length=10000)
    priority: IncidentPriority

    @field_validator("title")
    @classmethod
    def clean_title(cls, value: str) -> str:
        return _clean_text(value, field="title")

    @field_validator("description")
    @classmethod
    def clean_description(cls, value: str) -> str:
        return _clean_text(value, field="description")


class IncidentAssign(BaseModel):
    model_config = ConfigDict(extra="forbid")

    assignee_id: UUID


class SLAResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    response_target_seconds: int
    resolution_target_seconds: int
    started_at: datetime
    response_deadline: datetime
    resolution_deadline: datetime
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    response_breached_at: datetime | None
    resolution_breached_at: datetime | None
    response_outcome: ObjectiveOutcome
    resolution_outcome: ObjectiveOutcome


class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    description: str
    priority: IncidentPriority
    status: IncidentStatus
    revision: int
    reporter_id: UUID
    assignee_id: UUID | None
    acknowledged_at: datetime | None
    resolved_at: datetime | None
    closed_at: datetime | None
    created_at: datetime
    updated_at: datetime
    reporter: UserSummary
    assignee: UserSummary | None
    sla: SLAResponse


class IncidentListResponse(BaseModel):
    items: list[IncidentResponse]
    total: int
    offset: int
    limit: int


class IncidentTimelineResponse(BaseModel):
    incident_id: UUID
    events: list[IncidentEventResponse]


from app.schemas.event import IncidentEventResponse  # noqa: E402

IncidentTimelineResponse.model_rebuild()
