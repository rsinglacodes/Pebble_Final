"""Parsing: section extraction, fence stripping, precise ParseErrors."""

from __future__ import annotations

import json

import pytest

from pebble.errors import ParseError
from pebble.parsing import parse_response
from tests.conftest import VALID_MANIM, VALID_META, VALID_SOLUTION, make_response


def test_valid_response_parses():
    result = parse_response(make_response())
    assert len(result.meta.scenes) == 2
    assert result.meta.scenes[0].class_name == "Scene1_Intro"
    assert result.meta.solution_source == "provided"
    assert result.meta.complexity.time == "O(n)"
    assert "class Solution" in result.solution_code
    assert result.manim_code.startswith("from manim import *")


def test_fenced_code_is_stripped():
    response = make_response(
        solution_code="```python\nx = 1\n```\n",
        manim_code="```python\nfrom manim import *\n```\n",
    )
    result = parse_response(response)
    assert "```" not in result.solution_code
    assert "```" not in result.manim_code
    assert result.solution_code == "x = 1"
    assert result.manim_code == "from manim import *"


def test_missing_meta_section_is_precise():
    with pytest.raises(ParseError) as excinfo:
        parse_response(make_response(omit=("pebble_meta",)))
    assert "pebble_meta" in excinfo.value.missing


def test_missing_solution_section_is_precise():
    with pytest.raises(ParseError) as excinfo:
        parse_response(make_response(omit=("solution_code",)))
    assert excinfo.value.missing == ["solution_code"]


def test_missing_manim_section_is_precise():
    with pytest.raises(ParseError) as excinfo:
        parse_response(make_response(omit=("manim_code",)))
    assert excinfo.value.missing == ["manim_code"]


def test_all_sections_missing_lists_all():
    with pytest.raises(ParseError) as excinfo:
        parse_response("nothing useful here")
    assert set(excinfo.value.missing) == {"pebble_meta", "solution_code", "manim_code"}


def test_invalid_meta_json_is_parse_error():
    response = make_response(meta=None)
    response = response.replace("{", "{not json", 1)
    with pytest.raises(ParseError) as excinfo:
        parse_response(response)
    assert "pebble_meta" in excinfo.value.missing


def test_empty_response_is_parse_error():
    with pytest.raises(ParseError):
        parse_response("   ")
    with pytest.raises(ParseError):
        parse_response("")


def test_meta_falls_back_to_first_json_object():
    meta_json = json.dumps(VALID_META)
    response = (
        meta_json
        + "\n<solution_code>\n"
        + VALID_SOLUTION
        + "</solution_code>\n<manim_code>\n"
        + VALID_MANIM
        + "</manim_code>"
    )
    result = parse_response(response)
    assert len(result.meta.scenes) == 2
    assert result.meta.solution_source == "provided"


def test_fallback_ignores_unrelated_json_in_code():
    # solution code contains `seen = {}`, which must not be mistaken for meta.
    response = make_response(omit=("pebble_meta",))
    with pytest.raises(ParseError) as excinfo:
        parse_response(response)
    assert "pebble_meta" in excinfo.value.missing


def _meta_block() -> str:
    return "<pebble_meta>\n" + json.dumps(VALID_META, indent=2) + "\n</pebble_meta>"


def test_unterminated_final_manim_section_is_accepted():
    # Observed live: the model stops right after finish_scene(self) and never
    # writes the closing tag. The last section's body is the rest of the text.
    text = (
        _meta_block()
        + "\n<solution_code>\nclass Solution:\n    pass\n</solution_code>"
        + "\n<manim_code>\n"
        + VALID_MANIM
    )
    result = parse_response(text)
    assert result.manim_code.strip() == VALID_MANIM.strip()
    assert "class Solution" in result.solution_code


def test_unterminated_section_stops_at_the_next_section():
    text = (
        _meta_block()
        + "\n<solution_code>\nclass Solution:\n    pass\n"
        + "<manim_code>\nfrom manim import *\n"
    )
    result = parse_response(text)
    assert result.solution_code == "class Solution:\n    pass"
    assert result.manim_code == "from manim import *"


def test_missing_section_still_raises_when_the_tag_is_absent():
    text = _meta_block() + "\n<solution_code>\nclass Solution:\n    pass\n</solution_code>"
    with pytest.raises(ParseError) as excinfo:
        parse_response(text)
    assert excinfo.value.missing == ["manim_code"]
