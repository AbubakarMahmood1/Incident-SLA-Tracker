# CLAUDE.md - Incident & SLA Tracker

## Project Overview

**Incident & SLA Tracker** is a production-ready Python FastAPI application that manages incidents with Service Level Agreement (SLA) tracking, background job processing, and comprehensive observability.

### Technology Stack

- **API Framework**: FastAPI (Python)
- **Database**: PostgreSQL with Alembic migrations
- **Background Jobs**: Celery + Redis
- **Observability**: OpenTelemetry SDK → Grafana/Prometheus/Tempo
- **E2E Testing**: Playwright
- **Deployment Targets**: Render/Fly.io/Hetzner

### Core Features

1. **Incident Management**: Create, track, and manage incidents
2. **SLA Tracking**: Monitor SLA compliance with breach detection
3. **Comments & Attachments**: Support for incident documentation
4. **Background Processing**:
   - SLA breach checks (scheduled)
   - Email notifications
5. **Observability**: Full tracing and metrics via OpenTelemetry
6. **E2E Testing**: Critical flows tested with Playwright

---

## Development Roadmap

The project follows this implementation sequence:

1. **Phase 1**: Schemas + simplest endpoints (FastAPI models, basic CRUD)
2. **Phase 2**: Background jobs (Celery workers for SLA checks, notifications)
3. **Phase 3**: OpenTelemetry traces (instrumentation, exporters)
4. **Phase 4**: Playwright suite (E2E test automation)
5. **Phase 5**: Deployment (containerization, CI/CD, cloud deployment)

**Current Phase**: Initial setup

---

## Project Structure

```
incident-sla-tracker/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI application entry point
│   ├── config.py               # Configuration management
│   ├── database.py             # Database connection & session
│   ├── models/                 # SQLAlchemy ORM models
│   │   ├── __init__.py
│   │   ├── incident.py
│   │   ├── sla.py
│   │   ├── comment.py
│   │   └── attachment.py
│   ├── schemas/                # Pydantic schemas (request/response)
│   │   ├── __init__.py
│   │   ├── incident.py
│   │   ├── sla.py
│   │   ├── comment.py
│   │   └── attachment.py
│   ├── api/                    # API routes
│   │   ├── __init__.py
│   │   ├── v1/
│   │   │   ├── __init__.py
│   │   │   ├── incidents.py
│   │   │   ├── slas.py
│   │   │   ├── comments.py
│   │   │   └── attachments.py
│   ├── services/               # Business logic layer
│   │   ├── __init__.py
│   │   ├── incident_service.py
│   │   ├── sla_service.py
│   │   └── notification_service.py
│   ├── tasks/                  # Celery background tasks
│   │   ├── __init__.py
│   │   ├── sla_checker.py
│   │   └── notifications.py
│   ├── utils/                  # Utility functions
│   │   ├── __init__.py
│   │   └── datetime_utils.py
│   └── telemetry/              # OpenTelemetry setup
│       ├── __init__.py
│       └── tracing.py
├── tests/
│   ├── __init__.py
│   ├── unit/                   # Unit tests
│   ├── integration/            # Integration tests
│   └── e2e/                    # Playwright E2E tests
│       └── test_incident_flow.py
├── alembic/                    # Database migrations
│   ├── versions/
│   └── env.py
├── docker/
│   ├── Dockerfile
│   ├── docker-compose.yml      # Local dev stack
│   └── docker-compose.observability.yml
├── .env.example
├── requirements.txt
├── pyproject.toml
├── alembic.ini
├── README.md
└── CLAUDE.md                   # This file
```

---

## Development Guidelines

### 1. Code Style & Standards

- **Python Version**: 3.11+
- **Formatter**: `black` (line length: 88)
- **Linter**: `ruff` or `pylint`
- **Type Hints**: Use throughout (enforce with `mypy`)
- **Docstrings**: Google-style docstrings for all public functions

### 2. Database Conventions

- **Migrations**: Always use Alembic for schema changes
- **Naming**: Use snake_case for tables and columns
- **Timestamps**: Include `created_at` and `updated_at` on all models
- **Soft Deletes**: Use `deleted_at` for soft deletion pattern

### 3. API Design

- **Versioning**: Use `/api/v1/` prefix
- **REST Conventions**: Follow standard HTTP methods (GET, POST, PUT, PATCH, DELETE)
- **Response Format**:
  ```json
  {
    "success": true,
    "data": {},
    "message": "Optional message",
    "errors": []
  }
  ```
- **Status Codes**: Use appropriate HTTP status codes
  - 200: Success
  - 201: Created
  - 400: Bad Request
  - 404: Not Found
  - 422: Validation Error
  - 500: Internal Server Error

