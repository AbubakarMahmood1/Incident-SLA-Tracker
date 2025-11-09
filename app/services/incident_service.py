"""Incident service for business logic."""

from datetime import datetime
from typing import Sequence
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.models import Incident, IncidentPriority, IncidentStatus, SLA
from app.schemas import IncidentCreate, IncidentUpdate
from app.utils import add_hours, utc_now


class IncidentService:
    """Service for incident operations."""

    def __init__(self, db: AsyncSession):
        """Initialize the service.

        Args:
            db: Database session
        """
        self.db = db

    async def create_incident(
        self, incident_data: IncidentCreate, reporter_id: UUID
    ) -> Incident:
        """Create a new incident with automatic SLA assignment.

        Args:
            incident_data: Incident creation data
            reporter_id: ID of the user creating the incident

        Returns:
            Incident: Created incident with SLA
        """
        # Create incident
        incident = Incident(
            title=incident_data.title,
            description=incident_data.description,
            priority=incident_data.priority,
            status=IncidentStatus.OPEN,
            reporter_id=reporter_id,
        )
        self.db.add(incident)
        await self.db.flush()

        # Create SLA based on priority
        sla_deadlines = settings.get_sla_deadlines(incident.priority.value)
        now = utc_now()

        sla = SLA(
            incident_id=incident.id,
            response_deadline=add_hours(now, sla_deadlines["response_hours"]),
            resolution_deadline=add_hours(now, sla_deadlines["resolution_hours"]),
        )
        self.db.add(sla)
        await self.db.commit()
        await self.db.refresh(incident)

        return incident

    async def get_incident(self, incident_id: UUID) -> Incident | None:
        """Get an incident by ID with relationships.

        Args:
            incident_id: Incident ID

        Returns:
            Incident | None: Incident if found
        """
        stmt = (
            select(Incident)
            .options(
                selectinload(Incident.reporter),
                selectinload(Incident.assignee),
                selectinload(Incident.sla),
            )
            .where(Incident.id == incident_id, Incident.deleted_at.is_(None))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_incidents(
        self,
        skip: int = 0,
        limit: int = 100,
        status: IncidentStatus | None = None,
        priority: IncidentPriority | None = None,
        assignee_id: UUID | None = None,
        reporter_id: UUID | None = None,
        search: str | None = None,
    ) -> tuple[Sequence[Incident], int]:
        """List incidents with filters and pagination.

        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            status: Filter by status
            priority: Filter by priority
            assignee_id: Filter by assignee
            reporter_id: Filter by reporter
            search: Search in title and description

        Returns:
            tuple: (List of incidents, Total count)
        """
        # Build base query
        stmt = (
            select(Incident)
            .options(
                selectinload(Incident.reporter),
                selectinload(Incident.assignee),
                selectinload(Incident.sla),
            )
            .where(Incident.deleted_at.is_(None))
        )

        # Apply filters
        if status:
            stmt = stmt.where(Incident.status == status)
        if priority:
            stmt = stmt.where(Incident.priority == priority)
        if assignee_id:
            stmt = stmt.where(Incident.assignee_id == assignee_id)
        if reporter_id:
            stmt = stmt.where(Incident.reporter_id == reporter_id)
        if search:
            search_pattern = f"%{search}%"
            stmt = stmt.where(
                or_(
                    Incident.title.ilike(search_pattern),
                    Incident.description.ilike(search_pattern),
                )
            )

        # Get total count
        count_stmt = select(func.count()).select_from(stmt.alias())
        total = await self.db.scalar(count_stmt) or 0

        # Apply pagination
        stmt = stmt.order_by(Incident.created_at.desc()).offset(skip).limit(limit)

        # Execute query
        result = await self.db.execute(stmt)
        incidents = result.scalars().all()

        return incidents, total

    async def update_incident(
        self, incident_id: UUID, incident_data: IncidentUpdate
    ) -> Incident | None:
        """Update an incident.

        Args:
            incident_id: Incident ID
            incident_data: Update data

        Returns:
            Incident | None: Updated incident if found
        """
        incident = await self.get_incident(incident_id)
        if not incident:
            return None

        # Update fields
        update_data = incident_data.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(incident, field, value)

        await self.db.commit()
        await self.db.refresh(incident)
        return incident

    async def assign_incident(
        self, incident_id: UUID, assignee_id: UUID
    ) -> Incident | None:
        """Assign an incident to a user.

        Args:
            incident_id: Incident ID
            assignee_id: Assignee user ID

        Returns:
            Incident | None: Updated incident if found
        """
        incident = await self.get_incident(incident_id)
        if not incident:
            return None

        incident.assignee_id = assignee_id
        if incident.status == IncidentStatus.OPEN:
            incident.status = IncidentStatus.IN_PROGRESS

        await self.db.commit()
        await self.db.refresh(incident)
        return incident

    async def update_status(
        self, incident_id: UUID, status: IncidentStatus
    ) -> Incident | None:
        """Update incident status.

        Args:
            incident_id: Incident ID
            status: New status

        Returns:
            Incident | None: Updated incident if found
        """
        incident = await self.get_incident(incident_id)
        if not incident:
            return None

        incident.status = status

        # Set resolved_at if resolving
        if status == IncidentStatus.RESOLVED and not incident.resolved_at:
            incident.resolved_at = utc_now()

            # Update SLA status if exists
            if incident.sla:
                from app.models import SLAStatus

                incident.sla.status = SLAStatus.MET

        # Set closed_at if closing
        if status == IncidentStatus.CLOSED and not incident.closed_at:
            incident.closed_at = utc_now()

        await self.db.commit()
        await self.db.refresh(incident)
        return incident

    async def delete_incident(self, incident_id: UUID) -> bool:
        """Soft delete an incident.

        Args:
            incident_id: Incident ID

        Returns:
            bool: True if deleted, False if not found
        """
        incident = await self.get_incident(incident_id)
        if not incident:
            return False

        incident.deleted_at = utc_now()
        await self.db.commit()
        return True

    async def get_incident_stats(self, user_id: UUID | None = None) -> dict:
        """Get incident statistics.

        Args:
            user_id: Optional user ID to filter stats

        Returns:
            dict: Statistics dictionary
        """
        base_query = select(Incident).where(Incident.deleted_at.is_(None))

        if user_id:
            base_query = base_query.where(
                or_(
                    Incident.reporter_id == user_id,
                    Incident.assignee_id == user_id,
                )
            )

        # Total incidents
        total = await self.db.scalar(select(func.count()).select_from(base_query.alias()))

        # By status
        open_count = await self.db.scalar(
            select(func.count()).select_from(
                base_query.where(Incident.status == IncidentStatus.OPEN).alias()
            )
        )
        in_progress_count = await self.db.scalar(
            select(func.count()).select_from(
                base_query.where(
                    Incident.status == IncidentStatus.IN_PROGRESS
                ).alias()
            )
        )
        resolved_count = await self.db.scalar(
            select(func.count()).select_from(
                base_query.where(Incident.status == IncidentStatus.RESOLVED).alias()
            )
        )

        # By priority
        critical_count = await self.db.scalar(
            select(func.count()).select_from(
                base_query.where(Incident.priority == IncidentPriority.CRITICAL).alias()
            )
        )
        high_count = await self.db.scalar(
            select(func.count()).select_from(
                base_query.where(Incident.priority == IncidentPriority.HIGH).alias()
            )
        )

        return {
            "total": total or 0,
            "by_status": {
                "open": open_count or 0,
                "in_progress": in_progress_count or 0,
                "resolved": resolved_count or 0,
            },
            "by_priority": {
                "critical": critical_count or 0,
                "high": high_count or 0,
            },
        }
