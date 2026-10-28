"""Pebble exception hierarchy."""

from __future__ import annotations


class PebbleError(Exception):
    """Base class for every error raised by Pebble."""


class ConfigError(PebbleError):
    """Missing or invalid configuration (usually .env)."""


class ParseError(PebbleError):
    """The LLM response could not be parsed into the required sections."""

    def __init__(self, message: str, missing: list[str] | None = None) -> None:
        super().__init__(message)
        self.missing = missing or []


class TruncatedOutputError(PebbleError):
    """The LLM response was cut off by the token limit (finish_reason == 'length')."""


class GenerationError(PebbleError):
    """Every generation attempt failed; carries all problems from the last attempt."""

    def __init__(self, message: str, problems: list[str] | None = None) -> None:
        super().__init__(message)
        self.problems = problems or []


class RenderError(PebbleError):
    """A Manim scene could not be rendered, even after the repair loop."""

    def __init__(
        self,
        message: str,
        scene_class: str | None = None,
        error_tail: str = "",
    ) -> None:
        super().__init__(message)
        self.scene_class = scene_class
        self.error_tail = error_tail


class TTSError(PebbleError):
    """Azure Speech synthesis failed."""


class MuxError(PebbleError):
    """ffmpeg muxing or stitching failed."""


class PebbleLayoutError(PebbleError):
    """The layout audit found overlapping or off-frame content in a scene."""

    def __init__(self, message: str, issues: list[str] | None = None) -> None:
        super().__init__(message)
        self.issues = issues or []
