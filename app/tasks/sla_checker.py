"""Background tasks for SLA breach checking."""

from datetime import timedelta

from sqlalchemy import and_, or_, select

from app.config import settings
from app.models import Incident, SLA, SLAStatus, User
from app.tasks.celery_app import celery_app
from app.tasks.notifications import send_sla_breach_notification
from app.utils import utc_now


@celery_app.task(name="app.tasks.sla_checker.check_sla_breaches")
def check_sla_breaches() -> dict:
    """Check for SLA breaches and send notifications.

    This task runs periodically (every 5 minutes) to check for:
    - Response deadline breaches
    - Resolution deadline breaches

    Returns:
        dict: Summary of breaches detected
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    # Create synchronous engine for Celery task
    sync_db_url = settings.database_url.replace("+asyncpg", "")
    engine = create_engine(sync_db_url)

    breaches_detected = 0
    notifications_sent = 0

    try:
        with Session(engine) as session:
            now = utc_now()

            # Query for active SLAs that are breached
            stmt = (
                select(SLA, Incident, User)
                .join(Incident, SLA.incident_id == Incident.id)
                .outerjoin(User, Incident.assignee_id == User.id)
                .where(
                    and_(
                        SLA.status == SLAStatus.ACTIVE,
                        or_(
                            # Response deadline breached
                            and_(
                                SLA.response_at.is_(None),
                                SLA.response_deadline < now,
                            ),
                            # Resolution deadline breached
                            and_(
                                SLA.resolution_deadline < now,
                                Incident.resolved_at.is_(None),
                            ),
                        ),
                        SLA.breach_notified_at.is_(None),  # Not yet notified
                    )
                )
            )

            results = session.execute(stmt).all()

            for sla, incident, assignee in results:
                breaches_detected += 1

                # Mark SLA as breached
                sla.status = SLAStatus.BREACHED
                sla.breach_notified_at = now

                # Determine breach type
                breach_type = "Response" if not sla.response_at else "Resolution"

                # Send notification to assignee if exists
                if assignee and assignee.email:
                    send_sla_breach_notification.delay(
                        incident_id=str(incident.id),
                        assignee_email=assignee.email,
                        breach_type=breach_type,
                    )
                    notifications_sent += 1

            session.commit()

    except Exception as e:
        print(f"Error checking SLA breaches: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
        }
    finally:
        engine.dispose()

    return {
        "status": "success",
        "breaches_detected": breaches_detected,
        "notifications_sent": notifications_sent,
    }


@celery_app.task(name="app.tasks.sla_checker.check_approaching_deadlines")
def check_approaching_deadlines() -> dict:
    """Check for approaching SLA deadlines and send warnings.

    This task runs periodically (every 15 minutes) to check for:
    - Resolution deadlines within 1 hour for critical/high priority
    - Resolution deadlines within 4 hours for medium/low priority

    Returns:
        dict: Summary of warnings sent
    """
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session

    from app.models import IncidentPriority

    # Create synchronous engine for Celery task
    sync_db_url = settings.database_url.replace("+asyncpg", "")
    engine = create_engine(sync_db_url)

    warnings_sent = 0

    try:
        with Session(engine) as session:
            now = utc_now()

            # Check for approaching deadlines
            # Critical/High: warn 1 hour before
            # Medium/Low: warn 4 hours before
            stmt = (
                select(SLA, Incident, User)
                .join(Incident, SLA.incident_id == Incident.id)
                .outerjoin(User, Incident.assignee_id == User.id)
                .where(
                    and_(
                        SLA.status == SLAStatus.ACTIVE,
                        Incident.resolved_at.is_(None),
                        or_(
                            # Critical/High priority - 1 hour warning
                            and_(
                                Incident.priority.in_(
                                    [IncidentPriority.CRITICAL, IncidentPriority.HIGH]
                                ),
                                SLA.resolution_deadline > now,
                                SLA.resolution_deadline
                                <= now + timedelta(hours=1),
                            ),
                            # Medium/Low priority - 4 hour warning
                            and_(
                                Incident.priority.in_(
                                    [IncidentPriority.MEDIUM, IncidentPriority.LOW]
                                ),
                                SLA.resolution_deadline > now,
                                SLA.resolution_deadline
                                <= now + timedelta(hours=4),
                            ),
                        ),
                    )
                )
            )

            results = session.execute(stmt).all()

            for sla, incident, assignee in results:
                # Send notification to assignee if exists
                if assignee and assignee.email:
                    from app.tasks.notifications import (
                        send_approaching_deadline_notification,
                    )

                    time_remaining = sla.resolution_deadline - now
                    send_approaching_deadline_notification.delay(
                        incident_id=str(incident.id),
                        assignee_email=assignee.email,
                        time_remaining_minutes=int(time_remaining.total_seconds() // 60),
                    )
                    warnings_sent += 1

    except Exception as e:
        print(f"Error checking approaching deadlines: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
        }
    finally:
        engine.dispose()

    return {
        "status": "success",
        "warnings_sent": warnings_sent,
    }
