"""Validators: structural, safety and consistency checks."""

from __future__ import annotations

import json

import pytest

from pebble.models import VideoRequest
from pebble.parsing import parse_response
import ast

from pebble.validators import _check_result_scene, validate_generation
from tests.conftest import VALID_MANIM, VALID_META, make_response


def _problems(response: str, request: VideoRequest, env_info) -> list[str]:
    return validate_generation(parse_response(response), request, env_info)


def _meta(**changes):
    meta = json.loads(json.dumps(VALID_META))
    meta.update(changes)
    return meta


def test_valid_two_scene_response_is_accepted(env_info, verified_request):
    assert _problems(make_response(), verified_request, env_info) == []


def test_wrong_numbering_is_rejected(env_info, verified_request):
    bad = VALID_MANIM.replace("class Scene2_Trace", "class Scene3_Trace").replace(
        "Scene2_Trace", "Scene9_Trace"
    )
    response = make_response(manim_code=bad)
    problems = _problems(response, verified_request, env_info)
    assert any("numbering" in p for p in problems)


def test_scene_count_mismatch_is_rejected(env_info, verified_request):
    meta = _meta(scenes=VALID_META["scenes"][:1])
    problems = _problems(make_response(meta=meta), verified_request, env_info)
    assert any("scene count mismatch" in p for p in problems)


def test_class_name_mismatch_is_rejected(env_info, verified_request):
    meta = _meta(
        scenes=[
            {"scene_id": 1, "class_name": "Scene1_Wrong", "title": "a", "narration": "n"},
            {"scene_id": 2, "class_name": "Scene2_Trace", "title": "b", "narration": "n"},
        ]
    )
    problems = _problems(make_response(meta=meta), verified_request, env_info)
    assert any("does not match" in p for p in problems)


def test_empty_narration_is_rejected(env_info, verified_request):
    meta = _meta(
        scenes=[
            {"scene_id": 1, "class_name": "Scene1_Intro", "title": "a", "narration": "   "},
            {"scene_id": 2, "class_name": "Scene2_Trace", "title": "b", "narration": "n"},
        ]
    )
    problems = _problems(make_response(meta=meta), verified_request, env_info)
    assert any("narration is empty" in p for p in problems)


def test_forbidden_import_is_rejected(env_info, verified_request):
    bad = VALID_MANIM + "\nimport os\n"
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("import of 'os' is not allowed" in p for p in problems)


def test_subprocess_import_is_rejected(env_info, verified_request):
    bad = VALID_MANIM + "\nimport subprocess as sp\n"
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("not allowed" in p for p in problems)


def test_dangerous_calls_are_rejected(env_info, verified_request):
    for snippet in ("eval('1+1')", "exec('x=1')", "open('f.txt')", "input()", "getattr(x, 'y')"):
        bad = VALID_MANIM + f"\ndef _bad():\n    {snippet}\n"
        problems = _problems(make_response(manim_code=bad), verified_request, env_info)
        assert problems, f"expected a problem for {snippet}"


def test_dunder_attribute_access_is_rejected(env_info, verified_request):
    bad = VALID_MANIM + "\ndef _bad(obj):\n    return obj.__class__\n"
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("dunder" in p for p in problems)


def test_code_class_is_rejected(env_info, verified_request):
    bad = VALID_MANIM + "\ndef _bad():\n    return Code('main.py')\n"
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("Code class" in p for p in problems)


def test_math_tex_rejected_without_latex(env_info, verified_request):
    bad = VALID_MANIM + "\ndef _bad():\n    return MathTex(r'x^2')\n"
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("requires LaTeX" in p for p in problems)


def test_math_tex_allowed_when_latex_available(latex_env_info, verified_request):
    bad = VALID_MANIM + "\ndef _bad():\n    return MathTex(r'x^2')\n"
    problems = _problems(make_response(manim_code=bad), verified_request, latex_env_info)
    assert problems == []


def test_missing_manim_star_import_is_rejected(env_info, verified_request):
    bad = VALID_MANIM.replace("from manim import *", "import manim")
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("from manim import *" in p for p in problems)


def test_syntax_error_is_reported(env_info, verified_request):
    problems = _problems(
        make_response(manim_code="from manim import *\ndef broken(:\n"), verified_request, env_info
    )
    assert any("not valid Python" in p for p in problems)


def test_missing_meta_fields_are_reported(env_info, verified_request):
    meta = _meta()
    del meta["problem_summary"]
    problems = _problems(make_response(meta=meta), verified_request, env_info)
    assert any("problem_summary" in p for p in problems)


