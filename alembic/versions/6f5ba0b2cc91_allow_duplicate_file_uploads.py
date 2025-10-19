"""allow duplicate file uploads

Revision ID: 6f5ba0b2cc91
Revises: 8f2b2fe76fd4
Create Date: 2025-10-16 09:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "6f5ba0b2cc91"
down_revision: Union[str, None] = "8f2b2fe76fd4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _drop_checksum_unique_constraint() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    unique_constraints = inspector.get_unique_constraints("files")
    target_name: Union[str, None] = None

    for constraint in unique_constraints:
        columns = constraint.get("column_names") or []
        if columns == ["checksum"]:
            target_name = constraint.get("name")
            break

    if not target_name:
        return

    with op.batch_alter_table("files") as batch_op:
        batch_op.drop_constraint(target_name, type_="unique")


def upgrade() -> None:
    _drop_checksum_unique_constraint()



def downgrade() -> None:
    with op.batch_alter_table("files") as batch_op:
        batch_op.create_unique_constraint("uq_files_checksum", ["checksum"])
