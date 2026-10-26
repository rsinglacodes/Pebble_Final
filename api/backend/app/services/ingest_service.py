"""Service to ingest problems and solutions from walkccc/LeetCode."""

import hashlib
import os
import re
import subprocess
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy import select, text
from sqlalchemy.orm import Session
from backend.app.models.problem import Problem
from backend.app.models.solution import Solution
from backend.app.repositories.problem_repository import ProblemRepository
from backend.app.repositories.solution_repository import SolutionRepository

# Supported language extensions
LANG_EXT_MAP = {
    ".py": "python",
    ".java": "java",
    ".cpp": "cpp",
}

# Explicitly skipped extensions
SKIPPED_EXTS = {
    ".ts": "TypeScript",
    ".sql": "MySQL",
}


@dataclass
class SolutionFile:
    rel_path: str
    language: str
    code: str


@dataclass
class ProblemData:
    number: int
    title: str
    slug: str
    solutions: List[SolutionFile] = field(default_factory=list)


@dataclass
class IngestionStats:
    problems_created: int = 0
    problems_updated: int = 0
    problems_unchanged: int = 0
    solutions_created: Dict[str, int] = field(default_factory=lambda: {"python": 0, "java": 0, "cpp": 0})
    solutions_updated: Dict[str, int] = field(default_factory=lambda: {"python": 0, "java": 0, "cpp": 0})
    solutions_unchanged: Dict[str, int] = field(default_factory=lambda: {"python": 0, "java": 0, "cpp": 0})
    skipped_files: Dict[str, int] = field(default_factory=dict)