### 4. SLA Logic

**SLA Priority Levels**:
- **Critical**: Response < 1hr, Resolution < 4hrs
- **High**: Response < 4hrs, Resolution < 24hrs
- **Medium**: Response < 8hrs, Resolution < 72hrs
- **Low**: Response < 24hrs, Resolution < 7 days

**States**:
- `ACTIVE`: SLA is being tracked
- `PAUSED`: Clock stopped (awaiting customer, etc.)
- `BREACHED`: Deadline exceeded
- `MET`: Resolved within SLA

### 5. Background Jobs

**Celery Tasks**:
- `check_sla_breaches`: Runs every 5 minutes, checks for approaching/breached SLAs
- `send_breach_notification`: Triggered when breach detected
- `send_incident_created_email`: On incident creation
- `send_incident_resolved_email`: On resolution

**Task Naming**: Use verb_noun pattern (e.g., `check_sla_breaches`)

### 6. Testing Strategy

**Unit Tests**:
- Test individual functions and methods
- Mock external dependencies
- Coverage target: 80%+

**Integration Tests**:
- Test API endpoints with real database (use test DB)
- Test Celery task execution

**E2E Tests** (Playwright):
- Critical user flows:
  1. Create incident → SLA auto-assigned → background check → breach notification
  2. Add comment to incident
  3. Upload attachment
  4. Resolve incident within SLA

### 7. Observability

**Tracing**:
- Instrument all API endpoints
- Trace database queries
- Trace Celery tasks
- Custom spans for business logic

**Metrics**:
- Request latency (p50, p95, p99)
- SLA breach rate
- Incident creation rate
- Background task duration

**Logs**:
- Structured JSON logging
- Include trace_id and span_id
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

---

## Environment Variables

```bash
# Application
APP_NAME=incident-sla-tracker
APP_ENV=development  # development, staging, production
DEBUG=true

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/incident_tracker
TEST_DATABASE_URL=postgresql://user:password@localhost:5432/incident_tracker_test

# Redis/Celery
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/1

# Email (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
EMAIL_FROM=noreply@incident-tracker.com

# OpenTelemetry
OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
OTEL_SERVICE_NAME=incident-sla-tracker

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
```

---

## Common Development Tasks

### Initial Setup

```bash
# Clone repository
git clone <repository-url>
cd Incident-SLA-Tracker

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy environment file
cp .env.example .env
# Edit .env with your configuration

# Run database migrations
alembic upgrade head

# Start services (Docker)
docker-compose up -d postgres redis

# Run application
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Start Celery worker (separate terminal)
celery -A app.tasks.celery_app worker --loglevel=info

# Start Celery beat (scheduler)
celery -A app.tasks.celery_app beat --loglevel=info
```

### Database Migrations

```bash
# Create new migration
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Running Tests

```bash
# All tests
pytest

# Unit tests only
pytest tests/unit/

# With coverage
pytest --cov=app --cov-report=html

# E2E tests
pytest tests/e2e/

# Install Playwright browsers (first time)
playwright install
```

### Code Quality

```bash
# Format code
black app/ tests/

# Lint
ruff check app/ tests/

# Type checking
mypy app/

# Run all checks
black app/ tests/ && ruff check app/ tests/ && mypy app/ && pytest
```

---

## API Endpoints (Planned)

### Incidents
- `POST /api/v1/incidents` - Create incident
- `GET /api/v1/incidents` - List incidents (with filters)
- `GET /api/v1/incidents/{id}` - Get incident details
- `PATCH /api/v1/incidents/{id}` - Update incident
- `DELETE /api/v1/incidents/{id}` - Soft delete incident
- `POST /api/v1/incidents/{id}/resolve` - Mark as resolved

### SLAs
- `GET /api/v1/incidents/{incident_id}/sla` - Get SLA for incident
- `PATCH /api/v1/slas/{id}/pause` - Pause SLA clock
- `PATCH /api/v1/slas/{id}/resume` - Resume SLA clock

### Comments
- `POST /api/v1/incidents/{incident_id}/comments` - Add comment
- `GET /api/v1/incidents/{incident_id}/comments` - List comments
- `DELETE /api/v1/comments/{id}` - Delete comment

### Attachments
- `POST /api/v1/incidents/{incident_id}/attachments` - Upload file
- `GET /api/v1/attachments/{id}` - Download file
- `DELETE /api/v1/attachments/{id}` - Delete attachment

---

## Database Schema (Core Models)

### Incident
```sql
- id: UUID (primary key)
- title: VARCHAR(255)
- description: TEXT
- status: ENUM('open', 'in_progress', 'resolved', 'closed')
- priority: ENUM('critical', 'high', 'medium', 'low')
- reporter_id: UUID (FK to users)
- assignee_id: UUID (FK to users, nullable)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
- resolved_at: TIMESTAMP (nullable)
- deleted_at: TIMESTAMP (nullable)
```

### SLA
```sql
- id: UUID (primary key)
- incident_id: UUID (FK to incidents)
- response_deadline: TIMESTAMP
- resolution_deadline: TIMESTAMP
- status: ENUM('active', 'paused', 'breached', 'met')
- response_at: TIMESTAMP (nullable)
- paused_at: TIMESTAMP (nullable)
- paused_duration: INTERVAL (accumulated pause time)
- breach_notified_at: TIMESTAMP (nullable)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

