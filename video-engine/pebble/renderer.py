"""Render each scene with Manim, repairing crashes *and* layout problems.

The generated script is rendered through a wrapper file, ``animation_render.py``,
which is the script text with the kit and helper imports prepended on the *same
first line*. Line numbers therefore stay identical to ``animation.py``, which
matters for the repair loop: the stderr tail we feed back points at the real
script.

Every scene also runs the kit's layout audit. In strict mode a broken frame
raises before the narration-length hold, so the render fails fast and the repair
loop gets the audit's findings. If a scene still has layout problems after the
repair budget, the scene is re-rendered in warn mode: a slightly imperfect frame
must not lose the whole video.
"""

from __future__ import annotations

import ast
import json
import logging
import os
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from pebble.config import Settings
from pebble.cost import CostTracker, log_llm_call
from pebble.environment import EnvInfo
from pebble.errors import RenderError
from pebble.llm import LLMClient
from pebble.models import GenerationResult, SceneMeta
from pebble.mux import probe_duration
from pebble.prompt_builder import build_fixer_prompt
from pebble.validators import validate_manim_code
from pebble.workspace import JobWorkspace

logger = logging.getLogger(__name__)

MANIM_TIMEOUT = 900
ERROR_TAIL_LINES = 60

TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
HELPERS_TEMPLATE = TEMPLATES_DIR / "pebble_helpers.py"
KIT_TEMPLATE = TEMPLATES_DIR / "pebble_kit.py"
HELPER_IMPORT = "from pebble_kit import *; from pebble_helpers import finish_scene; "
REQUIRED_FIRST_LINE = "from manim import *"
AUDIT_DIR = "audit"
STRICT_ENV = "PEBBLE_LAYOUT_STRICT"


@dataclass(frozen=True)
class SceneRender:
    index: int
    class_name: str
    video_path: Path
    duration: float
    repair_attempts: int = 0
    repairs_applied: int = 0
    layout_issues: list[str] = field(default_factory=list)
    used_fallback: bool = False


@dataclass(frozen=True)
class RenderAttempt:
    """One manim invocation plus what the layout audit said about it."""

    output: Path | None
    error: str
    issues: list[str] = field(default_factory=list)
    layout_failed: bool = False


def tail_lines(text: str, count: int = ERROR_TAIL_LINES) -> str:
    lines = [line for line in (text or "").strip().splitlines() if line.strip()]
    return "\n".join(lines[-count:])


def strip_markdown_fences(text: str) -> str:
    """Remove ``` fences that a model added around a whole file."""
    cleaned = (text or "").strip()
    if not cleaned.startswith("```"):
        return cleaned
    first_newline = cleaned.find("\n")
    if first_newline == -1:
        return cleaned.strip("`").strip()
    body = cleaned[first_newline + 1 :]
    if body.rstrip().endswith("```"):
        body = body.rstrip()[: -3]
    return body.strip() + "\n"


def scene_targets(result: GenerationResult) -> list[SceneMeta]:
    """Scene metadata in the order the scenes must be rendered."""
    return list(result.meta.scenes)


def install_runtime(workspace: JobWorkspace) -> None:
    """Copy the kit and the helper module next to the script (found via cwd)."""
    for template, destination in (
        (KIT_TEMPLATE, workspace.kit_path),
        (HELPERS_TEMPLATE, workspace.helpers_path),
    ):
        if not template.exists():
            raise RenderError(f"runtime template is missing: {template}")
        shutil.copyfile(template, destination)


def build_render_script(workspace: JobWorkspace) -> Path:
    """Write animation_render.py: kit + helper import on the script's first line."""
    script = workspace.animation_path.read_text(encoding="utf-8")
    first_line = script.splitlines()[0].strip() if script.strip() else ""
    if first_line != REQUIRED_FIRST_LINE:
        raise RenderError(
            "animation.py must start with 'from manim import *' "
            f"(found {first_line[:60]!r}); cannot attach the visual kit"
        )
    workspace.animation_render_path.write_text(HELPER_IMPORT + script, encoding="utf-8")
    return workspace.animation_render_path


