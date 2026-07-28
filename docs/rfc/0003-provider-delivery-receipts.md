# RFC-0003: Provider Delivery Receipts and Stronger Deduplication

- **Status:** Draft
- **Created:** 2026-07-27
- **Target version:** Unscheduled

## Summary

Extend the at-least-once outbox with provider-specific idempotency, submission identifiers, and signed delivery webhooks. The purpose is to reduce duplicates and improve outcome evidence, not to claim universal exactly-once delivery.

## Current boundary

A worker can submit a message and crash before recording `sent`. The lease later expires and another worker may submit the same deduplication key again. This is correct at-least-once behavior.

## Proposed direction

- Add transport attempt rows rather than overloading one outbox row with provider history.
- Pass the stable deduplication key to providers that support idempotency keys.
- Persist provider submission identifiers and sanitized responses.
- Validate signed asynchronous webhooks and record delivered, bounced, or rejected evidence.
- Make provider capabilities explicit; transports without idempotency remain at least once.

## Non-goal

Do not advertise exactly-once email or webhook consumption. Local state and an external provider cannot generally share one atomic commit.

## Acceptance criteria

A transport contract, fake-provider integration suite, duplicate/reordered webhook tests, privacy retention policy, and operator recovery workflow are required.