### Comment
```sql
- id: UUID (primary key)
- incident_id: UUID (FK to incidents)
- author_id: UUID (FK to users)
- content: TEXT
- is_internal: BOOLEAN (default false)
- created_at: TIMESTAMP
- updated_at: TIMESTAMP
```

### Attachment
```sql
- id: UUID (primary key)
- incident_id: UUID (FK to incidents)
- filename: VARCHAR(255)
- file_path: VARCHAR(500)
- file_size: BIGINT
- mime_type: VARCHAR(100)
- uploaded_by: UUID (FK to users)
- created_at: TIMESTAMP
```

---

## Deployment Considerations

### Docker
- Multi-stage builds for smaller images
- Non-root user for security
- Health checks for orchestration

### Environment-Specific Config
- Use environment variables (12-factor app)
- Secrets management (e.g., AWS Secrets Manager, Vault)

### Monitoring
- Application metrics via Prometheus
- Distributed tracing via Tempo
- Log aggregation (consider ELK/Loki)
- Alerts for SLA breach rate, error rate, latency

### CI/CD Pipeline
```yaml
stages:
  - lint (black, ruff, mypy)
  - test (pytest with coverage)
  - e2e (Playwright tests)
  - build (Docker image)
  - deploy (to staging/production)
```

---

## Working with Claude

### When Adding Features
1. Review this CLAUDE.md for conventions
2. Check existing models/schemas for patterns
3. Create database migration if schema changes
4. Implement service layer logic first
5. Add API endpoint with proper validation
6. Write unit tests (aim for 80%+ coverage)
7. Add integration test for the endpoint
8. Update OpenAPI/Swagger docs (automatic with FastAPI)
9. Consider E2E test if critical flow

### When Fixing Bugs
1. Write a failing test that reproduces the bug
2. Fix the bug
3. Ensure test passes
4. Check for similar issues elsewhere
5. Update documentation if behavior changed

### When Refactoring
1. Ensure comprehensive test coverage first
2. Make small, incremental changes
3. Run tests after each change
4. Maintain backward compatibility for APIs
5. Update migrations carefully (test rollback)

### Questions to Ask
- Does this need a database migration?
- Should this be a background task?
- What happens if this fails? (error handling)
- How will this be traced/monitored?
- What are the security implications?
- Does the API response format match conventions?

---

## Troubleshooting

### Common Issues

**Database Connection Errors**:
- Check DATABASE_URL in .env
- Ensure PostgreSQL is running (`docker-compose ps`)
- Verify migrations are applied (`alembic current`)

**Celery Tasks Not Running**:
- Check Redis connection (REDIS_URL)
- Ensure Celery worker is running
- Check Celery logs for errors
- Verify task is registered (`celery -A app.tasks.celery_app inspect registered`)

**SLA Not Updating**:
- Check Celery Beat scheduler is running
- Verify cron schedule in task definition
- Check background task logs

**OpenTelemetry Not Working**:
- Ensure OTEL_EXPORTER_OTLP_ENDPOINT is correct
- Check if Tempo/Jaeger is running
- Verify instrumentation is initialized in main.py

---

## Resources

- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [Celery Documentation](https://docs.celeryproject.org/)
- [Alembic Tutorial](https://alembic.sqlalchemy.org/en/latest/tutorial.html)
- [OpenTelemetry Python](https://opentelemetry.io/docs/instrumentation/python/)
- [Playwright Python](https://playwright.dev/python/)
- [SQLAlchemy ORM](https://docs.sqlalchemy.org/en/20/orm/)

---

## License

[Specify your license here]

---

**Last Updated**: 2025-11-09
**Maintained By**: Project Team
**Claude Branch**: `claude/initial-setup-claude-md-011CUxkrEfoash3w92v8BsXH`
