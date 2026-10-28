"""Shared fixtures and canned LLM responses for the Pebble test suite."""

from __future__ import annotations

import json
import math
import struct
import subprocess
import wave
from pathlib import Path

import pytest

from pebble.environment import EnvInfo
from pebble.llm import LLMResponse, LLMUsage
from pebble.models import VideoRequest

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SAMPLES = PROJECT_ROOT / "samples"

VALID_MANIM = '''from manim import *


def build_trace():
    values = [2, 7, 11, 15]
    return [(index, value) for index, value in enumerate(values)]


class Scene1_Intro(Scene):
    def construct(self):
        self.title_card("Two Sum", "Find two numbers that add to a target")
        self.set_caption("Each number needs a partner")
        self.wait(1)
        finish_scene(self)


class Scene2_Trace(Scene):
    def construct(self):
        trace = build_trace()
        nums = ArrayViz([value for _, value in trace])
        self.play(nums.intro())
        chips = StatePanel({"need": 7})
        self.play(chips.intro())
        self.wait(1.6)
        finish_scene(self)
'''

VALID_SOLUTION = '''class Solution:
    def twoSum(self, nums, target):
        seen = {}
        for i, value in enumerate(nums):
            need = target - value
            if need in seen:
                return [seen[need], i]
            seen[value] = i
        return []
'''

VALID_META = {
    "problem_summary": "Given an array of integers and a target, return the indices of the two numbers that add up to the target.",
    "example": {"input": "nums = [2, 7, 11, 15], target = 9", "output": "[0, 1]"},
    "validation": {"performed": False, "is_correct": None, "issues": [], "notes": ""},
    "solution_source": "provided",
    "programming_language": "python",
    "complexity": {"time": "O(n)", "space": "O(n)"},
    "scenes": [
        {"scene_id": 1, "class_name": "Scene1_Intro", "title": "Intro", "narration": "We solve the two sum problem."},
        {"scene_id": 2, "class_name": "Scene2_Trace", "title": "Trace", "narration": "We walk through the array once."},
    ],
}


def load_sample(name: str) -> VideoRequest:
    return VideoRequest.model_validate(json.loads((SAMPLES / name).read_text(encoding="utf-8")))


def llm_reply(
    text: str,
    prompt_tokens: int | None = 1000,
    completion_tokens: int | None = 2000,
    reasoning_tokens: int | None = None,
    seconds: float = 1.0,
) -> LLMResponse:
    """An LLMResponse with hand-set usage, for mocks that must report cost."""
    usage = None
    if prompt_tokens is not None or completion_tokens is not None:
        usage = LLMUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            reasoning_tokens=reasoning_tokens,
        )
    return LLMResponse(text=text, usage=usage, seconds=seconds)


def make_response(
    meta: dict | None = None,
    solution_code: str | None = None,
    manim_code: str | None = None,
    omit: tuple[str, ...] = (),
) -> str:
    """Build a complete tagged LLM response; `omit` drops whole sections."""
    meta = VALID_META if meta is None else meta
    solution_code = VALID_SOLUTION if solution_code is None else solution_code
    manim_code = VALID_MANIM if manim_code is None else manim_code

    sections = []
    if "pebble_meta" not in omit:
        sections.append("<pebble_meta>\n" + json.dumps(meta, indent=2) + "\n</pebble_meta>")
    if "solution_code" not in omit:
        sections.append("<solution_code>\n" + solution_code + "</solution_code>")
    if "manim_code" not in omit:
        sections.append("<manim_code>\n" + manim_code + "</manim_code>")
    return "\n".join(sections)


@pytest.fixture
def env_info() -> EnvInfo:
    return EnvInfo(
        manim_version="0.18.1",
        latex_available=False,
        ffmpeg_available=True,
        ffprobe_available=True,
        code_font="Menlo",
    )


@pytest.fixture
def latex_env_info() -> EnvInfo:
    return EnvInfo(
        manim_version="0.18.1",
        latex_available=True,
        ffmpeg_available=True,
        ffprobe_available=True,
        code_font="Menlo",
    )


@pytest.fixture
def verified_request() -> VideoRequest:
    return load_sample("two_sum.json")


# ---------------------------------------------------------------------------
# media helpers (real ffmpeg / wav generation, used by mux, tts, pipeline tests)
# ---------------------------------------------------------------------------


def run_ffmpeg(args: list[str]) -> None:
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", *args],
        check=True,
        capture_output=True,
        timeout=180,
    )


def make_color_video(path: Path, duration: float, size: str = "320x240") -> Path:
    run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            f"color=c=black:s={size}:d={duration}:r=15",
            "-pix_fmt",
            "yuv420p",
            str(path),
        ]
    )
    return path


def make_sine_wav(path: Path, duration: float, freq: int = 440) -> Path:
    run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            f"sine=frequency={freq}:duration={duration}",
            "-ar",
            "44100",
            "-ac",
            "2",
            str(path),
        ]
    )
    return path


def wav_bytes(seconds: float = 1.0, freq: int = 440, rate: int = 16000) -> bytes:
    """A small mono 16-bit WAV, no ffmpeg needed."""
    frames = bytearray()
    total = int(seconds * rate)
    for index in range(total):
        value = int(12000 * math.sin(2 * math.pi * freq * index / rate))
        frames += struct.pack("<h", value)

    buffer = __import__("io").BytesIO()
    with wave.open(buffer, "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(bytes(frames))
    return buffer.getvalue()


TINY_MANIM = '''from manim import *


class Scene1_Intro(Scene):
    def construct(self):
        nums = ArrayViz([2, 7])
        self.play(nums.intro(), run_time=0.4)
        self.wait(0.2)
        finish_scene(self)


class Scene2_Trace(Scene):
    def construct(self):
        self.show_title("Trace")
        nums = ArrayViz([2, 7, 11])
        self.play(nums.intro(), run_time=0.4)
        self.wait(0.2)
        finish_scene(self)
'''
