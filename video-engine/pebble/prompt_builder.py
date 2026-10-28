"""Builds the single prompt sent to the LLM from a VideoRequest."""

from __future__ import annotations

import re
from pathlib import Path

from pebble.environment import EnvInfo
from pebble.errors import ConfigError
from pebble.models import (
    REQUEST_KIND_ALGORITHM,
    REQUEST_KIND_LEETCODE,
    STATE_MISSING,
    STATE_UNVERIFIED,
    STATE_VERIFIED,
    VideoRequest,
)
from pebble.styles import get_style

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
SYSTEM_PROMPT_PATH = PROMPTS_DIR / "system_prompt.txt"
DIAGRAM_RECIPES_PATH = PROMPTS_DIR / "diagram_recipes.txt"
KIT_REFERENCE_PATH = PROMPTS_DIR / "kit_reference.txt"
FIXER_PROMPT_PATH = PROMPTS_DIR / "fixer_prompt.txt"

_PLACEHOLDER_RE = re.compile(r"\{\{(\w+)\}\}")

SOLUTION_VERIFIED = (
    "A verified solution is provided. It is the source of truth: visualize exactly "
    "its logic and do not change it. Set solution_source to \"provided\", "
    "validation.performed false, is_correct null."
)
SOLUTION_UNVERIFIED = (
    "A solution is provided but it is NOT verified. FIRST validate it carefully "
    "against the problem: correctness, edge cases (empty input, duplicates, "
    "negatives, single element, off-by-one), and complexity. If it is correct, keep "
    "it exactly and set solution_source \"provided\". If it has a bug or fails an "
    "edge case, fix it minimally, set solution_source \"corrected\", list each issue "
    "in validation.issues, visualize the CORRECTED version, and add one short scene "
    "that shows the bug and the fix. Always set validation.performed true and "
    "is_correct to your verdict about the ORIGINAL code. Never change it silently."
)
SOLUTION_MISSING_LEETCODE = (
    "No solution was provided. Solve the problem yourself first, with an approach "
    "suited to an interview, correct for edge cases and with the best reasonable "
    "complexity, written in the programming language above. Set solution_source "
    "\"generated\", validation.performed false."
)
SOLUTION_MISSING_ALGORITHM = (
    "No code was provided. Write a clear, standard, textbook implementation of the "
    "algorithm named in the title in the programming language above. Set "
    "solution_source \"generated\", validation.performed false."
)

PROBLEM_LEETCODE = (
    "Only the id, slug and title are given, with no problem statement. Reconstruct "
    "the problem from your knowledge of this LeetCode problem and from the solution "
    "code. Do NOT invent constraints or details you are unsure about; keep the "
    "summary general where unsure. Paraphrase: never reproduce the official "
    "statement word for word. Choose your own small valid example."
)
PROBLEM_ALGORITHM = (
    "The title names an algorithm or topic, not a LeetCode problem. Explain what it "
    "does, the intuition, how it works step by step on a small example, and its "
    "complexity."
)

LATEX_AVAILABLE = (
    "LaTeX is available. Use MathTex only for real math, with raw strings r\"...\" "
    "and single braces; use Text for everything else. Write complexity as plain Text "
    "such as Text(\"O(n log n)\") if unsure."
)
LATEX_MISSING = (
    "LaTeX is NOT installed. Never use MathTex, Tex, Matrix, DecimalNumber, Integer, "
    "Variable, Axes, NumberPlane or NumberLine. Write everything, including "
    "complexity, with Text."
)


def _read(path: Path, label: str) -> str:
    if not path.exists():
        raise ConfigError(f"Missing {label}: {path}")
    return path.read_text(encoding="utf-8")


def build_input_block(request: VideoRequest) -> str:
    lines: list[str] = []
    if request.request_kind == REQUEST_KIND_LEETCODE:
        question = request.question_or_empty
        header = "LEETCODE PROBLEM:"
        if question.id is not None and str(question.id).strip():
            header += f" #{question.id}"
        if (question.title or "").strip():
            header += f" {question.title.strip()}"
        if (question.slug or "").strip():
            header += f" (slug: {question.slug.strip()})"
        lines.append(header)
    else:
        lines.append(f"ALGORITHM / TOPIC TO EXPLAIN: {request.title or '(untitled)'}")

    lines.append("SOLUTION:")
    code = request.solution_code
    if code:
        lines.append(code)
    else:
        lines.append("(none provided)")
    return "\n".join(lines)


def build_solution_block(request: VideoRequest) -> str:
    state = request.solution_state
    if state == STATE_VERIFIED:
        return SOLUTION_VERIFIED
    if state == STATE_UNVERIFIED:
        return SOLUTION_UNVERIFIED
    if request.request_kind == REQUEST_KIND_LEETCODE:
        return SOLUTION_MISSING_LEETCODE
    return SOLUTION_MISSING_ALGORITHM


def build_problem_block(request: VideoRequest) -> str:
    if request.request_kind == REQUEST_KIND_LEETCODE:
        return PROBLEM_LEETCODE
    return PROBLEM_ALGORITHM


def build_latex_block(env_info: EnvInfo) -> str:
    return LATEX_AVAILABLE if env_info.latex_available else LATEX_MISSING


def build_prompt_template() -> str:
    return _read(SYSTEM_PROMPT_PATH, "system prompt template")


def _fill(template: str, values: dict[str, str], label: str) -> str:
    """One substitution pass; inserted values are never re-scanned."""
    unknown: list[str] = []

    def _sub(match: re.Match[str]) -> str:
        key = match.group(1)
        if key not in values:
            unknown.append(key)
            return match.group(0)
        return values[key]

    filled = _PLACEHOLDER_RE.sub(_sub, template)
    if unknown:
        raise ConfigError(
            f"Unknown placeholder(s) in {label}: " + ", ".join(sorted(set(unknown)))
        )
    return filled


def build_fixer_prompt(
    script: str,
    scene_class: str,
    error_tail: str,
    env_info: EnvInfo,
) -> str:
    """Prompt asking the LLM to repair a script whose scene failed to render."""
    template = _read(FIXER_PROMPT_PATH, "fixer prompt template")
    return _fill(
        template,
        {
            "manim_version": env_info.manim_version,
            "latex_block": build_latex_block(env_info),
            "scene_class": scene_class,
            "error_tail": error_tail,
            "script": script,
        },
        "fixer_prompt.txt",
    )


def build_prompt(request: VideoRequest, env_info: EnvInfo) -> str:
    """Fill system_prompt.txt in exactly one substitution pass."""
    template = _read(SYSTEM_PROMPT_PATH, "system prompt template")
    recipes = _read(DIAGRAM_RECIPES_PATH, "diagram recipes")
    kit_reference = _read(KIT_REFERENCE_PATH, "visual kit reference")

    style_name, style_text = get_style(request.preferences_or_default.explanation_style)

    values: dict[str, str] = {
        "manim_version": env_info.manim_version,
        "kit_reference": kit_reference,
        "latex_block": build_latex_block(env_info),
        "request_kind": request.request_kind,
        "input_block": build_input_block(request),
        "programming_language": request.programming_language,
        "explanation_language": request.preferences_or_default.language,
        "style_name": style_name,
        "style_text": style_text,
        "solution_block": build_solution_block(request),
        "problem_block": build_problem_block(request),
        "diagram_recipes": recipes,
    }

    return _fill(template, values, "system_prompt.txt")
