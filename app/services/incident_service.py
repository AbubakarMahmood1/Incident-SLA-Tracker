"""Incident aggregate commands and access-controlled queries."""

from __future__ import annotations

import uuid
from collections.abc import Sequence
from datetime import datetime
from typing import cast

from sqlalchemy import func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy.orm.interfaces import ORMOption

from app.config import Settings
from app.domain import (
    IncidentEventType,
    IncidentPriority,
    IncidentStatus,
    LifecycleState,
    acknowledge,
    build_sla_state,
    close,
    resolve,
)
from app.models import SLA, CommandReceipt, Incident, IncidentEvent, User
from app.schemas import IncidentCreate
from app.services.errors import (
    ConflictError,
    ForbiddenError,
    IdempotencyConflictError,
    InvalidTransitionError,
    NotFoundError,
)
from app.services.sla_service import apply_sla_state, persist_due_breaches
from app.utils import Clock, canonical_request_hash


class IncidentService:
    def __init__(
        self,
        db: AsyncSession,
        *,
        settings: Settings,
        clock: Clock | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.clock = clock

    async def create_incident(
        self,
        *,
        data: IncidentCreate,
        actor: User,
        idempotency_key: str,
    ) -> Incident:
        payload = data.model_dump(mode="json")
        async with self.db.begin():
            receipt, is_new = await self._claim_receipt(
                actor_id=actor.id,
                idempotency_key=idempotency_key,
                command_type="incident.create",
                payload=payload,
            )
            if is_new:
                now = await self._current_time()
                policy = self.settings.sla_policies[data.priority]
                state = build_sla_state(now, policy)
                incident = Incident(
                    title=data.title,
                    description=data.description,
                    priority=data.priority,
                    status=IncidentStatus.OPEN,
                    revision=1,
                    reporter_id=actor.id,
                )
                self.db.add(incident)
                await self.db.flush()

                sla = SLA(
                    incident_id=incident.id,
                    response_target_seconds=policy.response_minutes * 60,
                    resolution_target_seconds=policy.resolution_minutes * 60,
                    started_at=state.started_at,
                    response_deadline=state.response_deadline,
                    resolution_deadline=state.resolution_deadline,
                )
                self.db.add(sla)
                event = await self._record_event(
                    incident=incident,
                    event_type=IncidentEventType.CREATED,
                    actor_id=actor.id,
                    occurred_at=now,
                    payload={
                        "priority": data.priority.value,
                        "response_deadline": state.response_deadline.isoformat(),
                        "resolution_deadline": state.resolution_deadline.isoformat(),
                    },
                )
                receipt.incident_id = incident.id
                receipt.event_sequence = event.sequence
            else:
                self._require_receipt_result(receipt)
            result = await self._load_incident_required(receipt.incident_id)

        return result

    async def assign_incident(
        self,
        *,
        incident_id: uuid.UUID,
        assignee_id: uuid.UUID,
        actor: User,
        idempotency_key: str,
    ) -> Incident:
        async with self.db.begin():
            receipt, is_new = await self._claim_receipt(
                actor_id=actor.id,
                idempotency_key=idempotency_key,
                command_type="incident.assign",
                payload={"incident_id": str(incident_id), "assignee_id": str(assignee_id)},
            )
            if is_new:
                if not actor.is_admin:
                    raise ForbiddenError("only administrators can assign incidents")
                incident = await self._load_incident_for_update(incident_id)
                if incident.status not in {
                    IncidentStatus.OPEN,
                    IncidentStatus.ACKNOWLEDGED,
                }:
                    raise InvalidTransitionError(
                        "only open or acknowledged incidents can be assigned"
                    )
                assignee = await self.db.scalar(
                    select(User).where(User.id == assignee_id, User.is_active.is_(True))
                )
                if assignee is None:
                    raise NotFoundError("active assignee not found")
                if incident.assignee_id == assignee_id:
                    raise ConflictError("incident is already assigned to this user")

                now = await self._current_time()
                previous = incident.assignee_id
                incident.assignee_id = assignee_id
                incident.revision += 1
                event = await self._record_event(
                    incident=incident,
                    event_type=IncidentEventType.ASSIGNED,
                    actor_id=actor.id,
                    occurred_at=now,
                    payload={
                        "previous_assignee_id": str(previous) if previous else None,
                        "assignee_id": str(assignee_id),
                    },
                )
                await persist_due_breaches(
                    self.db,
                    incident=incident,
                    sla=incident.sla,
                    now=now,
                    source="api",
                )
                receipt.incident_id = incident.id
                receipt.event_sequence = event.sequence
            else:
                self._require_receipt_result(receipt)
            result = await self._load_incident_required(receipt.incident_id)

        return result

    async def acknowledge_incident(
        self,
        *,
        incident_id: uuid.UUID,
        actor: User,
        idempotency_key: str,
    ) -> Incident:
        async with self.db.begin():
            receipt, is_new = await self._claim_receipt(
                actor_id=actor.id,
                idempotency_key=idempotency_key,
                command_type="incident.acknowledge",
                payload={"incident_id": str(incident_id)},
            )
            if is_new:
                incident = await self._load_incident_for_update(incident_id)
                self._ensure_assignee_or_admin(incident, actor)
                now = await self._current_time()
                await persist_due_breaches(
                    self.db,
                    incident=incident,
                    sla=incident.sla,
                    now=now,
                    source="api",
                )
                try:
                    lifecycle, sla_state, _ = acknowledge(
                        self._lifecycle(incident), incident.sla.as_domain(), now
                    )
                except ValueError as exc:
                    raise InvalidTransitionError(str(exc)) from exc
                self._apply_lifecycle(incident, lifecycle)
                apply_sla_state(incident.sla, sla_state)
                incident.revision += 1
                event = await self._record_event(
                    incident=incident,
                    event_type=IncidentEventType.ACKNOWLEDGED,
                    actor_id=actor.id,
                    occurred_at=now,
                    payload={},
                )
                receipt.incident_id = incident.id
                receipt.event_sequence = event.sequence
            else:
                self._require_receipt_result(receipt)
            result = await self._load_incident_required(receipt.incident_id)

        return result

    async def resolve_incident(
        self,
        *,
        incident_id: uuid.UUID,
        actor: User,
        idempotency_key: str,
    ) -> Incident:
        async with self.db.begin():
            receipt, is_new = await self._claim_receipt(
                actor_id=actor.id,
                idempotency_key=idempotency_key,
                command_type="incident.resolve",
                payload={"incident_id": str(incident_id)},
            )
            if is_new:
                incident = await self._load_incident_for_update(incident_id)
                self._ensure_assignee_or_admin(incident, actor)
                now = await self._current_time()
                await persist_due_breaches(
                    self.db,
                    incident=incident,
                    sla=incident.sla,
                    now=now,
                    source="api",
                )
                was_open = incident.status is IncidentStatus.OPEN
                try:
                    lifecycle, sla_state, _ = resolve(
                        self._lifecycle(incident), incident.sla.as_domain(), now
                    )
                except ValueError as exc:
                    raise InvalidTransitionError(str(exc)) from exc
                self._apply_lifecycle(incident, lifecycle)
                apply_sla_state(incident.sla, sla_state)
                if was_open:
                    incident.revision += 1
                    await self._record_event(
                        incident=incident,
                        event_type=IncidentEventType.ACKNOWLEDGED,
                        actor_id=actor.id,
                        occurred_at=now,
                        payload={"implicit": True, "reason": "resolved_without_prior_ack"},
                    )
                incident.revision += 1
                event = await self._record_event(
                    incident=incident,
                    event_type=IncidentEventType.RESOLVED,
                    actor_id=actor.id,
                    occurred_at=now,
                    payload={},
                )
                receipt.incident_id = incident.id
                receipt.event_sequence = event.sequence
            else:
                self._require_receipt_result(receipt)
            result = await self._load_incident_required(receipt.incident_id)

        return result

    async def close_incident(
        self,
        *,
        incident_id: uuid.UUID,
        actor: User,
        idempotency_key: str,
    ) -> Incident:
        async with self.db.begin():
            receipt, is_new = await self._claim_receipt(
                actor_id=actor.id,
                idempotency_key=idempotency_key,
                command_type="incident.close",
                payload={"incident_id": str(incident_id)},
            )
            if is_new:
                incident = await self._load_incident_for_update(incident_id)
                self._ensure_reporter_or_admin(incident, actor)
                now = await self._current_time()
                try:
                    lifecycle = close(self._lifecycle(incident), now)
                except ValueError as exc:
                    raise InvalidTransitionError(str(exc)) from exc
                self._apply_lifecycle(incident, lifecycle)
                incident.revision += 1
                event = await self._record_event(
                    incident=incident,
                    event_type=IncidentEventType.CLOSED,
                    actor_id=actor.id,
                    occurred_at=now,
                    payload={},
                )
                receipt.incident_id = incident.id
                receipt.event_sequence = event.sequence
            else:
                self._require_receipt_result(receipt)
            result = await self._load_incident_required(receipt.incident_id)

        return result

    async def get_incident(self, *, incident_id: uuid.UUID, actor: User) -> Incident:
        async with self.db.begin():
            incident = await self._load_incident_required(incident_id)
            self._ensure_visible(incident, actor)
        return incident

    async def list_incidents(
        self,
        *,
        actor: User,
        offset: int,
        limit: int,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        search: str | None = None,
    ) -> tuple[Sequence[Incident], int]:
        filters = []
        if not actor.is_admin:
            filters.append(or_(Incident.reporter_id == actor.id, Incident.assignee_id == actor.id))
        if status is not None:
            filters.append(Incident.status == status)
        if priority is not None:
            filters.append(Incident.priority == priority)
        if search:
            escaped = search.strip().replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            if escaped:
                pattern = f"%{escaped}%"
                filters.append(
                    or_(
                        Incident.title.ilike(pattern, escape="\\"),
                        Incident.description.ilike(pattern, escape="\\"),
                    )
                )

        async with self.db.begin():
            total = int(await self.db.scalar(select(func.count(Incident.id)).where(*filters)) or 0)
            rows = (
                (
                    await self.db.execute(
                        select(Incident)
                        .options(*self._load_options())
                        .where(*filters)
                        .order_by(Incident.created_at.desc(), Incident.id.desc())
                        .offset(offset)
                        .limit(limit)
                    )
                )
                .scalars()
                .all()
            )
        return rows, total

    async def timeline(self, *, incident_id: uuid.UUID, actor: User) -> Sequence[IncidentEvent]:
        async with self.db.begin():
            incident = await self._load_incident_required(incident_id)
            self._ensure_visible(incident, actor)
            events = (
                (
                    await self.db.execute(
                        select(IncidentEvent)
                        .where(IncidentEvent.incident_id == incident.id)
                        .order_by(IncidentEvent.sequence)
                    )
                )
                .scalars()
                .all()
            )
        return events

    async def _current_time(self) -> datetime:
        if self.clock is not None:
            return self.clock.now()
        value = cast(datetime | None, await self.db.scalar(select(func.clock_timestamp())))
        if value is None or value.tzinfo is None or value.utcoffset() is None:
            raise RuntimeError("PostgreSQL did not return a timezone-aware clock value")
        return value

    async def _claim_receipt(
        self,
        *,
        actor_id: uuid.UUID,
        idempotency_key: str,
        command_type: str,
        payload: object,
    ) -> tuple[CommandReceipt, bool]:
        request_hash = canonical_request_hash(command_type, payload)
        receipt_id = uuid.uuid4()
        inserted_id = await self.db.scalar(
            pg_insert(CommandReceipt)
            .values(
                id=receipt_id,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
                command_type=command_type,
                request_hash=request_hash,
            )
            .on_conflict_do_nothing(
                index_elements=[
                    CommandReceipt.actor_id,
                    CommandReceipt.idempotency_key,
                ]
            )
            .returning(CommandReceipt.id)
        )
        if inserted_id is not None:
            receipt = await self.db.get(CommandReceipt, inserted_id)
            if receipt is None:
                raise RuntimeError("inserted command receipt could not be reloaded")
            return receipt, True

        receipt = await self.db.scalar(
            select(CommandReceipt)
            .where(
                CommandReceipt.actor_id == actor_id,
                CommandReceipt.idempotency_key == idempotency_key,
            )
            .with_for_update()
        )
        if receipt is None:
            raise RuntimeError("conflicting command receipt disappeared")
        if receipt.command_type != command_type or receipt.request_hash != request_hash:
            raise IdempotencyConflictError(
                "Idempotency-Key was already used for a different command or payload"
            )
        return receipt, False

    async def _record_event(
        self,
        *,
        incident: Incident,
        event_type: IncidentEventType,
        actor_id: uuid.UUID | None,
        occurred_at: datetime,
        payload: dict[str, object],
    ) -> IncidentEvent:
        event = IncidentEvent(
            incident_id=incident.id,
            event_type=event_type,
            actor_id=actor_id,
            occurred_at=occurred_at,
            effective_at=occurred_at,
            source="api",
            payload=payload,
        )
        self.db.add(event)
        await self.db.flush()
        return event

    async def _load_incident_required(self, incident_id: uuid.UUID | None) -> Incident:
        if incident_id is None:
            raise RuntimeError("command receipt has no incident result")
        incident = await self.db.scalar(
            select(Incident).options(*self._load_options()).where(Incident.id == incident_id)
        )
        if incident is None:
            raise NotFoundError("incident not found")
        return incident

    async def _load_incident_for_update(self, incident_id: uuid.UUID) -> Incident:
        incident = await self.db.scalar(
            select(Incident)
            .join(SLA, SLA.incident_id == Incident.id)
            .options(*self._load_options())
            .where(Incident.id == incident_id)
            .with_for_update()
        )
        if incident is None:
            raise NotFoundError("incident not found")
        return incident

    @staticmethod
    def _load_options() -> tuple[ORMOption, ...]:
        return (
            selectinload(Incident.reporter),
            selectinload(Incident.assignee),
            selectinload(Incident.sla),
        )

    @staticmethod
    def _require_receipt_result(receipt: CommandReceipt) -> None:
        if receipt.incident_id is None or receipt.event_sequence is None:
            raise ConflictError("the original command did not complete")

    @staticmethod
    def _lifecycle(incident: Incident) -> LifecycleState:
        return LifecycleState(
            status=incident.status,
            acknowledged_at=incident.acknowledged_at,
            resolved_at=incident.resolved_at,
            closed_at=incident.closed_at,
        )

    @staticmethod
    def _apply_lifecycle(incident: Incident, state: LifecycleState) -> None:
        incident.status = state.status
        incident.acknowledged_at = state.acknowledged_at
        incident.resolved_at = state.resolved_at
        incident.closed_at = state.closed_at

    @staticmethod
    def _ensure_visible(incident: Incident, actor: User) -> None:
        if actor.is_admin:
            return
        if incident.reporter_id == actor.id or incident.assignee_id == actor.id:
            return
        raise ForbiddenError("incident is not visible to this user")

    @staticmethod
    def _ensure_assignee_or_admin(incident: Incident, actor: User) -> None:
        if actor.is_admin or incident.assignee_id == actor.id:
            return
        raise ForbiddenError("only the current assignee or an administrator may do this")

    @staticmethod
    def _ensure_reporter_or_admin(incident: Incident, actor: User) -> None:
        if actor.is_admin or incident.reporter_id == actor.id:
            return
        raise ForbiddenError("only the reporter or an administrator may close the incident")
