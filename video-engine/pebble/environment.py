"""Cached environment detection. Every probe must be failure-tolerant."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from functools import lru_cache

CODE_FONTS = ("Menlo", "Consolas", "DejaVu Sans Mono", "Courier New", "Monospace")


@dataclass(frozen=True)
class EnvInfo:
    manim_version: str = "unknown"
    latex_available: bool = False
    ffmpeg_available: bool = False
    ffprobe_available: bool = False
    code_font: str = "Courier New"
    errors: list[str] = field(default_factory=list)

    @property
    def manim_available(self) -> bool:
        return self.manim_version != "unknown"


def _manim_version() -> tuple[str, bool]:
    try:
        import manim  # noqa: F401

        return str(getattr(manim, "__version__", "unknown")), True
    except Exception as exc:  # pragma: no cover - import failure is not fatal
        return f"unknown ({type(exc).__name__})", False


def _latex_available() -> bool:
    return shutil.which("latex") is not None and shutil.which("dvisvgm") is not None


def _which(name: str) -> bool:
    return shutil.which(name) is not None


def _code_font() -> str:
    try:
        import manimpango

        fonts = {str(f) for f in manimpango.list_fonts()}
    except Exception:
        fonts = set()
    for candidate in CODE_FONTS:
        if candidate in fonts:
            return candidate
    return "Courier New"


@lru_cache(maxsize=1)
def detect() -> EnvInfo:
    """Detect the toolchain once per process; never raises."""
    errors: list[str] = []
    version, manim_ok = _manim_version()
    if not manim_ok:
        errors.append(f"manim import failed: {version}")
    if not _latex_available():
        errors.append("LaTeX unavailable (latex and/or dvisvgm not on PATH)")
    if not _which("ffmpeg"):
        errors.append("ffmpeg not on PATH")
    if not _which("ffprobe"):
        errors.append("ffprobe not on PATH")
    return EnvInfo(
        manim_version=version,
        latex_available=_latex_available(),
        ffmpeg_available=_which("ffmpeg"),
        ffprobe_available=_which("ffprobe"),
        code_font=_code_font(),
        errors=errors,
    )
