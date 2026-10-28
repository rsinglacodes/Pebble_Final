"""Explanation styles shared by the prompt builder and the CLI."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

BEGINNER_FRIENDLY = "beginner_friendly"

STYLES: dict[str, str] = {
    "beginner_friendly": (
        "Assume the viewer is new to the topic. Start with the intuition in everyday "
        "words, define every term when it first appears, go through the example one "
        "step at a time and say why each step happens. Use 9-12 scenes, about 3-5 "
        "minutes total."
    ),
    "interview_focused": (
        "Assume the viewer is preparing for coding interviews. Briefly state the brute "
        "force and why it is slow, then the optimal idea, trace it once on an example, "
        "call out edge cases, and end with time/space trade-offs and what to say in an "
        "interview. Use 7-10 scenes, about 3-4 minutes total."
    ),
    "detailed": (
        "Deep dive: intuition, why it is correct, two examples including an edge case, "
        "a line-by-line code walkthrough, complexity derivation, common mistakes. Use "
        "10-14 scenes, about 5-7 minutes total."
    ),
    "concise": (
        "Quick recap for someone who knows the basics: the problem in one sentence, "
        "the key idea, one fast trace, the code, the complexity. Use 5-7 scenes, about "
        "1.5-2 minutes total."
    ),
}

DEFAULT_STYLE = BEGINNER_FRIENDLY


def supported_styles() -> list[str]:
    """Canonical style names, in the order they are documented."""
    return list(STYLES)


def is_supported_style(name: str | None) -> bool:
    """True when the style is one of the known styles (case-insensitive)."""
    return (name or "").strip().lower() in STYLES


def get_style(name: str | None) -> tuple[str, str]:
    """Return (canonical_name, style_text); unknown names fall back with a warning."""
    key = (name or "").strip().lower()
    if key in STYLES:
        return key, STYLES[key]
    logger.warning(
        "Unknown explanation style %r; falling back to %r", name, DEFAULT_STYLE
    )
    return DEFAULT_STYLE, STYLES[DEFAULT_STYLE]
