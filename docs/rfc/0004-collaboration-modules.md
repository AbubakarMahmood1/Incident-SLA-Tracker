# RFC-0004: Collaboration Modules

- **Status:** Draft
- **Created:** 2026-07-27
- **Target version:** Unscheduled

## Summary

Decide whether comments and attachments should return as bounded modules, be delegated to external systems, or remain excluded.

## Motivation

The original repository advertised comments and attachments, but their presence did not strengthen the SLA-transition proof and introduced content moderation, storage, malware, authorization, retention, and privacy obligations.

## Options

1. **Remain excluded.** Keep the repository focused on lifecycle and evidence.
2. **Text-only internal notes.** Append immutable note events with strict visibility and size limits.
3. **External references.** Store validated links or opaque identifiers to a document system.
4. **Managed object storage.** Add signed upload/download flows, scanning, retention, checksums, and deletion policy.

## Decision criteria

- Clear user value beyond portfolio feature count
- No dilution of the incident/SLA thesis
- Explicit authorization and tenant implications
- Safe content handling and retention
- Bounded acceptance tests and operational cost

## Acceptance criteria

The RFC must select one option, define its trust boundary, and show why the added maintenance burden is justified. No generic attachment upload endpoint is acceptable.
