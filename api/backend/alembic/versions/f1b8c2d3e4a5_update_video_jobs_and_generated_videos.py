"""update_video_jobs_and_generated_videos_schema

Revision ID: f1b8c2d3e4a5
Revises: e4a2c1f09b40
Create Date: 2026-10-26 00:30:00.000000

"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f1b8c2d3e4a5"
down_revision: Union[str, None] = "e4a2c1f09b40"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add provider_job_id to video_jobs
    op.add_column("video_jobs", sa.Column("provider_job_id", sa.String(length=255), nullable=True))

    # 2. Add video_url and blob_name to generated_videos
    op.add_column("generated_videos", sa.Column("video_url", sa.Text(), nullable=True))
    op.add_column("generated_videos", sa.Column("blob_name", sa.Text(), nullable=True))

    # 3. Drop unused legacy columns from generated_videos
    op.drop_column("generated_videos", "r2_object_key")
    op.drop_column("generated_videos", "content_type")
    op.drop_column("generated_videos", "size_bytes")
    op.drop_column("generated_videos", "duration_seconds")
    op.drop_column("generated_videos", "render_version")


def downgrade() -> None:
    # Restore legacy columns to generated_videos
    op.add_column("generated_videos", sa.Column("render_version", sa.String(length=50), nullable=True))
    op.add_column("generated_videos", sa.Column("duration_seconds", sa.Float(), nullable=True))
    op.add_column("generated_videos", sa.Column("size_bytes", sa.BigInteger(), nullable=True))
    op.add_column("generated_videos", sa.Column("content_type", sa.String(length=50), nullable=True))
    op.add_column("generated_videos", sa.Column("r2_object_key", sa.String(length=500), nullable=True))

    op.drop_column("generated_videos", "blob_name")
    op.drop_column("generated_videos", "video_url")
    op.drop_column("video_jobs", "provider_job_id")
