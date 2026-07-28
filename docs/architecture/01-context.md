# C4 Level 1 — System Context

```mermaid
flowchart LR
    Reporter[Reporter\ncreates and closes incidents]
    Assignee[Assignee\nacknowledges and resolves]
    Admin[Administrator\nprovisions and assigns]
    Operator[Repository operator\nmigrates and recovers]
    System[Incident SLA Ledger\nauditable SLA transitions]
    Notify[Notification recipient / provider]

    Reporter -->|JWT-authenticated commands and queries| System
    Assignee -->|JWT-authenticated lifecycle commands| System
    Admin -->|assignment and privileged commands| System
    Operator -->|CLI, migration, worker operation| System
    System -->|at-least-once breach envelope with deduplication key| Notify
```

## Boundary notes

- Authentication identifies an owner-provisioned principal; it is not a full identity-management product.
- Notification providers are outside the PostgreSQL transaction and may observe duplicates.
- The operator controls database and SMTP credentials and is responsible for transport TLS, backups, and clock discipline.
