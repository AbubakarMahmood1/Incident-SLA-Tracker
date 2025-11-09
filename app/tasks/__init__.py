"""Tasks package for background jobs."""

from app.tasks.celery_app import celery_app
from app.tasks.notifications import (
    send_approaching_deadline_notification,
    send_incident_created_email,
    send_incident_resolved_email,
    send_sla_breach_notification,
)
from app.tasks.sla_checker import check_approaching_deadlines, check_sla_breaches

__all__ = [
    "celery_app",
    "check_sla_breaches",
    "check_approaching_deadlines",
    "send_incident_created_email",
    "send_sla_breach_notification",
    "send_approaching_deadline_notification",
    "send_incident_resolved_email",
]
