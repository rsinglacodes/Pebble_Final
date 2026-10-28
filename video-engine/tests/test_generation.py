"""Generation: retry loop, retry prompt content, byte-for-byte solution restore."""

from __future__ import annotations

import json

import pytest

from pebble.config import Settings
from pebble.errors import GenerationError
from pebble.generation import generate
from pebble.models import VideoRequest
from pebble.workspace import JobWorkspace
from tests.conftest import (
    VALID_MANIM,
    VALID_META,
    VALID_SOLUTION,
    llm_reply,
    load_sample,
    make_response,
)

RAW_CODE = (
    "class Solution:\n"
    "    def twoSum(self, nums, target):   \n"
    "        seen = {}\n"
    "        for i, value in enumerate(nums):\n"
    "            need = target - value\n"
    "            if need in seen:\n"
    "                return [seen[need], i]\n"
    "            seen[value] = i\n"
    "        return []\n"
)


class FakeClient:
    """Stands in for pebble.generation.LLMClient."""

    def __init__(self, responses):
        self.responses = list(responses)
        self.prompts: list[str] = []

    def call_llm(self, prompt: str):
        self.prompts.append(prompt)
        if not self.responses:
            raise AssertionError("LLM called more times than expected")
        return llm_reply(self.responses.pop(0))


@pytest.fixture
def settings() -> Settings:
    return Settings(max_generation_attempts=3)


def _patch(monkeypatch, responses):
    client = FakeClient(responses)
    monkeypatch.setattr("pebble.generation.LLMClient", lambda _settings: client)
    return client


def test_retries_after_invalid_response(monkeypatch, tmp_path, settings, env_info):
    invalid = make_response(manim_code=VALID_MANIM + "\nimport os\n")
    valid = make_response()
    client = _patch(monkeypatch, [invalid, valid])

    workspace = JobWorkspace(f"test_{next_id()}")
    request = load_sample("two_sum.json")
    result = generate(request, workspace, settings, env_info)

    assert len(client.prompts) == 2
    retry = client.prompts[1]
    assert "YOUR PREVIOUS RESPONSE WAS REJECTED." in retry
    assert "import of 'os' is not allowed" in retry
    assert "Return the COMPLETE response again" in retry
    assert len(result.meta.scenes) == 2


def test_attempt_files_are_saved(monkeypatch, settings, env_info):
    client = _patch(monkeypatch, [make_response(manim_code=VALID_MANIM + "\nimport os\n"), make_response()])
    workspace = JobWorkspace(f"test_{next_id()}")
    generate(load_sample("two_sum.json"), workspace, settings, env_info)

    for attempt in (1, 2):
        prompt_path, response_path = workspace.attempt_paths(attempt)
        assert prompt_path.exists() and prompt_path.stat().st_size > 0
        assert response_path.exists() and response_path.stat().st_size > 0
    first_prompt = workspace.attempt_paths(1)[0].read_text(encoding="utf-8")
    first_response = workspace.attempt_paths(1)[1].read_text(encoding="utf-8")
    assert "import os" in first_response  # raw reply is preserved verbatim
    assert "REQUEST KIND: leetcode_problem" in first_prompt


def test_provided_solution_is_restored_byte_for_byte(monkeypatch, settings, env_info):
    client = _patch(monkeypatch, [make_response()])
    workspace = JobWorkspace(f"test_{next_id()}")

    request = VideoRequest.model_validate(
        {
            "question": {"id": 1, "slug": "two-sum", "title": "Two Sum"},
            "solution": {"code": RAW_CODE, "programming_language": "python", "validated": True},
        }
    )
    result = generate(request, workspace, settings, env_info)

    assert result.meta.solution_source == "provided"
    assert result.solution_code == RAW_CODE
    doc = json.loads(workspace.generation_path.read_text(encoding="utf-8"))
    assert doc["solution"] == RAW_CODE
    assert doc["style"] == "beginner_friendly"
    assert workspace.animation_path.read_text(encoding="utf-8").strip() == VALID_MANIM.strip()


def test_gives_up_after_max_attempts(monkeypatch, settings, env_info):
    bad = make_response(manim_code=VALID_MANIM + "\nimport subprocess\n")
    client = _patch(monkeypatch, [bad, bad, bad])
    workspace = JobWorkspace(f"test_{next_id()}")

    with pytest.raises(GenerationError) as excinfo:
        generate(load_sample("two_sum.json"), workspace, settings, env_info)

    assert len(client.prompts) == 3
    assert excinfo.value.problems
    assert any("subprocess" in problem for problem in excinfo.value.problems)
    assert not workspace.animation_path.exists()


def test_parse_failure_is_retried(monkeypatch, settings, env_info):
    client = _patch(monkeypatch, ["this is not the required format", make_response()])
    workspace = JobWorkspace(f"test_{next_id()}")
    result = generate(load_sample("two_sum.json"), workspace, settings, env_info)
    assert len(client.prompts) == 2
    assert len(result.meta.scenes) == 2


