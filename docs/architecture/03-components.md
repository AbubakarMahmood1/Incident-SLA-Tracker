# C4 Level 3 — Components

```mermaid
flowchart TB
    subgraph API[FastAPI process]
      Routes[HTTP routes and dependencies]
      Auth[JWT and Argon2 boundary]
      IncidentSvc[IncidentService\ncommand aggregate]
      Domain[Pure SLA and lifecycle domain]
      Eval[SLA evaluation service]
      Outbox[Outbox service]
      Transport[Console / SMTP adapter]
      ORM[SQLAlchemy models and sessions]
    end

    DB[(PostgreSQL)]

    Routes --> Auth
    Routes --> IncidentSvc
    IncidentSvc --> Domain
    IncidentSvc --> Eval
    IncidentSvc --> ORM
    Eval --> Domain
    Eval --> ORM
    Outbox --> ORM
    Outbox --> Transport
    ORM --> DB
```

## Important dependency directions

- Pure domain code does not import FastAPI, SQLAlchemy, or transport code.
- Route functions delegate mutation semantics to services rather than editing ORM objects directly.
- The evaluator and command service call the same deadline functions.
- Outbox publication occurs in the breach transaction, while external delivery occurs later.
- Transport adapters do not decide whether a breach exists.
