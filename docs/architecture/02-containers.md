# C4 Level 2 — Containers

```mermaid
flowchart LR
    Actor[Authenticated actor]
    Operator[Operator]
    API[FastAPI API\ncommands, queries, health]
    Worker[Evaluator and outbox worker\nperiodic bounded batches]
    CLI[Administrative CLI\nlocal user provisioning]
    DB[(PostgreSQL\nincidents, SLA snapshots, events,\nreceipts, outbox, triggers)]
    SMTP[Console or SMTP transport]

    Actor -->|HTTPS at deployment boundary| API
    Operator -->|local command| CLI
    API -->|transactions and PostgreSQL clock| DB
    Worker -->|SKIP LOCKED transactions and PostgreSQL clock| DB
    CLI -->|user transaction| DB
    Worker -->|at-least-once message| SMTP
```

## Container responsibilities

| Container | Responsibility | Explicit exclusion |
|---|---|---|
| API | Authenticate, authorize, validate, execute aggregate commands, serve queries | Scheduling, external side effects, public registration |
| Worker | Detect overdue objectives, lease outbox rows, invoke transport | Owning incident policy or changing lifecycle |
| CLI | Owner-controlled initial user provisioning | Public user administration |
| PostgreSQL | Transactional state, locks, shared clock, constraints, history, receipts, outbox | External-message acknowledgement |
| Transport | Console evidence or SMTP submission | Exactly-once consumption guarantee |
