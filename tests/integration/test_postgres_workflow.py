from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError

from app.config import Settings
from app.domain import IncidentEventType, IncidentPriority, IncidentStatus
from app.models import SLA, Incident, IncidentEvent, OutboxMessage
from app.schemas import IncidentCreate
from app.services.errors import (
    ForbiddenError,
    IdempotencyConflictError,
    InvalidTransitionError,
)
from app.services.incident_service import IncidentService
from app.services.sla_service import SLAEvaluationService
from app.utils import FixedClock

pytestmark = pytest.mark.postgres

START = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)


def settings() -> Settings:
    return Settings(
        app_env="test",
        jwt_secret="x" * 40,
        database_url="postgresql+psycopg://unused:unused@localhost/unused",
        sla_high_response_minutes=30,
        sla_high_resolution_minutes=120,
    )


async def test_idempotent_lifecycle_and_timeline(db, users) -> None:
    create_service = IncidentService(db, settings=settings(), clock=FixedClock(START))
    payload = IncidentCreate(
        title="Payments unavailable",
        description="Checkout requests return 503",
        priority=IncidentPriority.HIGH,
    )
    first = await create_service.create_incident(
        data=payload,
        actor=users["reporter"],
        idempotency_key="create-payment-001",
    )
    repeated = await create_service.create_incident(
        data=payload,
        actor=users["reporter"],
        idempotency_key="create-payment-001",
    )
    assert repeated.id == first.id
    incident_id = first.id

    assigned = await create_service.assign_incident(
        incident_id=incident_id,
        assignee_id=users["assignee"].id,
        actor=users["admin"],
        idempotency_key="assign-payment-001",
    )
    assert assigned.assignee_id == users["assignee"].id
    assert assigned.status is IncidentStatus.OPEN

    ack_time = START + timedelta(minutes=10)
    acknowledged = await IncidentService(
        db, settings=settings(), clock=FixedClock(ack_time)
    ).acknowledge_incident(
        incident_id=incident_id,
        actor=users["assignee"],
        idempotency_key="ack-payment-001",
    )
    assert acknowledged.status is IncidentStatus.ACKNOWLEDGED
    assert acknowledged.sla.response_breached_at is None

    resolved_time = START + timedelta(minutes=60)
    resolved = await IncidentService(
        db, settings=settings(), clock=FixedClock(resolved_time)
    ).resolve_incident(
        incident_id=incident_id,
        actor=users["assignee"],
        idempotency_key="resolve-payment-001",
    )
    assert resolved.status is IncidentStatus.RESOLVED
    assert resolved.sla.resolution_breached_at is None

    closed = await IncidentService(
        db, settings=settings(), clock=FixedClock(resolved_time + timedelta(minutes=1))
    ).close_incident(
        incident_id=incident_id,
        actor=users["reporter"],
        idempotency_key="close-payment-001",
    )
    assert closed.status is IncidentStatus.CLOSED

    events = await create_service.timeline(incident_id=incident_id, actor=users["reporter"])
    assert [event.event_type for event in events] == [
        IncidentEventType.CREATED,
        IncidentEventType.ASSIGNED,
        IncidentEventType.ACKNOWLEDGED,
        IncidentEventType.RESOLVED,
        IncidentEventType.CLOSED,
    ]

    with pytest.raises(IdempotencyConflictError):
        await create_service.create_incident(
            data=payload.model_copy(update={"title": "Different payload"}),
            actor=users["reporter"],
            idempotency_key="create-payment-001",
        )


async def test_visibility_is_limited_to_reporter_assignee_or_admin(db, users) -> None:
    service = IncidentService(db, settings=settings(), clock=FixedClock(START))
    incident = await service.create_incident(
        data=IncidentCreate(
            title="Private incident",
            description="Only related principals should see this",
            priority=IncidentPriority.MEDIUM,
        ),
        actor=users["reporter"],
        idempotency_key="create-private-001",
    )
    incident_id = incident.id
    assert (
        await service.get_incident(incident_id=incident_id, actor=users["admin"])
    ).id == incident_id
    with pytest.raises(ForbiddenError):
        await service.get_incident(incident_id=incident_id, actor=users["outsider"])


