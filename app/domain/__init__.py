"""Dependency-free domain model for incident and SLA decisions."""

from app.domain.sla import (
    BreachDecision,
    IncidentEventType,
    IncidentPriority,
    IncidentStatus,
    LifecycleState,
    ObjectiveOutcome,
    SLAObjective,
    SLAPolicy,
    SLAState,
    acknowledge,
    build_sla_state,
    close,
    detect_due_breaches,
    objective_outcome,
    resolve,
)

__all__ = [
    "BreachDecision",
    "IncidentEventType",
    "IncidentPriority",
    "IncidentStatus",
    "LifecycleState",
    "ObjectiveOutcome",
    "SLAObjective",
    "SLAPolicy",
    "SLAState",
    "acknowledge",
    "build_sla_state",
    "close",
    "detect_due_breaches",
    "objective_outcome",
    "resolve",
]
