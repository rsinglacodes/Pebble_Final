#!/usr/bin/env python3
"""CLI script to ingest solutions and problems from walkccc/LeetCode repository."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config import get_settings
from backend.app.db.session import get_db_session
from backend.app.services.ingest_service import IngestService


def clone_repository(repo_url: str, target_dir: str, skip_clone: bool = False) -> None:
    """Clone the source repository if it does not already exist."""
    solutions_dir = os.path.join(target_dir, "solutions")
    git_dir = os.path.join(target_dir, ".git")

    if skip_clone:
        print("[INFO] Skipping repository clone/pull due to --skip-clone flag.")
        return

    if os.path.exists(solutions_dir) and os.path.isdir(solutions_dir):
        print(f"[INFO] Solutions directory already exists at {solutions_dir}. Using existing solutions and skipping git clone/pull.")
        return

    if os.path.exists(git_dir):
        print(f"[INFO] Source repository already cloned at {target_dir}")
        return

    os.makedirs(target_dir, exist_ok=True)
    print(f"[INFO] Cloning {repo_url} (depth 1) into {target_dir}...")
    try:
        subprocess.run(
            ["git", "clone", "--depth", "1", repo_url, target_dir],
            check=True,
            capture_output=True,
            text=True,
        )
        print("[INFO] Repository cloned successfully.")
    except subprocess.CalledProcessError as e:
        # On Windows, git clone may fail checkout on filenames with '?' or ':'
        # but the .git object database is intact, which IngestService can still read.
        if os.path.exists(git_dir):
            print(f"[WARN] Git clone completed with checkout warnings (expected on Windows NTFS): {e.stderr[:200]}")
        else:
            print(f"[ERROR] Failed to clone repository: {e.stderr}")
            raise


def main() -> None:
    """Main CLI execution."""
    parser = argparse.ArgumentParser(description="Ingest LeetCode solutions into Pebble database.")
    parser.add_argument(
        "--repo-path",
        default="data/source_repo",
        help="Local directory path for walkccc/LeetCode repository",
    )
    parser.add_argument(
        "--repo-url",
        default="https://github.com/walkccc/LeetCode",
        help="Git repository URL to clone",
    )
    parser.add_argument(
        "--skip-clone",
        action="store_true",
        help="Skip cloning or pulling the source repository",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Limit ingestion to the first N problems",
    )
    args = parser.parse_args()

    # Step 1: Clone or verify source repo
    target_path = os.path.abspath(args.repo_path)
    clone_repository(args.repo_url, target_path, skip_clone=args.skip_clone)

    # Step 2: Establish database connection
    db = get_db_session()
    if db is None:
        print("[ERROR] Database connection could not be established. Check DATABASE_URL in environment.")
        sys.exit(1)

    # Step 3: Run ingestion
    try:
        service = IngestService()
        stats = service.ingest(db=db, repo_path=target_path, limit=args.limit)
        print(f"[SUCCESS] Ingestion completed. Problems created: {stats.problems_created}, updated: {stats.problems_updated}, unchanged: {stats.problems_unchanged}")
    except Exception as exc:
        print(f"[ERROR] Ingestion failed: {exc}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
