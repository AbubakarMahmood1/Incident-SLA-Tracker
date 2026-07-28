"""Incident aggregate root."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain import IncidentPriority, IncidentStatus
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.event import IncidentEvent
    from app.models.sla import SLA
    from app.models.user import User


class Incident(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "incidents"
    __table_args__ = (
        CheckConstraint("revision >= 1", name="revision_positive"),
        CheckConstraint(
            "(status = 'open' AND acknowledged_at IS NULL AND resolved_at IS NULL "
            "AND closed_at IS NULL) OR "
            "(status = 'acknowledged' AND acknowledged_at IS NOT NULL "
            "AND resolved_at IS NULL AND closed_at IS NULL) OR "
            "(status = 'resolved' AND acknowledged_at IS NOT NULL "
            "AND resolved_at IS NOT NULL AND closed_at IS NULL) OR "
            "(status = 'closed' AND acknowledged_at IS NOT NULL "
            "AND resolved_at IS NOT NULL AND closed_at IS NOT NULL)",
            name="lifecycle_consistent",
        ),
        CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= acknowledged_at",
            name="resolution_not_before_acknowledgement",
        ),
        CheckConstraint(
            "closed_at IS NULL OR closed_at >= resolved_at",
            name="closure_not_before_resolution",
        ),
    )

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    priority: Mapped[IncidentPriority] = mapped_column(
        Enum(
            IncidentPriority,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
            length=16,
        ),
        nullable=False,
    )
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(
            IncidentStatus,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
            length=32,
        ),
        default=IncidentStatus.OPEN,
        nullable=False,
        index=True,
    )
    revision: Mapped[int] = mapped_column(Integer, default=1, nullable=False)

    reporter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )

    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    reporter: Mapped[User] = relationship(
        back_populates="reported_incidents", foreign_keys=[reporter_id], lazy="raise"
    )
    assignee: Mapped[User | None] = relationship(
        back_populates="assigned_incidents", foreign_keys=[assignee_id], lazy="raise"
    )
    sla: Mapped[SLA] = relationship(
        back_populates="incident",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="raise",
    )
    events: Mapped[list[IncidentEvent]] = relationship(
        back_populates="incident", order_by="IncidentEvent.sequence", lazy="raise"
    )
