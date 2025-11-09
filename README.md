# Incident & SLA Tracker

[![CI/CD Pipeline](https://github.com/AbubakarMahmood1/Incident-SLA-Tracker/actions/workflows/ci.yml/badge.svg)](https://github.com/AbubakarMahmood1/Incident-SLA-Tracker/actions)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-green.svg)](https://fastapi.tiangolo.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Production-ready Python FastAPI application for incident and SLA tracking with background jobs, observability, and E2E testing.

## 🚀 Features

### Core Functionality
- **Incident Management**: Full CRUD operations for incidents with priority levels (Critical, High, Medium, Low)
- **SLA Tracking**: Automatic SLA assignment based on priority with breach detection
- **Comments & Attachments**: Support for incident documentation and file uploads
- **User Management**: Authentication and authorization with JWT tokens

### Background Processing
- **Celery Workers**: Distributed task processing for SLA checks and notifications
- **Scheduled Tasks**:
  - SLA breach detection (every 5 minutes)
  - Approaching deadline warnings (every 15 minutes)
- **Email Notifications**:
  - Incident creation alerts
  - SLA breach notifications
  - Approaching deadline warnings
  - Resolution confirmations

### Observability
- **OpenTelemetry**: Distributed tracing for FastAPI, SQLAlchemy, and Celery
- **Grafana**: Pre-configured dashboards for visualization
- **Prometheus**: Metrics collection and alerting
- **Tempo**: Distributed trace storage and analysis

### Testing & Quality
- **Unit Tests**: Service layer and business logic testing
- **Integration Tests**: API endpoint testing with real database
- **E2E Tests**: Playwright-based critical flow testing
- **Code Quality**: Black, Ruff, MyPy for linting and type checking
- **CI/CD**: GitHub Actions pipeline with automated testing

## 🏗️ Architecture

```
incident-sla-tracker/
├── app/
│   ├── api/              # API routes and endpoints
│   ├── models/           # SQLAlchemy ORM models
│   ├── schemas/          # Pydantic request/response schemas
│   ├── services/         # Business logic layer
│   ├── tasks/            # Celery background tasks
│   ├── telemetry/        # OpenTelemetry instrumentation
│   ├── utils/            # Utility functions
│   ├── config.py         # Application configuration
│   ├── database.py       # Database setup
│   └── main.py           # FastAPI application
├── tests/
│   ├── unit/             # Unit tests
│   ├── integration/      # Integration tests
│   └── e2e/              # End-to-end tests
├── docker/               # Docker configurations
├── alembic/              # Database migrations
└── .github/              # CI/CD workflows
```

## 📋 Prerequisites

- Python 3.11+
- PostgreSQL 15+
- Redis 7+
- Docker & Docker Compose (optional)

## 🛠️ Installation

### Local Development

1. **Clone the repository**
```bash
git clone https://github.com/AbubakarMahmood1/Incident-SLA-Tracker.git
cd Incident-SLA-Tracker
```

2. **Create virtual environment**
```bash
python3.11 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Set up environment variables**
```bash
cp .env.example .env
# Edit .env with your configuration
```

5. **Run database migrations**
```bash
alembic upgrade head
```

6. **Start the application**
```bash
# Terminal 1: FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Terminal 2: Celery worker
celery -A app.tasks.celery_app worker --loglevel=info

# Terminal 3: Celery beat scheduler
celery -A app.tasks.celery_app beat --loglevel=info
```

### Docker Deployment

1. **Start all services**
```bash
docker-compose up -d
```

2. **Check service status**
```bash
docker-compose ps
```

3. **View logs**
```bash
docker-compose logs -f
```

4. **Access services**
- **API**: http://localhost:8000
- **API Docs**: http://localhost:8000/api/docs
- **Grafana**: http://localhost:3000 (admin/admin)
- **Prometheus**: http://localhost:9090
- **Tempo**: http://localhost:3200

## 🎯 Quick Start

### Create an Incident

```bash
curl -X POST "http://localhost:8000/api/v1/incidents" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{
    "title": "Production API Down",
    "description": "The main API endpoint is returning 503 errors",
    "priority": "critical"
  }'
```

### List Incidents

```bash
curl -X GET "http://localhost:8000/api/v1/incidents?status=open&priority=critical" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Update Incident Status

```bash
curl -X POST "http://localhost:8000/api/v1/incidents/{incident_id}/status" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -d '{"status": "resolved"}'
```

## 🧪 Testing

### Run All Tests
```bash
make test
```

### Run Specific Test Suites
```bash
# Unit tests only
make test-unit

# Integration tests only
make test-integration

# E2E tests only
make test-e2e
```

### Code Quality
```bash
# Run linters
make lint

# Format code
make format
```

## 📊 SLA Configuration

Default SLA deadlines by priority:

| Priority | Response Time | Resolution Time |
|----------|--------------|-----------------|
| Critical | 1 hour       | 4 hours         |
| High     | 4 hours      | 24 hours        |
| Medium   | 8 hours      | 72 hours        |
| Low      | 24 hours     | 7 days          |

Configure custom SLA times in `.env`:
```bash
SLA_CRITICAL_RESPONSE=1
SLA_CRITICAL_RESOLUTION=4
SLA_HIGH_RESPONSE=4
SLA_HIGH_RESOLUTION=24
# ... etc
```

## 🔧 Configuration

### Environment Variables

See `.env.example` for all available configuration options:

- **Application**: `APP_NAME`, `APP_ENV`, `DEBUG`
- **Database**: `DATABASE_URL`, `DATABASE_POOL_SIZE`
- **Redis/Celery**: `REDIS_URL`, `CELERY_BROKER_URL`
- **Email**: `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`
- **SLA**: `SLA_*_RESPONSE`, `SLA_*_RESOLUTION`
- **OpenTelemetry**: `OTEL_EXPORTER_OTLP_ENDPOINT`, `OTEL_SERVICE_NAME`
- **Security**: `SECRET_KEY`, `ALGORITHM`

## 📈 Monitoring & Observability

### Grafana Dashboards

Access Grafana at http://localhost:3000 (default: admin/admin)

Pre-configured data sources:
- **Prometheus**: Metrics and alerting
- **Tempo**: Distributed tracing

### Key Metrics

- Request latency (p50, p95, p99)
- SLA breach rate
- Incident creation rate
- Background task duration
- Database query performance

### Distributed Tracing

View traces in Grafana → Explore → Tempo:
- API endpoint traces
- Database query traces
- Celery task traces
- Cross-service correlation

## 🚀 Deployment

### Production Checklist

- [ ] Set `DEBUG=false` in production
- [ ] Use strong `SECRET_KEY`
- [ ] Configure proper SMTP credentials
- [ ] Set up SSL/TLS certificates
- [ ] Configure firewall rules
- [ ] Set up database backups
- [ ] Configure log aggregation
- [ ] Set up monitoring alerts
- [ ] Review CORS origins
- [ ] Enable database connection pooling

### Deployment Platforms

**Render/Fly.io/Railway**:
1. Connect GitHub repository
2. Set environment variables
3. Deploy API, Worker, and Beat as separate services
4. Add PostgreSQL and Redis add-ons

**Docker/Kubernetes**:
```bash
# Build image
docker build -t incident-sla-tracker:latest .

# Push to registry
docker tag incident-sla-tracker:latest your-registry/incident-sla-tracker:latest
docker push your-registry/incident-sla-tracker:latest

# Deploy with docker-compose or Kubernetes manifests
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Write tests for new features
- Update documentation
- Use type hints throughout
- Format code with Black
- Check types with MyPy
- Lint with Ruff

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Task queue by [Celery](https://docs.celeryproject.org/)
- Observability with [OpenTelemetry](https://opentelemetry.io/)
- Testing with [Pytest](https://pytest.org/) and [Playwright](https://playwright.dev/)

## 📞 Support

For support, email support@example.com or open an issue on GitHub.

## 🗺️ Roadmap

- [ ] Web UI with React/Vue
- [ ] Mobile app integration
- [ ] Advanced analytics dashboard
- [ ] AI-powered incident categorization
- [ ] Multi-tenancy support
- [ ] Slack/Teams integration
- [ ] Custom SLA rules engine
- [ ] Historical reporting

---

**Built with ❤️ using FastAPI, Celery, and OpenTelemetry**

For detailed implementation guide, see [CLAUDE.md](CLAUDE.md)