async def test_late_resolution_records_both_objectives_and_one_outbox_each(db, users) -> None:
    create_service = IncidentService(db, settings=settings(), clock=FixedClock(START))
    incident = await create_service.create_incident(
        data=IncidentCreate(
            title="Late incident",
            description="Deliberately misses both objectives",
            priority=IncidentPriority.HIGH,
        ),
        actor=users["reporter"],
        idempotency_key="create-late-001",
    )
    await create_service.assign_incident(
        incident_id=incident.id,
        assignee_id=users["assignee"].id,
        actor=users["admin"],
        idempotency_key="assign-late-001",
    )
    resolved = await IncidentService(
        db,
        settings=settings(),
        clock=FixedClock(START + timedelta(minutes=121)),
    ).resolve_incident(
        incident_id=incident.id,
        actor=users["assignee"],
        idempotency_key="resolve-late-001",
    )
    assert resolved.sla.response_breached_at == resolved.sla.response_deadline
    assert resolved.sla.resolution_breached_at == resolved.sla.resolution_deadline

    breach_count = await db.scalar(
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
    outbox_count = await db.scalar(select(func.count(OutboxMessage.id)))
    assert breach_count == 2
    assert outbox_count == 2


async def test_unassigned_breach_records_evidence_without_fabricated_recipient(db, users) -> None:
    config = settings()
    incident = await IncidentService(db, settings=config, clock=FixedClock(START)).create_incident(
        data=IncidentCreate(
            title="Unassigned breach",
            description="Breach evidence must not depend on a notification recipient",
            priority=IncidentPriority.HIGH,
        ),
        actor=users["reporter"],
        idempotency_key="create-unassigned-breach-001",
    )

    summary = await SLAEvaluationService(db).evaluate_once(
        now=START + timedelta(minutes=121), batch_size=10
    )
    assert summary.objectives_breached == 2

    breach_count = await db.scalar(
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
    outbox_count = await db.scalar(select(func.count(OutboxMessage.id)))
    assert breach_count == 2
    assert outbox_count == 0


async def test_assignment_rejects_resolved_incident(db, users) -> None:
    config = settings()
    service = IncidentService(db, settings=config, clock=FixedClock(START))
    incident = await service.create_incident(
        data=IncidentCreate(
            title="Resolved assignment boundary",
            description="Assignment is an active-handling command",
            priority=IncidentPriority.HIGH,
        ),
        actor=users["reporter"],
        idempotency_key="create-resolved-assignment-001",
    )
    await service.resolve_incident(
        incident_id=incident.id,
        actor=users["admin"],
        idempotency_key="resolve-before-assignment-001",
    )

    with pytest.raises(InvalidTransitionError, match="open or acknowledged"):
        await service.assign_incident(
            incident_id=incident.id,
            assignee_id=users["assignee"].id,
            actor=users["admin"],
            idempotency_key="assign-after-resolution-001",
        )


async def test_overdue_assignment_records_breach_for_new_assignee(db, users) -> None:
    config = settings()
    incident = await IncidentService(db, settings=config, clock=FixedClock(START)).create_incident(
        data=IncidentCreate(
            title="Overdue before assignment",
            description="The assignment command is the first observer after the deadline",
            priority=IncidentPriority.HIGH,
        ),
        actor=users["reporter"],
        idempotency_key="create-overdue-assignment-001",
    )

    assigned = await IncidentService(
        db,
        settings=config,
        clock=FixedClock(START + timedelta(minutes=31)),
    ).assign_incident(
        incident_id=incident.id,
        assignee_id=users["assignee"].id,
        actor=users["admin"],
        idempotency_key="assign-overdue-001",
    )
    assert assigned.sla.response_breached_at == assigned.sla.response_deadline

    outbox = await db.scalar(select(OutboxMessage))
    assert outbox is not None
    assert outbox.recipient == users["assignee"].email
    assert outbox.payload["objective"] == "response"


async def test_event_ledger_and_policy_snapshot_are_database_immutable(db, users) -> None:
    service = IncidentService(db, settings=settings(), clock=FixedClock(START))
    incident = await service.create_incident(
        data=IncidentCreate(
            title="Immutable evidence",
            description="Mutation attempts must fail in PostgreSQL",
            priority=IncidentPriority.LOW,
        ),
        actor=users["reporter"],
        idempotency_key="create-immutable-001",
    )
    incident_id = incident.id
    event = await db.scalar(select(IncidentEvent).where(IncidentEvent.incident_id == incident_id))
    assert event is not None
    event_sequence = event.sequence
    await db.rollback()

    with pytest.raises(DBAPIError):
        async with db.begin():
            await db.execute(
                update(IncidentEvent)
                .where(IncidentEvent.sequence == event_sequence)
                .values(source="tampered")
            )
    await db.rollback()

    sla = await db.scalar(select(SLA).where(SLA.incident_id == incident_id))
    assert sla is not None
    sla_id = sla.id
    changed_deadline = sla.response_deadline + timedelta(minutes=1)
    await db.rollback()
    with pytest.raises(DBAPIError):
        async with db.begin():
            await db.execute(
                update(SLA).where(SLA.id == sla_id).values(response_deadline=changed_deadline)
            )


async def test_database_rejects_progress_drift_and_missing_sla(db, users) -> None:
    service = IncidentService(db, settings=settings(), clock=FixedClock(START))
    incident = await service.create_incident(
        data=IncidentCreate(
            title="Cross-table invariant",
            description="Incident and SLA progress must remain aligned",
            priority=IncidentPriority.MEDIUM,
        ),
        actor=users["reporter"],
        idempotency_key="create-cross-table-001",
    )
    incident_id = incident.id

    with pytest.raises(DBAPIError):
        async with db.begin():
            await db.execute(
                update(Incident)
                .where(Incident.id == incident_id)
                .values(
                    status=IncidentStatus.ACKNOWLEDGED,
                    acknowledged_at=START + timedelta(minutes=1),
                )
            )
    await db.rollback()

    with pytest.raises(DBAPIError):
        async with db.begin():
            await db.execute(delete(SLA).where(SLA.incident_id == incident_id))
    await db.rollback()
