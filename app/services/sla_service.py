"""Transactional SLA evaluation and breach publication."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import and_, case, func, or_, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain import (
    BreachDecision,
    IncidentEventType,
    SLAObjective,
    SLAState,
    detect_due_breaches,
)
from app.models import SLA, Incident, IncidentEvent, OutboxMessage, User


@dataclass(frozen=True, slots=True)
class EvaluationSummary:
    incidents_examined: int
    objectives_breached: int


def apply_sla_state(model: SLA, state: SLAState) -> None:
    model.acknowledged_at = state.acknowledged_at
    model.resolved_at = state.resolved_at
    model.response_breached_at = state.response_breached_at
    model.resolution_breached_at = state.resolution_breached_at


async def persist_due_breaches(
    db: AsyncSession,
    *,
    incident: Incident,
    sla: SLA,
    now: datetime,
    source: str,
) -> tuple[BreachDecision, ...]:
    updated, decisions = detect_due_breaches(sla.as_domain(), now)
    if not decisions:
        return ()

    apply_sla_state(sla, updated)
    recipient: str | None = None
    if incident.assignee_id is not None:
        recipient = await db.scalar(
            select(User.email).where(
                User.id == incident.assignee_id,
                User.is_active.is_(True),
            )
        )

    for decision in decisions:
        if decision.objective is SLAObjective.RESPONSE:
            event_type = IncidentEventType.RESPONSE_BREACHED
            deadline = sla.response_deadline
        else:
            event_type = IncidentEventType.RESOLUTION_BREACHED
            deadline = sla.resolution_deadline

        event = IncidentEvent(
            incident_id=incident.id,
            event_type=event_type,
            actor_id=None,
            occurred_at=decision.detected_at,
            effective_at=decision.effective_at,
            source=source,
            payload={
                "objective": decision.objective.value,
                "deadline": deadline.isoformat(),
                "detected_at": decision.detected_at.isoformat(),
            },
        )
        db.add(event)
        await db.flush()

        if recipient:
            deduplication_key = f"incident:{incident.id}:sla:{decision.objective.value}:breach"
            await db.execute(
                pg_insert(OutboxMessage)
                .values(
                    event_sequence=event.sequence,
                    deduplication_key=deduplication_key,
                    topic="sla.breached",
                    recipient=recipient,
                    available_at=decision.detected_at,
                    payload={
                        "deduplication_key": deduplication_key,
                        "incident_id": str(incident.id),
                        "title": incident.title,
                        "priority": incident.priority.value,
                        "objective": decision.objective.value,
                        "deadline": deadline.isoformat(),
                        "detected_at": decision.detected_at.isoformat(),
                    },
                )
                .on_conflict_do_nothing(index_elements=[OutboxMessage.deduplication_key])
            )

    incident.revision += 1
    return decisions


class SLAEvaluationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def evaluate_once(
        self, *, batch_size: int, now: datetime | None = None
    ) -> EvaluationSummary:
        if now is not None and (now.tzinfo is None or now.utcoffset() is None):
            raise ValueError("SLA evaluation clock must be timezone-aware")

        async with self.db.begin():
            effective_now = now or await self.db.scalar(select(func.clock_timestamp()))
            if (
                effective_now is None
                or effective_now.tzinfo is None
                or effective_now.utcoffset() is None
            ):
                raise RuntimeError("PostgreSQL did not return a timezone-aware clock value")
            response_due = and_(
                SLA.acknowledged_at.is_(None),
                SLA.response_breached_at.is_(None),
                SLA.response_deadline < effective_now,
            )
            resolution_due = and_(
                SLA.resolved_at.is_(None),
                SLA.resolution_breached_at.is_(None),
                SLA.resolution_deadline < effective_now,
            )
            due = or_(response_due, resolution_due)
            earliest_due_deadline = case(
                (response_due, SLA.response_deadline),
                else_=SLA.resolution_deadline,
            )
            rows = (
                await self.db.execute(
                    select(Incident, SLA)
                    .join(SLA, SLA.incident_id == Incident.id)
                    .where(due)
                    .order_by(earliest_due_deadline, SLA.incident_id)
                    .limit(batch_size)
                    .with_for_update(skip_locked=True)
                )
            ).all()

            objective_count = 0
            for incident, sla in rows:
                objective_count += len(
                    await persist_due_breaches(
                        self.db,
                        incident=incident,
                        sla=sla,
                        now=effective_now,
                        source="worker",
                    )
                )

        return EvaluationSummary(incidents_examined=len(rows), objectives_breached=objective_count)
