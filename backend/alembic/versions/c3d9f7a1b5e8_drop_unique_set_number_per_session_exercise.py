"""drop unique set number per session exercise

Revision ID: c3d9f7a1b5e8
Revises: b6e4f9a1c7d2
"""

from typing import Sequence, Union

from alembic import op

revision: str = "c3d9f7a1b5e8"
down_revision: Union[str, None] = "b6e4f9a1c7d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_constraint("uq_workout_set_log_session_exercise_set", "workout_set_logs", type_="unique")


def downgrade() -> None:
    op.create_unique_constraint(
        "uq_workout_set_log_session_exercise_set",
        "workout_set_logs",
        ["session_id", "workout_exercise_id", "set_number"],
    )
