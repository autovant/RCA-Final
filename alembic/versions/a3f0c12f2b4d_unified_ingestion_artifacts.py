"""unified ingestion artifacts

Revision ID: a3f0c12f2b4d
Revises: add_draft_status
Create Date: 2025-10-17 20:15:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy


# revision identifiers, used by Alembic.
revision: str = "a3f0c12f2b4d"
down_revision: Union[str, None] = "add_draft_status"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Enumerations reused across objects
visibility_scope_enum = sa.Enum(
    "tenant_only",
    "multi_tenant",
    name="visibility_scope_enum",
)
fingerprint_status_enum = sa.Enum(
    "available",
    "degraded",
    "missing",
    name="fingerprint_status_enum",
)
platform_enum = sa.Enum(
    "blue_prism",
    "uipath",
    "appian",
    "automation_anywhere",
    "pega",
    "unknown",
    name="detected_platform_enum",
)
archive_type_enum = sa.Enum(
    "zip",
    "gz",
    "bz2",
    "xz",
    "tar_gz",
    "tar_bz2",
    "tar_xz",
    name="archive_type_enum",
)
archive_guardrail_enum = sa.Enum(
    "passed",
    "blocked_ratio",
    "blocked_members",
    "timeout",
    "error",
    name="archive_guardrail_status_enum",
)
audit_action_enum = sa.Enum(
    "viewed_related_incident",
    name="analyst_audit_action_enum",
)


def upgrade() -> None:
    bind = op.get_bind()
    visibility_scope_enum.create(bind, checkfirst=True)
    fingerprint_status_enum.create(bind, checkfirst=True)
    platform_enum.create(bind, checkfirst=True)
    archive_type_enum.create(bind, checkfirst=True)
    archive_guardrail_enum.create(bind, checkfirst=True)
    audit_action_enum.create(bind, checkfirst=True)

    op.create_table(
        "incident_fingerprints",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column(
            "embedding_vector",
            pgvector.sqlalchemy.Vector(dim=1536),
            nullable=True,
        ),
        sa.Column("summary_text", sa.Text(), nullable=False),
        sa.Column(
            "relevance_threshold",
            sa.Float(),
            nullable=False,
            server_default=sa.text("0.5"),
        ),
        sa.Column(
            "visibility_scope",
            visibility_scope_enum,
            nullable=False,
            server_default="tenant_only",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "fingerprint_status",
            fingerprint_status_enum,
            nullable=False,
            server_default="missing",
        ),
        sa.Column(
            "safeguard_notes",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.UniqueConstraint(
            "session_id",
            name="uq_incident_fingerprints_session",
        ),
        sa.CheckConstraint(
            "fingerprint_status != 'available' OR embedding_vector IS NOT NULL",
            name="ck_incident_fingerprints_vector_required",
        ),
        sa.CheckConstraint(
            "char_length(summary_text) <= 4096",
            name="ck_incident_fingerprints_summary_length",
        ),
        sa.CheckConstraint(
            "relevance_threshold >= 0 AND relevance_threshold <= 1",
            name="ck_incident_fingerprints_relevance_bounds",
        ),
    )

    op.create_index(
        "ix_incident_fingerprints_tenant_scope",
        "incident_fingerprints",
        ["tenant_id", "visibility_scope"],
    )
    op.create_index(
        "ix_incident_fingerprints_status",
        "incident_fingerprints",
        ["fingerprint_status"],
    )
    op.create_index(
        "ix_incident_fingerprints_updated_at",
        "incident_fingerprints",
        ["updated_at"],
    )
    op.create_index(
        "ix_incident_fingerprints_embedding_vector_ivfflat",
        "incident_fingerprints",
        ["embedding_vector"],
        unique=False,
        postgresql_using="ivfflat",
    )

    op.create_table(
        "platform_detection_results",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "job_id",
            sa.UUID(),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "detected_platform",
            platform_enum,
            nullable=False,
            server_default="unknown",
        ),
        sa.Column(
            "confidence_score",
            sa.Numeric(5, 4),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column("detection_method", sa.Text(), nullable=False),
        sa.Column(
            "parser_executed",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
        sa.Column("parser_version", sa.Text(), nullable=True),
        sa.Column(
            "extracted_entities",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "feature_flag_snapshot",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.UniqueConstraint(
            "job_id",
            name="uq_platform_detection_results_job",
        ),
        sa.CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_platform_detection_confidence_bounds",
        ),
    )

    op.create_index(
        "ix_platform_detection_results_job_id",
        "platform_detection_results",
        ["job_id"],
    )
    op.create_index(
        "ix_platform_detection_results_created_at",
        "platform_detection_results",
        ["created_at"],
    )
    op.create_index(
        "ix_platform_detection_results_platform",
        "platform_detection_results",
        ["detected_platform"],
    )

    op.create_table(
        "archive_extraction_audits",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column(
            "job_id",
            sa.UUID(),
            sa.ForeignKey("jobs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("source_filename", sa.Text(), nullable=False),
        sa.Column("archive_type", archive_type_enum, nullable=False),
        sa.Column(
            "member_count",
            sa.Integer(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "compressed_size_bytes",
            sa.BigInteger(),
            nullable=False,
        ),
        sa.Column(
            "estimated_uncompressed_bytes",
            sa.BigInteger(),
            nullable=True,
        ),
        sa.Column(
            "decompression_ratio",
            sa.Numeric(10, 2),
            nullable=True,
        ),
        sa.Column(
            "guardrail_status",
            archive_guardrail_enum,
            nullable=False,
            server_default="passed",
        ),
        sa.Column("blocked_reason", sa.Text(), nullable=True),
        sa.Column(
            "partial_members",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "completed_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.UniqueConstraint(
            "job_id",
            name="uq_archive_extraction_audits_job",
        ),
        sa.CheckConstraint(
            "member_count >= 0",
            name="ck_archive_audit_member_count_non_negative",
        ),
        sa.CheckConstraint(
            "compressed_size_bytes > 0",
            name="ck_archive_audit_compressed_size_positive",
        ),
        sa.CheckConstraint(
            "decompression_ratio IS NULL OR decompression_ratio >= 0",
            name="ck_archive_audit_ratio_non_negative",
        ),
        sa.CheckConstraint(
            "guardrail_status NOT IN ('blocked_ratio', 'blocked_members', 'error') OR blocked_reason IS NOT NULL",
            name="ck_archive_audit_blocked_reason_required",
        ),
    )

    op.create_index(
        "ix_archive_extraction_audits_job_id",
        "archive_extraction_audits",
        ["job_id"],
    )
    op.create_index(
        "ix_archive_extraction_audits_guardrail_status",
        "archive_extraction_audits",
        ["guardrail_status"],
    )
    op.create_index(
        "ix_archive_extraction_audits_completed_at",
        "archive_extraction_audits",
        ["completed_at"],
    )

    op.create_table(
        "analyst_audit_events",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("analyst_id", sa.UUID(), nullable=False),
        sa.Column("source_workspace_id", sa.UUID(), nullable=False),
        sa.Column("related_workspace_id", sa.UUID(), nullable=False),
        sa.Column("session_id", sa.UUID(), nullable=False),
        sa.Column("related_session_id", sa.UUID(), nullable=False),
        sa.Column("action", audit_action_enum, nullable=False),
        sa.Column(
            "timestamp",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "source_workspace_id <> related_workspace_id",
            name="ck_analyst_audit_distinct_workspaces",
        ),
    )

    op.create_index(
        "ix_analyst_audit_events_analyst_timestamp",
        "analyst_audit_events",
        ["analyst_id", "timestamp"],
    )
    op.create_index(
        "ix_analyst_audit_events_session",
        "analyst_audit_events",
        ["session_id", "related_session_id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_analyst_audit_events_session",
        table_name="analyst_audit_events",
    )
    op.drop_index(
        "ix_analyst_audit_events_analyst_timestamp",
        table_name="analyst_audit_events",
    )
    op.drop_table("analyst_audit_events")

    op.drop_index(
        "ix_archive_extraction_audits_completed_at",
        table_name="archive_extraction_audits",
    )
    op.drop_index(
        "ix_archive_extraction_audits_guardrail_status",
        table_name="archive_extraction_audits",
    )
    op.drop_index(
        "ix_archive_extraction_audits_job_id",
        table_name="archive_extraction_audits",
    )
    op.drop_table("archive_extraction_audits")

    op.drop_index(
        "ix_platform_detection_results_platform",
        table_name="platform_detection_results",
    )
    op.drop_index(
        "ix_platform_detection_results_created_at",
        table_name="platform_detection_results",
    )
    op.drop_index(
        "ix_platform_detection_results_job_id",
        table_name="platform_detection_results",
    )
    op.drop_table("platform_detection_results")

    op.drop_index(
        "ix_incident_fingerprints_embedding_vector_ivfflat",
        table_name="incident_fingerprints",
    )
    op.drop_index(
        "ix_incident_fingerprints_updated_at",
        table_name="incident_fingerprints",
    )
    op.drop_index(
        "ix_incident_fingerprints_status",
        table_name="incident_fingerprints",
    )
    op.drop_index(
        "ix_incident_fingerprints_tenant_scope",
        table_name="incident_fingerprints",
    )
    op.drop_table("incident_fingerprints")

    bind = op.get_bind()
    audit_action_enum.drop(bind, checkfirst=True)
    archive_guardrail_enum.drop(bind, checkfirst=True)
    archive_type_enum.drop(bind, checkfirst=True)
    platform_enum.drop(bind, checkfirst=True)
    fingerprint_status_enum.drop(bind, checkfirst=True)
    visibility_scope_enum.drop(bind, checkfirst=True)