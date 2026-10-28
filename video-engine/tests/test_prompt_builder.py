"""Prompt builder: placeholder resolution and style fallback."""

from __future__ import annotations

import pytest

from pebble.errors import ConfigError
from pebble.models import VideoRequest
from pebble.prompt_builder import build_prompt, build_prompt_template
from pebble.styles import get_style
from tests.conftest import load_sample


def test_all_template_placeholders_are_resolved(env_info):
    import re

    template = build_prompt_template()
    request = load_sample("two_sum.json")
    prompt = build_prompt(request, env_info)

    declared = set(re.findall(r"\{\{(\w+)\}\}", template))
    assert declared, "template should contain placeholders"
    assert declared == set(_values(request, env_info))

    # No placeholder of the *template's* naming survives substitution.
    leftovers = set(re.findall(r"\{\{(\w+)\}\}", prompt)) & declared
    assert leftovers == set()
    assert len(prompt) > len(template) // 2


def _values(request, env_info):
    from pebble.prompt_builder import _PLACEHOLDER_RE

    # Recompute the value map the same way build_prompt does.
    import pebble.prompt_builder as pb
    from pebble.styles import get_style as _gs

    style_name, style_text = _gs(request.preferences_or_default.explanation_style)
    return {
        "manim_version": env_info.manim_version,
        "kit_reference": pb._read(pb.KIT_REFERENCE_PATH, "visual kit reference"),
        "latex_block": pb.build_latex_block(env_info),
        "request_kind": request.request_kind,
        "input_block": pb.build_input_block(request),
        "programming_language": request.programming_language,
        "explanation_language": request.preferences_or_default.language,
        "style_name": style_name,
        "style_text": style_text,
        "solution_block": pb.build_solution_block(request),
        "problem_block": pb.build_problem_block(request),
        "diagram_recipes": pb._read(pb.DIAGRAM_RECIPES_PATH, "recipes"),
    }


def test_user_code_with_braces_is_inserted_untouched(env_info):
    request = VideoRequest.model_validate(
        {
            "question": {"id": 1, "slug": "two-sum", "title": "Two Sum"},
            "solution": {"code": "d = {'a': {{nested}} }", "validated": True},
        }
    )
    prompt = build_prompt(request, env_info)
    assert "d = {'a': {{nested}} }" in prompt

    # The inserted braces were not re-scanned: only the template's own keys resolve.
    import re

    declared = set(re.findall(r"\{\{(\w+)\}\}", build_prompt_template()))
    assert (set(re.findall(r"\{\{(\w+)\}\}", prompt)) & declared) == set()


def test_unknown_style_falls_back_to_beginner_friendly(env_info, caplog):
    request = VideoRequest.model_validate(
        {"preferences": {"explanation_style": "super_speedy"}}
    )
    name, text = get_style("super_speedy")
    assert name == "beginner_friendly"
    assert text.startswith("Assume the viewer is new to the topic.")

    prompt = build_prompt(request, env_info)
    assert "EXPLANATION STYLE: beginner_friendly" in prompt
    assert "Assume the viewer is new to the topic." in prompt


def test_latex_block_switches_with_env(env_info, latex_env_info):
    request = load_sample("two_sum.json")
    no_latex = build_prompt(request, env_info)
    with_latex = build_prompt(request, latex_env_info)
    assert "LaTeX is NOT installed." in no_latex
    assert "Never use MathTex" in no_latex
    assert "LaTeX is available." in with_latex
    assert "Never use MathTex" not in with_latex


def test_solution_block_variants(env_info, latex_env_info):
    from pebble.prompt_builder import build_solution_block

    assert build_solution_block(load_sample("two_sum.json")).startswith("A verified solution is provided")
    assert "NOT verified" in build_solution_block(load_sample("buggy_two_sum.json"))
    assert "No code was provided" in build_solution_block(load_sample("dijkstra_algorithm.json"))


def test_input_blocks(env_info):
    from pebble.prompt_builder import build_input_block

    two_sum = build_input_block(load_sample("two_sum.json"))
    assert "LEETCODE PROBLEM: #1 Two Sum (slug: two-sum)" in two_sum
    assert "SOLUTION:" in two_sum

    dijkstra = build_input_block(load_sample("dijkstra_algorithm.json"))
    assert "ALGORITHM / TOPIC TO EXPLAIN: Dijkstra's Algorithm" in dijkstra
    assert "(none provided)" in dijkstra


def test_diagram_recipes_are_included(env_info):
    prompt = build_prompt(load_sample("two_sum.json"), env_info)
    assert "CODE VISUALIZATION VOCABULARY" in prompt
    assert "CONSISTENCY REQUIREMENTS" in prompt


def test_kit_reference_is_included(env_info):
    prompt = build_prompt(load_sample("two_sum.json"), env_info)
    assert "VISUAL KIT" in prompt
    assert "ArrayViz(values, label=None, show_index=True)" in prompt
    assert "compare_panels(self, left_title, right_title" in prompt


def test_prompt_no_longer_talks_about_drawing_code(env_info):
    prompt = build_prompt(load_sample("two_sum.json"), env_info)
    assert "code_font" not in prompt
    assert "for code shown on screen" not in prompt
    assert "Code class" not in prompt.split("=== THE VISUAL KIT")[0]
    assert "NOTHING THAT LOOKS LIKE CODE" in prompt
    assert "font=\"" not in prompt


def test_unknown_placeholder_raises(monkeypatch, tmp_path, env_info):
    bad = tmp_path / "system_prompt.txt"
    bad.write_text("Hello {{mystery_key}}", encoding="utf-8")
    monkeypatch.setattr("pebble.prompt_builder.SYSTEM_PROMPT_PATH", bad)
    with pytest.raises(ConfigError) as excinfo:
        build_prompt(load_sample("two_sum.json"), env_info)
    assert "mystery_key" in str(excinfo.value)


def test_missing_template_raises(monkeypatch, tmp_path, env_info):
    monkeypatch.setattr(
        "pebble.prompt_builder.SYSTEM_PROMPT_PATH", tmp_path / "absent.txt"
    )
    with pytest.raises(ConfigError):
        build_prompt(load_sample("two_sum.json"), env_info)


def test_prompt_requires_finish_scene_and_drops_the_old_fade_ramp(env_info):
    from pebble.prompt_builder import build_fixer_prompt

    prompt = build_prompt(load_sample("two_sum.json"), env_info)
    assert "finish_scene(self)" in prompt
    assert "provided by the pipeline" in prompt
    assert "never write padding loops or while loops" in prompt
    # The old hand-rolled ending / word-count pacing instructions are gone.
    assert "Finish every scene with a short self.wait" not in prompt
    assert "about 2.2 words per second" not in prompt

    fixer = build_fixer_prompt("from manim import *\n", "Scene1_Intro", "boom", env_info)
    assert "finish_scene(self)" in fixer
    assert "finish_scene is provided by the pipeline" in fixer
    assert "FAILING SCENE: Scene1_Intro" in fixer
