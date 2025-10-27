"""add_performance_indexes

Adds performance indexes for frequently queried columns to improve query speed.

Indexes added:
- jobs: (status, created_at) for filtering and sorting
- jobs: (user_id, status) for user-specific job queries  
- files: (job_id, processing_status) for job file lookups
- incident_fingerprints: (visibility_scope, similarity_score) for fingerprint searches
- documents: (job_id) for job document lookups
- conversation_turns: (job_id, sequence) for conversation retrieval

Revision ID: fbf73ec766ed
Revises: 68d87d1fe83f
Create Date: 2025-10-22 23:07:38.401184

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'fbf73ec766ed'
down_revision: Union[str, None] = '68d87d1fe83f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add performance indexes.
    
    Note: Removed CONCURRENTLY option as it cannot run in a transaction.
    These indexes will lock the table briefly during creation, but should
    be fast enough for small-to-medium sized tables.
    """
    # Jobs table indexes
    op.create_index(
        'idx_jobs_status_created',
        'jobs',
        ['status', sa.text('created_at DESC')],
        if_not_exists=True
    )
    
    op.create_index(
        'idx_jobs_user_status',
        'jobs',
        ['user_id', 'status'],
        if_not_exists=True
    )
    
    # Files table indexes - using 'processed' column instead of 'processing_status'
    op.create_index(
        'idx_files_job_processed',
        'files',
        ['job_id', 'processed'],
        if_not_exists=True
    )
    
    # Documents table indexes
    op.create_index(
        'idx_documents_job_id',
        'documents',
        ['job_id'],
        if_not_exists=True
    )
    
    # Conversation turns table indexes
    op.create_index(
        'idx_conversation_turns_job_sequence',
        'conversation_turns',
        ['job_id', 'sequence'],
        if_not_exists=True
    )


def downgrade() -> None:
    """Remove performance indexes."""
    op.drop_index('idx_conversation_turns_job_sequence', table_name='conversation_turns')
    op.drop_index('idx_documents_job_id', table_name='documents')
    op.drop_index('idx_files_job_processed', table_name='files')
    op.drop_index('idx_jobs_user_status', table_name='jobs')
    op.drop_index('idx_jobs_status_created', table_name='jobs')
