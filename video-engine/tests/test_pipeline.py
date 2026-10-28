"""End-to-end pipeline with a mocked LLM, mocked TTS, real manim and ffmpeg."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from uuid import uuid4

import pytest

from pebble.config import Settings
from pebble.environment import EnvInfo
from pebble.models import VideoRequest
from pebble.mux import HOLD, ffprobe_info
from pebble.parsing import parse_response
from pebble.pipeline import run_pipeline
from tests.conftest import TINY_MANIM, load_sample, make_response, make_sine_wav

ENV = EnvInfo(
    manim_version="0.22.0",
    latex_available=False,
    ffmpeg_available=True,
    ffprobe_available=True,
    code_font="Menlo",
)


def _fake_generate(request: VideoRequest, workspace, settings, env_info, cost=None):
    result = parse_response(make_response(manim_code=TINY_MANIM))
    result.style_name = "beginner_friendly"
    workspace.animation_path.write_text(result.manim_code, encoding="utf-8")
    return result


def _fake_synth(text: str, voice: str, settings) -> bytes:
    tmp = Path(tempfile.mkdtemp()) / "tone.wav"
    make_sine_wav(tmp, 1.0)
    return tmp.read_bytes()


def test_pipeline_produces_a_finished_video(monkeypatch, tmp_path):
    monkeypatch.setattr("pebble.pipeline.generate", _fake_generate)
    monkeypatch.setattr("pebble.tts._synth_audio", _fake_synth)
    cost_log = tmp_path / "cost_log.jsonl"
    monkeypatch.setattr("pebble.pipeline.COST_LOG_PATH", cost_log)

    statuses: list[str] = []
    job_id = f"test_pipe_{uuid4().hex[:8]}"
    result = run_pipeline(
        load_sample("two_sum.json"),
        job_id=job_id,
        on_status=statuses.append,
        settings=Settings(render_quality="l", max_render_retries=0),
        env_info=ENV,
    )

    assert statuses == ["generating", "narrating", "rendering", "assembling", "done"]
    assert result.final_video.exists()
    info = ffprobe_info(result.final_video)
    assert info.has_video and info.has_audio
    assert info.video_codec == "h264"
    assert info.audio_codec == "aac"
    assert result.scene_count == 2
    assert abs(result.duration_seconds - sum(s.duration for s in result.rendered)) < 1.0

    workspace = result.workspace

    # Narration first: the targets file drives finish_scene at render time.
    targets = json.loads((workspace / "pebble_targets.json").read_text(encoding="utf-8"))
    assert set(targets) == {"Scene1_Intro", "Scene2_Trace"}
    for voice in result.audio:
        assert abs(targets[voice.class_name] - (voice.duration + HOLD)) < 0.01

    muxed = sorted((workspace / "muxed").glob("*.mp4"))
    assert len(muxed) == 2
    for path, voice in zip(muxed, result.audio):
        duration = ffprobe_info(path).duration
        assert abs(duration - (voice.duration + HOLD)) < 0.5, (path, duration)

    result_doc = json.loads((workspace / "result.json").read_text(encoding="utf-8"))
    assert result_doc["job_id"] == job_id
    assert Path(result_doc["final_video"]).is_absolute()
    assert result_doc["final_video"] == str(result.final_video.resolve())
    assert result_doc["scene_count"] == 2
    assert result_doc["duration_seconds"] > 0
    assert set(result_doc["solution"]) == {"code", "programming_language"}
    assert result_doc["solution"]["code"].strip().startswith("class Solution")

    metadata = json.loads((workspace / "metadata.json").read_text(encoding="utf-8"))
    for field in (
        "problem_summary",
        "example",
        "validation",
        "solution_source",
        "complexity",
        "scenes",
        "style",
        "explanation_language",
        "request_fingerprint",
        "manim_version",
        "render_quality",
        "timings",
        "repair_attempts",
        "pacing",
        "cost",
    ):
        assert field in metadata, field

    assert metadata["style"] == "beginner_friendly"
    assert metadata["explanation_language"] == "English"
    assert metadata["render_quality"] == "l"
    assert len(metadata["scenes"]) == 2
    first = metadata["scenes"][0]
    assert set(first) >= {
        "id",
        "title",
        "narration",
        "rendered_duration",
        "audio_duration",
        "target_seconds",
    }
    assert first["rendered_duration"] > 0
    assert first["audio_duration"] > 0
    assert metadata["timings"]["generate"] >= 0

    cost = metadata["cost"]
    assert cost["tts_characters"] > 0
    assert cost["total_usd"] >= 0
    assert len(cost["rows"]) == 4

    lines = cost_log.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    entry = json.loads(lines[0])
    assert entry["job_id"] == job_id
    assert entry["kind"] == "leetcode_problem"
    assert entry["video_seconds"] > 0
    assert entry["total_usd"] == cost["total_usd"]

    assert (workspace / "pipeline.log").read_text(encoding="utf-8").strip()
    assert (workspace / "pebble_helpers.py").exists()
    render_script = (workspace / "animation_render.py").read_text(encoding="utf-8")
    assert render_script.startswith(
        "from pebble_kit import *; from pebble_helpers import finish_scene; "
        "from manim import *"
    )
    assert (result.workspace / "pebble_kit.py").exists()
    assert render_script.splitlines()[1:] == (workspace / "animation.py").read_text(
        encoding="utf-8"
    ).splitlines()[1:]


# ---------------------------------------------------------------------------
# render fail-safe budget
# ---------------------------------------------------------------------------


def _scene_render(index: int, name: str, fallback: bool = False):
    from pebble.renderer import SceneRender

    return SceneRender(
        index=index,
        class_name=name,
        video_path=Path(f"/tmp/{name}.mp4"),
        duration=1.0,
        used_fallback=fallback,
    )


def test_one_fallback_scene_keeps_the_job_alive():
    from pebble.pipeline import check_fallback_budget

    rendered = [
        _scene_render(1, "Scene1_Intro"),
        _scene_render(2, "Scene2_Trace", fallback=True),
        _scene_render(3, "Scene3_Result"),
    ]
    assert check_fallback_budget(rendered) == ["Scene2_Trace"]


def test_too_many_fallback_scenes_fail_the_job():
    from pebble.errors import PebbleError
    from pebble.pipeline import check_fallback_budget

    rendered = [
        _scene_render(1, "Scene1_Intro", fallback=True),
        _scene_render(2, "Scene2_Trace", fallback=True),
        _scene_render(3, "Scene3_Result"),
    ]

    with pytest.raises(PebbleError) as excinfo:
        check_fallback_budget(rendered)
    assert "too many scenes failed to render" in str(excinfo.value)
