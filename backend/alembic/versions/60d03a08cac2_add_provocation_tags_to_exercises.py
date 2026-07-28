"""add provocation tags to exercises

Revision ID: 60d03a08cac2
Revises: 97445f694ec7
Create Date: 2026-07-21 15:56:37.017831

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "60d03a08cac2"
down_revision: Union[str, None] = "97445f694ec7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "exercises",
        sa.Column("provocation_tags", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.alter_column("exercises", "provocation_tags", server_default=None)


def downgrade() -> None:
    op.drop_column("exercises", "provocation_tags")
