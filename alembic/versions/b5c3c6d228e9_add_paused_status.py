"""Allow paused job status

Revision ID: b5c3c6d228e9
Revises: a3f0c12f2b4d
Create Date: 2025-10-18 00:00:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b5c3c6d228e9"
down_revision: Union[str, None] = "a3f0c12f2b4d"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Include "paused" in the job status constraint."""
    op.drop_constraint("valid_job_status", "jobs", type_="check")
    op.create_check_constraint(
        "valid_job_status",
        "jobs",
        "status IN ('draft', 'pending', 'running', 'paused', 'completed', 'failed', 'cancelled')",
    )


def downgrade() -> None:
    """Remove "paused" from the job status constraint."""
    op.drop_constraint("valid_job_status", "jobs", type_="check")
    op.create_check_constraint(
        "valid_job_status",
        "jobs",
        "status IN ('draft', 'pending', 'running', 'completed', 'failed', 'cancelled')",
    )
