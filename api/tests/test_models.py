"""Unit tests validating SQLAlchemy 2.0 ORM models and schema constraints."""

from backend.app.db.base import Base
from backend.app.models import (
    AuthIdentity,
    Conversation,
    ExecutionTraceModel,
    GeneratedVideo,
    Message,
    Problem,
    ProblemTest,
    Roadmap,
    RoadmapProblem,
    Solution,
    SolutionTest,
    User,
    UserPreference,
    UserProgress,
    VideoJobModel,
)


def test_registered_tables_count():
    """Verify all 15 tables are properly registered with Base.metadata."""
    table_names = set(Base.metadata.tables.keys())
    expected_tables = {
        "users",
        "auth_identities",
        "user_preferences",
        "problems",
        "problem_tests",
        "solutions",
        "solution_tests",
        "execution_traces",
        "conversations",
        "messages",
        "user_progress",
        "roadmaps",
        "roadmap_problems",
        "video_jobs",
        "generated_videos",
    }
    assert expected_tables.issubset(table_names), f"Missing tables: {expected_tables - table_names}"
    assert len(expected_tables) == 15


def test_problem_tests_columns():
    """Verify problem_tests table has all requested columns."""
    table = Base.metadata.tables["problem_tests"]
    columns = set(table.columns.keys())
    required_cols = {"id", "problem_id", "input_json", "expected_json", "source", "created_at"}
    assert required_cols.issubset(columns)


def test_unique_constraints():
    """Verify blueprint-required unique constraints."""
    # 1. auth provider + provider_subject
    auth_table = Base.metadata.tables["auth_identities"]
    auth_unique_names = {c.name for c in auth_table.constraints if hasattr(c, "columns")}
    assert "uq_auth_identities_provider_subject" in auth_unique_names

    # 2. user_id + problem_id in user_progress
    progress_table = Base.metadata.tables["user_progress"]
    progress_unique_names = {c.name for c in progress_table.constraints if hasattr(c, "columns")}
    assert "uq_user_progress_user_problem" in progress_unique_names

    # 3. fingerprint in generated_videos
    video_table = Base.metadata.tables["generated_videos"]
    video_unique_cols = [
        set(c.columns.keys()) for c in video_table.constraints if hasattr(c, "columns")
    ]
    assert {"fingerprint"} in video_unique_cols
