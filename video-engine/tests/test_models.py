"""Models: tolerant parsing and the two derived values."""

from __future__ import annotations

import json

from pebble.models import VideoRequest
from tests.conftest import SAMPLES, load_sample


def test_two_sum_is_verified_leetcode():
    request = load_sample("two_sum.json")
    assert request.request_kind == "leetcode_problem"
    assert request.solution_state == "verified"
    assert request.programming_language == "python"
    assert request.title == "Two Sum"


def test_buggy_two_sum_is_unverified():
    request = load_sample("buggy_two_sum.json")
    assert request.request_kind == "leetcode_problem"
    assert request.solution_state == "unverified"


def test_dijkstra_is_algorithm_missing():
    request = load_sample("dijkstra_algorithm.json")
    assert request.request_kind == "algorithm"
    assert request.solution_state == "missing"
    assert request.title == "Dijkstra's Algorithm"
    assert request.programming_language == "python"  # empty language defaults


def test_concise_sample_differs_in_style_from_default():
    default = load_sample("two_sum.json")
    concise = load_sample("two_sum_concise.json")
    assert concise.preferences_or_default.explanation_style == "concise"
    assert concise.request_fingerprint() != default.request_fingerprint()


def test_null_solution_is_missing():
    request = VideoRequest.model_validate({"solution": None})
    assert request.solution_state == "missing"
    assert request.request_kind == "algorithm"


def test_whitespace_code_is_missing():
    request = VideoRequest.model_validate(
        {"solution": {"code": "   \n\t  ", "validated": True}}
    )
    assert request.solution_state == "missing"


def test_null_id_and_slug_is_algorithm():
    request = VideoRequest.model_validate(
        {"question": {"id": None, "slug": "", "title": "Binary Search"}}
    )
    assert request.request_kind == "algorithm"


def test_nonempty_id_is_leetcode_even_without_slug():
    request = VideoRequest.model_validate({"question": {"id": 42, "slug": None}})
    assert request.request_kind == "leetcode_problem"


def test_missing_question_is_algorithm():
    request = VideoRequest.model_validate({})
    assert request.request_kind == "algorithm"
    assert request.solution_state == "missing"


def test_extra_fields_are_ignored():
    request = VideoRequest.model_validate(
        {
            "question": {"id": 1, "slug": "x", "title": "X", "difficulty": "easy"},
            "solution": {"code": "pass", "validated": True, "runtime_ms": 4},
            "preferences": {"explanation_style": "concise", "audience": "kids"},
            "unrelated": [1, 2, 3],
        }
    )
    assert request.request_kind == "leetcode_problem"
    assert request.preferences_or_default.explanation_style == "concise"
    assert request.preferences_or_default.explanation_language == "English"


def test_default_language_and_preferences():
    request = VideoRequest.model_validate({"solution": {"code": "x = 1"}})
    assert request.programming_language == "python"
    assert request.preferences_or_default.language == "English"
    assert request.preferences_or_default.explanation_style == "beginner_friendly"


def test_language_is_normalized_to_lowercase():
    request = VideoRequest.model_validate(
        {"solution": {"code": "x = 1", "programming_language": "  PYTHON "}}
    )
    assert request.programming_language == "python"


def test_fingerprint_is_stable_and_distinct():
    first = load_sample("two_sum.json")
    second = load_sample("two_sum.json")
    assert first.request_fingerprint() == second.request_fingerprint()
    assert len(first.request_fingerprint()) == 64
    assert int(first.request_fingerprint(), 16) >= 0

    other = VideoRequest.model_validate(
        {
            "question": {"id": 1, "slug": "two-sum", "title": "Two Sum"},
            "solution": {"code": "pass", "programming_language": "python", "validated": True},
        }
    )
    assert other.request_fingerprint() != first.request_fingerprint()


def test_fingerprint_ignores_code_line_endings():
    lf = VideoRequest.model_validate({"solution": {"code": "a = 1\nb = 2"}})
    crlf = VideoRequest.model_validate({"solution": {"code": "a = 1\r\nb = 2\r\n"}})
    assert lf.request_fingerprint() == crlf.request_fingerprint()


def test_samples_load_as_valid_json():
    for name in (
        "two_sum.json",
        "buggy_two_sum.json",
        "dijkstra_algorithm.json",
        "two_sum_concise.json",
    ):
        payload = json.loads((SAMPLES / name).read_text(encoding="utf-8"))
        assert isinstance(payload, dict)
        VideoRequest.model_validate(payload)
