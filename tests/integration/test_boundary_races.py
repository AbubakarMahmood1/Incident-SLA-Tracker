import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

import app.services.sla_service as sla_service_module
from app.config import Settings
from app.domain import IncidentEventType, IncidentPriority
from app.models import SLA, IncidentEvent, OutboxMessage, User
from app.schemas import IncidentCreate
from app.services.incident_service import IncidentService
from app.services.sla_service import SLAEvaluationService
from app.utils import FixedClock

pytestmark = pytest.mark.postgres

START = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
AFTER_DEADLINE = START + timedelta(minutes=3)


def settings(database_url: str, objective: str) -> Settings:
    return Settings(
        app_env="test",
        jwt_secret="x" * 40,
        database_url=database_url,
        sla_critical_response_minutes=1,
        sla_critical_resolution_minutes=60 if objective == "response" else 2,
    )


class _PauseAfterIncidentLockService(IncidentService):
    def __init__(
        self,
        *args,
        locked: asyncio.Event,
        release: asyncio.Event,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.locked = locked
        self.release = release

    async def _current_time(self) -> datetime:
        self.locked.set()
        await self.release.wait()
        return AFTER_DEADLINE


async def _prepare_incident(db, users, config: Settings, objective: str) -> UUID:
    service = IncidentService(db, settings=config, clock=FixedClock(START))
    incident = await service.create_incident(
        data=IncidentCreate(
            title=f"{objective.title()} deadline race",
            description="The API command and evaluator contend on one incident",
            priority=IncidentPriority.CRITICAL,
        ),
        actor=users["reporter"],
        idempotency_key=f"create-{objective}-race-001",
    )
    await service.assign_incident(
        incident_id=incident.id,
        assignee_id=users["assignee"].id,
        actor=users["admin"],
        idempotency_key=f"assign-{objective}-race-001",
    )
    if objective == "resolution":
        await IncidentService(
            db,
            settings=config,
            clock=FixedClock(START + timedelta(seconds=30)),
        ).acknowledge_incident(
            incident_id=incident.id,
            actor=users["assignee"],
            idempotency_key="ack-resolution-race-001",
        )
    return incident.id


async def _invoke_command(
    service: IncidentService,
    *,
    objective: str,
    incident_id: UUID,
    actor: User,
    key_suffix: str,
):
    if objective == "response":
        return await service.acknowledge_incident(
            incident_id=incident_id,
            actor=actor,
            idempotency_key=f"ack-response-race-{key_suffix}",
        )
    return await service.resolve_incident(
        incident_id=incident_id,
        actor=actor,
        idempotency_key=f"resolve-resolution-race-{key_suffix}",
    )


async def _assert_single_breach(factory, incident_id: UUID, objective: str) -> None:
    event_type = (
        IncidentEventType.RESPONSE_BREACHED
        if objective == "response"
        else IncidentEventType.RESOLUTION_BREACHED
    )
    async with factory() as session:
        event_count = await session.scalar(
            select(func.count(IncidentEvent.sequence)).where(
                IncidentEvent.incident_id == incident_id,
                IncidentEvent.event_type == event_type,
            )
        )
        outbox_count = await session.scalar(
            select(func.count(OutboxMessage.id)).where(
                OutboxMessage.payload["objective"].astext == objective
            )
        )
        sla = await session.scalar(select(SLA).where(SLA.incident_id == incident_id))
    assert event_count == 1
    assert outbox_count == 1
    assert sla is not None
    if objective == "response":
        assert sla.response_breached_at == sla.response_deadline
    else:
        assert sla.resolution_breached_at == sla.resolution_deadline


@pytest.mark.parametrize("objective", ["response", "resolution"])
async def test_api_command_holds_lock_and_evaluator_skips_without_losing_breach(
    db, users, postgres_url, objective
) -> None:
    config = settings(postgres_url, objective)
    incident_id = await _prepare_incident(db, users, config, objective)
    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    locked = asyncio.Event()
    release = asyncio.Event()

    async def run_command():
        async with factory() as session:
            async with session.begin():
                actor = await session.get(User, users["assignee"].id)
            assert actor is not None
            service = _PauseAfterIncidentLockService(
                session,
                settings=config,
                locked=locked,
                release=release,
            )
            return await _invoke_command(
                service,
                objective=objective,
                incident_id=incident_id,
                actor=actor,
                key_suffix="command-first",
            )

    command_task = asyncio.create_task(run_command())
    try:
        await asyncio.wait_for(locked.wait(), timeout=2)
        async with factory() as evaluator_session:
            summary = await SLAEvaluationService(evaluator_session).evaluate_once(
                now=AFTER_DEADLINE,
                batch_size=10,
            )
        assert summary.incidents_examined == 0
        assert summary.objectives_breached == 0
        release.set()
        await asyncio.wait_for(command_task, timeout=5)
        await _assert_single_breach(factory, incident_id, objective)
    finally:
        release.set()
        if not command_task.done():
            command_task.cancel()
        await asyncio.gather(command_task, return_exceptions=True)
        await engine.dispose()


@pytest.mark.parametrize("objective", ["response", "resolution"])
async def test_evaluator_holds_lock_and_api_command_converges_on_same_breach(
    db, users, postgres_url, objective, monkeypatch
) -> None:
    config = settings(postgres_url, objective)
    incident_id = await _prepare_incident(db, users, config, objective)
    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    locked = asyncio.Event()
    release = asyncio.Event()
    original = sla_service_module.persist_due_breaches
    first_call = True

    async def paused_persist(*args, **kwargs):
        nonlocal first_call
        if first_call:
            first_call = False
            locked.set()
            await release.wait()
        return await original(*args, **kwargs)

    monkeypatch.setattr(sla_service_module, "persist_due_breaches", paused_persist)

    async def run_evaluator():
        async with factory() as session:
            return await SLAEvaluationService(session).evaluate_once(
                now=AFTER_DEADLINE,
                batch_size=10,
            )

    async def run_command():
        async with factory() as session:
            async with session.begin():
                actor = await session.get(User, users["assignee"].id)
            assert actor is not None
            return await _invoke_command(
                IncidentService(session, settings=config, clock=FixedClock(AFTER_DEADLINE)),
                objective=objective,
                incident_id=incident_id,
                actor=actor,
                key_suffix="evaluator-first",
            )

    evaluator_task = asyncio.create_task(run_evaluator())
    command_task = None
    try:
        await asyncio.wait_for(locked.wait(), timeout=2)
        command_task = asyncio.create_task(run_command())
        await asyncio.sleep(0.05)
        assert not command_task.done()
        release.set()
        summary = await asyncio.wait_for(evaluator_task, timeout=5)
        await asyncio.wait_for(command_task, timeout=5)
        assert summary.incidents_examined == 1
        assert summary.objectives_breached == 1
        await _assert_single_breach(factory, incident_id, objective)
    finally:
        release.set()
        tasks = [evaluator_task]
        if command_task is not None:
            tasks.append(command_task)
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await engine.dispose()
