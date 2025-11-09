# Incident-SLA-Tracker
Python FastAPI “Incident & SLA Tracker” (Celery/Background tasks, Playwright E2E)

Why it matters: Python is surging and FastAPI shows uptrend; pairing it with background jobs, a queue, and E2E tests demonstrates production thinking. 
Stack Overflow
+1

What you’ll ship:

FastAPI services: incidents, SLAs, comments, file attachments

Background jobs (SLA breach checks, email notifications) via Celery/Redis or FastAPI tasks

Postgres + Alembic

Observability: OpenTelemetry SDK + dockerized Grafana/Prometheus/Tempo stack

E2E: Playwright runs critical flows in CI (create incident → breach clock → notify)
Roadmap:

Schemas + simplest endpoints → 2) background jobs → 3) OTel traces → 4) Playwright suite → 5) deploy (Render/Fly/Hetzner).
Hiring story: “I built an operational Python service with SLO/SLA logic, E2E tests, and tracing.” (Playwright is a strong signal; OTel is an emerging must‑have.)
