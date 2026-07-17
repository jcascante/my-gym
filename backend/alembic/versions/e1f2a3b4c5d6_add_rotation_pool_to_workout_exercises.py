"""add rotation_pool to workout_exercises

Revision ID: e1f2a3b4c5d6
Revises: d4e5f6a7b8c9
Create Date: 2026-07-17 09:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e1f2a3b4c5d6"
down_revision: Union[str, Sequence[str], None] = "d4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "workout_exercises",
        sa.Column("rotation_pool", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.alter_column("workout_exercises", "rotation_pool", server_default=None)


def downgrade() -> None:
    op.drop_column("workout_exercises", "rotation_pool")
