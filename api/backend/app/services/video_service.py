"""Video orchestration service managing video jobs, caching, deduplication, and polling."""

import asyncio
import logging
import threading
import time
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
import httpx
from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config import get_settings
from backend.app.core.dsa_keywords import contains_dsa_keyword, has_prompt_injection
from backend.app.db.session import get_db_session
from backend.app.integrations.video import VideoProvider, get_video_provider
from backend.app.models.problem import Problem
from backend.app.models.solution import Solution
from backend.app.models.user import User
from backend.app.models.video import VideoJobModel
from backend.app.repositories.problem_repository import ProblemRepository
from backend.app.repositories.solution_repository import SolutionRepository
from backend.app.repositories.video_repository import VideoRepository
from backend.app.schemas.video import (
    CreateVideoJobRequest,
    VideoJobResponse,
    VideoResultResponse,
)
from backend.app.services.cache_service import CacheService
from backend.app.services.payload_builder import PayloadBuilder

logger = logging.getLogger(__name__)

OUT_OF_SCOPE_MESSAGE = (
    "Sorry, I can only help with data structures and algorithms. "
    "Try a LeetCode number, a problem name, or a topic like arrays, trees or graphs."
)


class VideoService:
    """Service orchestrating video generation jobs and lifecycle management."""

    def __init__(
        self,
        video_repo: Optional[VideoRepository] = None,
        problem_repo: Optional[ProblemRepository] = None,
        solution_repo: Optional[SolutionRepository] = None,
        provider: Optional[VideoProvider] = None,
    ):
        self.video_repo = video_repo or VideoRepository()
        self.problem_repo = problem_repo or ProblemRepository()
        self.solution_repo = solution_repo or SolutionRepository()
        self.provider = provider or get_video_provider()

    @staticmethod
    def determine_solution_origin(
        returned_code: Optional[str],
        returned_lang: Optional[str],
        sent_code: Optional[str],
        sent_validated: bool,
        user_submitted_code: Optional[str],
    ) -> Optional[Dict[str, Any]]:
        """Determine provenance and validation status of returned code conforming to Requirement 8:
        - validated=true and origin='repo' only if returned code equals sent code AND sent validated=true;
        - origin='user_code' if returned code equals user-submitted code;
        - otherwise validated=false and origin='ai_generated'.
        """
        if returned_code is None:
            return None

        r_code = returned_code.strip()
        s_code = sent_code.strip() if sent_code else None
        u_code = user_submitted_code.strip() if user_submitted_code else None

        if sent_validated and s_code is not None and r_code == s_code:
            origin = "repo"
            validated = True
        elif u_code is not None and r_code == u_code:
            origin = "user_code"
            validated = False
        else:
            origin = "ai_generated"
            validated = False

        return {
            "code": returned_code,
            "programming_language": returned_lang,
            "validated": validated,
            "origin": origin,
        }

    def _verify_video_url_live(self, video_url: str) -> bool:
        """Perform HEAD request in non-mock mode. Returns False if 404."""
        settings = get_settings()
        if settings.VIDEO_PROVIDER.lower() == "mock":
            return True
        try:
            with httpx.Client(timeout=5.0) as client:
                res = client.head(video_url)
                return res.status_code != 404
        except Exception:
            return True

    def create_video_job(
        self,
        db: Session,
        user: User,
        req: CreateVideoJobRequest,
        background_tasks: BackgroundTasks,
    ) -> VideoJobResponse:
        """Initiate or reuse a video generation job following teammate contract rules."""
        # 1. Validation & Scope Check for unmatched text
        raw_text = req.text if req.text is not None else req.title
        if req.problem_id is None:
            clean_text = (raw_text or "").strip()
            if not clean_text or has_prompt_injection(clean_text) or not contains_dsa_keyword(clean_text[:300]):
                raise HTTPException(
                    status_code=422,
                    detail=OUT_OF_SCOPE_MESSAGE,
                )

        # 2. Resolve problem metadata (if problem_id provided)
        prob_obj = None
        prob_num = req.problem_id
        slug = None
        title = raw_text

        if prob_num is not None:
            prob_obj = self.problem_repo.get_by_external_id(db, str(prob_num))
            if prob_obj:
                slug = prob_obj.slug
                title = prob_obj.title

        # 3. Determine code & validation status
        is_user_code = bool(req.user_code and req.user_code.strip())
        solution_id = None
        code = None
        validated = None

        if is_user_code:
            code = req.user_code.strip()
            validated = False
        elif prob_obj:
            sols = self.solution_repo.get_by_problem_id(db, prob_obj.id, req.programming_language)
            if sols:
                code = sols[0].code
                validated = True
                solution_id = sols[0].id

        # 4. Compute internal cache key (problem number or normalized lowercase text, lang, user code hash)
        cache_key = CacheService.compute_cache_key(
            problem_id=prob_num,
            text=raw_text,
            programming_language=req.programming_language,
            user_code=code if is_user_code else None,
            is_user_code=is_user_code,
        )

        # 5. Completed video cache reuse
        existing_video = self.video_repo.get_completed_video_by_cache_key(db, cache_key)
        if existing_video:
            if self._verify_video_url_live(existing_video.video_url):
                return VideoJobResponse(
                    id=str(existing_video.video_job_id),
                    status="completed",
                    stage="completed",
                    video_url=existing_video.video_url,
                    error=None,
                )
            else:
                self.video_repo.delete_generated_video(db, existing_video)
                db.commit()

        # 6. Limit: at most 1 queued or running job per user (return existing job)
        user_active_job = self.video_repo.get_active_job_for_user(db, user.id)
        if user_active_job:
            q_pos, elapsed = self.video_repo.get_queue_position_and_elapsed(db, user_active_job)
            return VideoJobResponse(
                id=str(user_active_job.id),
                status=user_active_job.status,
                stage=user_active_job.stage,
                queue_position=q_pos,
                elapsed_seconds=elapsed,
                video_url=None,
                error=None,
            )

        # 7. Limit: global queue capacity (10 queued or running across all users -> 503)
        global_active = self.video_repo.count_active_jobs_global(db)
        if global_active >= 10:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={"error": "busy", "message": "Video queue is full, try again later"},
            )

        # 8. Limit: unmatched-text jobs 5 per hour per user
        if prob_obj is None:
            unmatched_count = self.video_repo.count_unmatched_jobs_for_user_in_last_hour(db, user.id)
            if unmatched_count >= 5:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Unmatched-text video jobs are limited to 5 per hour",
                )

        # 9. Build payload conforming to teammate's API
        payload = PayloadBuilder.build_payload(
            problem_id=prob_num,
            slug=slug,
            title=title,
            code=code,
            programming_language=req.programming_language,
            validated=validated,
            text=raw_text,
        )

        # 10. Submit to video engine provider
        provider_job_id = self.provider.submit(payload)

        # 11. Persist new video job
        job = self.video_repo.create_job(
            db=db,
            user_id=user.id,
            cache_key=cache_key,
            provider_job_id=provider_job_id,
            problem_id=prob_obj.id if prob_obj else None,
            solution_id=solution_id,
            status="queued",
            stage="queued",
        )
        db.commit()

        # 12. Schedule background polling (polling every 5 seconds)
        if get_settings().APP_ENV != "testing":
            background_tasks.add_task(
                self.poll_job_until_complete,
                job_id=str(job.id),
                provider_job_id=provider_job_id,
                cache_key=cache_key,
                sent_code=code,
                sent_validated=bool(validated),
                user_submitted_code=req.user_code.strip() if req.user_code else None,
                interval_seconds=5.0,
            )

        q_pos, elapsed = self.video_repo.get_queue_position_and_elapsed(db, job)

        return VideoJobResponse(
            id=str(job.id),
            status=job.status,
            stage=job.stage,
            queue_position=q_pos,
            elapsed_seconds=elapsed,
            video_url=None,
            error=None,
        )

    def get_job(self, db: Session, job_id: str, user: User) -> VideoJobResponse:
        """Fetch video job status. Enforces user ownership (404 otherwise)."""
        job = self.video_repo.get_job_by_id(db, job_id=job_id, user_id=user.id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video job not found",
            )

        video_url = None
        if job.status == "completed":
            gen_video = self.video_repo.get_completed_video_by_cache_key(db, job.fingerprint)
            if gen_video:
                video_url = gen_video.video_url

        q_pos, elapsed = self.video_repo.get_queue_position_and_elapsed(db, job)

        return VideoJobResponse(
            id=str(job.id),
            status=job.status,
            stage=job.stage,
            queue_position=q_pos,
            elapsed_seconds=elapsed,
            video_url=video_url,
            error=job.error_code,
        )

    def get_job_result(self, db: Session, job_id: str, user: User) -> VideoResultResponse:
        """Fetch completed video result. Enforces user ownership and completion status."""
        job = self.video_repo.get_job_by_id(db, job_id=job_id, user_id=user.id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video job not found",
            )

        if job.status == "failed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Video generation failed: {job.error_code or 'Unknown error'}",
            )

        if job.status != "completed":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Video job is not completed yet (status: {job.status}, stage: {job.stage})",
            )

        gen_video = self.video_repo.get_completed_video_by_cache_key(db, job.fingerprint)
        if not gen_video:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Generated video result artifact not found",
            )

        return VideoResultResponse(
            video_url=gen_video.video_url,
            blob_name=gen_video.blob_name,
            status="completed",
            solution=gen_video.solution_json,
        )

    def retry_job(
        self,
        db: Session,
        job_id: str,
        user: User,
        background_tasks: BackgroundTasks,
    ) -> VideoJobResponse:
        """Retry a failed video job. Only failed jobs can be retried."""
        job = self.video_repo.get_job_by_id(db, job_id=job_id, user_id=user.id)
        if not job:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Video job not found",
            )

        if job.status != "failed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only failed jobs can be retried",
            )

        dummy_payload = {"retry_job_id": str(job.id), "fingerprint": job.fingerprint}
        new_provider_job_id = self.provider.submit(dummy_payload)

        job.status = "queued"
        job.stage = "queued"
        job.error_code = None
        job.provider_job_id = new_provider_job_id
        db.commit()

        if get_settings().APP_ENV != "testing":
            background_tasks.add_task(
                self.poll_job_until_complete,
                job_id=str(job.id),
                provider_job_id=new_provider_job_id,
                cache_key=job.fingerprint,
                interval_seconds=5.0,
            )

        q_pos, elapsed = self.video_repo.get_queue_position_and_elapsed(db, job)

        return VideoJobResponse(
            id=str(job.id),
            status=job.status,
            stage=job.stage,
            queue_position=q_pos,
            elapsed_seconds=elapsed,
            video_url=None,
            error=None,
        )

    def poll_job_until_complete(
        self,
        job_id: str,
        provider_job_id: str,
        cache_key: str,
        sent_code: Optional[str] = None,
        sent_validated: bool = False,
        user_submitted_code: Optional[str] = None,
        db: Optional[Session] = None,
        max_duration_seconds: Optional[float] = None,
        interval_seconds: float = 5.0,
    ) -> None:
        """Background task polling provider status every 5 seconds until terminal state or timeout."""
        job_uuid = uuid.UUID(job_id) if isinstance(job_id, str) else job_id
        settings = get_settings()
        timeout_limit = (
            max_duration_seconds
            if max_duration_seconds is not None
            else float(settings.VIDEO_JOB_TIMEOUT_MINUTES * 60)
        )
        start_time = time.time()

        while True:
            # Check timeout
            elapsed = time.time() - start_time
            if elapsed >= timeout_limit:
                should_close = False
                session = db or get_db_session()
                if db is None:
                    should_close = True
                if session is not None:
                    try:
                        self.video_repo.update_job_status(
                            db=session,
                            job_id=job_uuid,
                            status="failed",
                            stage="failed",
                            error_code="timed out",
                        )
                        session.commit()
                    finally:
                        if should_close:
                            session.close()
                break

            status_data = self.provider.get_status(provider_job_id)

            # Retryable error (timeouts, 5xx): do not fail the job
            if status_data.get("retryable") or status_data.get("status") == "retry":
                if interval_seconds > 0:
                    time.sleep(interval_seconds)
                continue

            status_val = status_data.get("status")
            stage_val = status_data.get("stage", status_val)
            video_url = status_data.get("video_url")
            blob_name = status_data.get("blob_name")
            error_val = status_data.get("error")
            returned_sol = status_data.get("solution")

            should_close = False
            session = db or get_db_session()
            if db is None:
                should_close = True

            if session is not None:
                try:
                    if status_val == "completed":
                        # Determine solution provenance
                        ret_code = returned_sol.get("code") if isinstance(returned_sol, dict) else None
                        ret_lang = (
                            returned_sol.get("programming_language")
                            if isinstance(returned_sol, dict)
                            else None
                        )
                        solution_json = self.determine_solution_origin(
                            returned_code=ret_code,
                            returned_lang=ret_lang,
                            sent_code=sent_code,
                            sent_validated=sent_validated,
                            user_submitted_code=user_submitted_code,
                        )

                        self.video_repo.update_job_status(
                            db=session,
                            job_id=job_uuid,
                            status="completed",
                            stage="completed",
                            completed_at=datetime.now(timezone.utc),
                        )
                        if video_url and blob_name:
                            existing = self.video_repo.get_completed_video_by_cache_key(session, cache_key)
                            if not existing:
                                self.video_repo.create_generated_video(
                                    db=session,
                                    video_job_id=job_uuid,
                                    cache_key=cache_key,
                                    video_url=video_url,
                                    blob_name=blob_name,
                                    solution_json=solution_json,
                                )
                            elif solution_json and not existing.solution_json:
                                existing.solution_json = solution_json
                                session.flush()
                        session.commit()
                        break

                    elif status_val == "failed":
                        self.video_repo.update_job_status(
                            db=session,
                            job_id=job_uuid,
                            status="failed",
                            stage="failed",
                            error_code=error_val or "render_failed",
                        )
                        session.commit()
                        break

                    else:
                        # Still queued or running
                        self.video_repo.update_job_status(
                            db=session,
                            job_id=job_uuid,
                            status=status_val,
                            stage=stage_val,
                        )
                        session.commit()

                finally:
                    if should_close:
                        session.close()

            if interval_seconds > 0:
                time.sleep(interval_seconds)
            else:
                break

    @classmethod
    def resume_uncompleted_jobs(cls, db: Optional[Session] = None) -> List[str]:
        """On app startup, resume polling for video_jobs in queued or running state
        that have a provider_job_id; mark those without one as failed.
        """
        should_close = False
        session = db or get_db_session()
        if db is None:
            should_close = True

        if session is None:
            return []

        try:
            repo = VideoRepository()
            stmt = select(VideoJobModel).where(VideoJobModel.status.in_(["queued", "running"]))
            active_jobs = session.scalars(stmt).all()

            resumed_ids: List[str] = []
            for job in active_jobs:
                if not job.provider_job_id or not job.provider_job_id.strip():
                    job.status = "failed"
                    job.stage = "failed"
                    job.error_code = "failed"
                else:
                    resumed_ids.append(str(job.id))
                    if get_settings().APP_ENV != "testing":
                        service = cls()
                        # Resolve sent code if problem solution exists
                        sent_code = None
                        sent_val = False
                        if job.solution_id:
                            sol = session.get(Solution, job.solution_id)
                            if sol:
                                sent_code = sol.code
                                sent_val = True

                        threading.Thread(
                            target=service.poll_job_until_complete,
                            kwargs={
                                "job_id": str(job.id),
                                "provider_job_id": job.provider_job_id,
                                "cache_key": job.fingerprint,
                                "sent_code": sent_code,
                                "sent_validated": sent_val,
                                "interval_seconds": 5.0,
                            },
                            daemon=True,
                        ).start()

            session.commit()
            return resumed_ids
        finally:
            if should_close:
                session.close()
