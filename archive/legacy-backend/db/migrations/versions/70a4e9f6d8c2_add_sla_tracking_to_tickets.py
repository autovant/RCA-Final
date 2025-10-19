"""Add SLA tracking fields to tickets table.

Revision ID: 70a4e9f6d8c2
Revises: 60f3f78cb7d9
Create Date: 2025-10-12 10:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect
from sqlalchemy.exc import SQLAlchemyError

# revision identifiers, used by Alembic.
revision = "70a4e9f6d8c2"
down_revision = "60f3f78cb7d9"
branch_labels = None
depends_on = None


def _column_exists(inspector, table_name: str, column_name: str) -> bool:
    """Check if a column exists in a table."""
    try:
        columns = [col["name"] for col in inspector.get_columns(table_name)]
        return column_name in columns
    except SQLAlchemyError:
        return False


def upgrade() -> None:
    """Add SLA tracking columns to tickets table."""
    bind = op.get_bind()
    inspector = inspect(bind)

    # Add acknowledged_at timestamp
    if not _column_exists(inspector, "tickets", "acknowledged_at"):
        op.add_column(
            "tickets",
            sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True)
        )

    # Add resolved_at timestamp
    if not _column_exists(inspector, "tickets", "resolved_at"):
        op.add_column(
            "tickets",
            sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True)
        )

    # Add time_to_acknowledge in seconds
    if not _column_exists(inspector, "tickets", "time_to_acknowledge"):
        op.add_column(
            "tickets",
            sa.Column("time_to_acknowledge", sa.Integer(), nullable=True)
        )

    # Add time_to_resolve in seconds
    if not _column_exists(inspector, "tickets", "time_to_resolve"):
        op.add_column(
            "tickets",
            sa.Column("time_to_resolve", sa.Integer(), nullable=True)
        )


def downgrade() -> None:
    """Remove SLA tracking columns from tickets table."""
    op.drop_column("tickets", "time_to_resolve")
    op.drop_column("tickets", "time_to_acknowledge")
    op.drop_column("tickets", "resolved_at")
    op.drop_column("tickets", "acknowledged_at")
