"""finish_scene: real -ql renders proving scenes hold until the narration ends."""

from __future__ import annotations

import json
from uuid import uuid4

from pebble.config import Settings
from pebble.environment import EnvInfo
from pebble.models import GenerationMeta, GenerationResult
from pebble.renderer import render_scenes
from pebble.workspace import JobWorkspace

ENV = EnvInfo(
    manim_version="0.22.0",
    latex_available=False,
    ffmpeg_available=True,
    ffprobe_available=True,
    code_font="Menlo",
)

SCRIPT = '''from manim import *


class Scene1_Hold(Scene):
    def construct(self):
        nums = ArrayViz([1, 2, 3])
        self.play(nums.intro(), run_time={animation:.1f})
        finish_scene(self)
'''


def _result() -> GenerationResult:
    meta = GenerationMeta.model_validate(
        {
            "scenes": [
                {
                    "scene_id": 1,
                    "class_name": "Scene1_Hold",
                    "title": "Hold",
                    "narration": "n",
                }
            ]
        }
    )
    return GenerationResult(meta=meta)


def _render(animation: float, targets: dict[str, float] | None) -> float:
    workspace = JobWorkspace(f"test_hold_{uuid4().hex[:8]}")
    workspace.animation_path.write_text(SCRIPT.format(animation=animation), encoding="utf-8")
    if targets is not None:
        workspace.targets_path.write_text(json.dumps(targets), encoding="utf-8")

    rendered = render_scenes(
        _result(),
        workspace,
        Settings(render_quality="l", max_render_retries=0),
        ENV,
    )
    return rendered[0].duration


def test_short_animation_is_held_until_the_target():
    duration = _render(2.0, {"Scene1_Hold": 6.0})
    assert abs(duration - 6.0) < 0.3, duration


def test_long_animation_is_not_cut():
    duration = _render(2.0, {"Scene1_Hold": 1.0})
    # 2.0s of animation plus the 0.6s fade-out; nothing is trimmed.
    assert duration >= 2.5, duration


def test_missing_target_only_fades_out():
    duration = _render(0.5, None)
    assert 0.9 <= duration <= 2.0, duration
