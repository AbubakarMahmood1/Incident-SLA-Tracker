# Documentation Governance

## Purpose

Documentation is part of the project contract only when it stays connected to code, tests, evidence, and decisions. The goal is not to imitate bureaucracy or inflate page count.

## Document roles

| Document | Role | Update trigger |
|---|---|---|
| README | Public orientation, truthful status, quick start | Any public scope, evidence, or setup change |
| Spirit | Bounded thesis and kill condition | Product identity changes |
| SRS | Stable requirements and exclusions | Accepted behavior or quality requirement changes |
| Traceability | Requirement-to-code/test/evidence map | Any requirement, implementation, or evidence change |
| C4 views | Current architecture at useful levels | Container, component, integration, or deployment changes |
| ADR | Accepted architectural decision and trade-offs | New or superseding architecture choice |
| RFC | Material proposal not yet part of current claims | Significant proposed capability or contract change |
| Contracts | Exact API/data semantics | Interface or schema change |
| Security | Trust boundaries and known limitations | Auth, authorization, data, transport, or deployment change |
| Operations | Run and recover the current design | Migration, worker, deployment, or recovery change |
| Claims ledger | Separates observed, configured, pending, rejected | Every verification run or public claim change |
| Definition of done | Closure and kill gates | Evidence policy or release scope change |

## Change rules

- Requirement identifiers are never silently reused.
- A behavior-changing pull request updates SRS, traceability, tests, and claims together.
- ADRs remain after supersession and link to the replacing record.
- RFCs are not listed as features.
- Diagram source is canonical; rendered images, if added, identify their source revision.
- Evidence records include command, environment, revision, date, and limitations.
- Generated reports are not committed unless they are durable evidence with provenance.

## Standards language

The SRS uses familiar requirements-engineering concepts and stable traceability, but the repository does not claim certification or audited compliance with an IEEE, ISO, regulatory, or safety standard.

## Why no KEPs

Kubernetes Enhancement Proposals are suited to changes coordinated across a large, multi-team project with staged graduation, compatibility, release, and production-readiness governance. This repository has one maintainer and one bounded service. ADRs plus RFCs provide the needed history without duplicating a governance system the project does not possess.

Reconsider a KEP-like process only if the project becomes a multi-team platform with formal release trains, feature graduation, compatibility/version-skew policy, and named owner groups.

## Review cadence

Before any public release or portfolio refresh:

1. compare README claims with the claims ledger;
2. run link, requirement, and index validation;
3. render C4 diagrams;
4. remove stale setup instructions;
5. confirm future RFCs are not phrased as current behavior; and
6. decide whether the repository still meets its kill condition.