def test_missing_solution_requires_generated_source(monkeypatch, settings, env_info):
    meta = json.loads(json.dumps(VALID_META))
    meta["solution_source"] = "generated"
    meta["validation"] = {"performed": False, "is_correct": None, "issues": [], "notes": ""}

    # First reply wrongly claims "provided"; second one is consistent.
    client = _patch(monkeypatch, [make_response(), make_response(meta=meta)])
    workspace = JobWorkspace(f"test_{next_id()}")
    result = generate(load_sample("dijkstra_algorithm.json"), workspace, settings, env_info)

    assert len(client.prompts) == 2
    assert "YOUR PREVIOUS RESPONSE WAS REJECTED." in client.prompts[1]
    assert "solution_state is 'missing'" in client.prompts[1]
    assert result.meta.solution_source == "generated"
    assert result.solution_code == VALID_SOLUTION.strip()


_counter = {"n": 0}


def next_id() -> str:
    _counter["n"] += 1
    return f"{_counter['n']:06d}"


# ---------------------------------------------------------------------------
# hard vs soft problems (soft never kills a job)
# ---------------------------------------------------------------------------

SOFT_ONLY_MANIM = VALID_MANIM.replace(
    'self.set_caption("Each number needs a partner")',
    'self.set_caption("Each number needs a partner, so we remember every value '
    'we have already seen")',
)

SUPER_SOFT_MANIM = SOFT_ONLY_MANIM.replace(
    "        nums = ArrayViz([value for _, value in trace])\n"
    "        self.play(nums.intro())\n",
    "",
)


def test_soft_problems_are_accepted_with_warnings(monkeypatch, settings, env_info):
    client = _patch(monkeypatch, [make_response(manim_code=SOFT_ONLY_MANIM)] * 3)
    workspace = JobWorkspace(f"test_{next_id()}")

    result = generate(load_sample("two_sum.json"), workspace, settings, env_info)

    # Soft problems are fed back, but the third attempt is accepted anyway.
    assert len(client.prompts) == 3
    assert "70 characters" in client.prompts[1]
    assert result.generation_warnings
    assert any("70 characters" in warning for warning in result.generation_warnings)

    doc = json.loads(workspace.generation_path.read_text(encoding="utf-8"))
    assert doc["generation_warnings"] == result.generation_warnings
    assert (
        workspace.animation_path.read_text(encoding="utf-8").strip()
        == SOFT_ONLY_MANIM.strip()
    )


def test_a_clean_attempt_after_a_soft_one_wins(monkeypatch, settings, env_info):
    client = _patch(monkeypatch, [make_response(manim_code=SOFT_ONLY_MANIM), make_response()])
    workspace = JobWorkspace(f"test_{next_id()}")

    result = generate(load_sample("two_sum.json"), workspace, settings, env_info)

    assert len(client.prompts) == 2
    assert result.generation_warnings == []
    assert (
        workspace.animation_path.read_text(encoding="utf-8").strip()
        == VALID_MANIM.strip()
    )


def test_the_best_soft_attempt_is_kept(monkeypatch, settings, env_info):
    responses = [
        make_response(manim_code=SOFT_ONLY_MANIM),
        make_response(manim_code=VALID_MANIM + "\nimport os\n"),
        make_response(manim_code=SUPER_SOFT_MANIM),
    ]
    _patch(monkeypatch, responses)
    workspace = JobWorkspace(f"test_{next_id()}")

    result = generate(load_sample("two_sum.json"), workspace, settings, env_info)

    # The hard-broken attempt is unusable; of the two soft ones, one problem wins.
    assert len(result.generation_warnings) == 1
    assert (
        workspace.animation_path.read_text(encoding="utf-8").strip()
        == SOFT_ONLY_MANIM.strip()
    )
    assert result.meta.solution_source == "provided"


def test_hard_problems_still_fail_the_job(monkeypatch, settings, env_info):
    broken = make_response(manim_code=VALID_MANIM + "\nimport os\n")
    client = _patch(monkeypatch, [broken] * 3)
    workspace = JobWorkspace(f"test_{next_id()}")

    with pytest.raises(GenerationError) as excinfo:
        generate(load_sample("two_sum.json"), workspace, settings, env_info)

    assert len(client.prompts) == 3
    assert any("import of 'os'" in problem for problem in excinfo.value.problems)


def test_hard_beats_soft_in_the_retry_feedback(monkeypatch, settings, env_info):
    responses = [
        make_response(manim_code=SOFT_ONLY_MANIM),
        make_response(manim_code=VALID_MANIM + "\nimport os\n"),
        make_response(manim_code=VALID_MANIM + "\nimport os\n"),
    ]
    client = _patch(monkeypatch, responses)
    workspace = JobWorkspace(f"test_{next_id()}")

    generate(load_sample("two_sum.json"), workspace, settings, env_info)

    # Attempt 2's prompt carries the soft problem; attempt 3's carries the hard one.
    assert "70 characters" in client.prompts[1]
    assert "import of 'os' is not allowed" in client.prompts[2]