def test_solution_source_must_be_known(env_info, verified_request):
    problems = _problems(
        make_response(meta=_meta(solution_source="guessed")), verified_request, env_info
    )
    assert any("solution_source" in p for p in problems)


def test_verified_state_requires_provided_source(env_info, verified_request):
    problems = _problems(
        make_response(meta=_meta(solution_source="generated")), verified_request, env_info
    )
    assert any("verified" in p for p in problems)


def test_missing_state_requires_generated_source(env_info):
    from tests.conftest import load_sample

    request = load_sample("dijkstra_algorithm.json")
    meta = _meta(solution_source="provided")
    problems = _problems(make_response(meta=meta), request, env_info)
    assert any("missing" in p for p in problems)


def test_unverified_state_requires_performed_validation(env_info):
    from tests.conftest import load_sample

    request = load_sample("buggy_two_sum.json")
    meta = _meta(solution_source="provided", validation={"performed": False})
    problems = _problems(make_response(meta=meta), request, env_info)
    assert any("validation.performed" in p for p in problems)


def test_unverified_state_accepts_corrected_source(env_info):
    from tests.conftest import load_sample

    request = load_sample("buggy_two_sum.json")
    meta = _meta(
        solution_source="corrected",
        validation={"performed": True, "is_correct": False, "issues": ["off-by-one"]},
    )
    assert _problems(make_response(meta=meta), request, env_info) == []


def test_empty_solution_code_is_rejected(env_info, verified_request):
    problems = _problems(
        make_response(solution_code="   \n"), verified_request, env_info
    )
    assert any("solution_code is empty" in p for p in problems)


# ---------------------------------------------------------------------------
# finish_scene: the pipeline owns every scene ending
# ---------------------------------------------------------------------------


def test_missing_final_finish_scene_is_rejected(env_info, verified_request):
    bad = VALID_MANIM.replace("        finish_scene(self)\n", "", 1)
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("must be exactly finish_scene(self)" in p for p in problems)


def test_redefining_finish_scene_is_rejected(env_info, verified_request):
    bad = VALID_MANIM + "\n\ndef finish_scene(scene):\n    scene.wait(1)\n"
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("do not define it" in p for p in problems)


def test_importing_finish_scene_is_rejected(env_info, verified_request):
    bad = VALID_MANIM + "\nfrom pebble_helpers import finish_scene\n"
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("do not import it" in p for p in problems)


def test_while_loop_around_wait_is_rejected(env_info, verified_request):
    bad = VALID_MANIM.replace(
        "        self.wait(1.6)\n        finish_scene(self)",
        "        remaining = 1.0\n"
        "        while remaining > 0:\n"
        "            self.wait(0.5)\n"
        "            remaining -= 0.5\n"
        "        finish_scene(self)",
    )
    assert bad != VALID_MANIM
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("while loop around self.wait" in p for p in problems)


def test_repair_output_without_finish_scene_is_rejected(env_info):
    from pebble.validators import validate_manim_code

    broken = VALID_MANIM.replace("        finish_scene(self)\n", "", 1)
    problems = validate_manim_code(
        broken, ["Scene1_Intro", "Scene2_Trace"], env_info.latex_available
    )
    assert any("finish_scene(self)" in p for p in problems)

    assert (
        validate_manim_code(
            VALID_MANIM, ["Scene1_Intro", "Scene2_Trace"], env_info.latex_available
        )
        == []
    )


# ---------------------------------------------------------------------------
# no code on screen
# ---------------------------------------------------------------------------

def _with_text(value: str) -> str:
    """Put `value` on screen the only legal way: through the kit's caption."""
    return VALID_MANIM.replace(
        'self.set_caption("Each number needs a partner")',
        f"self.set_caption({value!r})",
    )


@pytest.mark.parametrize(
    "snippet",
    [
        "seen[need]",
        "for i in range(n):",
        "return [seen[x], i]",
        "def twoSum(self, nums, target):",
        "i += 1",
        "if need in seen:",
    ],
)
def test_code_like_on_screen_text_is_rejected(snippet, env_info, verified_request):
    problems = _problems(make_response(manim_code=_with_text(snippet)), verified_request, env_info)
    assert any("on-screen text" in problem for problem in problems), problems


