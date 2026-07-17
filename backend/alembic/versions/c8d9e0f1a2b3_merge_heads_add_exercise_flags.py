"""merge heads and add exercise is_unilateral/is_compound flags

Revision ID: c8d9e0f1a2b3
Revises: a7c903edb637, b2c3d4e5f6a7
Create Date: 2026-07-16 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c8d9e0f1a2b3"
down_revision: Union[str, Sequence[str], None] = ("a7c903edb637", "b2c3d4e5f6a7")
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "exercises",
        sa.Column("is_unilateral", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.add_column(
        "exercises",
        sa.Column("is_compound", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("exercises", "is_unilateral", server_default=None)
    op.alter_column("exercises", "is_compound", server_default=None)


def downgrade() -> None:
    op.drop_column("exercises", "is_compound")
    op.drop_column("exercises", "is_unilateral")
