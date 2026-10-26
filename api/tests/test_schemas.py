"""Unit tests verifying schemas conform to docs/api-contract.md."""

import pytest
from pydantic import ValidationError
from backend.app.schemas import (
    AskRequest,
    AskResponse,
    CandidateInfo,
    HealthResponse,
    ProblemInfo,
    SolutionInfo,
    VideoJob,
)


def test_ask_request_schema_valid():
    """Verify valid AskRequest instance."""
    req = AskRequest(text="Two Sum", programming_language="python")
    assert req.text == "Two Sum"
    assert req.programming_language == "python"

    # Default programming_language is python
    req_default = AskRequest(text="Two Sum")
    assert req_default.programming_language == "python"


def test_ask_request_schema_invalid():
    """Verify validation error on invalid language or empty text."""
    with pytest.raises(ValidationError):
        AskRequest(text="Two Sum", programming_language="rust")

    with pytest.raises(ValidationError):
        AskRequest(text="")


def test_ask_response_schema():
    """Verify AskResponse structure and statuses."""
    resp = AskResponse(
        status="found",
        message="Found verified Python solution",
        problem=ProblemInfo(id=1, slug="two-sum", title="Two Sum"),
        solution=SolutionInfo(language="python", code="def twoSum(): pass", validated=True),
        available_languages=["python", "java"],
        can_generate=True,
    )
    assert resp.status == "found"
    assert resp.can_generate is True
    assert resp.problem.id == 1
    assert resp.solution.validated is True
    assert resp.available_languages == ["python", "java"]


def test_candidate_info_schema():
    """Verify CandidateInfo structure for clarification candidates."""
    cand = CandidateInfo(id=1, slug="two-sum", title="Two Sum")
    assert cand.id == 1
    assert cand.slug == "two-sum"
    assert cand.title == "Two Sum"


def test_video_job_schema():
    """Verify VideoJob statuses and fields."""
    job = VideoJob(
        id="job_42",
        status="completed",
        stage="uploading",
        video_url="https://storage.blob.core.windows.net/videos/sample.mp4",
        error=None,
    )
    assert job.status == "completed"
    assert job.video_url is not None


def test_health_response_schema():
    """Verify HealthResponse schema structure."""
    resp = HealthResponse(status="ok", db=True)
    assert resp.status == "ok"
    assert resp.db is True