class IngestService:
    """Service orchestrating solution repository scanning and database upserts."""

    def __init__(
        self,
        problem_repo: ProblemRepository = None,
        solution_repo: SolutionRepository = None,
    ):
        self.problem_repo = problem_repo or ProblemRepository()
        self.solution_repo = solution_repo or SolutionRepository()

    @staticmethod
    def parse_problem_dir(dir_name: str) -> Optional[Tuple[int, str, str]]:
        """Extract number, title, and slug from directory name (e.g. '1. Two Sum')."""
        clean_name = dir_name.strip().strip('"').strip("'")
        match = re.match(r"^(\d+)\.\s+(.+)$", clean_name)
        if not match:
            return None
        number = int(match.group(1))
        title = match.group(2).strip()
        slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        return number, title, slug

    def get_commit_sha(self, repo_path: str) -> str:
        """Fetch git commit SHA for repository, or return fallback."""
        git_dir = os.path.join(repo_path, ".git")
        if not os.path.exists(git_dir):
            return "zip-download"
        try:
            out = subprocess.check_output(
                ["git", "-C", repo_path, "rev-parse", "HEAD"],
                encoding="utf-8",
                stderr=subprocess.DEVNULL,
            )
            return out.strip()
        except Exception:
            return "zip-download"

    def scan_repository(self, repo_path: str) -> Tuple[Dict[int, ProblemData], List[str], Dict[str, int]]:
        """Scan repository files, detecting naming patterns and extracting problem code.
        
        Supports both filesystem directory traversal and git-tree reading.
        """
        problems_map: Dict[int, ProblemData] = {}
        example_paths: List[str] = []
        skipped_files: Dict[str, int] = {}

        solutions_dir = os.path.join(repo_path, "solutions")

        # Case A: Solutions checked out on filesystem
        if os.path.isdir(solutions_dir) and os.listdir(solutions_dir):
            for root, _, files in os.walk(solutions_dir):
                rel_root = os.path.relpath(root, repo_path).replace("\\", "/")
                parts = rel_root.split("/")
                if len(parts) < 2:
                    continue
                dir_name = parts[1]
                parsed = self.parse_problem_dir(dir_name)
                if not parsed:
                    continue
                number, title, slug = parsed

                if number not in problems_map:
                    problems_map[number] = ProblemData(number=number, title=title, slug=slug)

                for f in sorted(files):
                    rel_file = f"{rel_root}/{f}"
                    _, ext = os.path.splitext(f)
                    ext = ext.lower()

                    if ext in SKIPPED_EXTS:
                        reason = f"Skipped {SKIPPED_EXTS[ext]} file ({ext})"
                        skipped_files[reason] = skipped_files.get(reason, 0) + 1
                        continue

                    if ext not in LANG_EXT_MAP:
                        reason = f"Unsupported file type ({ext})" if ext else "Non-solution file"
                        skipped_files[reason] = skipped_files.get(reason, 0) + 1
                        continue

                    if len(example_paths) < 3:
                        example_paths.append(rel_file)

                    file_full_path = os.path.join(root, f)
                    try:
                        with open(file_full_path, "r", encoding="utf-8", errors="replace") as fh:
                            code = fh.read()
                        problems_map[number].solutions.append(
                            SolutionFile(rel_path=rel_file, language=LANG_EXT_MAP[ext], code=code)
                        )
                    except Exception as e:
                        reason = f"Read error: {e}"
                        skipped_files[reason] = skipped_files.get(reason, 0) + 1

            return problems_map, example_paths, skipped_files

        # Case B: Read directly from git ls-tree (handles Windows NTFS path constraints)
        git_dir = os.path.join(repo_path, ".git")
        if os.path.exists(git_dir):
            tree_output = subprocess.check_output(
                ["git", "-C", repo_path, "ls-tree", "-r", "HEAD", "solutions/"],
                encoding="utf-8",
            )
            for line in tree_output.strip().splitlines():
                parts = line.split("\t")
                if len(parts) != 2:
                    continue
                meta, rel_path = parts[0], parts[1]
                blob_sha = meta.split()[2] if len(meta.split()) >= 3 else None

                path_parts = rel_path.split("/")
                if len(path_parts) < 3:
                    continue
                dir_name = path_parts[1]
                filename = path_parts[-1]

                parsed = self.parse_problem_dir(dir_name)
                if not parsed:
                    continue
                number, title, slug = parsed

                if number not in problems_map:
                    problems_map[number] = ProblemData(number=number, title=title, slug=slug)

                _, ext = os.path.splitext(filename)
                ext = ext.lower().strip('"')

                if ext in SKIPPED_EXTS:
                    reason = f"Skipped {SKIPPED_EXTS[ext]} file ({ext})"
                    skipped_files[reason] = skipped_files.get(reason, 0) + 1
                    continue

                if ext not in LANG_EXT_MAP:
                    reason = f"Unsupported file type ({ext})" if ext else "Non-solution file"
                    skipped_files[reason] = skipped_files.get(reason, 0) + 1
                    continue

                if len(example_paths) < 3:
                    example_paths.append(rel_path)

                if blob_sha:
                    code = subprocess.check_output(
                        ["git", "-C", repo_path, "cat-file", "-p", blob_sha],
                        encoding="utf-8",
                        errors="replace",
                    )
                    problems_map[number].solutions.append(
                        SolutionFile(rel_path=rel_path, language=LANG_EXT_MAP[ext], code=code)
                    )

        return problems_map, example_paths, skipped_files

    @staticmethod
    def _format_elapsed(seconds: float) -> str:
        """Format elapsed time in seconds as MM:SS (or HH:MM:SS if >= 1 hour)."""
        total_sec = int(seconds)
        hours = total_sec // 3600
        minutes = (total_sec % 3600) // 60
        secs = total_sec % 60
        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"

    def ingest(
        self,
        db: Session,
        repo_path: str,
        commit_sha: Optional[str] = None,
        limit: Optional[int] = None,
        batch_size: int = 500,
    ) -> IngestionStats:
        """Scan repository, print detected pattern and examples, and upsert to database in batches."""
        start_time = time.time()
        actual_sha = commit_sha or self.get_commit_sha(repo_path)
        stats = IngestionStats()

        # Step 1: Scan files
        problems_map, example_paths, skipped_files = self.scan_repository(repo_path)
        stats.skipped_files = skipped_files

        # Step 2: Compute counts BEFORE writing to database
        total_problems_detected = len(problems_map)
        py_count = sum(1 for p in problems_map.values() for s in p.solutions if s.language == "python")
        java_count = sum(1 for p in problems_map.values() for s in p.solutions if s.language == "java")
        cpp_count = sum(1 for p in problems_map.values() for s in p.solutions if s.language == "cpp")

        # Step 3: Print detected pattern, 3 example paths, and counts
        print("=" * 60)
        print("PRE-INGESTION DETECTION REPORT")
        print("=" * 60)
        print("Detected Naming Pattern: solutions/{number}. {title}/{number}[-approach].{ext}")
        print("3 Example Paths:")
        for idx, ex in enumerate(example_paths[:3], start=1):
            print(f"  {idx}. {ex}")
        print(f"Total Problems Detected: {total_problems_detected}")
        print(f"Total Solution Files Detected: Python={py_count}, Java={java_count}, C++={cpp_count}")
        print(f"Total Skipped Files: {sum(skipped_files.values())}")
        for reason, count in skipped_files.items():
            print(f"  - {reason}: {count}")
        print("=" * 60)

        # Apply --limit N if requested
        sorted_keys = sorted(problems_map.keys())
        if limit is not None and limit > 0:
            sorted_keys = sorted_keys[:limit]
            print(f"[INFO] Limit applied: ingesting first {len(sorted_keys)} problems.")

        problems_to_ingest = [problems_map[k] for k in sorted_keys]
        total_problems_to_ingest = len(problems_to_ingest)

        # Ensure unique indexes exist on target tables
        try:
            if db.bind and db.bind.dialect.name == "postgresql":
                db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_problems_source_external_id ON problems (source, external_problem_id);"))
                db.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS uq_solutions_problem_language ON solutions (problem_id, language);"))
                db.flush()
        except Exception:
            pass

        # Step 4: Speed optimization: Load all existing content hashes in ONE query at start
        stmt_hashes = (
            select(Problem.external_problem_id, Solution.language, Solution.content_hash)
            .join(Solution, Solution.problem_id == Problem.id)
            .where(Problem.source == "walkccc")
        )
        existing_hashes: Dict[Tuple[str, str], str] = {}
        for row in db.execute(stmt_hashes):
            existing_hashes[(str(row.external_problem_id), row.language.lower())] = row.content_hash

        # Load existing problems in ONE query to resolve IDs and detect changes
        stmt_problems = select(
            Problem.external_problem_id,
            Problem.id,
            Problem.title,
            Problem.slug,
            Problem.canonical_url,
        ).where(Problem.source == "walkccc")
        existing_problems: Dict[str, Dict[str, Any]] = {}
        problem_id_map: Dict[str, uuid.UUID] = {}
        for row in db.execute(stmt_problems):
            ext_id = str(row.external_problem_id)
            existing_problems[ext_id] = {
                "id": row.id,
                "title": row.title,
                "slug": row.slug,
                "canonical_url": row.canonical_url,
            }
            problem_id_map[ext_id] = row.id

        # Determine dialect-specific insert
        if db.bind and db.bind.dialect.name == "sqlite":
            from sqlalchemy.dialects.sqlite import insert as dialect_insert
        else:
            from sqlalchemy.dialects.postgresql import insert as dialect_insert

        # Step 5: Upsert problems in batches of batch_size (default 500)
        problems_done = 0
        solutions_done = 0

        # We first prepare the total number of distinct solutions across the problems to ingest
        # Deduplicating per language for each problem (canonical {number}.{ext} preferred)
        deduped_solutions_by_problem: Dict[int, Dict[str, SolutionFile]] = {}
        for pdata in problems_to_ingest:
            lang_sols: Dict[str, SolutionFile] = {}
            for sfile in pdata.solutions:
                lang = sfile.language
                if lang not in lang_sols:
                    lang_sols[lang] = sfile
                else:
                    filename = os.path.basename(sfile.rel_path)
                    expected_canonical = f"{pdata.number}."
                    if filename.startswith(expected_canonical) and "-" not in filename:
                        lang_sols[lang] = sfile
            deduped_solutions_by_problem[pdata.number] = lang_sols

        total_solutions_to_ingest = sum(len(sols) for sols in deduped_solutions_by_problem.values())

        for i in range(0, total_problems_to_ingest, batch_size):
            p_batch = problems_to_ingest[i : i + batch_size]
            batch_values = []
            for pdata in p_batch:
                ext_id = str(pdata.number)
                canonical_url = f"https://leetcode.com/problems/{pdata.slug}/"
                pid = problem_id_map.get(ext_id) or uuid.uuid4()
                problem_id_map[ext_id] = pid

                if ext_id not in existing_problems:
                    stats.problems_created += 1
                else:
                    ex = existing_problems[ext_id]
                    if (ex["title"] != pdata.title or ex["slug"] != pdata.slug or ex["canonical_url"] != canonical_url):
                        stats.problems_updated += 1
                    else:
                        stats.problems_unchanged += 1

                batch_values.append({
                    "id": pid,
                    "source": "walkccc",
                    "external_problem_id": ext_id,
                    "title": pdata.title,
                    "slug": pdata.slug,
                    "difficulty": "Medium",
                    "canonical_url": canonical_url,
                    "created_at": datetime.now(timezone.utc),
                })

            if batch_values:
                stmt_p = dialect_insert(Problem).values(batch_values)
                stmt_p = stmt_p.on_conflict_do_update(
                    index_elements=["source", "external_problem_id"],
                    set_={
                        "title": stmt_p.excluded.title,
                        "slug": stmt_p.excluded.slug,
                        "canonical_url": stmt_p.excluded.canonical_url,
                    },
                )
                if hasattr(stmt_p, "returning"):
                    stmt_p = stmt_p.returning(Problem.id, Problem.external_problem_id)
                    res = db.execute(stmt_p)
                    for r in res.all():
                        problem_id_map[str(r.external_problem_id)] = r.id
                else:
                    db.execute(stmt_p)

                db.commit()

            problems_done += len(p_batch)
            elapsed_str = self._format_elapsed(time.time() - start_time)
            print(f"problems {problems_done}/{total_problems_to_ingest}, solutions {solutions_done}/{total_solutions_to_ingest}, elapsed {elapsed_str}")

        # Step 6: Identify solutions to upsert vs skip
        solutions_to_upsert = []
        for pdata in problems_to_ingest:
            ext_id = str(pdata.number)
            prob_id = problem_id_map[ext_id]
            lang_sols = deduped_solutions_by_problem[pdata.number]

            for lang, sfile in lang_sols.items():
                content_hash = hashlib.sha256(sfile.code.encode("utf-8")).hexdigest()
                key = (ext_id, lang)

                if key in existing_hashes:
                    if existing_hashes[key] == content_hash:
                        stats.solutions_unchanged[lang] = stats.solutions_unchanged.get(lang, 0) + 1
                        solutions_done += 1
                        continue
                    else:
                        stats.solutions_updated[lang] = stats.solutions_updated.get(lang, 0) + 1
                else:
                    stats.solutions_created[lang] = stats.solutions_created.get(lang, 0) + 1

                github_url = f"https://github.com/walkccc/LeetCode/blob/{actual_sha}/{sfile.rel_path}"
                solutions_to_upsert.append({
                    "id": uuid.uuid4(),
                    "problem_id": prob_id,
                    "language": lang,
                    "code": sfile.code,
                    "source_type": "retrieved",
                    "source_url": github_url,
                    "content_hash": content_hash,
                    "commit_sha": actual_sha,
                    "validated": True,
                    "validation_status": "verified",
                    "created_at": datetime.now(timezone.utc),
                })

        # Step 7: Upsert solutions in batches of batch_size (default 500)
        for i in range(0, len(solutions_to_upsert), batch_size):
            s_batch = solutions_to_upsert[i : i + batch_size]
            stmt_s = dialect_insert(Solution).values(s_batch)
            stmt_s = stmt_s.on_conflict_do_update(
                index_elements=["problem_id", "language"],
                set_={
                    "code": stmt_s.excluded.code,
                    "content_hash": stmt_s.excluded.content_hash,
                    "source_url": stmt_s.excluded.source_url,
                    "commit_sha": stmt_s.excluded.commit_sha,
                    "validated": stmt_s.excluded.validated,
                    "validation_status": stmt_s.excluded.validation_status,
                },
            )
            db.execute(stmt_s)
            db.commit()
            solutions_done += len(s_batch)
            elapsed_str = self._format_elapsed(time.time() - start_time)
            print(f"problems {problems_done}/{total_problems_to_ingest}, solutions {solutions_done}/{total_solutions_to_ingest}, elapsed {elapsed_str}")

        # If all solutions were skipped without entering the loop, print the updated progress line
        if not solutions_to_upsert and total_solutions_to_ingest > 0:
            elapsed_str = self._format_elapsed(time.time() - start_time)
            print(f"problems {problems_done}/{total_problems_to_ingest}, solutions {solutions_done}/{total_solutions_to_ingest}, elapsed {elapsed_str}")

        # Step 8: Print summary
        print("=" * 60)
        print("INGESTION SUMMARY")
        print("=" * 60)
        print(f"Problems: Created={stats.problems_created}, Updated={stats.problems_updated}, Unchanged={stats.problems_unchanged}")
        print("Solutions per Language:")
        for lang in ["python", "java", "cpp"]:
            print(
                f"  {lang.capitalize()}: Created={stats.solutions_created.get(lang, 0)}, "
                f"Updated={stats.solutions_updated.get(lang, 0)}, "
                f"Unchanged={stats.solutions_unchanged.get(lang, 0)}"
            )
        print(f"Skipped Files: {sum(stats.skipped_files.values())}")
        for reason, count in stats.skipped_files.items():
            print(f"  - {reason}: {count}")
        print("=" * 60)

        return stats
