"""Add draft status to jobs

Revision ID: add_draft_status
Revises: 
Create Date: 2025-10-17 16:47:00

"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'add_draft_status'
down_revision: Union[str, None] = '6f5ba0b2cc91'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add 'draft' to the valid job status constraint."""
    # Drop the old constraint
    op.drop_constraint('valid_job_status', 'jobs', type_='check')
    
    # Create the new constraint with 'draft' included
    op.create_check_constraint(
        'valid_job_status',
        'jobs',
        "status IN ('draft', 'pending', 'running', 'completed', 'failed', 'cancelled')"
    )


def downgrade() -> None:
    """Remove 'draft' from the valid job status constraint."""
    # Drop the new constraint
    op.drop_constraint('valid_job_status', 'jobs', type_='check')
    
    # Restore the old constraint without 'draft'
    op.create_check_constraint(
        'valid_job_status',
        'jobs',
        "status IN ('pending', 'running', 'completed', 'failed', 'cancelled')"
    )
