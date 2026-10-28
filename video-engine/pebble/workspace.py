"""Per-job workspace directories under workspace/<job_id>/."""

from __future__ import annotations

import secrets
from pathlib import Path

SUBFOLDERS = (
    "llm",
    "scenes",
    "audio",
    "muxed",
    "media",
    "frames",
    "render_logs",
    "audit",
)

PROJECT_ROOT = Path(__file__).resolve().parent.parent
WORKSPACE_ROOT = PROJECT_ROOT / "workspace"


class JobWorkspace:
    """File layout for one generation job."""

    def __init__(self, job_id: str | None = None) -> None:
        self.job_id = job_id or f"job_{secrets.token_hex(4)}"
        self.root = WORKSPACE_ROOT / self.job_id
        for name in SUBFOLDERS:
            (self.root / name).mkdir(parents=True, exist_ok=True)

    @property
    def llm_dir(self) -> Path:
        return self.root / "llm"

    @property
    def scenes_dir(self) -> Path:
        return self.root / "scenes"

    @property
    def audio_dir(self) -> Path:
        return self.root / "audio"

    @property
    def muxed_dir(self) -> Path:
        return self.root / "muxed"

    @property
    def media_dir(self) -> Path:
        return self.root / "media"

    @property
    def animation_path(self) -> Path:
        return self.root / "animation.py"

    @property
    def animation_render_path(self) -> Path:
        """animation.py with the helper import prefixed on its first line."""
        return self.root / "animation_render.py"

    @property
    def helpers_path(self) -> Path:
        return self.root / "pebble_helpers.py"

    @property
    def kit_path(self) -> Path:
        return self.root / "pebble_kit.py"

    @property
    def audit_dir(self) -> Path:
        return self.root / "audit"

    @property
    def targets_path(self) -> Path:
        return self.root / "pebble_targets.json"

    @property
    def render_logs_dir(self) -> Path:
        return self.root / "render_logs"

    @property
    def generation_path(self) -> Path:
        return self.root / "generation.json"

    @property
    def request_path(self) -> Path:
        """The payload that produced this job (used to re-upload by hand)."""
        return self.root / "request.json"

    @property
    def frames_dir(self) -> Path:
        return self.root / "frames"

    @property
    def final_video_path(self) -> Path:
        return self.root / "final.mp4"

    @property
    def contact_sheet_path(self) -> Path:
        return self.root / "contact_sheet.png"

    @property
    def result_path(self) -> Path:
        return self.root / "result.json"

    @property
    def metadata_path(self) -> Path:
        return self.root / "metadata.json"

    @property
    def pipeline_log_path(self) -> Path:
        return self.root / "pipeline.log"

    @property
    def prompt_path(self) -> Path:
        return self.root / "prompt.txt"

    @property
    def response_path(self) -> Path:
        return self.root / "response.txt"

    def attempt_paths(self, attempt: int) -> tuple[Path, Path]:
        base = self.llm_dir / f"attempt_{attempt}"
        return base.with_name(base.name + "_prompt.txt"), base.with_name(
            base.name + "_response.txt"
        )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"JobWorkspace(job_id={self.job_id!r})"
