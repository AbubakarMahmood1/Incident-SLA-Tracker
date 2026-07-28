from datetime import UTC, datetime, timedelta

import pytest

from app.domain import (
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

START = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
POLICY = SLAPolicy(response_minutes=30, resolution_minutes=120)


def test_build_sla_state_snapshots_deadlines() -> None:
    state = build_sla_state(START, POLICY)
    assert state.response_deadline == START + timedelta(minutes=30)
    assert state.resolution_deadline == START + timedelta(minutes=120)


@pytest.mark.parametrize(
    ("response", "resolution"),
    [(0, 1), (-1, 1), (2, 1), (1, 0), (1, -1)],
)
def test_policy_rejects_invalid_targets(response: int, resolution: int) -> None:
    with pytest.raises(ValueError):
        SLAPolicy(response, resolution).validate()


def test_domain_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError, match="timezone-aware"):
        build_sla_state(datetime(2026, 1, 1), POLICY)


@pytest.mark.parametrize("delta_microseconds", [-1, 0])
def test_response_is_not_breached_at_or_before_deadline(delta_microseconds: int) -> None:
    state = build_sla_state(START, POLICY)
    now = state.response_deadline + timedelta(microseconds=delta_microseconds)
    updated, decisions = detect_due_breaches(state, now)
    assert decisions == ()
    assert updated.response_breached_at is None


def test_response_breach_effective_time_is_deadline_not_detection_time() -> None:
    state = build_sla_state(START, POLICY)
    detected = state.response_deadline + timedelta(minutes=17)
    updated, decisions = detect_due_breaches(state, detected)
    assert len(decisions) == 1
    assert decisions[0].objective is SLAObjective.RESPONSE
    assert decisions[0].effective_at == state.response_deadline
    assert decisions[0].detected_at == detected
    assert updated.response_breached_at == state.response_deadline


def test_both_objectives_can_breach_independently() -> None:
    state = build_sla_state(START, POLICY)
    after_both = state.resolution_deadline + timedelta(seconds=1)
    updated, decisions = detect_due_breaches(state, after_both)
    assert [decision.objective for decision in decisions] == [
        SLAObjective.RESPONSE,
        SLAObjective.RESOLUTION,
    ]
    assert objective_outcome(updated, SLAObjective.RESPONSE) is ObjectiveOutcome.BREACHED
    assert objective_outcome(updated, SLAObjective.RESOLUTION) is ObjectiveOutcome.BREACHED


def test_breach_detection_is_idempotent() -> None:
    state = build_sla_state(START, POLICY)
    first, decisions = detect_due_breaches(state, state.resolution_deadline + timedelta(seconds=1))
    second, repeated = detect_due_breaches(first, state.resolution_deadline + timedelta(hours=1))
    assert len(decisions) == 2
    assert repeated == ()
    assert second == first


@pytest.mark.parametrize("minutes", [1, 29, 30])
def test_acknowledgement_at_or_before_deadline_meets_response(minutes: int) -> None:
    lifecycle = LifecycleState(IncidentStatus.OPEN)
    sla = build_sla_state(START, POLICY)
    updated_lifecycle, updated_sla, breaches = acknowledge(
        lifecycle, sla, START + timedelta(minutes=minutes)
    )
    assert breaches == ()
    assert updated_lifecycle.status is IncidentStatus.ACKNOWLEDGED
    assert objective_outcome(updated_sla, SLAObjective.RESPONSE) is ObjectiveOutcome.MET


def test_late_acknowledgement_preserves_response_breach() -> None:
    lifecycle = LifecycleState(IncidentStatus.OPEN)
    sla = build_sla_state(START, POLICY)
    updated_lifecycle, updated_sla, breaches = acknowledge(
        lifecycle, sla, START + timedelta(minutes=31)
    )
    assert updated_lifecycle.status is IncidentStatus.ACKNOWLEDGED
    assert len(breaches) == 1
    assert objective_outcome(updated_sla, SLAObjective.RESPONSE) is ObjectiveOutcome.BREACHED


def test_resolving_open_incident_implicitly_acknowledges() -> None:
    lifecycle = LifecycleState(IncidentStatus.OPEN)
    sla = build_sla_state(START, POLICY)
    now = START + timedelta(minutes=20)
    updated_lifecycle, updated_sla, breaches = resolve(lifecycle, sla, now)
    assert breaches == ()
    assert updated_lifecycle.status is IncidentStatus.RESOLVED
    assert updated_lifecycle.acknowledged_at == now
    assert updated_lifecycle.resolved_at == now
    assert updated_sla.acknowledged_at == now
    assert updated_sla.resolved_at == now


def test_late_resolution_can_breach_both_objectives() -> None:
    lifecycle = LifecycleState(IncidentStatus.OPEN)
    sla = build_sla_state(START, POLICY)
    now = START + timedelta(minutes=121)
    _, updated_sla, breaches = resolve(lifecycle, sla, now)
    assert {decision.objective for decision in breaches} == {
        SLAObjective.RESPONSE,
        SLAObjective.RESOLUTION,
    }
    assert objective_outcome(updated_sla, SLAObjective.RESPONSE) is ObjectiveOutcome.BREACHED
    assert objective_outcome(updated_sla, SLAObjective.RESOLUTION) is ObjectiveOutcome.BREACHED


def test_close_requires_resolved_state() -> None:
    with pytest.raises(ValueError, match="only resolved"):
        close(LifecycleState(IncidentStatus.OPEN), START)


