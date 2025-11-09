"""Background tasks for sending notifications."""

from typing import Any

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Incident, SLA, User
from app.services.notification_service import NotificationService
from app.tasks.celery_app import celery_app


@celery_app.task(name="app.tasks.notifications.send_incident_created_email")
def send_incident_created_email(incident_id: str, assignee_email: str) -> bool:
    """Send email notification when an incident is created.

    Args:
        incident_id: Incident ID
        assignee_email: Assignee email address

    Returns:
        bool: True if sent successfully
    """
    # Create synchronous engine for Celery task
    sync_db_url = settings.database_url.replace("+asyncpg", "")
    engine = create_engine(sync_db_url)

    try:
        with Session(engine) as session:
            # Fetch incident with SLA
            stmt = select(Incident, SLA).outerjoin(SLA).where(Incident.id == incident_id)
            result = session.execute(stmt).first()

            if not result:
                print(f"Incident {incident_id} not found")
                return False

            incident, sla = result

            # Prepare incident data
            incident_data = {
                "title": incident.title,
                "description": incident.description,
                "priority": incident.priority.value,
                "status": incident.status.value,
                "response_deadline": (
                    sla.response_deadline.isoformat() if sla else "N/A"
                ),
                "resolution_deadline": (
                    sla.resolution_deadline.isoformat() if sla else "N/A"
                ),
            }

            # Generate email content
            subject, html_content = NotificationService.get_incident_created_email(
                incident_data
            )

            # Send email
            return NotificationService.send_email_sync(
                assignee_email, subject, html_content
            )

    except Exception as e:
        print(f"Error sending incident created email: {str(e)}")
        return False
    finally:
        engine.dispose()


@celery_app.task(name="app.tasks.notifications.send_sla_breach_notification")
def send_sla_breach_notification(
    incident_id: str, assignee_email: str, breach_type: str = "Resolution"
) -> bool:
    """Send email notification when an SLA is breached.

    Args:
        incident_id: Incident ID
        assignee_email: Assignee email address
        breach_type: Type of breach (Response or Resolution)

    Returns:
        bool: True if sent successfully
    """
    # Create synchronous engine for Celery task
    sync_db_url = settings.database_url.replace("+asyncpg", "")
    engine = create_engine(sync_db_url)

    try:
        with Session(engine) as session:
            # Fetch incident with SLA
            stmt = select(Incident, SLA).join(SLA).where(Incident.id == incident_id)
            result = session.execute(stmt).first()

            if not result:
                print(f"Incident {incident_id} not found")
                return False

            incident, sla = result

            # Calculate time breached
            from app.utils import utc_now

            now = utc_now()
            if breach_type == "Response":
                time_breached = now - sla.response_deadline
            else:
                time_breached = now - sla.resolution_deadline

            # Prepare incident data
            incident_data = {
                "title": incident.title,
                "priority": incident.priority.value,
                "status": incident.status.value,
                "breach_type": breach_type,
                "response_deadline": sla.response_deadline.isoformat(),
                "resolution_deadline": sla.resolution_deadline.isoformat(),
                "time_breached": str(time_breached),
            }

            # Generate email content
            subject, html_content = NotificationService.get_sla_breach_email(
                incident_data
            )

            # Send email
            return NotificationService.send_email_sync(
                assignee_email, subject, html_content
            )

    except Exception as e:
        print(f"Error sending SLA breach notification: {str(e)}")
        return False
    finally:
        engine.dispose()


@celery_app.task(name="app.tasks.notifications.send_approaching_deadline_notification")
def send_approaching_deadline_notification(
    incident_id: str, assignee_email: str, time_remaining_minutes: int
) -> bool:
    """Send email notification when SLA deadline is approaching.

    Args:
        incident_id: Incident ID
        assignee_email: Assignee email address
        time_remaining_minutes: Time remaining in minutes

    Returns:
        bool: True if sent successfully
    """
    # Create synchronous engine for Celery task
    sync_db_url = settings.database_url.replace("+asyncpg", "")
    engine = create_engine(sync_db_url)

    try:
        with Session(engine) as session:
            # Fetch incident with SLA
            stmt = select(Incident, SLA).join(SLA).where(Incident.id == incident_id)
            result = session.execute(stmt).first()

            if not result:
                print(f"Incident {incident_id} not found")
                return False

            incident, sla = result

            # Format time remaining
            hours = time_remaining_minutes // 60
            minutes = time_remaining_minutes % 60
            time_remaining_str = f"{hours}h {minutes}m" if hours > 0 else f"{minutes}m"

            # Prepare incident data
            incident_data = {
                "title": incident.title,
                "priority": incident.priority.value,
                "status": incident.status.value,
                "resolution_deadline": sla.resolution_deadline.isoformat(),
                "time_remaining": time_remaining_str,
            }

            # Generate email content
            subject, html_content = NotificationService.get_approaching_deadline_email(
                incident_data
            )

            # Send email
            return NotificationService.send_email_sync(
                assignee_email, subject, html_content
            )

    except Exception as e:
        print(f"Error sending approaching deadline notification: {str(e)}")
        return False
    finally:
        engine.dispose()


@celery_app.task(name="app.tasks.notifications.send_incident_resolved_email")
def send_incident_resolved_email(incident_id: str, reporter_email: str) -> bool:
    """Send email notification when an incident is resolved.

    Args:
        incident_id: Incident ID
        reporter_email: Reporter email address

    Returns:
        bool: True if sent successfully
    """
    # Create synchronous engine for Celery task
    sync_db_url = settings.database_url.replace("+asyncpg", "")
    engine = create_engine(sync_db_url)

    try:
        with Session(engine) as session:
            # Fetch incident with SLA
            stmt = select(Incident, SLA).join(SLA).where(Incident.id == incident_id)
            result = session.execute(stmt).first()

            if not result:
                print(f"Incident {incident_id} not found")
                return False

            incident, sla = result

            # Calculate resolution time
            if incident.resolved_at and incident.created_at:
                resolution_time = incident.resolved_at - incident.created_at
                resolution_time_str = str(resolution_time)
            else:
                resolution_time_str = "N/A"

            # Check if SLA was met
            from app.models import SLAStatus

            sla_met = "Yes" if sla.status == SLAStatus.MET else "No"

            # Prepare incident data
            incident_data = {
                "title": incident.title,
                "priority": incident.priority.value,
                "resolution_time": resolution_time_str,
                "sla_met": sla_met,
                "resolution_deadline": sla.resolution_deadline.isoformat(),
            }

            # Generate email content
            subject, html_content = NotificationService.get_incident_resolved_email(
                incident_data
            )

            # Send email
            return NotificationService.send_email_sync(
                reporter_email, subject, html_content
            )

    except Exception as e:
        print(f"Error sending incident resolved email: {str(e)}")
        return False
    finally:
        engine.dispose()
