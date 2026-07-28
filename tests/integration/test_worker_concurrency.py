import asyncio
import os
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.domain import IncidentEventType, IncidentPriority
from app.models import IncidentEvent, OutboxMessage, OutboxStatus
from app.schemas import IncidentCreate
from app.services.incident_service import IncidentService
from app.services.outbox_service import OutboxService
from app.services.sla_service import SLAEvaluationService
from app.utils import FixedClock

pytestmark = pytest.mark.postgres

START = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def settings() -> Settings:
    return Settings(
        app_env="test",
        jwt_secret="x" * 40,
        database_url=os.environ["TEST_DATABASE_URL"],
        sla_critical_response_minutes=1,
        sla_critical_resolution_minutes=2,
    )


async def test_competing_evaluators_publish_each_breach_once(db, users) -> None:
    config = settings()
    incident = await IncidentService(db, settings=config, clock=FixedClock(START)).create_incident(
        data=IncidentCreate(
            title="Concurrency probe",
            description="Two workers evaluate the same due objectives",
            priority=IncidentPriority.CRITICAL,
        ),
        actor=users["reporter"],
        idempotency_key="create-concurrency-001",
    )
    await IncidentService(db, settings=config, clock=FixedClock(START)).assign_incident(
        incident_id=incident.id,
        assignee_id=users["assignee"].id,
        actor=users["admin"],
        idempotency_key="assign-concurrency-001",
    )

    engine = create_async_engine(config.database_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    now = START + timedelta(minutes=3)

    async def run_worker() -> int:
        async with factory() as session:
            summary = await SLAEvaluationService(session).evaluate_once(now=now, batch_size=10)
            return summary.objectives_breached

    counts = await asyncio.gather(run_worker(), run_worker())
    assert sum(counts) == 2

    async with factory() as session:
        breach_events = await session.scalar(
            select(func.count(IncidentEvent.sequence)).where(
                IncidentEvent.incident_id == incident.id,
                IncidentEvent.event_type.in_(
                    [
                        IncidentEventType.RESPONSE_BREACHED,
                        IncidentEventType.RESOLUTION_BREACHED,
                    ]
                ),
            )
        )
        outbox = await session.scalar(select(func.count(OutboxMessage.id)))
    await engine.dispose()
    assert breach_events == 2
    assert outbox == 2


async def test_evaluator_prioritizes_the_earliest_due_objective(db, users) -> None:
    config = settings().model_copy(
        update={
            "sla_critical_response_minutes": 15,
            "sla_critical_resolution_minutes": 240,
            "sla_high_response_minutes": 30,
            "sla_high_resolution_minutes": 120,
        }
    )
    critical = await IncidentService(db, settings=config, clock=FixedClock(START)).create_incident(
        data=IncidentCreate(
            title="Earlier response objective",
            description="Its resolution deadline is later than the competing incident",
            priority=IncidentPriority.CRITICAL,
        ),
        actor=users["reporter"],
        idempotency_key="create-order-critical-001",
    )
    high = await IncidentService(
        db, settings=config, clock=FixedClock(START + timedelta(minutes=20))
    ).create_incident(
        data=IncidentCreate(
            title="Later response objective",
            description="Its resolution deadline is earlier",
            priority=IncidentPriority.HIGH,
        ),
        actor=users["reporter"],
        idempotency_key="create-order-high-001",
    )

    summary = await SLAEvaluationService(db).evaluate_once(
        now=START + timedelta(minutes=60), batch_size=1
    )
    assert summary.objectives_breached == 1

    breached_incident_ids = set(
        (
            await db.execute(
                select(IncidentEvent.incident_id).where(
                    IncidentEvent.event_type == IncidentEventType.RESPONSE_BREACHED
                )
            )
        ).scalars()
    )
    assert breached_incident_ids == {critical.id}
    assert high.id not in breached_incident_ids


async def test_outbox_stale_attempt_cannot_complete_a_newer_lease(db, users) -> None:
    config = settings().model_copy(update={"outbox_lease_seconds": 10, "outbox_max_attempts": 3})
    incident = await IncidentService(db, settings=config, clock=FixedClock(START)).create_incident(
        data=IncidentCreate(
            title="Outbox lease probe",
            description="A stale worker must not overwrite a reclaimed delivery",
            priority=IncidentPriority.CRITICAL,
        ),
        actor=users["reporter"],
        idempotency_key="create-outbox-lease-001",
    )
    await IncidentService(db, settings=config, clock=FixedClock(START)).assign_incident(
        incident_id=incident.id,
        assignee_id=users["assignee"].id,
        actor=users["admin"],
        idempotency_key="assign-outbox-lease-001",
    )
    await SLAEvaluationService(db).evaluate_once(now=START + timedelta(minutes=3), batch_size=10)

    outbox = OutboxService(db, settings=config)
    first = await outbox.claim_batch(now=START + timedelta(minutes=3))
    assert len(first) == 2
    reclaimed = await outbox.claim_batch(now=START + timedelta(minutes=3, seconds=11))
    assert len(reclaimed) == 2
    assert {item.attempt for item in reclaimed} == {2}

    await outbox.mark_sent(first[0], now=START + timedelta(minutes=3, seconds=12))
    row = await db.get(OutboxMessage, first[0].id)
    assert row is not None
    assert row.status is OutboxStatus.PROCESSING
    assert row.attempts == 2


async def test_expired_final_outbox_lease_becomes_dead(db, users) -> None:
    config = settings().model_copy(update={"outbox_lease_seconds": 10, "outbox_max_attempts": 1})
    incident = await IncidentService(db, settings=config, clock=FixedClock(START)).create_incident(
        data=IncidentCreate(
            title="Outbox terminal probe",
            description="An exhausted ambiguous lease must not remain processing forever",
            priority=IncidentPriority.CRITICAL,
        ),
        actor=users["reporter"],
        idempotency_key="create-outbox-terminal-001",
    )
    await IncidentService(db, settings=config, clock=FixedClock(START)).assign_incident(
        incident_id=incident.id,
        assignee_id=users["assignee"].id,
        actor=users["admin"],
        idempotency_key="assign-outbox-terminal-001",
    )
    await SLAEvaluationService(db).evaluate_once(now=START + timedelta(minutes=3), batch_size=10)

    outbox = OutboxService(db, settings=config)
    claimed = await outbox.claim_batch(now=START + timedelta(minutes=3))
    assert len(claimed) == 2
    assert not await outbox.claim_batch(now=START + timedelta(minutes=3, seconds=11))

    states = (
        (await db.execute(select(OutboxMessage.status).order_by(OutboxMessage.id))).scalars().all()
    )
    assert states == [OutboxStatus.DEAD, OutboxStatus.DEAD]


class _SuccessfulTransport:
    async def send(self, envelope) -> None:
        return None


class _FailingTransport:
    async def send(self, envelope) -> None:
        raise RuntimeError(f"provider rejected {envelope.recipient}: {'secret' * 1000}")


class _PauseBeforeMarkSentService(OutboxService):
    def __init__(
        self, *args, mark_started: asyncio.Event, release: asyncio.Event, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)
        self.mark_started = mark_started
        self.release = release

    async def mark_sent(self, envelope, *, now=None) -> None:
        self.mark_started.set()
        await self.release.wait()
        await super().mark_sent(envelope, now=now)


async def test_cancelled_after_provider_send_is_reclaimed_after_lease(db, users) -> None:
    config = settings().model_copy(
        update={
            "outbox_lease_seconds": 10,
            "outbox_max_attempts": 3,
            "worker_batch_size": 1,
        }
    )
    incident = await IncidentService(db, settings=config, clock=FixedClock(START)).create_incident(
        data=IncidentCreate(
            title="Ambiguous send cancellation",
            description="Cancellation after provider return must leave a reclaimable lease",
            priority=IncidentPriority.CRITICAL,
        ),
        actor=users["reporter"],
        idempotency_key="create-cancelled-delivery-001",
    )
    await IncidentService(db, settings=config, clock=FixedClock(START)).assign_incident(
        incident_id=incident.id,
        assignee_id=users["assignee"].id,
        actor=users["admin"],
        idempotency_key="assign-cancelled-delivery-001",
    )
    await SLAEvaluationService(db).evaluate_once(now=START + timedelta(minutes=3), batch_size=10)

    mark_started = asyncio.Event()
    release = asyncio.Event()
    service = _PauseBeforeMarkSentService(
        db,
        settings=config,
        mark_started=mark_started,
        release=release,
    )
    delivery = asyncio.create_task(
        service.deliver_once(
            transport=_SuccessfulTransport(),
            now=START + timedelta(minutes=3),
        )
    )
    await asyncio.wait_for(mark_started.wait(), timeout=2)
    delivery.cancel()
    with pytest.raises(asyncio.CancelledError):
        await delivery

    processing = await db.scalar(
        select(OutboxMessage).where(OutboxMessage.status == OutboxStatus.PROCESSING)
    )
    assert processing is not None
    assert processing.attempts == 1
    processing_id = processing.id
    await db.rollback()

    reclaimed = await service.claim_batch(now=START + timedelta(minutes=3, seconds=11))
    assert len(reclaimed) == 1
    assert reclaimed[0].id == processing_id
    assert reclaimed[0].attempt == 2


async def test_provider_failures_retry_then_dead_with_safe_diagnostics(db, users) -> None:
    config = settings().model_copy(
        update={
            "sla_critical_resolution_minutes": 60,
            "outbox_max_attempts": 2,
            "worker_batch_size": 1,
        }
    )
    incident = await IncidentService(db, settings=config, clock=FixedClock(START)).create_incident(
        data=IncidentCreate(
            title="Provider retry",
            description="One breach message exercises bounded retry diagnostics",
            priority=IncidentPriority.CRITICAL,
        ),
        actor=users["reporter"],
        idempotency_key="create-provider-retry-001",
    )
    await IncidentService(db, settings=config, clock=FixedClock(START)).assign_incident(
        incident_id=incident.id,
        assignee_id=users["assignee"].id,
        actor=users["admin"],
        idempotency_key="assign-provider-retry-001",
    )
    now = START + timedelta(minutes=2)
    await SLAEvaluationService(db).evaluate_once(now=now, batch_size=10)

    service = OutboxService(db, settings=config)
    first = await service.deliver_once(transport=_FailingTransport(), now=now)
    assert first == {"claimed": 1, "sent": 0, "failed": 1}
    row = await db.scalar(select(OutboxMessage))
    assert row is not None
    assert row.status is OutboxStatus.PENDING
    assert row.attempts == 1
    assert row.last_error == "RuntimeError"
    await db.rollback()

    second = await service.deliver_once(
        transport=_FailingTransport(),
        now=now + timedelta(seconds=1),
    )
    assert second == {"claimed": 1, "sent": 0, "failed": 1}
    row = await db.scalar(select(OutboxMessage))
    assert row is not None
    assert row.status is OutboxStatus.DEAD
    assert row.attempts == 2
    assert row.claimed_at is None
    assert row.last_error == "RuntimeError"
