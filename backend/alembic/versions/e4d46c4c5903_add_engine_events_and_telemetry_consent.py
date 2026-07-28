"""add engine_events and telemetry_consent

Revision ID: e4d46c4c5903
Revises: e1f2a3b4c5d6
Create Date: 2026-07-19 23:11:31.279473

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "e4d46c4c5903"
down_revision: Union[str, None] = "e1f2a3b4c5d6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "engine_events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("event_type", sa.String(length=50), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("config_version", sa.String(length=50), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_engine_events_user_id"), "engine_events", ["user_id"], unique=False)
    op.create_index(op.f("ix_engine_events_event_type"), "engine_events", ["event_type"], unique=False)

    op.add_column(
        "user_profiles",
        sa.Column("telemetry_consent", sa.Boolean(), nullable=False, server_default=sa.false()),
    )
    op.alter_column("user_profiles", "telemetry_consent", server_default=None)


def downgrade() -> None:
    op.drop_column("user_profiles", "telemetry_consent")
    op.drop_index(op.f("ix_engine_events_event_type"), table_name="engine_events")
    op.drop_index(op.f("ix_engine_events_user_id"), table_name="engine_events")
    op.drop_table("engine_events")
