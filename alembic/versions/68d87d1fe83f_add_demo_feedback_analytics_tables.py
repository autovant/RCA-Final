"""add_demo_feedback_analytics_tables

Revision ID: 68d87d1fe83f
Revises: b5c3c6d228e9
Create Date: 2025-10-22 22:43:44.799148

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68d87d1fe83f'
down_revision: Union[str, None] = 'b5c3c6d228e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create demo_feedback table
    op.create_table(
        'demo_feedback',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('demo_id', sa.String(length=255), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('user_email', sa.String(length=255), nullable=True),
        sa.Column('feature_requests', sa.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range')
    )
    op.create_index(op.f('ix_demo_feedback_demo_id'), 'demo_feedback', ['demo_id'], unique=False)
    op.create_index(op.f('ix_demo_feedback_created_at'), 'demo_feedback', ['created_at'], unique=False)
    
    # Create demo_analytics table
    op.create_table(
        'demo_analytics',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('demo_id', sa.String(length=255), nullable=False),
        sa.Column('event_type', sa.String(length=100), nullable=False),
        sa.Column('metadata', sa.JSON(), nullable=True),
        sa.Column('session_id', sa.String(length=255), nullable=True),
        sa.Column('timestamp', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_demo_analytics_demo_id'), 'demo_analytics', ['demo_id'], unique=False)
    op.create_index(op.f('ix_demo_analytics_event_type'), 'demo_analytics', ['event_type'], unique=False)
    op.create_index(op.f('ix_demo_analytics_session_id'), 'demo_analytics', ['session_id'], unique=False)
    op.create_index(op.f('ix_demo_analytics_timestamp'), 'demo_analytics', ['timestamp'], unique=False)
    
    # Create demo_shares table
    op.create_table(
        'demo_shares',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('share_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('config', sa.JSON(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('access_count', sa.Integer(), server_default='0', nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('share_id', name='uq_demo_shares_share_id')
    )
    op.create_index(op.f('ix_demo_shares_share_id'), 'demo_shares', ['share_id'], unique=True)
    op.create_index(op.f('ix_demo_shares_expires_at'), 'demo_shares', ['expires_at'], unique=False)


def downgrade() -> None:
    # Drop demo_shares table
    op.drop_index(op.f('ix_demo_shares_expires_at'), table_name='demo_shares')
    op.drop_index(op.f('ix_demo_shares_share_id'), table_name='demo_shares')
    op.drop_table('demo_shares')
    
    # Drop demo_analytics table
    op.drop_index(op.f('ix_demo_analytics_timestamp'), table_name='demo_analytics')
    op.drop_index(op.f('ix_demo_analytics_session_id'), table_name='demo_analytics')
    op.drop_index(op.f('ix_demo_analytics_event_type'), table_name='demo_analytics')
    op.drop_index(op.f('ix_demo_analytics_demo_id'), table_name='demo_analytics')
    op.drop_table('demo_analytics')
    
    # Drop demo_feedback table
    op.drop_index(op.f('ix_demo_feedback_created_at'), table_name='demo_feedback')
    op.drop_index(op.f('ix_demo_feedback_demo_id'), table_name='demo_feedback')
    op.drop_table('demo_feedback')
