"""Pipeline-provided helper for generated Manim scripts.

This file is copied into the job workspace as ``pebble_helpers.py`` and is
imported on the *same first line* of ``animation_render.py`` as the generated
script, so tracebacks keep the same line numbers as ``animation.py``.

The only public API is :func:`finish_scene`. A generated scene calls it as its
final statement; it holds the finished picture on screen until the narration for
that scene ends (duration read from ``pebble_targets.json``) and then fades
everything out. Scenes without a target entry simply fade out.
"""

from __future__ import annotations

import json
from pathlib import Path

from manim import *  # noqa: F401,F403  (the generated script relies on this)

__all__ = ["finish_scene"]

TARGETS_FILE = "pebble_targets.json"
FADE_OUT_TIME = 0.6
MIN_PAD = 0.05

_targets_cache: dict[str, float] | None = None


def load_targets() -> dict[str, float]:
    """Scene class name -> target on-screen seconds, read once per process."""
    global _targets_cache
    if _targets_cache is None:
        targets: dict[str, float] = {}
        path = Path(TARGETS_FILE)
        if path.exists():
            try:
                raw = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                raw = {}
            if isinstance(raw, dict):
                for key, value in raw.items():
                    try:
                        targets[str(key)] = float(value)
                    except (TypeError, ValueError):
                        continue
        _targets_cache = targets
    return _targets_cache


def scene_time(scene) -> float:
    """Seconds of animation already played in this scene."""
    renderer = getattr(scene, "renderer", None)
    value = getattr(renderer, "time", None) if renderer is not None else None
    if value is None:
        value = getattr(scene, "time", 0.0)
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _audit(scene):
    """Run the kit's layout audit on the finished frame (no-op without the kit)."""
    try:
        import pebble_kit
    except Exception:
        return []
    audit = getattr(pebble_kit, "audit_scene", None)
    if audit is None:
        return []
    return audit(scene)


def finish_scene(scene, fade_time: float = FADE_OUT_TIME) -> None:
    """Hold the picture until the narration ends, then fade everything out."""
    # Audit the final picture before the long hold: a broken frame then costs
    # one short render instead of a full narration-length one.
    _audit(scene)
    target = load_targets().get(type(scene).__name__)
    if target is not None:
        remaining = target - scene_time(scene) - fade_time
        if remaining > MIN_PAD:
            scene.wait(remaining)
    if getattr(scene, "mobjects", None):
        scene.play(*[FadeOut(mob) for mob in scene.mobjects], run_time=fade_time)
