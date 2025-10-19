"""Add classification labels, watcher config, and ITSM profiles."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy import inspect

# revision identifiers, used by Alembic.
revision = "4f85b8d5c3a4"
down_revision = None
branch_labels = None
depends_on = None


def _table_exists(inspector, table_name: str) -> bool:
    return table_name in inspector.get_table_names()


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    try:
        return any(col["name"] == column_name for col in inspector.get_columns(table_name))
    except sa.exc.NoSuchTableError:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')

    if _column_exists(inspector, "files", "labels") is False:
        op.add_column(
            "files",
            sa.Column("labels", postgresql.ARRAY(sa.Text()), nullable=True),
        )

    if _column_exists(inspector, "documents", "labels") is False:
        op.add_column(
            "documents",
            sa.Column("labels", postgresql.ARRAY(sa.Text()), nullable=True),
        )

    op.execute("ALTER TABLE documents ALTER COLUMN content_embedding TYPE vector(384)")

    if not _table_exists(inspector, "itsm_profiles"):
        op.create_table(
            "itsm_profiles",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("name", sa.String(length=100), nullable=False, unique=True),
            sa.Column("platform", sa.String(length=50), nullable=False),
            sa.Column("base_url", sa.String(length=500), nullable=False),
            sa.Column("auth_method", sa.String(length=50), nullable=False),
            sa.Column("secret_ref", sa.String(length=255), nullable=False),
            sa.Column("defaults", postgresql.JSONB, nullable=True),
            sa.CheckConstraint("platform IN ('servicenow', 'jira')", name="valid_itsm_platform"),
        )
        op.create_index("ix_itsm_profiles_name", "itsm_profiles", ["name"], unique=True)

    if not _table_exists(inspector, "watcher_configs"):
        op.create_table(
            "watcher_configs",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("roots", postgresql.ARRAY(sa.Text()), nullable=True),
            sa.Column("include_globs", postgresql.ARRAY(sa.Text()), nullable=True),
            sa.Column("exclude_globs", postgresql.ARRAY(sa.Text()), nullable=True),
            sa.Column("max_file_size_mb", sa.Integer(), nullable=True),
            sa.Column("allowed_mime_types", postgresql.ARRAY(sa.Text()), nullable=True),
            sa.Column("batch_window_seconds", sa.Integer(), nullable=True),
            sa.Column("auto_create_jobs", sa.Boolean(), nullable=False, server_default=sa.text("true")),
            sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )
        op.create_index("ix_watcher_configs_enabled", "watcher_configs", ["enabled"])

    if not _table_exists(inspector, "watcher_events"):
        op.create_table(
            "watcher_events",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("watcher_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("watcher_configs.id", ondelete="SET NULL"), nullable=True),
            sa.Column("event_type", sa.String(length=50), nullable=False),
            sa.Column("payload", postgresql.JSONB, nullable=True),
            sa.Column("ts", sa.DateTime(timezone=True), server_default=sa.text("NOW()"), nullable=False),
        )
        op.create_index("ix_watcher_events_event_type", "watcher_events", ["event_type"])
        op.create_index("ix_watcher_events_ts", "watcher_events", ["ts"])
        op.create_index("ix_watcher_events_watcher_id", "watcher_events", ["watcher_id"])

    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_documents_content_embedding_ivfflat
        ON documents USING ivfflat (content_embedding vector_l2_ops)
        WITH (lists = 100)
        """
    )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    op.execute("DROP INDEX IF EXISTS ix_documents_content_embedding_ivfflat")

    if _table_exists(inspector, "watcher_events"):
        op.drop_index("ix_watcher_events_event_type", table_name="watcher_events")
        op.drop_index("ix_watcher_events_ts", table_name="watcher_events")
        op.drop_index("ix_watcher_events_watcher_id", table_name="watcher_events")
        op.drop_table("watcher_events")

    if _table_exists(inspector, "watcher_configs"):
        op.drop_index("ix_watcher_configs_enabled", table_name="watcher_configs")
        op.drop_table("watcher_configs")

    if _table_exists(inspector, "itsm_profiles"):
        op.drop_index("ix_itsm_profiles_name", table_name="itsm_profiles")
        op.drop_table("itsm_profiles")

    if _column_exists(inspector, "documents", "labels"):
        op.drop_column("documents", "labels")

    if _column_exists(inspector, "files", "labels"):
        op.drop_column("files", "labels")

    op.execute("ALTER TABLE documents ALTER COLUMN content_embedding TYPE vector")

