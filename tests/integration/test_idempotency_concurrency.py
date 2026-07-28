import asyncio
from datetime import UTC, datetime
from uuid import UUID

import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.config import Settings
from app.domain import IncidentPriority
from app.models import SLA, CommandReceipt, Incident, IncidentEvent, User
from app.schemas import IncidentCreate
from app.services.incident_service import IncidentService

pytestmark = pytest.mark.postgres

START = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
PAYLOAD = IncidentCreate(
    title="Concurrent receipt",
    description="Two requests share one actor and one idempotency key",
    priority=IncidentPriority.HIGH,
)


def settings(database_url: str) -> Settings:
    return Settings(
        app_env="test",
        jwt_secret="x" * 40,
        database_url=database_url,
    )


class _PausedClaimService(IncidentService):
    def __init__(
        self,
        *args,
        claimed: asyncio.Event,
        release: asyncio.Event,
        fail_after_claim: bool,
        **kwargs,
    ) -> None:
        super().__init__(*args, **kwargs)
        self.claimed = claimed
        self.release = release
        self.fail_after_claim = fail_after_claim

    async def _current_time(self) -> datetime:
        self.claimed.set()
        await self.release.wait()
        if self.fail_after_claim:
            raise RuntimeError("first claimant rolled back")
        return START


class _AttemptSignallingService(IncidentService):
    def __init__(self, *args, attempted: asyncio.Event, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self.attempted = attempted

    async def _claim_receipt(
        self,
        *,
        actor_id: UUID,
        idempotency_key: str,
        command_type: str,
        payload: object,
    ) -> tuple[CommandReceipt, bool]:
        self.attempted.set()
        return await super()._claim_receipt(
            actor_id=actor_id,
            idempotency_key=idempotency_key,
            command_type=command_type,
            payload=payload,
        )


async def _run_receipt_race(
    *,
    postgres_url: str,
    reporter_id: UUID,
    fail_after_claim: bool,
) -> None:
    config = settings(postgres_url)
    engine = create_async_engine(postgres_url)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    claimed = asyncio.Event()
    attempted = asyncio.Event()
    release = asyncio.Event()

    async def first_request() -> Incident:
        async with factory() as session:
            async with session.begin():
                actor = await session.get(User, reporter_id)
            assert actor is not None
            return await _PausedClaimService(
                session,
                settings=config,
                claimed=claimed,
                release=release,
                fail_after_claim=fail_after_claim,
            ).create_incident(
                data=PAYLOAD,
                actor=actor,
                idempotency_key="concurrent-create-001",
            )

    async def second_request() -> Incident:
        async with factory() as session:
            async with session.begin():
                actor = await session.get(User, reporter_id)
            assert actor is not None
            return await _AttemptSignallingService(
                session,
                settings=config,
                attempted=attempted,
            ).create_incident(
                data=PAYLOAD,
                actor=actor,
                idempotency_key="concurrent-create-001",
            )

    first_task = asyncio.create_task(first_request())
    second_task: asyncio.Task[Incident] | None = None
    try:
        await asyncio.wait_for(claimed.wait(), timeout=2)
        second_task = asyncio.create_task(second_request())
        await asyncio.wait_for(attempted.wait(), timeout=2)
        await asyncio.sleep(0.05)
        assert not second_task.done()

        release.set()
        if fail_after_claim:
            with pytest.raises(RuntimeError, match="first claimant rolled back"):
                await asyncio.wait_for(first_task, timeout=5)
            result = await asyncio.wait_for(second_task, timeout=5)
        else:
            first_result, result = await asyncio.wait_for(
                asyncio.gather(first_task, second_task),
                timeout=5,
            )
            assert first_result.id == result.id

        async with factory() as session:
            incident_count = await session.scalar(select(func.count(Incident.id)))
            sla_count = await session.scalar(select(func.count(SLA.id)))
            event_count = await session.scalar(select(func.count(IncidentEvent.sequence)))
            receipt_count = await session.scalar(select(func.count(CommandReceipt.id)))
        assert (incident_count, sla_count, event_count, receipt_count) == (1, 1, 1, 1)
    finally:
        release.set()
        tasks = [first_task]
        if second_task is not None:
            tasks.append(second_task)
        for task in tasks:
            if not task.done():
                task.cancel()
        await asyncio.gather(*tasks, return_exceptions=True)
        await engine.dispose()


async def test_same_actor_same_key_concurrent_create_converges_after_commit(
    postgres_url, users
) -> None:
    await _run_receipt_race(
        postgres_url=postgres_url,
        reporter_id=users["reporter"].id,
        fail_after_claim=False,
    )


async def test_same_actor_same_key_retries_after_first_claimant_rolls_back(
    postgres_url, users
) -> None:
    await _run_receipt_race(
        postgres_url=postgres_url,
        reporter_id=users["reporter"].id,
        fail_after_claim=True,
    )
