"""add duration_weeks range to program templates

Revision ID: d1fcbf156087
Revises: c3d9f7a1b5e8
Create Date: 2026-08-05 00:00:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d1fcbf156087"
down_revision: Union[str, None] = "c3d9f7a1b5e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# (default, min, max) per template slug - see docs/superpowers/specs/2026-08-05-template-duration-weeks-design.md
DURATION_WEEKS_BY_SLUG = {
    "full-body-x3": (8, 4, 12),
    "bodyweight-full-body-x3": (8, 4, 12),
    "upper-lower-x4": (8, 4, 12),
    "push-pull-legs-x6": (12, 6, 18),
    "full-body-x2": (8, 4, 12),
    "full-body-endurance-x3": (8, 4, 12),
    "full-body-undulating-x3": (8, 4, 12),
    "upper-lower-advanced-x4": (8, 4, 12),
    "body-part-split-x5": (10, 5, 15),
    "powerlifting-strength-x4": (12, 8, 16),
}


def upgrade() -> None:
    op.add_column(
        "program_templates",
        sa.Column("duration_weeks_default", sa.Integer(), nullable=False, server_default="8"),
    )
    op.add_column(
        "program_templates",
        sa.Column("duration_weeks_min", sa.Integer(), nullable=False, server_default="4"),
    )
    op.add_column(
        "program_templates",
        sa.Column("duration_weeks_max", sa.Integer(), nullable=False, server_default="12"),
    )
    connection = op.get_bind()
    for slug, (default, minimum, maximum) in DURATION_WEEKS_BY_SLUG.items():
        connection.execute(
            sa.text(
                "UPDATE program_templates SET duration_weeks_default = :default, "
                "duration_weeks_min = :minimum, duration_weeks_max = :maximum WHERE slug = :slug"
            ),
            {"default": default, "minimum": minimum, "maximum": maximum, "slug": slug},
        )
    op.alter_column("program_templates", "duration_weeks_default", server_default=None)
    op.alter_column("program_templates", "duration_weeks_min", server_default=None)
    op.alter_column("program_templates", "duration_weeks_max", server_default=None)


def downgrade() -> None:
    op.drop_column("program_templates", "duration_weeks_max")
    op.drop_column("program_templates", "duration_weeks_min")
    op.drop_column("program_templates", "duration_weeks_default")
