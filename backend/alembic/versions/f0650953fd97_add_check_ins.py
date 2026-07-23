"""add check ins

Revision ID: f0650953fd97
Revises: 60d03a08cac2
Create Date: 2026-07-21 18:04:29.432174

"""

from typing import Sequence, Union

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f0650953fd97"
down_revision: Union[str, None] = "60d03a08cac2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# injuryregion already exists (created by 97445f694ec7_add_injury_records.py) - reuse
# the Postgres type without re-creating it (generic sa.Enum's create_type=False isn't
# honored inside create_table; postgresql.ENUM's is).
check_in_region_enum = postgresql.ENUM(
    "SHOULDER",
    "ELBOW",
    "WRIST",
    "CERVICAL",
    "THORACIC",
    "LUMBAR",
    "HIP",
    "KNEE",
    "ANKLE_FOOT",
    name="injuryregion",
    create_type=False,
)
check_in_status_enum = sa.Enum(
    "GREEN",
    "AMBER",
    "RED",
    name="checkinstatus",
)


def upgrade() -> None:
    op.create_table(
        "check_ins",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("program_id", sa.Integer(), nullable=False),
        sa.Column("region", check_in_region_enum, nullable=False),
        sa.Column("status", check_in_status_enum, nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["program_id"], ["workout_programs.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_check_ins_user_id"), "check_ins", ["user_id"], unique=False)
    op.create_index(op.f("ix_check_ins_program_id"), "check_ins", ["program_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_check_ins_program_id"), table_name="check_ins")
    op.drop_index(op.f("ix_check_ins_user_id"), table_name="check_ins")
    op.drop_table("check_ins")
    check_in_status_enum.drop(op.get_bind(), checkfirst=True)
