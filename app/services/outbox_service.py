"""Lease-based, at-least-once delivery for the PostgreSQL outbox."""

from __future__ import annotations

import asyncio
import json
import logging
import smtplib
import ssl
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import EmailMessage
from typing import Protocol
from uuid import UUID

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import Settings
from app.models import OutboxMessage, OutboxStatus

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class OutboxEnvelope:
    id: UUID
    deduplication_key: str
    topic: str
    recipient: str
    payload: dict[str, object]
    attempt: int


class NotificationTransport(Protocol):
    async def send(self, envelope: OutboxEnvelope) -> None: ...


class ConsoleTransport:
    async def send(self, envelope: OutboxEnvelope) -> None:
        logger.info(
            "outbox delivery",
            extra={
                "outbox_id": str(envelope.id),
                "deduplication_key": envelope.deduplication_key,
                "topic": envelope.topic,
                "incident_id": envelope.payload.get("incident_id"),
                "objective": envelope.payload.get("objective"),
                "attempt": envelope.attempt,
            },
        )


class SMTPTransport:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def send(self, envelope: OutboxEnvelope) -> None:
        await asyncio.to_thread(self._send_sync, envelope)

    def _send_sync(self, envelope: OutboxEnvelope) -> None:
        message = EmailMessage()
        message["From"] = self.settings.smtp_from
        message["To"] = envelope.recipient
        message["Subject"] = (
            f"SLA {envelope.payload.get('objective', 'objective')} breached: "
            f"{envelope.payload.get('title', 'incident')}"
        )
        message["X-Idempotency-Key"] = envelope.deduplication_key
        message.set_content(json.dumps(envelope.payload, indent=2, default=str))

        with smtplib.SMTP(
            self.settings.smtp_host,
            self.settings.smtp_port,
            timeout=15,
        ) as client:
            if self.settings.smtp_starttls:
                client.starttls(context=ssl.create_default_context())
            if self.settings.smtp_username:
                client.login(
                    self.settings.smtp_username,
                    self.settings.smtp_password,
                )
            client.send_message(message)


def build_transport(settings: Settings) -> NotificationTransport:
    if settings.outbox_transport == "smtp":
        return SMTPTransport(settings)
    return ConsoleTransport()


def delivery_error_summary(error: Exception) -> str:
    if isinstance(error, smtplib.SMTPResponseException):
        return f"{type(error).__name__}:smtp_code={error.smtp_code}"
    return type(error).__name__


