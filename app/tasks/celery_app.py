"""Celery application configuration."""

from celery import Celery
from celery.schedules import crontab

from app.config import settings

# Create Celery app
celery_app = Celery(
    "incident_sla_tracker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
)

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60,  # 30 minutes
    task_soft_time_limit=25 * 60,  # 25 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=1000,
)

# Periodic task schedule
celery_app.conf.beat_schedule = {
    "check-sla-breaches": {
        "task": "app.tasks.sla_checker.check_sla_breaches",
        "schedule": crontab(minute="*/5"),  # Every 5 minutes
    },
    "check-approaching-deadlines": {
        "task": "app.tasks.sla_checker.check_approaching_deadlines",
        "schedule": crontab(minute="*/15"),  # Every 15 minutes
    },
}

# Auto-discover tasks
celery_app.autodiscover_tasks(["app.tasks"])
