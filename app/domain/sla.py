"""Pure incident lifecycle and SLA calculations.

The database and worker layers call these functions rather than reimplementing deadline
semantics. Every datetime accepted here must be timezone-aware. An objective is met when the
corresponding action happens at or before its deadline and is breached only after the deadline.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import StrEnum


class IncidentPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class IncidentStatus(StrEnum):
    OPEN = "open"
    ACKNOWLEDGED = "acknowledged"
    RESOLVED = "resolved"
    CLOSED = "closed"


class SLAObjective(StrEnum):
    RESPONSE = "response"
    RESOLUTION = "resolution"


class ObjectiveOutcome(StrEnum):
    PENDING = "pending"
    MET = "met"
    BREACHED = "breached"


class IncidentEventType(StrEnum):
    CREATED = "incident.created"
    ASSIGNED = "incident.assigned"
    ACKNOWLEDGED = "incident.acknowledged"
    RESOLVED = "incident.resolved"
    CLOSED = "incident.closed"
    RESPONSE_BREACHED = "sla.response_breached"
    RESOLUTION_BREACHED = "sla.resolution_breached"


@dataclass(frozen=True, slots=True)
class SLAPolicy:
    response_minutes: int
    resolution_minutes: int

    def validate(self) -> None:
        if self.response_minutes <= 0:
            raise ValueError("response_minutes must be positive")
        if self.resolution_minutes <= 0:
            raise ValueError("resolution_minutes must be positive")
        if self.resolution_minutes < self.response_minutes:
            raise ValueError("resolution_minutes must be >= response_minutes")


@dataclass(frozen=True, slots=True)
class SLAState:
    started_at: datetime
    response_deadline: datetime
    resolution_deadline: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    response_breached_at: datetime | None = None
    resolution_breached_at: datetime | None = None

    def validate(self) -> None:
        for value in (
            self.started_at,
            self.response_deadline,
            self.resolution_deadline,
            self.acknowledged_at,
            self.resolved_at,
            self.response_breached_at,
            self.resolution_breached_at,
        ):
            if value is not None:
                _require_aware(value)
        if self.response_deadline <= self.started_at:
            raise ValueError("response deadline must be after start")
        if self.resolution_deadline < self.response_deadline:
            raise ValueError("resolution deadline must not precede response deadline")
        if self.resolved_at is not None and self.acknowledged_at is None:
            raise ValueError("resolution requires acknowledgement")
        if self.acknowledged_at is not None and self.acknowledged_at < self.started_at:
            raise ValueError("acknowledgement cannot precede SLA start")
        if self.resolved_at is not None and self.resolved_at < self.started_at:
            raise ValueError("resolution cannot precede SLA start")
        if (
            self.acknowledged_at is not None
            and self.resolved_at is not None
            and self.resolved_at < self.acknowledged_at
        ):
            raise ValueError("resolution cannot precede acknowledgement")
        if (
            self.response_breached_at is not None
            and self.response_breached_at != self.response_deadline
        ):
            raise ValueError("response breach evidence must use the response deadline")
        if (
            self.resolution_breached_at is not None
            and self.resolution_breached_at != self.resolution_deadline
        ):
            raise ValueError("resolution breach evidence must use the resolution deadline")
        if self.acknowledged_at is not None:
            if self.acknowledged_at <= self.response_deadline:
                if self.response_breached_at is not None:
                    raise ValueError(
                        "on-time acknowledgement cannot carry response breach evidence"
                    )
            elif self.response_breached_at is None:
                raise ValueError("late acknowledgement requires response breach evidence")
        if self.resolved_at is not None:
            if self.resolved_at <= self.resolution_deadline:
                if self.resolution_breached_at is not None:
                    raise ValueError("on-time resolution cannot carry resolution breach evidence")
            elif self.resolution_breached_at is None:
                raise ValueError("late resolution requires resolution breach evidence")


@dataclass(frozen=True, slots=True)
class LifecycleState:
    status: IncidentStatus
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None

    def validate(self) -> None:
        for value in (self.acknowledged_at, self.resolved_at, self.closed_at):
            if value is not None:
                _require_aware(value)
        if self.status is IncidentStatus.OPEN:
            if any((self.acknowledged_at, self.resolved_at, self.closed_at)):
                raise ValueError("open incidents cannot carry terminal timestamps")
        elif self.status is IncidentStatus.ACKNOWLEDGED:
            if self.acknowledged_at is None or self.resolved_at or self.closed_at:
                raise ValueError("acknowledged state is inconsistent")
        elif self.status is IncidentStatus.RESOLVED:
            if self.acknowledged_at is None or self.resolved_at is None or self.closed_at:
                raise ValueError("resolved state is inconsistent")
        elif self.status is IncidentStatus.CLOSED and not all(
            (self.acknowledged_at, self.resolved_at, self.closed_at)
        ):
            raise ValueError("closed state requires all lifecycle timestamps")

        if (
            self.acknowledged_at is not None
            and self.resolved_at is not None
            and self.resolved_at < self.acknowledged_at
        ):
            raise ValueError("resolution cannot precede acknowledgement")
        if (
            self.resolved_at is not None
            and self.closed_at is not None
            and self.closed_at < self.resolved_at
        ):
            raise ValueError("closure cannot precede resolution")


@dataclass(frozen=True, slots=True)
class BreachDecision:
    objective: SLAObjective
    effective_at: datetime
    detected_at: datetime


def build_sla_state(started_at: datetime, policy: SLAPolicy) -> SLAState:
    _require_aware(started_at)
    policy.validate()
    state = SLAState(
        started_at=started_at,
        response_deadline=started_at + timedelta(minutes=policy.response_minutes),
        resolution_deadline=started_at + timedelta(minutes=policy.resolution_minutes),
    )
    state.validate()
    return state


def detect_due_breaches(
    state: SLAState, now: datetime
) -> tuple[SLAState, tuple[BreachDecision, ...]]:
    """Persist every objective that has become irreversibly breached by ``now``.

    ``effective_at`` is the contractual deadline. ``detected_at`` records worker or command
    latency without moving the contractual boundary.
    """

    state.validate()
    _require_aware(now)
    decisions: list[BreachDecision] = []
    updated = state

    if (
        state.acknowledged_at is None
        and state.response_breached_at is None
        and now > state.response_deadline
    ):
        updated = replace(updated, response_breached_at=state.response_deadline)
        decisions.append(
            BreachDecision(
                objective=SLAObjective.RESPONSE,
                effective_at=state.response_deadline,
                detected_at=now,
            )
        )

    if (
        state.resolved_at is None
        and state.resolution_breached_at is None
        and now > state.resolution_deadline
    ):
        updated = replace(updated, resolution_breached_at=state.resolution_deadline)
        decisions.append(
            BreachDecision(
                objective=SLAObjective.RESOLUTION,
                effective_at=state.resolution_deadline,
                detected_at=now,
            )
        )

    updated.validate()
    return updated, tuple(decisions)


def acknowledge(
    lifecycle: LifecycleState, sla: SLAState, now: datetime
) -> tuple[LifecycleState, SLAState, tuple[BreachDecision, ...]]:
    lifecycle.validate()
    _require_aware(now)
    if lifecycle.status is not IncidentStatus.OPEN:
        raise ValueError("only open incidents can be acknowledged")
    updated_sla, breaches = detect_due_breaches(sla, now)
    updated_sla = replace(updated_sla, acknowledged_at=now)
    updated_lifecycle = LifecycleState(
        status=IncidentStatus.ACKNOWLEDGED,
        acknowledged_at=now,
    )
    updated_lifecycle.validate()
    updated_sla.validate()
    return updated_lifecycle, updated_sla, breaches


def resolve(
    lifecycle: LifecycleState, sla: SLAState, now: datetime
) -> tuple[LifecycleState, SLAState, tuple[BreachDecision, ...]]:
    lifecycle.validate()
    _require_aware(now)
    if lifecycle.status not in {IncidentStatus.OPEN, IncidentStatus.ACKNOWLEDGED}:
        raise ValueError("only open or acknowledged incidents can be resolved")
    updated_sla, breaches = detect_due_breaches(sla, now)
    acknowledged_at = lifecycle.acknowledged_at or now
    updated_sla = replace(
        updated_sla,
        acknowledged_at=updated_sla.acknowledged_at or now,
        resolved_at=now,
    )
    updated_lifecycle = LifecycleState(
        status=IncidentStatus.RESOLVED,
        acknowledged_at=acknowledged_at,
        resolved_at=now,
    )
    updated_lifecycle.validate()
    updated_sla.validate()
    return updated_lifecycle, updated_sla, breaches


def close(lifecycle: LifecycleState, now: datetime) -> LifecycleState:
    lifecycle.validate()
    _require_aware(now)
    if lifecycle.status is not IncidentStatus.RESOLVED:
        raise ValueError("only resolved incidents can be closed")
    updated = replace(lifecycle, status=IncidentStatus.CLOSED, closed_at=now)
    updated.validate()
    return updated


def objective_outcome(state: SLAState, objective: SLAObjective) -> ObjectiveOutcome:
    state.validate()
    if objective is SLAObjective.RESPONSE:
        if state.response_breached_at is not None:
            return ObjectiveOutcome.BREACHED
        if state.acknowledged_at is not None:
            return ObjectiveOutcome.MET
        return ObjectiveOutcome.PENDING

    if state.resolution_breached_at is not None:
        return ObjectiveOutcome.BREACHED
    if state.resolved_at is not None:
        return ObjectiveOutcome.MET
    return ObjectiveOutcome.PENDING


def _require_aware(value: datetime) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("datetime values must be timezone-aware")
