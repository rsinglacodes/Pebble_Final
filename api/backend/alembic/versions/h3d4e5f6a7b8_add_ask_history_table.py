"""add_ask_history_table

Revision ID: h3d4e5f6a7b8
Revises: g2c9d3e4f5b6
Create Date: 2026-10-26 10:35:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "h3d4e5f6a7b8"
down_revision: Union[str, None] = "g2c9d3e4f5b6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    tables = inspector.get_table_names()
    if "ask_history" not in tables:
        op.create_table(
            "ask_history",
            sa.Column("id", sa.Uuid(), primary_key=True),
            sa.Column(
                "user_id",
                sa.Uuid(),
                sa.ForeignKey("users.id", ondelete="CASCADE"),
                nullable=False,
            ),
            sa.Column("text", sa.String(length=5000), nullable=False),
            sa.Column("status", sa.String(length=20), nullable=False),
            sa.Column(
                "problem_id",
                sa.Uuid(),
                sa.ForeignKey("problems.id", ondelete="SET NULL"),
                nullable=True,
            ),
            sa.Column("programming_language", sa.String(length=10), nullable=True),
            sa.Column(
                "created_at",
                sa.DateTime(timezone=True),
                server_default=sa.text("now()"),
                nullable=False,
            ),
        )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_ask_history_user_id_created_at ON ask_history (user_id, created_at DESC);"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_ask_history_user_id_created_at;")
    op.drop_table("ask_history")
