"""Immutable policy snapshot and objective progress for an incident."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.domain import ObjectiveOutcome, SLAObjective, SLAState, objective_outcome
from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.incident import Incident


class SLA(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "slas"
    __table_args__ = (
        CheckConstraint("response_target_seconds > 0", name="response_target_positive"),
        CheckConstraint("resolution_target_seconds > 0", name="resolution_target_positive"),
        CheckConstraint(
            "resolution_target_seconds >= response_target_seconds",
            name="targets_ordered",
        ),
        CheckConstraint("response_deadline > started_at", name="response_after_start"),
        CheckConstraint(
            "resolution_deadline >= response_deadline", name="resolution_after_response"
        ),
        CheckConstraint(
            "resolved_at IS NULL OR acknowledged_at IS NOT NULL",
            name="resolution_requires_response",
        ),
        CheckConstraint(
            "acknowledged_at IS NULL OR acknowledged_at >= started_at",
            name="acknowledgement_not_before_start",
        ),
        CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= acknowledged_at",
            name="resolution_not_before_acknowledgement",
        ),
        CheckConstraint(
            "response_breached_at IS NULL OR response_breached_at = response_deadline",
            name="response_breach_uses_deadline",
        ),
        CheckConstraint(
            "resolution_breached_at IS NULL OR resolution_breached_at = resolution_deadline",
            name="resolution_breach_uses_deadline",
        ),
        CheckConstraint(
            "acknowledged_at IS NULL OR "
            "(acknowledged_at <= response_deadline AND response_breached_at IS NULL) OR "
            "(acknowledged_at > response_deadline "
            "AND response_breached_at IS NOT NULL "
            "AND response_breached_at = response_deadline)",
            name="response_outcome_consistent",
        ),
        CheckConstraint(
            "resolved_at IS NULL OR "
            "(resolved_at <= resolution_deadline AND resolution_breached_at IS NULL) OR "
            "(resolved_at > resolution_deadline "
            "AND resolution_breached_at IS NOT NULL "
            "AND resolution_breached_at = resolution_deadline)",
            name="resolution_outcome_consistent",
        ),
    )

    incident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("incidents.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    response_target_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    resolution_target_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    response_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    resolution_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    response_breached_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    resolution_breached_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    incident: Mapped[Incident] = relationship(back_populates="sla", lazy="raise")

    def as_domain(self) -> SLAState:
        return SLAState(
            started_at=self.started_at,
            response_deadline=self.response_deadline,
            resolution_deadline=self.resolution_deadline,
            acknowledged_at=self.acknowledged_at,
            resolved_at=self.resolved_at,
            response_breached_at=self.response_breached_at,
            resolution_breached_at=self.resolution_breached_at,
        )

    @property
    def response_outcome(self) -> ObjectiveOutcome:
        return objective_outcome(self.as_domain(), SLAObjective.RESPONSE)

    @property
    def resolution_outcome(self) -> ObjectiveOutcome:
        return objective_outcome(self.as_domain(), SLAObjective.RESOLUTION)
