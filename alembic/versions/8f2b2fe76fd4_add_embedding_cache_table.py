"""add embedding cache table

Revision ID: 8f2b2fe76fd4
Revises: 4b9a5b36a142
Create Date: 2025-10-14 13:05:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8f2b2fe76fd4"
down_revision: Union[str, None] = "4b9a5b36a142"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "embedding_cache",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
    sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("content_sha256", sa.String(length=64), nullable=False),
        sa.Column("model", sa.String(length=128), nullable=False),
        sa.Column("embedding_vector_id", sa.UUID(), nullable=True),
        sa.Column(
            "hit_count",
            sa.BigInteger(),
            nullable=False,
            server_default=sa.text("0"),
        ),
        sa.Column(
            "last_accessed_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("payload_ciphertext", sa.LargeBinary(), nullable=False),
        sa.ForeignKeyConstraint(
            ["embedding_vector_id"],
            ["documents.id"],
            ondelete="SET NULL",
        ),
        sa.UniqueConstraint(
            "tenant_id",
            "content_sha256",
            "model",
            name="uq_embedding_cache_tenant_sha_model",
        ),
        sa.CheckConstraint(
            "char_length(content_sha256) = 64",
            name="ck_embedding_cache_sha_length",
        ),
        sa.CheckConstraint(
            "hit_count >= 0",
            name="ck_embedding_cache_hit_count_non_negative",
        ),
        sa.CheckConstraint(
            "expires_at IS NULL OR expires_at > created_at",
            name="ck_embedding_cache_expiry_after_creation",
        ),
    )

    op.create_index(
        "ix_embedding_cache_tenant_id",
        "embedding_cache",
        ["tenant_id"],
        unique=False,
    )
    op.create_index(
        "ix_embedding_cache_last_accessed_at",
        "embedding_cache",
        ["last_accessed_at"],
        unique=False,
    )
    op.create_index(
        "ix_embedding_cache_embedding_vector_id",
        "embedding_cache",
        ["embedding_vector_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_embedding_cache_embedding_vector_id", table_name="embedding_cache")
    op.drop_index("ix_embedding_cache_last_accessed_at", table_name="embedding_cache")
    op.drop_index("ix_embedding_cache_tenant_id", table_name="embedding_cache")
    op.drop_table("embedding_cache")
