"""Incident event ledger response schemas."""

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from app.domain import IncidentEventType


class IncidentEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    sequence: int
    event_id: UUID
    incident_id: UUID
    event_type: IncidentEventType
    actor_id: UUID | None
    occurred_at: datetime
    effective_at: datetime
    payload: dict[str, Any]
    source: str