def test_close_preserves_prior_timestamps() -> None:
    resolved = LifecycleState(
        IncidentStatus.RESOLVED,
        acknowledged_at=START + timedelta(minutes=10),
        resolved_at=START + timedelta(minutes=50),
    )
    closed = close(resolved, START + timedelta(minutes=60))
    assert closed.status is IncidentStatus.CLOSED
    assert closed.acknowledged_at == resolved.acknowledged_at
    assert closed.resolved_at == resolved.resolved_at
    assert closed.closed_at == START + timedelta(minutes=60)


@pytest.mark.parametrize(
    "state",
    [
        LifecycleState(IncidentStatus.OPEN, acknowledged_at=START),
        LifecycleState(IncidentStatus.ACKNOWLEDGED),
        LifecycleState(IncidentStatus.RESOLVED, acknowledged_at=START),
        LifecycleState(
            IncidentStatus.CLOSED,
            acknowledged_at=START,
            resolved_at=START + timedelta(minutes=1),
        ),
    ],
)
def test_lifecycle_rejects_inconsistent_timestamp_combinations(
    state: LifecycleState,
) -> None:
    with pytest.raises(ValueError):
        state.validate()


def test_sla_rejects_resolution_without_acknowledgement() -> None:
    state = SLAState(
        started_at=START,
        response_deadline=START + timedelta(minutes=1),
        resolution_deadline=START + timedelta(minutes=2),
        resolved_at=START + timedelta(minutes=1),
    )
    with pytest.raises(ValueError, match="requires acknowledgement"):
        state.validate()


@pytest.mark.parametrize("priority", list(IncidentPriority))
def test_priority_values_are_stable_lowercase_strings(priority: IncidentPriority) -> None:
    assert priority.value == priority.value.lower()
    assert " " not in priority.value


@pytest.mark.parametrize("offset", range(-5, 6))
def test_response_outcome_follows_action_relative_to_deadline(offset: int) -> None:
    state = build_sla_state(START, POLICY)
    action_time = state.response_deadline + timedelta(seconds=offset)
    lifecycle = LifecycleState(IncidentStatus.OPEN)
    _, updated, _ = acknowledge(lifecycle, state, action_time)
    expected = ObjectiveOutcome.MET if offset <= 0 else ObjectiveOutcome.BREACHED
    assert objective_outcome(updated, SLAObjective.RESPONSE) is expected


@pytest.mark.parametrize("offset", range(-5, 6))
def test_resolution_outcome_follows_action_relative_to_deadline(offset: int) -> None:
    state = build_sla_state(START, POLICY)
    action_time = state.resolution_deadline + timedelta(seconds=offset)
    lifecycle = LifecycleState(IncidentStatus.OPEN)
    _, updated, _ = resolve(lifecycle, state, action_time)
    expected = ObjectiveOutcome.MET if offset <= 0 else ObjectiveOutcome.BREACHED
    assert objective_outcome(updated, SLAObjective.RESOLUTION) is expected


def test_acknowledgement_cannot_be_applied_twice() -> None:
    lifecycle, sla, _ = acknowledge(
        LifecycleState(IncidentStatus.OPEN),
        build_sla_state(START, POLICY),
        START + timedelta(minutes=1),
    )
    with pytest.raises(ValueError, match="only open"):
        acknowledge(lifecycle, sla, START + timedelta(minutes=2))


def test_resolution_cannot_be_applied_twice() -> None:
    lifecycle, sla, _ = resolve(
        LifecycleState(IncidentStatus.OPEN),
        build_sla_state(START, POLICY),
        START + timedelta(minutes=1),
    )
    with pytest.raises(ValueError, match="only open or acknowledged"):
        resolve(lifecycle, sla, START + timedelta(minutes=2))


def test_lifecycle_rejects_reverse_timestamp_order() -> None:
    with pytest.raises(ValueError, match="resolution cannot precede"):
        LifecycleState(
            IncidentStatus.RESOLVED,
            acknowledged_at=START + timedelta(minutes=2),
            resolved_at=START + timedelta(minutes=1),
        ).validate()
    with pytest.raises(ValueError, match="closure cannot precede"):
        LifecycleState(
            IncidentStatus.CLOSED,
            acknowledged_at=START,
            resolved_at=START + timedelta(minutes=2),
            closed_at=START + timedelta(minutes=1),
        ).validate()


def test_sla_rejects_non_deadline_breach_evidence() -> None:
    state = build_sla_state(START, POLICY)
    with pytest.raises(ValueError, match="response breach evidence"):
        SLAState(
            started_at=state.started_at,
            response_deadline=state.response_deadline,
            resolution_deadline=state.resolution_deadline,
            response_breached_at=state.response_deadline + timedelta(seconds=1),
        ).validate()


def test_sla_rejects_breach_evidence_for_an_on_time_action() -> None:
    state = build_sla_state(START, POLICY)
    with pytest.raises(ValueError, match="on-time acknowledgement"):
        SLAState(
            started_at=state.started_at,
            response_deadline=state.response_deadline,
            resolution_deadline=state.resolution_deadline,
            acknowledged_at=state.response_deadline,
            response_breached_at=state.response_deadline,
        ).validate()


def test_sla_rejects_late_action_without_breach_evidence() -> None:
    state = build_sla_state(START, POLICY)
    with pytest.raises(ValueError, match="late acknowledgement"):
        SLAState(
            started_at=state.started_at,
            response_deadline=state.response_deadline,
            resolution_deadline=state.resolution_deadline,
            acknowledged_at=state.response_deadline + timedelta(seconds=1),
        ).validate()
    with pytest.raises(ValueError, match="late resolution"):
        SLAState(
            started_at=state.started_at,
            response_deadline=state.response_deadline,
            resolution_deadline=state.resolution_deadline,
            acknowledged_at=state.response_deadline,
            resolved_at=state.resolution_deadline + timedelta(seconds=1),
        ).validate()
