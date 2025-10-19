"""Add ticket integration settings table."""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = "60f3f78cb7d9"
down_revision = "4f85b8d5c3a4"
branch_labels = None
depends_on = None


def _table_exists(inspector, table_name: str) -> bool:
    try:
        return table_name in inspector.get_table_names()
    except sa.exc.SQLAlchemyError:
        return False


def upgrade() -> None:
    bind = op.get_bind()
    inspector = inspect(bind)

    if not _table_exists(inspector, "ticket_integration_settings"):
        op.create_table(
            "ticket_integration_settings",
            sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
            sa.Column("servicenow_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("jira_enabled", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column("dual_mode", sa.Boolean(), nullable=False, server_default=sa.text("false")),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                nullable=False,
                server_default=sa.func.now(),
            ),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    op.drop_table("ticket_integration_settings")