class OutboxService:
    def __init__(self, db: AsyncSession, *, settings: Settings) -> None:
        self.db = db
        self.settings = settings

    async def claim_batch(self, *, now: datetime | None = None) -> list[OutboxEnvelope]:
        if now is not None and (now.tzinfo is None or now.utcoffset() is None):
            raise ValueError("outbox clock must be timezone-aware")
        async with self.db.begin():
            effective_now = now or await self.db.scalar(select(func.clock_timestamp()))
            if (
                effective_now is None
                or effective_now.tzinfo is None
                or effective_now.utcoffset() is None
            ):
                raise RuntimeError("PostgreSQL did not return a timezone-aware clock value")
            lease_cutoff = effective_now - timedelta(seconds=self.settings.outbox_lease_seconds)
            eligible = or_(
                and_(
                    OutboxMessage.status == OutboxStatus.PENDING,
                    OutboxMessage.available_at <= effective_now,
                ),
                and_(
                    OutboxMessage.status == OutboxStatus.PROCESSING,
                    OutboxMessage.claimed_at < lease_cutoff,
                ),
            )
            await self.db.execute(
                update(OutboxMessage)
                .where(
                    OutboxMessage.status == OutboxStatus.PROCESSING,
                    OutboxMessage.claimed_at < lease_cutoff,
                    OutboxMessage.attempts >= self.settings.outbox_max_attempts,
                )
                .values(
                    status=OutboxStatus.DEAD,
                    claimed_at=None,
                    last_error="delivery lease expired after the final allowed attempt",
                )
                .execution_options(synchronize_session=False)
            )
            messages = (
                (
                    await self.db.execute(
                        select(OutboxMessage)
                        .where(
                            eligible,
                            OutboxMessage.attempts < self.settings.outbox_max_attempts,
                        )
                        .order_by(OutboxMessage.available_at, OutboxMessage.id)
                        .limit(self.settings.worker_batch_size)
                        .with_for_update(skip_locked=True)
                    )
                )
                .scalars()
                .all()
            )
            envelopes: list[OutboxEnvelope] = []
            for message in messages:
                message.status = OutboxStatus.PROCESSING
                message.claimed_at = effective_now
                message.attempts += 1
                envelopes.append(
                    OutboxEnvelope(
                        id=message.id,
                        deduplication_key=message.deduplication_key,
                        topic=message.topic,
                        recipient=message.recipient,
                        payload=dict(message.payload),
                        attempt=message.attempts,
                    )
                )
        return envelopes

    async def mark_sent(self, envelope: OutboxEnvelope, *, now: datetime | None = None) -> None:
        if now is not None and (now.tzinfo is None or now.utcoffset() is None):
            raise ValueError("outbox clock must be timezone-aware")
        async with self.db.begin():
            effective_now = now or await self.db.scalar(select(func.clock_timestamp()))
            if (
                effective_now is None
                or effective_now.tzinfo is None
                or effective_now.utcoffset() is None
            ):
                raise RuntimeError("PostgreSQL did not return a timezone-aware clock value")
            message = await self.db.get(OutboxMessage, envelope.id, with_for_update=True)
            if (
                message is None
                or message.status != OutboxStatus.PROCESSING
                or message.attempts != envelope.attempt
            ):
                return
            message.status = OutboxStatus.SENT
            message.sent_at = effective_now
            message.claimed_at = None
            message.last_error = None

    async def mark_failed(
        self,
        envelope: OutboxEnvelope,
        *,
        error: Exception,
        now: datetime | None = None,
    ) -> None:
        if now is not None and (now.tzinfo is None or now.utcoffset() is None):
            raise ValueError("outbox clock must be timezone-aware")
        async with self.db.begin():
            effective_now = now or await self.db.scalar(select(func.clock_timestamp()))
            if (
                effective_now is None
                or effective_now.tzinfo is None
                or effective_now.utcoffset() is None
            ):
                raise RuntimeError("PostgreSQL did not return a timezone-aware clock value")
            message = await self.db.get(OutboxMessage, envelope.id, with_for_update=True)
            if (
                message is None
                or message.status != OutboxStatus.PROCESSING
                or message.attempts != envelope.attempt
            ):
                return
            message.last_error = delivery_error_summary(error)
            message.claimed_at = None
            if message.attempts >= self.settings.outbox_max_attempts:
                message.status = OutboxStatus.DEAD
                return
            delay_seconds = min(2 ** max(message.attempts - 1, 0), 3600)
            message.status = OutboxStatus.PENDING
            message.available_at = effective_now + timedelta(seconds=delay_seconds)

    async def deliver_once(
        self,
        *,
        transport: NotificationTransport,
        now: datetime | None = None,
    ) -> dict[str, int]:
        envelopes = await self.claim_batch(now=now)
        sent = 0
        failed = 0
        for envelope in envelopes:
            try:
                await transport.send(envelope)
            except Exception as exc:
                failed += 1
                logger.error(
                    "outbox delivery failed",
                    extra={
                        "outbox_id": str(envelope.id),
                        "deduplication_key": envelope.deduplication_key,
                        "error_type": type(exc).__name__,
                    },
                )
                await self.mark_failed(envelope, now=now, error=exc)
            else:
                sent += 1
                await self.mark_sent(envelope, now=now)
        return {"claimed": len(envelopes), "sent": sent, "failed": failed}