MAX_CAPTION = 70


def build_fallback_script(script: str, class_name: str, title: str) -> str:
    """Replace one scene class with a kit-only title card.

    Used when a scene cannot be rendered even after the repair budget: keeping
    the job alive with a plain title card beats losing the whole video. Every
    other class, and the class name itself, is preserved.
    """
    try:
        tree = ast.parse(script)
    except SyntaxError:
        return script

    target = next(
        (
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.ClassDef) and node.name == class_name
        ),
        None,
    )
    if target is None or target.end_lineno is None:
        return script

    heading = " ".join((title or class_name).split()) or class_name
    caption = heading[:MAX_CAPTION].rstrip()
    replacement = [
        f"class {class_name}(Scene):",
        "    def construct(self):",
        f"        show_title(self, {heading!r})",
        f"        set_caption(self, {caption!r})",
        "        finish_scene(self)",
    ]
    lines = script.splitlines()
    new_lines = lines[: target.lineno - 1] + replacement + lines[target.end_lineno :]
    return "\n".join(new_lines) + "\n"


def read_audit(workspace: JobWorkspace, class_name: str) -> list[str]:
    """Layout issues the kit wrote while finishing this scene (empty if none)."""
    path = workspace.root / AUDIT_DIR / f"{class_name}.json"
    if not path.exists():
        return []
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return []
    issues = payload.get("issues") or []
    return [str(issue) for issue in issues]


