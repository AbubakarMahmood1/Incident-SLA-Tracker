"""Append-only incident event ledger."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    Identity,
    Index,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain import IncidentEventType
from app.models.base import Base

if TYPE_CHECKING:
    from app.models.incident import Incident


class IncidentEvent(Base):
    __tablename__ = "incident_events"
    __table_args__ = (
        CheckConstraint("effective_at <= occurred_at", name="effective_not_after_observation"),
        CheckConstraint("source IN ('api', 'worker')", name="source_known"),
        CheckConstraint("jsonb_typeof(payload) = 'object'", name="payload_is_object"),
        Index(
            "uq_incident_events_response_breach",
            "incident_id",
            unique=True,
            postgresql_where=text("event_type = 'sla.response_breached'"),
        ),
        Index(
            "uq_incident_events_resolution_breach",
            "incident_id",
            unique=True,
            postgresql_where=text("event_type = 'sla.resolution_breached'"),
        ),
    )

    sequence: Mapped[int] = mapped_column(BigInteger, Identity(always=False), primary_key=True)
    event_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), default=uuid.uuid4, unique=True, nullable=False
    )
    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    event_type: Mapped[IncidentEventType] = mapped_column(
        Enum(
            IncidentEventType,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
            length=64,
        ),
        nullable=False,
    )
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=True
    )
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    effective_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, nullable=False)
    source: Mapped[str] = mapped_column(String(32), nullable=False)

    incident: Mapped[Incident] = relationship(back_populates="events", lazy="raise")
