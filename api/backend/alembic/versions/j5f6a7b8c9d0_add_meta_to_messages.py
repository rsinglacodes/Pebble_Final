"""add_meta_to_messages

Revision ID: j5f6a7b8c9d0
Revises: i4e5f6a7b8c9
Create Date: 2026-10-26 12:00:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "j5f6a7b8c9d0"
down_revision: Union[str, None] = "i4e5f6a7b8c9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("messages")]
    if "meta" not in columns:
        op.add_column(
            "messages",
            sa.Column(
                "meta",
                sa.JSON().with_variant(postgresql.JSONB(astext_type=sa.Text()), "postgresql"),
                nullable=True,
            ),
        )


def downgrade() -> None:
    conn = op.get_bind()
    inspector = sa.inspect(conn)
    columns = [c["name"] for c in inspector.get_columns("messages")]
    if "meta" in columns:
        op.drop_column("messages", "meta")