class SceneRenderer:
    """Owns the current animation.py, the repair loop and the layout audit."""

    def __init__(
        self,
        workspace: JobWorkspace,
        settings: Settings,
        env_info: EnvInfo,
        expected_names: list[str],
        client: LLMClient | None = None,
        cost: CostTracker | None = None,
    ) -> None:
        self.workspace = workspace
        self.settings = settings
        self.env_info = env_info
        self.expected_names = list(expected_names)
        self._client = client
        self.cost = cost

    @property
    def client(self) -> LLMClient:
        if self._client is None:
            self._client = LLMClient(self.settings)
        return self._client

    # -- manim ---------------------------------------------------------
    def _strict(self) -> bool:
        """Layout audit mode: warn (default) logs, strict fails the scene."""
        return getattr(self.settings, "audit_mode", "warn") == "strict"

    def _run_manim(self, class_name: str, strict: bool | None = None) -> RenderAttempt:
        media_dir = self.workspace.media_dir / class_name
        media_dir.mkdir(parents=True, exist_ok=True)
        for stale in media_dir.rglob(f"{class_name}.mp4"):
            if "partial_movie_files" not in stale.parts:
                stale.unlink(missing_ok=True)

        quality = f"-q{self.settings.render_quality}"
        cmd = [
            sys.executable,
            "-m",
            "manim",
            "render",
            quality,
            "--disable_caching",
            "--media_dir",
            str(media_dir),
            "-o",
            class_name,
            str(self.workspace.animation_render_path),
            class_name,
        ]
        if strict is None:
            strict = self._strict()
        env = dict(os.environ)
        env[STRICT_ENV] = "1" if strict else "0"

        started = time.monotonic()
        try:
            completed = subprocess.run(
                cmd,
                cwd=str(self.workspace.root),
                capture_output=True,
                text=True,
                timeout=MANIM_TIMEOUT,
                env=env,
            )
            stdout, stderr, code = completed.stdout, completed.stderr, completed.returncode
        except subprocess.TimeoutExpired:
            error = f"manim timed out after {MANIM_TIMEOUT}s rendering {class_name}"
            return RenderAttempt(None, error, [], False)
        except OSError as exc:
            return RenderAttempt(None, f"manim could not start: {exc}", [], False)

        elapsed = time.monotonic() - started
        self._write_render_log(class_name, cmd, stdout, stderr, code, elapsed)
        issues = read_audit(self.workspace, class_name)
        output = self._find_output(media_dir, class_name)

        if code == 0 and output is not None:
            logger.info(
                "[render] %s ok  %.1fs%s",
                class_name,
                elapsed,
                f"  ({len(issues)} layout issue(s))" if issues else "",
            )
            return RenderAttempt(output, "", issues, False)

        error = tail_lines(stderr) or tail_lines(stdout) or f"manim exited with code {code}"
        layout_failed = bool(issues) and (
            "PebbleLayoutError" in (stderr or "") or "layout audit" in (stderr or "")
        )
        logger.warning(
            "[render] %s %s (exit %s)  %.1fs",
            class_name,
            "failed the layout audit" if layout_failed else "failed",
            code,
            elapsed,
        )
        return RenderAttempt(None, error, issues, layout_failed)

    def _write_render_log(
        self,
        class_name: str,
        cmd: list[str],
        stdout: str,
        stderr: str,
        code: int,
        elapsed: float,
    ) -> None:
        log_path = self.workspace.render_logs_dir / f"{class_name}.log"
        body = [
            f"$ {' '.join(cmd)}",
            f"exit code: {code}   elapsed: {elapsed:.1f}s",
            "",
            "--- stdout ---",
            stdout or "",
            "--- stderr ---",
            stderr or "",
        ]
        try:
            log_path.write_text("\n".join(body), encoding="utf-8")
        except OSError:  # pragma: no cover - logging must never break a render
            logger.debug("could not write render log %s", log_path)

    @staticmethod
    def _find_output(media_dir: Path, class_name: str) -> Path | None:
        if not media_dir.exists():
            return None
        matches = list(media_dir.rglob(f"{class_name}.mp4"))
        if not matches:
            return None
        final = [p for p in matches if "partial_movie_files" not in p.parts]
        candidates = final or matches
        return sorted(candidates, key=lambda path: len(path.parts))[0]

    # -- repair --------------------------------------------------------
    def _repair_problems(self, attempt: RenderAttempt) -> str:
        if attempt.layout_failed:
            lines = "\n".join(f"- {issue}" for issue in attempt.issues[:8])
            return (
                "The scene rendered but the automatic layout audit rejected the "
                "finished frame. Fix the layout so nothing overlaps and everything "
                "stays inside the frame. Use the kit's own helpers and structures "
                "instead of hand-placed text wherever possible.\n"
                f"LAYOUT PROBLEMS:\n{lines}"
            )
        return attempt.error

    def _try_repair(
        self, class_name: str, problems: str, expected: list[str]
    ) -> str | None:
        """Ask the LLM for a fix. Returns the accepted code, or None if rejected."""
        script = self.workspace.animation_path.read_text(encoding="utf-8")
        prompt = build_fixer_prompt(script, class_name, problems, self.env_info)
        response = self.client.call_llm(prompt)

        if self.cost is not None:
            self.cost.record_llm(
                "repair",
                self.settings.azure_deployment or "unknown",
                response.usage,
                response.seconds,
            )
            log_llm_call(logger, "repair", None, response, self.cost)

        candidate = strip_markdown_fences(response.text)

        problems_found = validate_manim_code(
            candidate, expected, self.env_info.latex_available
        )
        if problems_found:
            logger.warning(
                "repair for %s rejected (%d problem(s)): %s",
                class_name,
                len(problems_found),
                "; ".join(problems_found[:3]),
            )
            return None
        return candidate

    def _backup(self, attempt: int) -> Path:
        path = self.workspace.root / f"animation.attempt_{attempt}.py"
        shutil.copyfile(self.workspace.animation_path, path)
        return path

    # -- public --------------------------------------------------------
    def _use_fallback(self, scene: SceneMeta) -> None:
        """Swap the failing scene for a kit-only title card in animation.py."""
        script = self.workspace.animation_path.read_text(encoding="utf-8")
        fallback = build_fallback_script(script, scene.class_name, scene.title)
        if fallback == script:  # pragma: no cover - defensive
            logger.warning("could not build a fallback for %s", scene.class_name)
            return
        self.workspace.animation_path.write_text(fallback, encoding="utf-8")
        build_render_script(self.workspace)

    def render_scene(self, scene: SceneMeta, index: int) -> SceneRender:
        expected = self.expected_names
        logger.info("[render %d/%d] %s", index, len(expected), scene.class_name)
        attempt = self._run_manim(scene.class_name)
        attempts = 0
        applied = 0

        while attempt.output is None and attempts < self.settings.max_render_retries:
            attempts += 1
            logger.info(
                "[render %d/%d] %s repair attempt %d/%d",
                index,
                len(expected),
                scene.class_name,
                attempts,
                self.settings.max_render_retries,
            )
            candidate = self._try_repair(
                scene.class_name, self._repair_problems(attempt), expected
            )
            if candidate is None:
                continue

            self._backup(attempts)
            self.workspace.animation_path.write_text(candidate, encoding="utf-8")
            build_render_script(self.workspace)
            applied += 1
            # Only the failing scene is re-rendered; finished scenes are kept.
            attempt = self._run_manim(scene.class_name)

        used_fallback = False

        if attempt.output is None and attempt.layout_failed:
            # Layout-only failure: keep the video rather than losing the job.
            logger.warning(
                "[render] %s still has layout problems after %d repair(s); "
                "re-rendering in warn mode",
                scene.class_name,
                attempts,
            )
            attempt = self._run_manim(scene.class_name, strict=False)

        if attempt.output is None:
            # Fail-safe: swap in a kit-only title card and render that instead.
            first_error = attempt.error
            logger.warning(
                "[render] %s failed after %d repair attempt(s); using a fallback "
                "scene for it",
                scene.class_name,
                attempts,
            )
            self._use_fallback(scene)
            attempt = self._run_manim(scene.class_name)
            used_fallback = attempt.output is not None

        if attempt.output is None:
            raise RenderError(
                f"scene {scene.class_name} failed to render even as a fallback scene",
                scene_class=scene.class_name,
                error_tail=attempt.error or first_error,
            )

        if attempt.issues:
            logger.warning(
                "[layout] %s kept %d issue(s): %s",
                scene.class_name,
                len(attempt.issues),
                "; ".join(attempt.issues[:3]),
            )

        destination = self.workspace.scenes_dir / f"{index:02d}_{scene.class_name}.mp4"
        shutil.copyfile(attempt.output, destination)
        duration = probe_duration(destination)
        return SceneRender(
            index=index,
            class_name=scene.class_name,
            video_path=destination,
            duration=duration,
            repair_attempts=attempts,
            repairs_applied=applied,
            layout_issues=list(attempt.issues),
            used_fallback=used_fallback,
        )


def render_scenes(
    result: GenerationResult,
    workspace: JobWorkspace,
    settings: Settings,
    env_info: EnvInfo,
    client: LLMClient | None = None,
    on_scene: Callable[[SceneRender], None] | None = None,
    cost: CostTracker | None = None,
) -> list[SceneRender]:
    """Render every scene in order; raises RenderError instead of skipping one."""
    scenes = scene_targets(result)
    install_runtime(workspace)
    build_render_script(workspace)

    renderer = SceneRenderer(
        workspace, settings, env_info, [meta.class_name for meta in scenes], client, cost
    )

    rendered: list[SceneRender] = []
    for index, scene in enumerate(scenes, start=1):
        scene_render = renderer.render_scene(scene, index)
        rendered.append(scene_render)
        if on_scene is not None:
            on_scene(scene_render)
    return rendered
