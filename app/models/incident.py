"""Incident model for tracking issues and requests."""

from datetime import datetime
from enum import Enum

from sqlalchemy import DateTime, Enum as SQLEnum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, SoftDeleteMixin, TimestampMixin, UUIDMixin


class IncidentStatus(str, Enum):
    """Incident status enumeration."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class IncidentPriority(str, Enum):
    """Incident priority enumeration."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Incident(Base, UUIDMixin, TimestampMixin, SoftDeleteMixin):
    """Incident model for tracking issues and service requests."""

    __tablename__ = "incidents"

    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[IncidentStatus] = mapped_column(
        SQLEnum(IncidentStatus, name="incident_status"),
        default=IncidentStatus.OPEN,
        nullable=False,
    )
    priority: Mapped[IncidentPriority] = mapped_column(
        SQLEnum(IncidentPriority, name="incident_priority"),
        default=IncidentPriority.MEDIUM,
        nullable=False,
    )

    # Foreign Keys
    reporter_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False
    )
    assignee_id: Mapped[UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True
    )

    # Timestamps
    resolved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    closed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    reporter: Mapped["User"] = relationship(
        "User", back_populates="reported_incidents", foreign_keys=[reporter_id]
    )
    assignee: Mapped["User | None"] = relationship(
        "User", back_populates="assigned_incidents", foreign_keys=[assignee_id]
    )
    sla: Mapped["SLA | None"] = relationship(
        "SLA", back_populates="incident", uselist=False, cascade="all, delete-orphan"
    )
    comments: Mapped[list["Comment"]] = relationship(
        "Comment", back_populates="incident", cascade="all, delete-orphan"
    )
    attachments: Mapped[list["Attachment"]] = relationship(
        "Attachment", back_populates="incident", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Incident(id={self.id}, title={self.title}, status={self.status}, priority={self.priority})>"
