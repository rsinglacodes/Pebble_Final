"""add_solution_json_to_generated_videos

Revision ID: i4e5f6a7b8c9
Revises: h3d4e5f6a7b8
Create Date: 2026-10-26 10:55:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "i4e5f6a7b8c9"
down_revision: Union[str, None] = "h3d4e5f6a7b8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("generated_videos")]
    if "solution_json" not in columns:
        op.add_column(
            "generated_videos",
            sa.Column(
                "solution_json",
                sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("generated_videos")]
    if "solution_json" in columns:
        op.drop_column("generated_videos", "solution_json")
