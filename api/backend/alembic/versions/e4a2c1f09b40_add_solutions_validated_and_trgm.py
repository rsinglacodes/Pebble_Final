"""add_solutions_validated_commit_sha_and_trgm_indexes

Revision ID: e4a2c1f09b40
Revises: dec6626353f0
Create Date: 2026-10-25 20:20:00.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e4a2c1f09b40"
down_revision: Union[str, None] = "dec6626353f0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable pg_trgm extension for fuzzy string matching
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    # 2. Add validated and commit_sha to solutions table
    op.add_column(
        "solutions",
        sa.Column("validated", sa.Boolean(), server_default=sa.text("false"), nullable=False),
    )
    op.add_column(
        "solutions",
        sa.Column("commit_sha", sa.Text(), nullable=True),
    )

    # 3. Add trigram GIN indexes on problems.title and problems.slug
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_problems_title_trgm ON problems USING gin (title gin_trgm_ops);"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_problems_slug_trgm ON problems USING gin (slug gin_trgm_ops);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_problems_slug_trgm;")
    op.execute("DROP INDEX IF EXISTS ix_problems_title_trgm;")
    op.drop_column("solutions", "commit_sha")
    op.drop_column("solutions", "validated")
