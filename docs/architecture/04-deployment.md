# C4 Deployment View — Supplied Compose Topology

```mermaid
flowchart LR
    subgraph Host[Developer or CI host]
      Port8000[127.0.0.1:8000]

      subgraph Backend[internal backend network]
        Migrate[migrate container\none-shot Alembic]
        API[api container\nnon-root, read-only]
        Worker[worker container\nnon-root, read-only]
        PG[(PostgreSQL 16 container\npersistent volume)]
      end

      subgraph Egress[worker egress network]
        EgressAttachment[worker-only network attachment]
      end

      subgraph Edge[loopback edge bridge]
        Port8000
      end
    end

    SMTP[Optional SMTP provider]

    Port8000 --> API
    Migrate --> PG
    API --> PG
    Worker --> PG
    Worker --- EgressAttachment
    EgressAttachment --> SMTP
```

## Deployment qualifications

- Compose is a development and evidence topology, not a production platform prescription.
- TLS termination, secret injection, backups, process supervision, SMTP trust, and network policy belong to the deployment environment.
- The image and Compose controls were observed in the local candidate smoke gate; they remain development evidence rather than a production deployment prescription.
- PostgreSQL has no published host port in this topology.
- The API edge bridge exists to publish loopback port 8000; it is not a production egress-deny policy.
