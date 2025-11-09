"""SLA model for tracking service level agreements."""

from datetime import datetime, timedelta
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, Interval
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class SLAStatus(str, Enum):
    """SLA status enumeration."""

    ACTIVE = "active"
    PAUSED = "paused"
    BREACHED = "breached"
    MET = "met"


class SLA(Base, UUIDMixin, TimestampMixin):
    """SLA model for tracking service level agreement compliance."""

    __tablename__ = "slas"

    # Foreign Key
    incident_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id"), unique=True, nullable=False
    )

    # Deadlines
    response_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    resolution_deadline: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )

    # Status
    status: Mapped[SLAStatus] = mapped_column(
        SQLEnum(SLAStatus, name="sla_status"), default=SLAStatus.ACTIVE, nullable=False
    )

    # Response tracking
    response_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Pause tracking
    paused_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    paused_duration: Mapped[timedelta] = mapped_column(
        Interval, default=timedelta(0), nullable=False
    )

    # Breach tracking
    breach_notified_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    incident: Mapped["Incident"] = relationship("Incident", back_populates="sla")

    def __repr__(self) -> str:
        return f"<SLA(id={self.id}, incident_id={self.incident_id}, status={self.status})>"

    @property
    def is_response_breached(self) -> bool:
        """Check if response SLA is breached."""
        if self.response_at:
            return False
        now = datetime.now(self.response_deadline.tzinfo)
        return now > self.response_deadline

    @property
    def is_resolution_breached(self) -> bool:
        """Check if resolution SLA is breached."""
        if self.status == SLAStatus.MET:
            return False
        now = datetime.now(self.resolution_deadline.tzinfo)
        return now > self.resolution_deadline

    def get_time_remaining(self, deadline_type: str = "resolution") -> timedelta:
        """Get time remaining until deadline.

        Args:
            deadline_type: Either 'response' or 'resolution'

        Returns:
            timedelta: Time remaining (negative if breached)
        """
        now = datetime.now(self.resolution_deadline.tzinfo)
        if deadline_type == "response":
            return self.response_deadline - now
        return self.resolution_deadline - now
