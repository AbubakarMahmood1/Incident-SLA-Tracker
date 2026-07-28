# RFC-0001: Business Calendars, Pauses, and Deadline Rebasing

- **Status:** Draft
- **Created:** 2026-07-27
- **Target version:** Unscheduled

## Summary

Define how SLA elapsed time behaves outside business hours, during approved pauses, and after an explicit policy correction. Version 1 uses continuous elapsed time and immutable deadlines.

## Motivation

Real support agreements often exclude weekends, maintenance windows, or periods waiting on a requester. Adding a boolean `paused` flag would be inadequate because historical calculations, concurrent commands, and breach evidence must remain explainable.

## Proposed direction

- Version business calendars and snapshot the calendar identifier with each incident.
- Represent pauses as append-only intervals with actor, reason, start, and end.
- Derive an effective elapsed duration rather than mutating historical start time.
- Treat a policy correction as a compensating rebase event, never a silent update.
- Specify whether an already-breached objective can be unbreached; the default proposal is **no**.

## Required design work

- Calendar timezone and daylight-saving behavior
- Overlapping and open pause intervals
- Idempotent pause/resume commands
- Worker locks while a pause command races with evaluation
- Migration of active incidents
- Query performance and reproducible deadline explanation

## Acceptance criteria

The RFC may be accepted only with a pure calculation model, migration plan, property tests across timezone transitions, PostgreSQL concurrency tests, and an operator-visible explanation of every derived deadline.
