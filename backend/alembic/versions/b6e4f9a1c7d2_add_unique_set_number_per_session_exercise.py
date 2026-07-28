"""add unique set number per session exercise

Revision ID: b6e4f9a1c7d2
Revises: a3f81c9d2e40
"""

from typing import Sequence, Union

from alembic import op

revision: str = "b6e4f9a1c7d2"
down_revision: Union[str, None] = "a3f81c9d2e40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_workout_set_log_session_exercise_set",
        "workout_set_logs",
        ["session_id", "workout_exercise_id", "set_number"],
    )


def downgrade() -> None:
    op.drop_constraint("uq_workout_set_log_session_exercise_set", "workout_set_logs", type_="unique")
