"""add_unique_constraints_problems_solutions

Revision ID: g2c9d3e4f5b6
Revises: f1b8c2d3e4a5
Create Date: 2026-10-26 03:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "g2c9d3e4f5b6"
down_revision: Union[str, None] = "f1b8c2d3e4a5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_problems_source_external_id ON problems (source, external_problem_id);"
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_solutions_problem_language ON solutions (problem_id, language);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS uq_solutions_problem_language;")
    op.execute("DROP INDEX IF EXISTS uq_problems_source_external_id;")
