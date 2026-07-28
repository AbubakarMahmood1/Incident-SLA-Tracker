"""Durable command receipts for idempotent API mutations."""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    String,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, UUIDPrimaryKeyMixin


class CommandReceipt(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "command_receipts"
    __table_args__ = (
        UniqueConstraint("actor_id", "idempotency_key", name="actor_idempotency_key"),
        CheckConstraint(
            "(incident_id IS NULL AND event_sequence IS NULL) OR "
            "(incident_id IS NOT NULL AND event_sequence IS NOT NULL)",
            name="result_complete",
        ),
    )

    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False
    )
    idempotency_key: Mapped[str] = mapped_column(String(128), nullable=False)
    command_type: Mapped[str] = mapped_column(String(64), nullable=False)
    request_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    incident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("incidents.id", ondelete="RESTRICT"), nullable=True
    )
    event_sequence: Mapped[int | None] = mapped_column(
        BigInteger,
        ForeignKey("incident_events.sequence", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