@pytest.mark.parametrize(
    "snippet",
    [
        "need = 7",
        "O(n log n)",
        "[2, 7, 11, 15]",
        "two numbers add up to the target",
        "index 0 and index 1",
        "Step 2 of 5",
        "the value 7 is already stored",
    ],
)
def test_plain_language_on_screen_text_is_accepted(snippet, env_info, verified_request):
    problems = _problems(make_response(manim_code=_with_text(snippet)), verified_request, env_info)
    assert problems == [], problems


# ---------------------------------------------------------------------------
# the kit owns the visuals
# ---------------------------------------------------------------------------

def test_redefining_a_kit_structure_is_rejected(env_info, verified_request):
    bad = VALID_MANIM + "\n\nclass ArrayViz:\n    pass\n"
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("provided by the visual kit" in problem for problem in problems)


def test_importing_the_kit_is_rejected(env_info, verified_request):
    bad = VALID_MANIM + "\nfrom pebble_kit import ArrayViz\n"
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("do not import" in problem for problem in problems)


def test_missing_kit_structure_is_rejected(env_info, verified_request):
    no_kit = (
        "from manim import *\n\n\n"
        "class Scene1_Intro(Scene):\n"
        "    def construct(self):\n"
        "        self.play(Create(Dot()), run_time=0.5)\n"
        "        finish_scene(self)\n"
    )
    problems = _problems(make_response(manim_code=no_kit), verified_request, env_info)
    assert any("kit structure" in problem for problem in problems)


def test_raw_text_is_rejected(env_info, verified_request):
    bad = VALID_MANIM + (
        "\ndef _onscreen():\n"
        "    return Text('a floating sentence', font_size=30)\n"
    )
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("do not place on-screen text" in problem for problem in problems)


def test_font_override_is_rejected(env_info, verified_request):
    bad = VALID_MANIM + (
        "\ndef _onscreen():\n"
        "    return Text('hello', font='Arial', font_size=30)\n"
    )
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("font=" in problem for problem in problems)


def test_small_font_size_is_rejected(env_info, verified_request):
    bad = VALID_MANIM + "\ndef _onscreen():\n    return Text('hello', font_size=14)\n"
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("too small" in problem for problem in problems)


def test_config_use_is_rejected(env_info, verified_request):
    for line in (
        'config.background_color = "#000000"',
        "config.frame_width = 20",
        "with tempconfig({'frame_width': 20}):\n    pass",
    ):
        bad = VALID_MANIM + "\n\n" + line + "\n"
        problems = _problems(make_response(manim_code=bad), verified_request, env_info)
        assert any("do not use" in problem for problem in problems), (line, problems)


def test_invented_kit_method_is_rejected(env_info, verified_request):
    bad = VALID_MANIM.replace(
        "        nums = ArrayViz([value for _, value in trace])",
        "        nums = ArrayViz([value for _, value in trace])\n"
        "        nums.get_cell(0)",
    )
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("not a method of ArrayViz" in problem for problem in problems), problems


def test_documented_kit_methods_are_accepted(env_info, verified_request):
    assert _problems(make_response(), verified_request, env_info) == []


def test_intro_result_assigned_to_a_variable_is_rejected(env_info, verified_request):
    bad = VALID_MANIM.replace(
        "        nums = ArrayViz([value for _, value in trace])",
        "        nums = ArrayViz([value for _, value in trace]).intro(at=LEFT_LANE)",
    )
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("returns an Animation" in problem for problem in problems), problems


def test_result_scene_with_a_structure_is_rejected():
    script = (
        "from manim import *\n\n"
        "class Scene1_Result(Scene):\n"
        "    def construct(self):\n"
        "        ArrayViz([1, 2], at=RIGHT_LANE)\n"
        "        self.result_cards('[0, 1]', 'O(n)', 'O(n)')\n"
        "        finish_scene(self)\n"
    )
    problems = _check_result_scene(ast.parse(script))
    assert problems and "result cards" in problems[0]


def test_result_scene_with_only_cards_is_accepted():
    script = (
        "from manim import *\n\n"
        "class Scene1_Result(Scene):\n"
        "    def construct(self):\n"
        "        self.result_cards('[0, 1]', 'O(n)', 'O(n)')\n"
        "        finish_scene(self)\n"
    )
    assert _check_result_scene(ast.parse(script)) == []


def test_overlong_caption_is_rejected(env_info, verified_request):
    long_line = "Check every pair of numbers and remember the value you still need for it"
    bad = VALID_MANIM.replace(
        'self.set_caption("Each number needs a partner")',
        f'self.set_caption("{long_line}")',
    )
    assert bad != VALID_MANIM
    problems = _problems(make_response(manim_code=bad), verified_request, env_info)
    assert any("at most 70 characters" in problem for problem in problems), problems


