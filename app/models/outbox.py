"""Durable notification outbox."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class OutboxStatus(StrEnum):
    PENDING = "pending"
    PROCESSING = "processing"
    SENT = "sent"
    DEAD = "dead"


class OutboxMessage(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "outbox_messages"
    __table_args__ = (
        CheckConstraint("attempts >= 0", name="attempts_nonnegative"),
        CheckConstraint("jsonb_typeof(payload) = 'object'", name="payload_is_object"),
        CheckConstraint(
            "(status = 'pending' AND claimed_at IS NULL AND sent_at IS NULL) OR "
            "(status = 'processing' AND claimed_at IS NOT NULL AND sent_at IS NULL) OR "
            "(status = 'sent' AND claimed_at IS NULL AND sent_at IS NOT NULL) OR "
            "(status = 'dead' AND claimed_at IS NULL AND sent_at IS NULL)",
            name="state_consistent",
        ),
    )

    event_sequence: Mapped[int] = mapped_column(
        ForeignKey("incident_events.sequence", ondelete="CASCADE"), nullable=False
    )
    deduplication_key: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    topic: Mapped[str] = mapped_column(String(100), nullable=False)
    recipient: Mapped[str] = mapped_column(String(320), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    status: Mapped[OutboxStatus] = mapped_column(
        Enum(
            OutboxStatus,
            native_enum=False,
            create_constraint=True,
            validate_strings=True,
            values_callable=lambda enum: [member.value for member in enum],
            length=16,
        ),
        default=OutboxStatus.PENDING,
        nullable=False,
        index=True,
    )
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    available_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    claimed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
