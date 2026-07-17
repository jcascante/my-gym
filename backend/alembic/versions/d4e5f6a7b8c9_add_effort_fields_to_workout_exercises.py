"""add target_rpe and intensity_pct to workout_exercises

Revision ID: d4e5f6a7b8c9
Revises: c8d9e0f1a2b3
Create Date: 2026-07-16 09:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, Sequence[str], None] = "c8d9e0f1a2b3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("workout_exercises", sa.Column("target_rpe", sa.Float(), nullable=True))
    op.add_column("workout_exercises", sa.Column("intensity_pct", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("workout_exercises", "intensity_pct")
    op.drop_column("workout_exercises", "target_rpe")
