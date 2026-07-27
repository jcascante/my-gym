"""add workout_sessions

Revision ID: a3f81c9d2e40
Revises: 9f1a2b3c4d5e
"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

revision: str = "a3f81c9d2e40"
down_revision: Union[str, None] = "9f1a2b3c4d5e"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

SESSION_STATUS = sa.Enum("SCHEDULED", "IN_PROGRESS", "COMPLETED", "MISSED", "SKIPPED", name="sessionstatus")


def upgrade() -> None:
    op.create_table(
        "workout_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("workout_id", sa.Integer(), nullable=False),
        sa.Column("week", sa.Integer(), nullable=False),
        sa.Column("scheduled_date", sa.Date(), nullable=False),
        sa.Column("status", SESSION_STATUS, nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["program_id"], ["workout_programs.id"]),
        sa.ForeignKeyConstraint(["workout_id"], ["workouts.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("program_id", "workout_id", "week", name="uq_session_program_workout_week"),
    )
    op.create_index(op.f("ix_workout_sessions_program_id"), "workout_sessions", ["program_id"])
    op.create_index(op.f("ix_workout_sessions_workout_id"), "workout_sessions", ["workout_id"])
    op.create_index(op.f("ix_workout_sessions_scheduled_date"), "workout_sessions", ["scheduled_date"])

    # Dev-stage: no backfill, so pre-existing logs cannot satisfy a NOT NULL
    # session_id. They are discarded rather than left unanchored.
    op.execute("DELETE FROM workout_set_logs")
    op.execute("DELETE FROM user_workout_logs")

    for table in ("workout_set_logs", "user_workout_logs"):
        op.add_column(table, sa.Column("session_id", sa.Integer(), nullable=False))
        op.create_index(op.f(f"ix_{table}_session_id"), table, ["session_id"])
        op.create_foreign_key(f"fk_{table}_session_id", table, "workout_sessions", ["session_id"], ["id"])


def downgrade() -> None:
    for table in ("workout_set_logs", "user_workout_logs"):
        op.drop_constraint(f"fk_{table}_session_id", table, type_="foreignkey")
        op.drop_index(op.f(f"ix_{table}_session_id"), table_name=table)
        op.drop_column(table, "session_id")

    op.drop_index(op.f("ix_workout_sessions_scheduled_date"), table_name="workout_sessions")
    op.drop_index(op.f("ix_workout_sessions_workout_id"), table_name="workout_sessions")
    op.drop_index(op.f("ix_workout_sessions_program_id"), table_name="workout_sessions")
    op.drop_table("workout_sessions")
    SESSION_STATUS.drop(op.get_bind(), checkfirst=True)
