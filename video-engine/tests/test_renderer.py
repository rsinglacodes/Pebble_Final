"""Renderer: real manim rendering plus the LLM repair loop."""

from __future__ import annotations

import pytest

from pebble.config import Settings
from pebble.environment import EnvInfo
from pebble.errors import RenderError
from pebble.models import GenerationMeta, GenerationResult
from pebble.renderer import (
    RenderAttempt,
    SceneRenderer,
    render_scenes,
    strip_markdown_fences,
)
from pebble.workspace import JobWorkspace
from tests.conftest import llm_reply

ENV = EnvInfo(
    manim_version="0.22.0",
    latex_available=False,
    ffmpeg_available=True,
    ffprobe_available=True,
    code_font="Menlo",
)

TINY_SCENE = '''from manim import *


class Scene1_Tiny(Scene):
    def construct(self):
        nums = ArrayViz([1, 2, 3])
        self.play(nums.intro(), run_time=0.5)
        self.wait(0.2)
        finish_scene(self)
'''

BROKEN_SCENE = '''from manim import *


class Scene1_Tiny(Scene):
    def construct(self):
        nums = ArrayViz([1, 2, 3])
        self.play(nums.intro(), run_time=0.5)
        missing_helper_that_does_not_exist()
        finish_scene(self)
'''

# Renders fine, but two captions sit on top of each other: only the audit fails.
OVERLAP_SCENE = '''from manim import *


class Scene1_Tiny(Scene):
    def construct(self):
        nums = ArrayViz([1, 2, 3])
        self.play(nums.intro(), run_time=0.4)
        first = Text("two numbers", font_size=30).move_to(ORIGIN)
        second = Text("add to target", font_size=30).move_to(ORIGIN + RIGHT * 0.2)
        self.play(FadeIn(first), FadeIn(second), run_time=0.4)
        finish_scene(self)
'''


class FakeClient:
    def __init__(self, replies: list[str]) -> None:
        self.replies = list(replies)
        self.prompts: list[str] = []

    def call_llm(self, prompt: str):
        self.prompts.append(prompt)
        if not self.replies:
            raise AssertionError("fixer called more times than expected")
        return llm_reply(self.replies.pop(0))


def _job() -> JobWorkspace:
    from uuid import uuid4

    return JobWorkspace(f"test_render_{uuid4().hex[:8]}")


def _result(class_names: list[str]) -> GenerationResult:
    meta = GenerationMeta.model_validate(
        {
            "scenes": [
                {
                    "scene_id": index,
                    "class_name": name,
                    "title": "t",
                    "narration": "n",
                }
                for index, name in enumerate(class_names, start=1)
            ]
        }
    )
    return GenerationResult(meta=meta)


def _settings(retries: int = 0, audit_mode: str = "strict") -> Settings:
    return Settings(render_quality="l", max_render_retries=retries, audit_mode=audit_mode)


def test_renders_a_tiny_scene():
    workspace = _job()
    workspace.animation_path.write_text(TINY_SCENE, encoding="utf-8")

    rendered = render_scenes(
        _result(["Scene1_Tiny"]), workspace, _settings(), ENV, client=FakeClient([])
    )

    assert len(rendered) == 1
    scene = rendered[0]
    assert scene.class_name == "Scene1_Tiny"
    assert scene.video_path.name == "01_Scene1_Tiny.mp4"
    assert scene.video_path.exists()
    assert scene.duration > 0
    assert scene.repair_attempts == 0


def test_repair_loop_fixes_a_failing_scene():
    workspace = _job()
    workspace.animation_path.write_text(BROKEN_SCENE, encoding="utf-8")
    client = FakeClient([TINY_SCENE])

    rendered = render_scenes(
        _result(["Scene1_Tiny"]), workspace, _settings(retries=2), ENV, client=client
    )

    assert len(rendered) == 1
    assert rendered[0].repairs_applied == 1
    assert rendered[0].repair_attempts == 1
    assert rendered[0].video_path.exists()

    backup = workspace.root / "animation.attempt_1.py"
    assert backup.exists()
    assert "missing_helper_that_does_not_exist" in backup.read_text(encoding="utf-8")
    assert "missing_helper_that_does_not_exist" not in workspace.animation_path.read_text(
        encoding="utf-8"
    )

    prompt = client.prompts[0]
    assert "FAILING SCENE: Scene1_Tiny" in prompt
    assert "ERROR (tail):" in prompt
    assert "class Scene1_Tiny(Scene)" in prompt


