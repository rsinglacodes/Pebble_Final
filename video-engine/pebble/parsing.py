"""Parse the LLM response into a GenerationResult."""

from __future__ import annotations

import json
import re

from pebble.errors import ParseError
from pebble.models import GenerationMeta, GenerationResult

META_RE = re.compile(r"<pebble_meta>\s*(.*?)\s*</pebble_meta>", re.DOTALL)
SOLUTION_RE = re.compile(r"<solution_code>\s*(.*?)\s*</solution_code>", re.DOTALL)
MANIM_RE = re.compile(r"<manim_code>\s*(.*?)\s*</manim_code>", re.DOTALL)


def _strip_fences(text: str) -> str:
    """Remove markdown code fences wrapping a code section."""
    lines = text.strip().split("\n")
    if lines and lines[0].strip().startswith("```"):
        lines = lines[1:]
    if lines and lines[-1].strip() == "```":
        lines = lines[:-1]
    cleaned = "\n".join(lines).strip()
    if cleaned.startswith("```"):  # single-line fence: ```python ... ```
        cleaned = re.sub(r"^```[A-Za-z0-9_+.-]*\s*", "", cleaned)
        if cleaned.endswith("```"):
            cleaned = cleaned[:-3]
    return cleaned.strip()


_NEXT_SECTION_RE = re.compile(r"<(pebble_meta|solution_code|manim_code)>")


def _section_body(text: str, label: str, pattern: re.Pattern[str]) -> str | None:
    """Body of one tagged section, or None when the section is absent.

    Models sometimes stop right after the last line of the final section and
    never emit its closing tag (observed with the code section). Since that
    section is last, everything after the opening tag is the body: take it up to
    the next tagged section, or to the end of the response.
    """
    match = pattern.search(text)
    if match:
        return match.group(1).strip()

    opener = re.search(rf"<{label}>", text)
    if not opener:
        return None
    rest = text[opener.end() :]
    following = _NEXT_SECTION_RE.search(rest)
    if following:
        rest = rest[: following.start()]
    return rest.strip()


def _extract(pattern: re.Pattern[str], text: str, label: str) -> str:
    body = _section_body(text, label, pattern)
    if body is None:
        raise ParseError(f"Missing <{label}> section in the LLM response", missing=[label])
    return body


def _balanced_object(text: str, start: int) -> str | None:
    """Return the {...} slice beginning at `start`, honouring strings/escapes."""
    depth = 0
    in_string = False
    escaped = False
    for index in range(start, len(text)):
        char = text[index]
        if in_string:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            continue
        if char == '"':
            in_string = True
        elif char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return text[start : index + 1]
    return None


def _first_meta_object(text: str) -> str | None:
    """Fallback: first {...} block that looks like the meta object."""
    search_from = 0
    while True:
        start = text.find("{", search_from)
        if start == -1:
            return None
        blob = _balanced_object(text, start)
        if blob is None:
            return None
        search_from = start + 1
        try:
            data = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and set(data) & set(REQUIRED_META_KEYS):
            return blob


REQUIRED_META_KEYS = (
    "problem_summary",
    "solution_source",
    "programming_language",
    "complexity",
    "validation",
    "scenes",
)


def parse_response(text: str) -> GenerationResult:
    if not (text or "").strip():
        raise ParseError("Empty LLM response", missing=["pebble_meta", "solution_code", "manim_code"])

    match = META_RE.search(text)
    raw_meta: str | None = match.group(1).strip() if match else None
    if raw_meta is None:
        raw_meta = _first_meta_object(text)

    missing: list[str] = []
    if raw_meta is None:
        missing.append("pebble_meta")
    for label, pattern in (
        ("solution_code", SOLUTION_RE),
        ("manim_code", MANIM_RE),
    ):
        if _section_body(text, label, pattern) is None:
            missing.append(label)
    if missing:
        raise ParseError(
            "Missing section(s) in the LLM response: " + ", ".join(missing), missing=missing
        )

    assert raw_meta is not None
    try:
        data = json.loads(raw_meta)
    except json.JSONDecodeError as exc:
        raise ParseError(
            f"Invalid JSON in <pebble_meta>: {exc.msg} at line {exc.lineno} column {exc.colno}",
            missing=["pebble_meta"],
        ) from exc
    if not isinstance(data, dict):
        raise ParseError("<pebble_meta> must contain a JSON object", missing=["pebble_meta"])

    try:
        meta = GenerationMeta.model_validate(data)
    except Exception as exc:  # pydantic ValidationError
        raise ParseError(f"Invalid <pebble_meta> content: {exc}", missing=["pebble_meta"]) from exc

    # An empty (but present) section is left for validate_generation to report,
    # so rule 8 (solution_code non-empty) has a single owner.
    solution_code = _strip_fences(_extract(SOLUTION_RE, text, "solution_code"))
    manim_code = _strip_fences(_extract(MANIM_RE, text, "manim_code"))

    return GenerationResult(meta=meta, solution_code=solution_code, manim_code=manim_code)
