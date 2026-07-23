"""add injury records

Revision ID: 97445f694ec7
Revises: 207a071d1a2a
Create Date: 2026-07-21 14:24:56.286104

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "97445f694ec7"
down_revision: Union[str, None] = "207a071d1a2a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

injury_region_enum = sa.Enum(
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
)
injury_condition_enum = sa.Enum(
    "ACUTE_PAIN",
    "POST_SURGICAL",
    "TENDINOPATHY",
    "JOINT_INSTABILITY",
    "CHRONIC_RECURRENT",
    "RESOLVED_CAUTIOUS",
    "UNSPECIFIED",
    name="injurycondition",
)
injury_phase_enum = sa.Enum(
    "ACUTE",
    "REHABILITATING",
    "RESOLVED_CAUTIOUS",
    "CLEARED",
    name="injuryphase",
)
injury_source_enum = sa.Enum(
    "USER_REPORTED",
    "PROFESSIONAL_CLEARED",
    name="injurysource",
)


def upgrade() -> None:
    op.create_table(
        "injury_records",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("region", injury_region_enum, nullable=False),
        sa.Column("condition", injury_condition_enum, nullable=False),
        sa.Column("phase", injury_phase_enum, nullable=False),
        sa.Column("provocations", sa.JSON(), nullable=False),
        sa.Column("severity", sa.Integer(), nullable=False),
        sa.Column("reported_at", sa.Date(), nullable=False),
        sa.Column("source", injury_source_enum, nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_injury_records_user_id"), "injury_records", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_injury_records_user_id"), table_name="injury_records")
    op.drop_table("injury_records")
    injury_region_enum.drop(op.get_bind(), checkfirst=True)
    injury_condition_enum.drop(op.get_bind(), checkfirst=True)
    injury_phase_enum.drop(op.get_bind(), checkfirst=True)
    injury_source_enum.drop(op.get_bind(), checkfirst=True)
