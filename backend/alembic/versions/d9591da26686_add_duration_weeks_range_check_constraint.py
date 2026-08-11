"""add duration_weeks range check constraint to program_templates

Revision ID: d9591da26686
Revises: d1fcbf156087
Create Date: 2026-08-11 00:00:00.000000

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "d9591da26686"
down_revision: Union[str, None] = "d1fcbf156087"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


CONSTRAINT_NAME = "ck_program_templates_duration_weeks_range"
CONSTRAINT_SQL = "duration_weeks_min <= duration_weeks_default AND duration_weeks_default <= duration_weeks_max"


def upgrade() -> None:
    with op.batch_alter_table("program_templates") as batch_op:
        batch_op.create_check_constraint(CONSTRAINT_NAME, CONSTRAINT_SQL)


def downgrade() -> None:
    with op.batch_alter_table("program_templates") as batch_op:
        batch_op.drop_constraint(CONSTRAINT_NAME, type_="check")
