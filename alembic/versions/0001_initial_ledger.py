"""Initial incident SLA ledger schema.

Revision ID: 0001_initial_ledger
Revises:
Create Date: 2026-07-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial_ledger"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


incident_priority = sa.Enum(
    "critical",
    "high",
    "medium",
    "low",
    name="incidentpriority",
    native_enum=False,
    create_constraint=True,
)
incident_status = sa.Enum(
    "open",
    "acknowledged",
    "resolved",
    "closed",
    name="incidentstatus",
    native_enum=False,
    create_constraint=True,
)
event_type = sa.Enum(
    "incident.created",
    "incident.assigned",
    "incident.acknowledged",
    "incident.resolved",
    "incident.closed",
    "sla.response_breached",
    "sla.resolution_breached",
    name="incidenteventtype",
    native_enum=False,
    create_constraint=True,
)
outbox_status = sa.Enum(
    "pending",
    "processing",
    "sent",
    "dead",
    name="outboxstatus",
    native_enum=False,
    create_constraint=True,
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("username", sa.String(length=100), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=512), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("is_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("email", name="uq_users_email"),
        sa.UniqueConstraint("username", name="uq_users_username"),
    )

    op.create_table(
        "incidents",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("priority", incident_priority, nullable=False),
        sa.Column("status", incident_status, nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("reporter_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("assignee_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("closed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint("revision >= 1", name="revision_positive"),
        sa.CheckConstraint(
            "(status = 'open' AND acknowledged_at IS NULL AND resolved_at IS NULL "
            "AND closed_at IS NULL) OR "
            "(status = 'acknowledged' AND acknowledged_at IS NOT NULL "
            "AND resolved_at IS NULL AND closed_at IS NULL) OR "
            "(status = 'resolved' AND acknowledged_at IS NOT NULL "
            "AND resolved_at IS NOT NULL AND closed_at IS NULL) OR "
            "(status = 'closed' AND acknowledged_at IS NOT NULL "
            "AND resolved_at IS NOT NULL AND closed_at IS NOT NULL)",
            name="lifecycle_consistent",
        ),
        sa.CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= acknowledged_at",
            name="resolution_not_before_acknowledgement",
        ),
        sa.CheckConstraint(
            "closed_at IS NULL OR closed_at >= resolved_at",
            name="closure_not_before_resolution",
        ),
        sa.ForeignKeyConstraint(
            ["assignee_id"],
            ["users.id"],
            name="fk_incidents_assignee_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["reporter_id"],
            ["users.id"],
            name="fk_incidents_reporter_id_users",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_incidents"),
    )
    op.create_index("ix_incidents_assignee_id", "incidents", ["assignee_id"])
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index(
        "ix_incidents_reporter_created",
        "incidents",
        ["reporter_id", "created_at"],
    )

    op.create_table(
        "slas",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("response_target_seconds", sa.Integer(), nullable=False),
        sa.Column("resolution_target_seconds", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("response_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolution_deadline", sa.DateTime(timezone=True), nullable=False),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("response_breached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_breached_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "response_target_seconds > 0",
            name="response_target_positive",
        ),
        sa.CheckConstraint(
            "resolution_target_seconds > 0",
            name="resolution_target_positive",
        ),
        sa.CheckConstraint(
            "resolution_target_seconds >= response_target_seconds",
            name="targets_ordered",
        ),
        sa.CheckConstraint(
            "response_deadline > started_at",
            name="response_after_start",
        ),
        sa.CheckConstraint(
            "resolution_deadline >= response_deadline",
            name="resolution_after_response",
        ),
        sa.CheckConstraint(
            "resolved_at IS NULL OR acknowledged_at IS NOT NULL",
            name="resolution_requires_response",
        ),
        sa.CheckConstraint(
            "acknowledged_at IS NULL OR acknowledged_at >= started_at",
            name="acknowledgement_not_before_start",
        ),
        sa.CheckConstraint(
            "resolved_at IS NULL OR resolved_at >= acknowledged_at",
            name="resolution_not_before_acknowledgement",
        ),
        sa.CheckConstraint(
            "response_breached_at IS NULL OR response_breached_at = response_deadline",
            name="response_breach_uses_deadline",
        ),
        sa.CheckConstraint(
            "resolution_breached_at IS NULL "
            "OR resolution_breached_at = resolution_deadline",
            name="resolution_breach_uses_deadline",
        ),
        sa.CheckConstraint(
            "acknowledged_at IS NULL OR "
            "(acknowledged_at <= response_deadline AND response_breached_at IS NULL) OR "
            "(acknowledged_at > response_deadline "
            "AND response_breached_at IS NOT NULL "
            "AND response_breached_at = response_deadline)",
            name="response_outcome_consistent",
        ),
        sa.CheckConstraint(
            "resolved_at IS NULL OR "
            "(resolved_at <= resolution_deadline AND resolution_breached_at IS NULL) OR "
            "(resolved_at > resolution_deadline "
            "AND resolution_breached_at IS NOT NULL "
            "AND resolution_breached_at = resolution_deadline)",
            name="resolution_outcome_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name="fk_slas_incident_id_incidents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_slas"),
        sa.UniqueConstraint("incident_id", name="uq_slas_incident_id"),
    )
    op.create_index("ix_slas_response_deadline", "slas", ["response_deadline"])
    op.create_index("ix_slas_resolution_deadline", "slas", ["resolution_deadline"])

    op.create_table(
        "incident_events",
        sa.Column(
            "sequence",
            sa.BigInteger(),
            sa.Identity(always=False),
            nullable=False,
        ),
        sa.Column("event_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_type", event_type, nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("effective_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("source", sa.String(length=32), nullable=False),
        sa.CheckConstraint(
            "effective_at <= occurred_at",
            name="effective_not_after_observation",
        ),
        sa.CheckConstraint(
            "source IN ('api', 'worker')",
            name="source_known",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'",
            name="payload_is_object",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name="fk_incident_events_actor_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name="fk_incident_events_incident_id_incidents",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("sequence", name="pk_incident_events"),
        sa.UniqueConstraint("event_id", name="uq_incident_events_event_id"),
    )
    op.create_index(
        "ix_incident_events_incident_id", "incident_events", ["incident_id"]
    )
    op.create_index(
        "uq_incident_events_response_breach",
        "incident_events",
        ["incident_id"],
        unique=True,
        postgresql_where=sa.text("event_type = 'sla.response_breached'"),
    )
    op.create_index(
        "uq_incident_events_resolution_breach",
        "incident_events",
        ["incident_id"],
        unique=True,
        postgresql_where=sa.text("event_type = 'sla.resolution_breached'"),
    )

    op.create_table(
        "command_receipts",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("actor_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("command_type", sa.String(length=64), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("incident_id", postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column("event_sequence", sa.BigInteger(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.CheckConstraint(
            "(incident_id IS NULL AND event_sequence IS NULL) OR "
            "(incident_id IS NOT NULL AND event_sequence IS NOT NULL)",
            name="result_complete",
        ),
        sa.ForeignKeyConstraint(
            ["actor_id"],
            ["users.id"],
            name="fk_command_receipts_actor_id_users",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["event_sequence"],
            ["incident_events.sequence"],
            name="fk_command_receipts_event_sequence_incident_events",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["incident_id"],
            ["incidents.id"],
            name="fk_command_receipts_incident_id_incidents",
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_command_receipts"),
        sa.UniqueConstraint(
            "actor_id",
            "idempotency_key",
            name="uq_command_receipts_actor_idempotency_key",
        ),
    )

    op.create_table(
        "outbox_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("event_sequence", sa.BigInteger(), nullable=False),
        sa.Column("deduplication_key", sa.String(length=255), nullable=False),
        sa.Column("topic", sa.String(length=100), nullable=False),
        sa.Column("recipient", sa.String(length=320), nullable=False),
        sa.Column("payload", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("status", outbox_status, nullable=False, server_default="pending"),
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "available_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("claimed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("sent_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.CheckConstraint(
            "attempts >= 0", name="attempts_nonnegative"
        ),
        sa.CheckConstraint(
            "jsonb_typeof(payload) = 'object'", name="payload_is_object"
        ),
        sa.CheckConstraint(
            "(status = 'pending' AND claimed_at IS NULL AND sent_at IS NULL) OR "
            "(status = 'processing' AND claimed_at IS NOT NULL AND sent_at IS NULL) OR "
            "(status = 'sent' AND claimed_at IS NULL AND sent_at IS NOT NULL) OR "
            "(status = 'dead' AND claimed_at IS NULL AND sent_at IS NULL)",
            name="state_consistent",
        ),
        sa.ForeignKeyConstraint(
            ["event_sequence"],
            ["incident_events.sequence"],
            name="fk_outbox_messages_event_sequence_incident_events",
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name="pk_outbox_messages"),
        sa.UniqueConstraint(
            "deduplication_key", name="uq_outbox_messages_deduplication_key"
        ),
    )
    op.create_index("ix_outbox_messages_status", "outbox_messages", ["status"])
    op.create_index(
        "ix_outbox_messages_available_at", "outbox_messages", ["available_at"]
    )

    op.execute(
        """
        CREATE FUNCTION reject_incident_event_mutation() RETURNS trigger AS $$
        BEGIN
            RAISE EXCEPTION 'incident_events is append-only';
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER incident_events_append_only
        BEFORE UPDATE OR DELETE ON incident_events
        FOR EACH ROW EXECUTE FUNCTION reject_incident_event_mutation();
        """
    )
    op.execute(
        """
        CREATE FUNCTION protect_sla_policy_snapshot() RETURNS trigger AS $$
        BEGIN
            IF NEW.incident_id IS DISTINCT FROM OLD.incident_id
               OR NEW.response_target_seconds IS DISTINCT FROM OLD.response_target_seconds
               OR NEW.resolution_target_seconds IS DISTINCT FROM OLD.resolution_target_seconds
               OR NEW.started_at IS DISTINCT FROM OLD.started_at
               OR NEW.response_deadline IS DISTINCT FROM OLD.response_deadline
               OR NEW.resolution_deadline IS DISTINCT FROM OLD.resolution_deadline THEN
                RAISE EXCEPTION 'SLA policy snapshot is immutable';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER slas_policy_snapshot_immutable
        BEFORE UPDATE ON slas
        FOR EACH ROW EXECUTE FUNCTION protect_sla_policy_snapshot();
        """
    )
    op.execute(
        """
        CREATE FUNCTION protect_incident_priority() RETURNS trigger AS $$
        BEGIN
            IF NEW.priority IS DISTINCT FROM OLD.priority THEN
                RAISE EXCEPTION 'incident priority is immutable in v1';
            END IF;
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER incidents_priority_immutable
        BEFORE UPDATE ON incidents
        FOR EACH ROW EXECUTE FUNCTION protect_incident_priority();
        """
    )
    op.execute(
        """
        CREATE FUNCTION validate_incident_sla_progress() RETURNS trigger AS $$
        DECLARE
            target_incident_id uuid;
            incident_acknowledged_at timestamptz;
            incident_resolved_at timestamptz;
            sla_acknowledged_at timestamptz;
            sla_resolved_at timestamptz;
        BEGIN
            IF TG_TABLE_NAME = 'incidents' THEN
                target_incident_id := NEW.id;
            ELSIF TG_OP = 'DELETE' THEN
                target_incident_id := OLD.incident_id;
            ELSE
                target_incident_id := NEW.incident_id;
            END IF;

            SELECT acknowledged_at, resolved_at
              INTO incident_acknowledged_at, incident_resolved_at
              FROM incidents WHERE id = target_incident_id;
            IF NOT FOUND THEN
                -- The parent incident was deleted; its cascading SLA delete is valid.
                RETURN NULL;
            END IF;

            SELECT acknowledged_at, resolved_at
              INTO sla_acknowledged_at, sla_resolved_at
              FROM slas WHERE incident_id = target_incident_id;
            IF NOT FOUND THEN
                RAISE EXCEPTION 'every incident requires an SLA policy snapshot';
            END IF;

            IF incident_acknowledged_at IS DISTINCT FROM sla_acknowledged_at
               OR incident_resolved_at IS DISTINCT FROM sla_resolved_at THEN
                RAISE EXCEPTION 'incident and SLA progress timestamps are inconsistent';
            END IF;
            RETURN NULL;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER incidents_sla_progress_consistent
        AFTER INSERT OR UPDATE ON incidents
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION validate_incident_sla_progress();
        """
    )
    op.execute(
        """
        CREATE CONSTRAINT TRIGGER slas_incident_progress_consistent
        AFTER INSERT OR UPDATE OR DELETE ON slas
        DEFERRABLE INITIALLY DEFERRED
        FOR EACH ROW EXECUTE FUNCTION validate_incident_sla_progress();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS slas_incident_progress_consistent ON slas")
    op.execute("DROP TRIGGER IF EXISTS incidents_sla_progress_consistent ON incidents")
    op.execute("DROP FUNCTION IF EXISTS validate_incident_sla_progress()")
    op.execute("DROP TRIGGER IF EXISTS incidents_priority_immutable ON incidents")
    op.execute("DROP FUNCTION IF EXISTS protect_incident_priority()")
    op.execute("DROP TRIGGER IF EXISTS slas_policy_snapshot_immutable ON slas")
    op.execute("DROP FUNCTION IF EXISTS protect_sla_policy_snapshot()")
    op.execute("DROP TRIGGER IF EXISTS incident_events_append_only ON incident_events")
    op.execute("DROP FUNCTION IF EXISTS reject_incident_event_mutation()")

    op.drop_table("outbox_messages")
    op.drop_table("command_receipts")
    op.drop_index(
        "uq_incident_events_resolution_breach", table_name="incident_events"
    )
    op.drop_index(
        "uq_incident_events_response_breach", table_name="incident_events"
    )
    op.drop_index("ix_incident_events_incident_id", table_name="incident_events")
    op.drop_table("incident_events")
    op.drop_index("ix_slas_resolution_deadline", table_name="slas")
    op.drop_index("ix_slas_response_deadline", table_name="slas")
    op.drop_table("slas")
    op.drop_index("ix_incidents_reporter_created", table_name="incidents")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_index("ix_incidents_assignee_id", table_name="incidents")
    op.drop_table("incidents")
    op.drop_table("users")
