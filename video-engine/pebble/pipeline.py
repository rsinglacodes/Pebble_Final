"""End-to-end pipeline: generate -> narrate -> render -> mux -> stitch.

Narration comes *before* rendering on purpose: speech is measured with ffprobe,
the durations are written to ``pebble_targets.json``, and the render helper
``finish_scene`` holds each finished picture until its narration ends. That is
what stops a scene from freezing on a blank frame while the voice keeps talking.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from pebble.config import Settings, load_settings
from pebble.cost import COST_LOG_PATH, CostTracker, append_cost_log
from pebble.environment import EnvInfo, detect
from pebble.errors import PebbleError
from pebble.generation import generate
from pebble.logging_setup import setup_logging, stage_banner
from pebble.models import Complexity, GenerationResult, Validation, VideoRequest
from pebble.mux import HOLD, mux_scene, probe_duration, stitch
from pebble.renderer import SceneRender, render_scenes
from pebble.styles import get_style
from pebble.tts import SceneAudio, narrate_scenes
from pebble.workspace import JobWorkspace

logger = logging.getLogger(__name__)

StageCallback = Callable[[str], None]
STAGES = ("generating", "narrating", "rendering", "assembling", "done")


@dataclass
class PipelineResult:
    job_id: str
    workspace: Path
    final_video: Path
    duration_seconds: float
    scene_count: int
    solution_code: str
    programming_language: str
    solution_source: str
    validation: Validation
    complexity: Complexity
    timings: dict[str, float] = field(default_factory=dict)
    repair_attempts: int = 0
    repairs_applied: int = 0
    rendered: list[SceneRender] = field(default_factory=list)
    audio: list[SceneAudio] = field(default_factory=list)
    cost: dict[str, Any] = field(default_factory=dict)
    cost_table: str = ""


def write_targets(workspace: JobWorkspace, audio: list[SceneAudio]) -> Path:
    """Per-scene on-screen target: narration length plus the mux hold."""
    targets = {item.class_name: round(item.duration + HOLD, 3) for item in audio}
    workspace.targets_path.write_text(
        json.dumps(targets, indent=2) + "\n", encoding="utf-8"
    )
    return workspace.targets_path


def check_fallback_budget(rendered: list[SceneRender]) -> list[str]:
    """Names of the scenes that needed a fallback card.

    A couple of fallbacks keep the job alive; losing more than half of the
    scenes means the generated script is not really explaining anything, so
    that is a hard failure.
    """
    fallbacks = [item.class_name for item in rendered if item.used_fallback]
    if fallbacks and len(fallbacks) * 2 > len(rendered):
        raise PebbleError(
            f"too many scenes failed to render: {len(fallbacks)} of {len(rendered)} "
            "scenes used a fallback title card"
        )
    return fallbacks


def _notify(callback: StageCallback | None, stage: str) -> None:
    if callback is not None:
        callback(stage)


def _human_size(num_bytes: int) -> str:
    size = float(num_bytes)
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024 or unit == "GB":
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} GB"


def _scene_entries(
    result: GenerationResult, rendered: list[SceneRender], audio: list[SceneAudio]
) -> list[dict[str, Any]]:
    by_index = {item.index: item for item in rendered}
    audio_by_index = {item.index: item for item in audio}
    entries: list[dict[str, Any]] = []
    for position, scene in enumerate(result.scenes, start=1):
        render = by_index.get(position)
        voice = audio_by_index.get(position)
        entries.append(
            {
                "id": scene.scene_id or position,
                "class_name": scene.class_name,
                "title": scene.title,
                "narration": scene.narration,
                "rendered_duration": round(render.duration, 3) if render else None,
                "audio_duration": round(voice.duration, 3) if voice else None,
                "target_seconds": (
                    round(voice.duration + HOLD, 3) if voice else None
                ),
            }
        )
    return entries


def run_pipeline(
    payload: dict | VideoRequest,
    job_id: str | None = None,
    on_status: StageCallback | None = None,
    settings: Settings | None = None,
    env_info: EnvInfo | None = None,
    cost: CostTracker | None = None,
    verbose: bool = False,
    quiet: bool = False,
) -> PipelineResult:
    """Run every stage and return the finished video description."""
    request = payload if isinstance(payload, VideoRequest) else VideoRequest.model_validate(payload)
    settings = settings or load_settings()
    env_info = env_info or detect()
    workspace = JobWorkspace(job_id)
    setup_logging(workspace=workspace, verbose=verbose, quiet=quiet)
    tracker = cost or CostTracker(settings)

    workspace.request_path.write_text(
        json.dumps(request.model_dump(), indent=2, ensure_ascii=False), encoding="utf-8"
    )

    style_name, _ = get_style(request.preferences_or_default.explanation_style)
    timings: dict[str, float] = {}
    stage = "generating"
    total_started = time.perf_counter()

    logger.info(
        "[job %s] %s / solution %s / style %s / %s / fingerprint %s",
        workspace.job_id,
        request.request_kind,
        request.solution_state,
        style_name,
        request.preferences_or_default.language,
        request.request_fingerprint()[:12],
    )

    try:
        stage_banner(1, len(STAGES), "generating")
        _notify(on_status, "generating")
        started = time.perf_counter()
        result: GenerationResult = generate(request, workspace, settings, env_info, cost=tracker)
        timings["generate"] = round(time.perf_counter() - started, 2)
        logger.info(
            "generating done in %.1fs: %d scene(s), solution_source %s",
            timings["generate"],
            len(result.scenes),
            result.meta.solution_source,
        )

        stage = "narrating"
        stage_banner(2, len(STAGES), "narrating")
        _notify(on_status, "narrating")
        started = time.perf_counter()
        audio = narrate_scenes(
            result,
            workspace,
            settings,
            request.preferences_or_default.language,
            cost=tracker,
        )
        timings["narrate"] = round(time.perf_counter() - started, 2)
        targets = write_targets(workspace, audio)
        logger.info(
            "narrating done in %.1fs: %d scene(s), %.1fs of narration, targets -> %s",
            timings["narrate"],
            len(audio),
            sum(item.duration for item in audio),
            targets.name,
        )

        stage = "rendering"
        stage_banner(3, len(STAGES), "rendering")
        _notify(on_status, "rendering")
        started = time.perf_counter()
        rendered = render_scenes(result, workspace, settings, env_info, cost=tracker)
        timings["render"] = round(time.perf_counter() - started, 2)
        logger.info(
            "rendering done in %.1fs: %d scene(s), %d repair(s) applied",
            timings["render"],
            len(rendered),
            sum(item.repairs_applied for item in rendered),
        )

        stage = "assembling"
        stage_banner(4, len(STAGES), "assembling")
        _notify(on_status, "assembling")
        started = time.perf_counter()
        if len(rendered) != len(audio):
            raise PebbleError(
                f"scene/audio count mismatch: {len(rendered)} video(s) vs {len(audio)} audio"
            )

        check_fallback_budget(rendered)

        muxed: list[Path] = []
        for render, voice in zip(rendered, audio):
            out = workspace.muxed_dir / f"{render.index:02d}_{render.class_name}.mp4"
            mux_scene(render.video_path, voice.audio_path, out)
            muxed.append(out)
            logger.info(
                "[mux %d/%d] %s video %.2fs + audio %.2fs -> %.2fs",
                render.index,
                len(rendered),
                render.class_name,
                render.duration,
                voice.duration,
                probe_duration(out),
            )
        timings["mux"] = round(time.perf_counter() - started, 2)

        started = time.perf_counter()
        stitch(muxed, workspace.final_video_path)
        timings["stitch"] = round(time.perf_counter() - started, 2)
        logger.info("stitch done in %.1fs: %s", timings["stitch"], workspace.final_video_path)

        duration = probe_duration(workspace.final_video_path)
        timings["total"] = round(time.perf_counter() - total_started, 2)

        repair_attempts = sum(item.repair_attempts for item in rendered)
        repairs_applied = sum(item.repairs_applied for item in rendered)
        fallback_scenes = [item.class_name for item in rendered if item.used_fallback]

        result_doc = {
            "job_id": workspace.job_id,
            "final_video": str(workspace.final_video_path.resolve()),
            "duration_seconds": round(duration, 2),
            "scene_count": len(rendered),
            "solution": {
                "code": result.solution_code,
                "programming_language": result.meta.programming_language
                or request.programming_language,
            },
        }
        workspace.result_path.write_text(
            json.dumps(result_doc, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        cost_doc = tracker.to_dict(duration)
        cost_table = tracker.format_table(duration)
        metadata = {
            "problem_summary": result.meta.problem_summary,
            "example": result.meta.example.model_dump(),
            "validation": result.meta.validation.model_dump(),
            "solution_source": result.meta.solution_source,
            "complexity": result.meta.complexity.model_dump(),
            "scenes": _scene_entries(result, rendered, audio),
            "style": style_name,
            "explanation_language": request.preferences_or_default.language,
            "request_fingerprint": request.request_fingerprint(),
            "manim_version": env_info.manim_version,
            "render_quality": settings.render_quality,
            "timings": timings,
            "repair_attempts": repair_attempts,
            "repairs_applied": repairs_applied,
            "fallback_scenes": fallback_scenes,
            "generation_warnings": list(result.generation_warnings),
            "pacing": {
                "hold_seconds": HOLD,
                "targets": json.loads(workspace.targets_path.read_text(encoding="utf-8")),
            },
            "cost": cost_doc,
        }
        workspace.metadata_path.write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        append_cost_log(
            COST_LOG_PATH,
            job_id=workspace.job_id,
            fingerprint=request.request_fingerprint(),
            kind=request.request_kind,
            style=style_name,
            video_seconds=duration,
            total_usd=tracker.total_usd,
        )

        stage_banner(5, len(STAGES), "done")
        _notify(on_status, "done")

        if fallback_scenes:
            logger.warning(
                "%d scene(s) used a fallback title card: %s",
                len(fallback_scenes),
                ", ".join(fallback_scenes),
            )

        size = workspace.final_video_path.stat().st_size
        logger.info(
            "video %s | %.1fs | %s | %d scenes | %s | validation performed=%s "
            "is_correct=%s | repairs %d",
            workspace.final_video_path,
            duration,
            _human_size(size),
            len(rendered),
            result.meta.solution_source,
            result.meta.validation.performed,
            result.meta.validation.is_correct,
            repairs_applied,
        )
        logger.info(
            "stage timings: "
            + "  ".join(f"{key} {value:.1f}s" for key, value in timings.items())
        )
        for line in cost_table.splitlines():
            logger.info(line)

        return PipelineResult(
            job_id=workspace.job_id,
            workspace=workspace.root,
            final_video=workspace.final_video_path,
            duration_seconds=duration,
            scene_count=len(rendered),
            solution_code=result.solution_code,
            programming_language=result.meta.programming_language
            or request.programming_language,
            solution_source=result.meta.solution_source,
            validation=result.meta.validation,
            complexity=result.meta.complexity,
            timings=timings,
            repair_attempts=repair_attempts,
            repairs_applied=repairs_applied,
            rendered=rendered,
            audio=audio,
            cost=cost_doc,
            cost_table=cost_table,
        )
    except Exception as exc:
        logger.error(
            "pipeline failed during %s: %s: %s", stage, type(exc).__name__, exc
        )
        logger.info("workspace kept for debugging: %s", workspace.root)
        raise