# ---------------------------------------------------------------------------
# compare_panels owns the whole stage
# ---------------------------------------------------------------------------

PANEL_SCENE = (
    "class Scene3_Fix(Scene):\n"
    "    def construct(self):\n"
    "        show_title(self, \"Bug and fix\")\n"
    "        left_at, right_at = compare_panels(self, \"Buggy\", \"Fixed\")\n"
    "        wrong = ArrayViz([3, 2, 4], at=left_at, max_width=5.2)\n"
    "        right = ArrayViz([3, 2, 4], at=right_at, max_width=5.2)\n"
    "        self.play(wrong.intro(), right.intro())\n"
    "        finish_scene(self)\n"
)


def _with_panel_scene(body: str = PANEL_SCENE):
    return VALID_MANIM + "\n\n" + body


PANEL_META = {
    "scenes": [
        {"scene_id": 1, "class_name": "Scene1_Intro", "title": "a", "narration": "n"},
        {"scene_id": 2, "class_name": "Scene2_Trace", "title": "b", "narration": "n"},
        {"scene_id": 3, "class_name": "Scene3_Fix", "title": "c", "narration": "n"},
    ]
}


CORRECTED_META = {
    **{key: value for key, value in PANEL_META.items()},
    "solution_source": "corrected",
    "validation": {"performed": True, "is_correct": False, "issues": [], "notes": ""},
}


@pytest.fixture
def corrected_request() -> VideoRequest:
    """An unverified solution the model had to fix: compare_panels is allowed."""
    from tests.conftest import load_sample

    return load_sample("buggy_two_sum.json")


def test_compare_panel_scene_with_panel_anchors_is_accepted(
    env_info, corrected_request
):
    response = make_response(
        manim_code=_with_panel_scene(), meta=_meta(**CORRECTED_META)
    )
    assert _problems(response, corrected_request, env_info) == []


def test_compare_panels_without_a_bug_is_only_a_warning(env_info, verified_request):
    """The rule is soft: it is reported but never blocks a working script."""
    from pebble.validators import validate_generation_split

    response = make_response(manim_code=_with_panel_scene(), meta=_meta(**PANEL_META))
    problems = validate_generation_split(parse_response(response), verified_request, env_info)
    assert problems.hard == []
    assert any("compare_panels" in problem for problem in problems.soft)


def test_lane_anchor_inside_a_compare_scene_is_rejected(env_info, corrected_request):
    body = PANEL_SCENE.replace(
        "        right = ArrayViz([3, 2, 4], at=right_at, max_width=5.2)",
        "        right = MapViz(\"seen\", at=RIGHT_LANE, max_width=5.2)",
    )
    problems = _problems(
        make_response(manim_code=_with_panel_scene(body), meta=_meta(**CORRECTED_META)),
        corrected_request,
        env_info,
    )
    assert any("compare_panels together with" in problem for problem in problems), problems


def test_structure_without_a_panel_anchor_in_a_compare_scene_is_rejected(
    env_info, corrected_request
):
    body = PANEL_SCENE.replace(
        "        right = ArrayViz([3, 2, 4], at=right_at, max_width=5.2)",
        "        right = ArrayViz([3, 2, 4])",
    )
    problems = _problems(
        make_response(manim_code=_with_panel_scene(body), meta=_meta(**CORRECTED_META)),
        corrected_request,
        env_info,
    )
    assert any("needs at=left_at or at=right_at" in problem for problem in problems), problems


def test_state_panel_does_not_need_a_panel_anchor(env_info, corrected_request):
    body = PANEL_SCENE.replace(
        "        self.play(wrong.intro(), right.intro())",
        "        chips = StatePanel({\"need\": 7})\n"
        "        self.play(wrong.intro(), right.intro(), chips.intro())",
    )
    problems = _problems(
        make_response(manim_code=_with_panel_scene(body), meta=_meta(**CORRECTED_META)),
        corrected_request,
        env_info,
    )
    assert not any("needs at=left_at" in problem for problem in problems), problems


def test_prose_parenthetical_is_not_mistaken_for_a_call(env_info, verified_request):
    ok = VALID_MANIM.replace(
        "Each number needs a partner", "The original loop (buggy) skips the last index"
    )
    problems = _problems(make_response(manim_code=ok), verified_request, env_info)
    assert not any("function-call syntax" in problem for problem in problems), problems
