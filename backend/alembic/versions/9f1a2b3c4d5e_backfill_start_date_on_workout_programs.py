"""backfill start_date on workout_programs

Revision ID: 9f1a2b3c4d5e
Revises: 6b1a2c3d4e5f
Create Date: 2026-07-26 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9f1a2b3c4d5e"
down_revision: Union[str, None] = "6b1a2c3d4e5f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Existing rows (any status) predate WorkoutProgram.start_date ever being
    # written - approximate it from created_at so "current week" math
    # (app/api/v1/endpoints/programs.py::_preview_out) has something to work
    # with for programs accepted before this migration shipped.
    op.execute("UPDATE workout_programs SET start_date = date(created_at) WHERE start_date IS NULL")


def downgrade() -> None:
    # Backfilled values are approximations derived from created_at, not real
    # user input - there's nothing meaningful to restore on downgrade.
    pass