def test_repair_that_renames_a_class_is_rejected_and_the_fallback_renders():
    workspace = _job()
    workspace.animation_path.write_text(BROKEN_SCENE, encoding="utf-8")
    renamed = TINY_SCENE.replace("Scene1_Tiny", "Scene1_TinyFixed")
    client = FakeClient([renamed])

    rendered = render_scenes(
        _result(["Scene1_Tiny"]), workspace, _settings(retries=1), ENV, client=client
    )

    # The broken repair is rejected (no backup of it), so the fail-safe title
    # card replaces the scene and the job still produces a video.
    assert not (workspace.root / "animation.attempt_1.py").exists()
    assert rendered[0].used_fallback is True
    assert rendered[0].video_path.exists()
    script = workspace.animation_path.read_text(encoding="utf-8")
    assert "missing_helper_that_does_not_exist" not in script
    assert "show_title" in script


def test_fallback_scene_that_also_fails_still_raises(monkeypatch):
    workspace = _job()
    workspace.animation_path.write_text(BROKEN_SCENE, encoding="utf-8")
    client = FakeClient([])

    def always_fails(self, class_name, strict=None):
        return RenderAttempt(None, "boom", [], False)

    monkeypatch.setattr(SceneRenderer, "_run_manim", always_fails)
    with pytest.raises(RenderError) as excinfo:
        render_scenes(
            _result(["Scene1_Tiny"]), workspace, _settings(retries=0), ENV, client=client
        )
    assert "fallback" in str(excinfo.value)


def test_warn_mode_keeps_a_layout_issue_without_failing():
    workspace = _job()
    workspace.animation_path.write_text(OVERLAP_SCENE, encoding="utf-8")

    rendered = render_scenes(
        _result(["Scene1_Tiny"]),
        workspace,
        _settings(retries=1, audit_mode="warn"),
        ENV,
        client=FakeClient([]),
    )

    assert rendered[0].video_path.exists()
    assert rendered[0].repair_attempts == 0
    assert rendered[0].layout_issues, "warn mode still records the findings"


def test_layout_only_failure_falls_back_to_warn_mode():
    workspace = _job()
    workspace.animation_path.write_text(OVERLAP_SCENE, encoding="utf-8")
    # The fixer keeps returning the same overlapping scene: the layout problem
    # survives the repair budget. The video must still be kept.
    client = FakeClient([OVERLAP_SCENE])

    rendered = render_scenes(
        _result(["Scene1_Tiny"]), workspace, _settings(retries=1), ENV, client=client
    )

    assert rendered[0].video_path.exists()
    assert rendered[0].duration > 0
    assert rendered[0].repair_attempts == 1
    assert rendered[0].layout_issues, "the audit findings should be recorded"


def test_audit_fix_is_accepted_and_layout_issue_disappears():
    workspace = _job()
    workspace.animation_path.write_text(OVERLAP_SCENE, encoding="utf-8")
    client = FakeClient([TINY_SCENE])

    rendered = render_scenes(
        _result(["Scene1_Tiny"]), workspace, _settings(retries=2), ENV, client=client
    )

    assert rendered[0].repairs_applied == 1
    assert rendered[0].layout_issues == []
    assert "LAYOUT PROBLEMS" in client.prompts[0]
    assert "overlaps" in client.prompts[0]
    audit = workspace.root / "audit" / "Scene1_Tiny.json"
    assert audit.exists()


def test_layout_audit_json_is_written_even_when_clean():
    workspace = _job()
    workspace.animation_path.write_text(TINY_SCENE, encoding="utf-8")
    render_scenes(
        _result(["Scene1_Tiny"]), workspace, _settings(), ENV, client=FakeClient([])
    )
    audit = workspace.root / "audit" / "Scene1_Tiny.json"
    assert audit.exists()
    assert audit.read_text(encoding="utf-8").find('"issues": []') != -1


def test_strip_markdown_fences():
    assert strip_markdown_fences("```python\nfrom manim import *\n```").strip() == (
        "from manim import *"
    )
    assert strip_markdown_fences("from manim import *").strip() == "from manim import *"
