"""add goal_weights to user_profiles

Revision ID: 207a071d1a2a
Revises: e4d46c4c5903
Create Date: 2026-07-20 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "207a071d1a2a"
down_revision: Union[str, Sequence[str], None] = "e4d46c4c5903"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user_profiles", sa.Column("goal_weights", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("user_profiles", "goal_weights")
