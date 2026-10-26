"""Repository handling database access for VideoJobModel and GeneratedVideo."""

import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple, Union
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from backend.app.models.video import GeneratedVideo, VideoJobModel


class VideoRepository:
    """Repository handling database operations for video jobs and generated videos."""

    @staticmethod
    def get_completed_video_by_cache_key(
        db: Session, cache_key: str
    ) -> Optional[GeneratedVideo]:
        """Fetch completed video record by unique cache key."""
        stmt = select(GeneratedVideo).where(GeneratedVideo.fingerprint == cache_key)
        return db.scalars(stmt).first()

    @staticmethod
    def delete_generated_video(db: Session, video: GeneratedVideo) -> None:
        """Remove a stale generated video record."""
        db.delete(video)
        db.flush()

    @staticmethod
    def create_generated_video(
        db: Session,
        video_job_id: uuid.UUID,
        cache_key: str,
        video_url: str,
        blob_name: str,
        solution_json: Optional[Dict[str, Any]] = None,
    ) -> GeneratedVideo:
        """Persist a completed generated video."""
        gen_video = GeneratedVideo(
            video_job_id=video_job_id,
            fingerprint=cache_key,
            video_url=video_url,
            blob_name=blob_name,
            solution_json=solution_json,
        )
        db.add(gen_video)
        db.flush()
        db.refresh(gen_video)
        return gen_video

    @staticmethod
    def get_active_job_by_cache_key(
        db: Session, cache_key: str
    ) -> Optional[VideoJobModel]:
        """Fetch active (queued or running) job matching cache key."""
        stmt = (
            select(VideoJobModel)
            .where(
                VideoJobModel.fingerprint == cache_key,
                VideoJobModel.status.in_(["queued", "running"]),
            )
            .order_by(VideoJobModel.created_at.desc())
        )
        return db.scalars(stmt).first()

    @staticmethod
    def get_active_job_for_user(
        db: Session, user_id: Union[uuid.UUID, str]
    ) -> Optional[VideoJobModel]:
        """Fetch currently active (queued or running) job for a specific user (limit 1)."""
        uid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
        stmt = (
            select(VideoJobModel)
            .where(
                VideoJobModel.user_id == uid,
                VideoJobModel.status.in_(["queued", "running"]),
            )
            .order_by(VideoJobModel.created_at.desc())
        )
        return db.scalars(stmt).first()

    @staticmethod
    def count_active_jobs_global(db: Session) -> int:
        """Count total queued or running jobs across all users (queue capacity limit 10)."""
        stmt = select(func.count(VideoJobModel.id)).where(
            VideoJobModel.status.in_(["queued", "running"])
        )
        return int(db.scalar(stmt) or 0)

    @staticmethod
    def count_unmatched_jobs_for_user_in_last_hour(
        db: Session, user_id: Union[uuid.UUID, str]
    ) -> int:
        """Count unmatched-text jobs (problem_id is None) created by user in last 1 hour (limit 5)."""
        uid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
        one_hour_ago = datetime.now(timezone.utc) - timedelta(hours=1)
        stmt = select(func.count(VideoJobModel.id)).where(
            VideoJobModel.user_id == uid,
            VideoJobModel.problem_id.is_(None),
            VideoJobModel.created_at >= one_hour_ago,
        )
        return int(db.scalar(stmt) or 0)

    @staticmethod
    def get_queue_position_and_elapsed(
        db: Session, job: VideoJobModel
    ) -> Tuple[Optional[int], Optional[int]]:
        """Calculate queue_position and elapsed_seconds for active jobs."""
        if job.status not in ("queued", "running"):
            return None, None

        # Count earlier jobs still queued or running
        stmt = select(func.count(VideoJobModel.id)).where(
            VideoJobModel.status.in_(["queued", "running"]),
            VideoJobModel.created_at < job.created_at,
        )
        earlier_count = int(db.scalar(stmt) or 0)
        queue_position = earlier_count + 1

        # Elapsed seconds since creation
        now_utc = datetime.now(timezone.utc)
        created_utc = job.created_at
        if created_utc.tzinfo is None:
            created_utc = created_utc.replace(tzinfo=timezone.utc)
        elapsed_seconds = max(0, int((now_utc - created_utc).total_seconds()))

        return queue_position, elapsed_seconds

    @staticmethod
    def create_job(
        db: Session,
        user_id: Union[uuid.UUID, str],
        cache_key: str,
        provider_job_id: Optional[str] = None,
        problem_id: Optional[Union[uuid.UUID, str]] = None,
        solution_id: Optional[Union[uuid.UUID, str]] = None,
        status: str = "queued",
        stage: str = "queued",
    ) -> VideoJobModel:
        """Create and persist a new video generation job."""
        if isinstance(user_id, str):
            user_id = uuid.UUID(user_id)
        if problem_id and isinstance(problem_id, str):
            problem_id = uuid.UUID(problem_id)
        if solution_id and isinstance(solution_id, str):
            solution_id = uuid.UUID(solution_id)

        job = VideoJobModel(
            user_id=user_id,
            problem_id=problem_id,
            solution_id=solution_id,
            fingerprint=cache_key,
            provider_job_id=provider_job_id,
            status=status,
            stage=stage,
        )
        db.add(job)
        db.flush()
        db.refresh(job)
        return job

    @staticmethod
    def get_job_by_id(
        db: Session,
        job_id: Union[uuid.UUID, str],
        user_id: Optional[Union[uuid.UUID, str]] = None,
    ) -> Optional[VideoJobModel]:
        """Fetch video job by UUID, optionally enforcing user ownership."""
        if isinstance(job_id, str):
            try:
                job_id = uuid.UUID(job_id)
            except ValueError:
                return None

        stmt = select(VideoJobModel).where(VideoJobModel.id == job_id)
        if user_id is not None:
            if isinstance(user_id, str):
                try:
                    user_id = uuid.UUID(user_id)
                except ValueError:
                    return None
            stmt = stmt.where(VideoJobModel.user_id == user_id)

        return db.scalars(stmt).first()

    @staticmethod
    def update_job_status(
        db: Session,
        job_id: uuid.UUID,
        status: str,
        stage: str,
        error_code: Optional[str] = None,
        completed_at: Optional[datetime] = None,
    ) -> Optional[VideoJobModel]:
        """Update lifecycle status and stage of a video job."""
        job = VideoRepository.get_job_by_id(db, job_id)
        if job:
            job.status = status
            job.stage = stage
            if error_code is not None:
                job.error_code = error_code
            if completed_at is not None:
                job.completed_at = completed_at
            elif status == "completed" and not job.completed_at:
                job.completed_at = datetime.now(timezone.utc)
            db.flush()
            db.refresh(job)
        return job
