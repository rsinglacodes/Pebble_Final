"""Typed request/response models.

The input payload is deliberately tolerated: teammates send the documented
shape, but ids/slug/code/language may be null or empty and extra fields are
ignored.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import BaseModel, ConfigDict

from pebble.config import PIPELINE_VERSION

DEFAULT_LANGUAGE = "python"
DEFAULT_EXPLANATION_LANGUAGE = "English"
DEFAULT_STYLE = "beginner_friendly"

REQUEST_KIND_LEETCODE = "leetcode_problem"
REQUEST_KIND_ALGORITHM = "algorithm"

STATE_MISSING = "missing"
STATE_VERIFIED = "verified"
STATE_UNVERIFIED = "unverified"


def _present(value: Any) -> bool:
    """True when a value is non-empty after string stripping (0 is non-empty)."""
    if value is None:
        return False
    if isinstance(value, str):
        return value.strip() != ""
    return str(value).strip() != ""


def normalize_code(code: Any) -> str:
    """Canonical form of solution code: CRLF->LF, per-line rstrip, outer strip."""
    if code is None:
        return ""
    text = str(code).replace("\r\n", "\n").replace("\r", "\n")
    return "\n".join(line.rstrip() for line in text.split("\n")).strip()


class Question(BaseModel):
    model_config = ConfigDict(extra="ignore")

    id: Any = None
    slug: str | None = None
    title: str | None = None

    @property
    def has_identity(self) -> bool:
        return _present(self.id) or _present(self.slug)


class Solution(BaseModel):
    model_config = ConfigDict(extra="ignore")

    code: str | None = None
    programming_language: str | None = None
    validated: bool | None = None

    @property
    def normalized_code(self) -> str:
        return normalize_code(self.code)

    @property
    def language(self) -> str:
        lang = (self.programming_language or "").strip().lower()
        return lang or DEFAULT_LANGUAGE


class Preferences(BaseModel):
    model_config = ConfigDict(extra="ignore")

    explanation_language: str = DEFAULT_EXPLANATION_LANGUAGE
    explanation_style: str = DEFAULT_STYLE

    @property
    def language(self) -> str:
        return (self.explanation_language or "").strip() or DEFAULT_EXPLANATION_LANGUAGE


class VideoRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    question: Question | None = None
    solution: Solution | None = None
    preferences: Preferences | None = None

    # --- derived values -------------------------------------------------
    @property
    def question_or_empty(self) -> Question:
        return self.question if self.question is not None else Question()

    @property
    def preferences_or_default(self) -> Preferences:
        return self.preferences if self.preferences is not None else Preferences()

    @property
    def request_kind(self) -> str:
        return REQUEST_KIND_LEETCODE if self.question_or_empty.has_identity else REQUEST_KIND_ALGORITHM

    @property
    def solution_state(self) -> str:
        if self.solution is None or not _present(normalize_code(self.solution.code)):
            return STATE_MISSING
        if self.solution.validated is True:
            return STATE_VERIFIED
        return STATE_UNVERIFIED

    @property
    def title(self) -> str:
        return (self.question_or_empty.title or "").strip()

    @property
    def solution_code(self) -> str:
        if self.solution is None:
            return ""
        return self.solution.normalized_code

    @property
    def raw_solution_code(self) -> str:
        """The original code verbatim (used for byte-for-byte restoration)."""
        if self.solution is None or self.solution.code is None:
            return ""
        return self.solution.code

    @property
    def programming_language(self) -> str:
        if self.solution is None:
            return DEFAULT_LANGUAGE
        return self.solution.language

    def request_fingerprint(self) -> str:
        """Stable sha256 cache key over the values that define the work."""
        parts = [
            PIPELINE_VERSION,
            self.request_kind,
            str(self.question_or_empty.id) if _present(self.question_or_empty.id) else "",
            (self.question_or_empty.slug or "").strip(),
            self.title,
            self.solution_code,
            self.programming_language,
            self.preferences_or_default.language,
            self.preferences_or_default.explanation_style or DEFAULT_STYLE,
        ]
        payload = json.dumps(parts, ensure_ascii=False, separators=(",", ":"))
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------
# Generation output
# --------------------------------------------------------------------------


class Example(BaseModel):
    model_config = ConfigDict(extra="ignore")

    input: str = ""
    output: str = ""


class Validation(BaseModel):
    model_config = ConfigDict(extra="ignore")

    performed: bool | None = None
    is_correct: bool | None = None
    issues: list[str] = []
    notes: str = ""


class Complexity(BaseModel):
    model_config = ConfigDict(extra="ignore")

    time: str = ""
    space: str = ""


class SceneMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")

    scene_id: int = 0
    class_name: str = ""
    title: str = ""
    narration: str = ""


class GenerationMeta(BaseModel):
    model_config = ConfigDict(extra="ignore")

    problem_summary: str = ""
    example: Example = Example()
    validation: Validation = Validation()
    solution_source: str = ""
    programming_language: str = ""
    complexity: Complexity = Complexity()
    scenes: list[SceneMeta] = []

    def field_present(self, name: str) -> bool:
        return name in self.model_fields_set

    def nested_field_present(self, parent: str, name: str) -> bool:
        child = getattr(self, parent, None)
        if child is None:
            return False
        fields = getattr(child, "model_fields_set", None)
        return fields is not None and name in fields


class GenerationResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    meta: GenerationMeta = GenerationMeta()
    solution_code: str = ""
    manim_code: str = ""
    style_name: str = DEFAULT_STYLE
    # Soft validation problems accepted on the best attempt (never fatal).
    generation_warnings: list[str] = []

    @property
    def scenes(self) -> list[SceneMeta]:
        return self.meta.scenes
