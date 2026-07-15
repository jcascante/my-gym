"""add environment type archetypes

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-07-15 13:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b2c3d4e5f6a7"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # SQLAlchemy's Enum column persists the Python enum member *name*
    # (matching the existing COMMERCIAL_GYM/HOME/... values), not its
    # lowercase .value, so the new members must be added uppercase too.
    op.execute("ALTER TYPE environmenttype ADD VALUE IF NOT EXISTS 'POWERLIFTING_GYM'")
    op.execute("ALTER TYPE environmenttype ADD VALUE IF NOT EXISTS 'STRENGTH_GYM'")


def downgrade() -> None:
    # Postgres cannot drop individual enum values without rebuilding the
    # type; any rows already using the new archetypes would need manual
    # handling first, so downgrade is a deliberate no-op.
    pass
