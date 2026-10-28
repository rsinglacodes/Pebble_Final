"""Pebble visual kit: the pre-built, tested visual vocabulary for generated videos.

The kit is copied into every job workspace as ``pebble_kit.py`` and imported on
the same first line as the generated script::

    from pebble_kit import *; from pebble_helpers import finish_scene;

Generated scripts choreograph these components; they never hand-place shapes or
draw source code. Everything here is sized for a 14.2 x 8 frame and uses one
colour language: amber = looking at it now, green = found/done, red = wrong,
blue-grey = ordinary, faded = finished.

Public API: see ``pebble/prompts/kit_reference.txt`` (the contract).
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path

from manim import *  # noqa: F401,F403

__all__ = [
    # theme constants
    "STAGE",
    "LEFT_LANE",
    "RIGHT_LANE",
    "T_FAST",
    "T_STEP",
    "T_SLOW",
    "C_TEXT",
    "C_MUTED",
    "C_ACCENT",
    "C_ACTIVE",
    "C_GOOD",
    "C_BAD",
    "C_BG",
    "C_PANEL",
    "STATE_STYLES",
    # scene helpers
    "show_title",
    "title_card",
    "set_caption",
    "show_legend",
    "step_tag",
    "result_cards",
    "compare_panels",
    # structures
    "ArrayViz",
    "Pointer",
    "MapViz",
    "StackViz",
    "QueueViz",
    "LinkedListViz",
    "TreeViz",
    "GraphViz",
    "GridViz",
    "BarsViz",
    "HeapViz",
    "StatePanel",
    # audit
    "audit_scene",
    "PebbleLayoutError",
]

# ---------------------------------------------------------------------------
# theme
# ---------------------------------------------------------------------------

C_BG = "#0F172A"  # calm dark navy, never pure black
C_PANEL = "#1E293B"
C_TEXT = "#E2E8F0"
C_MUTED = "#94A3B8"
C_ACCENT = "#60A5FA"
C_ACTIVE = "#FBBF24"
C_GOOD = "#34D399"
C_BAD = "#F87171"

PANEL_EDGE = "#334155"
DIM_EDGE = "#64748B"

# Each state: fill colour, stroke colour, fill opacity, stroke width.
STATE_STYLES = {
    "default": {"fill": C_PANEL, "stroke": DIM_EDGE, "fill_opacity": 0.95, "stroke_width": 2.6},
    "active": {"fill": "#78350F", "stroke": C_ACTIVE, "fill_opacity": 0.95, "stroke_width": 3.2},
    "good": {"fill": "#064E3B", "stroke": C_GOOD, "fill_opacity": 0.95, "stroke_width": 3.2},
    "bad": {"fill": "#7F1D1D", "stroke": C_BAD, "fill_opacity": 0.95, "stroke_width": 3.2},
    "dim": {"fill": C_PANEL, "stroke": DIM_EDGE, "fill_opacity": 0.4, "stroke_width": 1.8},
}

STAGE = DOWN * 0.15
LEFT_LANE = LEFT * 3.45 + DOWN * 0.15
RIGHT_LANE = RIGHT * 3.45 + DOWN * 0.15

T_FAST = 0.4
T_STEP = 0.7
T_SLOW = 1.1

SAFE_WIDTH = 12.6
SAFE_HEIGHT = 7.6

config.background_color = C_BG


def _pick_font() -> str | None:
    """First installed UI font from a curated list (None: keep Manim's default)."""
    try:
        import manimpango

        fonts = {str(name) for name in manimpango.list_fonts()}
    except Exception:
        fonts = set()
    for candidate in (
        "Inter",
        "SF Pro Display",
        "Helvetica Neue",
        "Avenir Next",
        "Segoe UI",
        "Arial",
        "DejaVu Sans",
    ):
        if candidate in fonts:
            return candidate
    return None


UI_FONT = _pick_font()
if UI_FONT:
    Text.set_default(font=UI_FONT)


class PebbleLayoutError(RuntimeError):
    """Raised by the layout audit in strict mode when the frame is broken."""


# ---------------------------------------------------------------------------
# small internals
# ---------------------------------------------------------------------------

def _text(value, size=26, color=C_TEXT, weight=NORMAL, line_spacing=None) -> Text:
    # Text always draws above the shapes it sits on. Manim re-adds a mobject to
    # the scene whenever it is animated on its own (chip background, cell, row),
    # which would otherwise paint that shape over its own label.
    kwargs = {}
    if line_spacing is not None:
        kwargs["line_spacing"] = line_spacing
    mob = Text(str(value), font_size=size, color=color, weight=weight, **kwargs)
    mob.set_z_index(2)
    return mob


_NULL_WORDS = {"", "none", "null", "nil", "nan", "n/a", "undefined", "unknown?"}


def _chip_label(name, value) -> str:
    """``need = 7``; an unknown value reads as ``need = ?`` instead of a blank."""
    shown = "?" if str(value).strip().lower() in _NULL_WORDS else value
    return f"{name} = {shown}"


def _style(state: str) -> dict:
    try:
        return STATE_STYLES[state]
    except KeyError:
        raise ValueError(
            f"unknown state {state!r}; use one of {sorted(STATE_STYLES)}"
        ) from None


def _check_index(index, length: int, label: str = "index") -> int:
    if not isinstance(index, int) or index < 0 or index >= length:
        raise ValueError(
            f"{label} {index!r} is out of range for this structure "
            f"(valid: 0..{length - 1})"
        )
    return index


def _state_anim(mob, state: str):
    """Animation that repaints a mobject in the given state's colours."""
    style = _style(state)
    return mob.animate.set_stroke(
        color=style["stroke"], width=style["stroke_width"]
    ).set_fill(color=style["fill"], opacity=style["fill_opacity"])


def _state_anims(mobs, state: str):
    style = _style(state)
    return [
        mob.animate.set_stroke(
            color=style["stroke"], width=style["stroke_width"]
        ).set_fill(color=style["fill"], opacity=style["fill_opacity"])
        for mob in mobs
    ]


def _become(old, new):
    """Rewrite a text in place.

    Swapping the mobject instead of mutating it leaves the old copy on screen:
    Manim adds a mobject to the scene whenever an animation targets it alone, so
    a label that was once animated stays visible after being removed from its
    group.
    """
    label = getattr(new, "original_text", None)
    try:
        old.become(new)
    except Exception:  # pragma: no cover - geometry fallback
        old.set_points(new.points)
    if label is not None:
        old.original_text = label
    old.set_z_index(2)
    return old


def _fit(mob, max_width=None, max_height=None):
    if max_width and mob.width > max_width:
        mob.scale_to_fit_width(max_width)
    if max_height and mob.height > max_height:
        mob.scale_to_fit_height(max_height)
    return mob


# The visible frame (Manim default 16:9) and the margin kept clear of its edge.
FRAME_HALF_W = 7.11
FRAME_HALF_H = 4.0
EDGE_MARGIN = 0.32

# A structure placed beside another one gets this width; centred structures get
# the full stage width.
LANE_X = 1.6
LANE_WIDTH = 5.2
STAGE_WIDTH = 8.6


def _width_for(at, default: float | None) -> float | None:
    """Narrow the default width when the structure sits in a side lane."""
    if default is None:
        return None
    try:
        x = abs(float(at[0]))
    except Exception:
        return default
    if x > LANE_X:
        return min(default, LANE_WIDTH)
    return default


def _clamp_into_frame(mob, margin: float = EDGE_MARGIN):
    """Shift a finished structure so no part of it is clipped by the frame."""
    dx = 0.0
    dy = 0.0
    left, right = mob.get_left()[0], mob.get_right()[0]
    bottom, top = mob.get_bottom()[1], mob.get_top()[1]
    if left < -FRAME_HALF_W + margin:
        dx = -FRAME_HALF_W + margin - left
    elif right > FRAME_HALF_W - margin:
        dx = FRAME_HALF_W - margin - right
    if bottom < -FRAME_HALF_H + margin:
        dy = -FRAME_HALF_H + margin - bottom
    elif top > FRAME_HALF_H - margin:
        dy = FRAME_HALF_H - margin - top
    if dx or dy:
        mob.shift(np.array([dx, dy, 0.0]))
    return mob


def _settle(mob, at, max_width=None, max_height=None):
    """Fit, place at ``at`` and keep the result inside the visible frame."""
    _fit(mob, _width_for(at, max_width), max_height)
    if at is not None:
        mob.move_to(at)
    return _clamp_into_frame(mob)


def _panel(width, height, state="default", corner=0.18) -> RoundedRectangle:
    style = _style(state)
    return RoundedRectangle(
        corner_radius=corner,
        width=width,
        height=height,
        fill_color=style["fill"],
        fill_opacity=style["fill_opacity"],
        stroke_color=style["stroke"],
        stroke_width=style["stroke_width"],
    )


# Every kit structure registers itself so the audit can tell "one structure"
# from "two elements stacked on top of each other".
_STRUCTURES: list = []

# Chrome (titles, captions, headings) that no structure may cover.
_RESERVED: list = []


def _reserve(*mobjects) -> None:
    _RESERVED.extend(mobjects)


# Token -> structure, for readable audit messages. Tokens (plain ints) are used
# instead of object references because Manim copies mobjects with deepcopy:
# a copied mobject must keep pointing at the same *structure*, not at a copy.
_OWNER_TOKENS: dict[int, object] = {}


def _owner_token(owner) -> int:
    token = getattr(owner, "_pebble_token", None)
    if token is None:
        token = len(_OWNER_TOKENS) + 1
        try:
            owner._pebble_token = token
        except Exception:
            pass
        _OWNER_TOKENS[token] = owner
    return token


def _stamp(mob, owner) -> None:
    """Record which structure a mobject belongs to (survives Manim bookkeeping)."""
    token = _owner_token(owner)

    def _apply(item):
        try:
            item._pebble_token = token
        except Exception:
            pass
        for child in getattr(item, "submobjects", []):
            _apply(child)

    _apply(mob)


class _IntroMixin:
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        _STRUCTURES.append(self)
        _stamp(self, self)

    def add(self, *mobjects, **kwargs):
        for mob in mobjects:
            # A structure built *inside* another one (a heap is a tree plus an
            # array) is part of its parent, not a second element on the stage.
            if isinstance(mob, _IntroMixin) and mob is not self:
                mob._pebble_nested = True
            _stamp(mob, self)
        return super().add(*mobjects, **kwargs)

    def intro(self, *args, fast: bool = False, at=None):
        """Fade the structure in; ``fast=True`` for a structure seen before.

        ``at=`` (and a stray positional position) is accepted so a script that
        writes ``ArrayViz(...).intro(LEFT_LANE)`` still land in the right lane.
        """
        position = at
        for arg in args:
            if isinstance(arg, bool):
                fast = fast or arg
            elif position is None:
                position = arg
        if position is not None:
            try:
                limit = _width_for(position, self.width)
                if limit is not None and self.width > limit:
                    self.scale_to_fit_width(limit)
                self.move_to(position)
                _clamp_into_frame(self)
            except Exception:
                pass
        _stamp(self, self)
        return FadeIn(self, shift=DOWN * 0.12, run_time=0.3 if fast else 0.65)


# ---------------------------------------------------------------------------
# pointer (under an array cell / list node)
# ---------------------------------------------------------------------------

POINTER_LEVEL_GAP = 0.52


class Pointer:
    """A short, upright marker under one cell, with its name below it."""

    def __init__(self, owner, name: str, index: int, state: str = "active", level: int = 0):
        self.owner = owner
        self.name = name
        self.level = level
        self.index = index
        style = _style(state)
        head = Triangle(fill_color=style["stroke"], fill_opacity=1, stroke_width=0)
        head.scale(0.15)
        head.rotate(PI)
        label = _text(name, size=22, color=style["stroke"])
        self.mob = VGroup(head, label)
        self.head = head
        self.label = label
        self.mob.arrange(DOWN, buff=0.06)
        owner.add(self.mob)
        self.mob.move_to(self._target(index))
        owner.store.setdefault("pointers", {})[name] = self

    def _target(self, index: int):
        cell = self.owner.cells[index]
        base_y = cell.get_bottom()[1] - 0.78 - self.level * POINTER_LEVEL_GAP
        return np.array([cell.get_center()[0], base_y, 0.0])

    def intro(self):
        return FadeIn(self.mob, shift=UP * 0.1, run_time=T_FAST)

    def to(self, index: int):
        _check_index(index, len(self.owner.cells), "cell index")
        self.index = index
        return AnimationGroup(
            self.mob.animate.move_to(self._target(index)), run_time=T_STEP
        )

    def hide(self):
        return FadeOut(self.mob, run_time=T_FAST)


# ---------------------------------------------------------------------------
# ArrayViz
# ---------------------------------------------------------------------------

class ArrayViz(_IntroMixin, VGroup):
    """A row of large numbered cells with optional index labels and pointers."""

    def __init__(
        self,
        values,
        label: str | None = None,
        show_index: bool = True,
        at=STAGE,
        max_width: float | None = 8.6,
        max_height: float | None = 2.6,
        cell: float | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.values = list(values)
        if not self.values:
            raise ValueError("ArrayViz needs at least one value")
        self.show_index = show_index
        self.store: dict = {}
        self.cells: list[RoundedRectangle] = []
        self.value_texts: list[Text] = []
        self.index_labels: list[Text] = []

        count = len(self.values)
        if cell is None:
            target = 8.4 if max_width is None else max(2.4, max_width)
            cell = min(1.7, max(0.62, (target - (count - 1) * 0.12) / count))
        for position, value in enumerate(self.values):
            style = _style("default")
            rect = RoundedRectangle(
                corner_radius=0.12,
                width=cell,
                height=cell,
                fill_color=style["fill"],
                fill_opacity=style["fill_opacity"],
                stroke_color=style["stroke"],
                stroke_width=style["stroke_width"],
            )
            self.cells.append(rect)

        self.row = VGroup(*self.cells)
        self.row.arrange(RIGHT, buff=0.12)

        for rect, value in zip(self.cells, self.values):
            text = _text(value, size=32)
            text.move_to(rect.get_center())
            self.value_texts.append(text)

        body = VGroup(self.row, *self.value_texts)

        if show_index:
            for position, rect in enumerate(self.cells):
                index_label = _text(position, size=20, color=C_MUTED)
                index_label.move_to(
                    np.array([rect.get_center()[0], rect.get_bottom()[1] - 0.3, 0.0])
                )
                self.index_labels.append(index_label)
            body.add(*self.index_labels)

        self.add(body)
        self.body = body

        self.header = None
        if label:
            self.header = _text(label, size=24, color=C_MUTED)
            self.header.next_to(self.row, UP, buff=0.22)
            self.add(self.header)

        _settle(self, at, max_width, max_height)

    # -- values ---------------------------------------------------------
    def _repaint_value(self, index: int, value) -> Text:
        old = self.value_texts[index]
        new = _text(value, size=32).move_to(old.get_center())
        self.value_texts[index] = new
        self.values[index] = value
        return new

    def set_state(self, index_or_list, state: str):
        style = _style(state)
        indices = (
            list(index_or_list)
            if isinstance(index_or_list, (list, tuple, set))
            else [index_or_list]
        )
        anims = []
        for index in indices:
            _check_index(index, len(self.cells), "cell index")
            anims.extend(_state_anims([self.cells[index]], state))
        if len(anims) == 1:
            return anims[0]
        return AnimationGroup(*anims, lag_ratio=0)

    def set_all(self, state: str):
        _style(state)
        anims = _state_anims(self.cells, state)
        return AnimationGroup(*anims, lag_ratio=0)

    def set_value(self, index: int, value):
        _check_index(index, len(self.cells), "cell index")
        old = self.value_texts[index]
        # Apply immediately: a forgotten self.play must still show the right
        # value. The returned animation is only the visual beat.
        new = _become(old, _text(value, size=32).move_to(old.get_center()))
        self.value_texts[index] = new
        self.values[index] = value
        return Indicate(new, color=C_TEXT, scale_factor=1.06)

    def swap(self, i: int, j: int):
        _check_index(i, len(self.cells))
        _check_index(j, len(self.cells))
        left, right = self.value_texts[i], self.value_texts[j]
        new_left = _become(left, _text(self.values[j], size=32).move_to(left.get_center()))
        new_right = _become(right, _text(self.values[i], size=32).move_to(right.get_center()))
        self.values[i], self.values[j] = self.values[j], self.values[i]
        self.value_texts[i], self.value_texts[j] = new_left, new_right
        return AnimationGroup(
            Indicate(new_left, color=C_TEXT, scale_factor=1.08),
            Indicate(new_right, color=C_TEXT, scale_factor=1.08),
            lag_ratio=0,
        )

    # -- pointers -------------------------------------------------------
    def pointer(self, name: str, index: int, state: str = "active", level: int = 0) -> Pointer:
        _check_index(index, len(self.cells), "cell index")
        return Pointer(self, name, index, state, level)

    # -- window ---------------------------------------------------------
    def window(self, left: int, right: int, state: str = "active"):
        _check_index(left, len(self.cells), "window start")
        _check_index(right, len(self.cells), "window end")
        style = _style(state)
        group = VGroup(*self.cells[left : right + 1])
        win = SurroundingRectangle(
            group,
            buff=0.08,
            color=style["stroke"],
            stroke_width=style["stroke_width"],
            corner_radius=0.1,
        )
        self.store["window"] = win
        self.add(win)
        return win

    def move_window(self, win, left: int, right: int):
        _check_index(left, len(self.cells), "window start")
        _check_index(right, len(self.cells), "window end")
        group = VGroup(*self.cells[left : right + 1])
        first, last = self.cells[left], self.cells[right]
        width = last.get_right()[0] - first.get_left()[0] + 0.16
        center = np.array(
            [
                (first.get_center()[0] + last.get_center()[0]) / 2,
                first.get_center()[1],
                0.0,
            ]
        )
        return AnimationGroup(
            win.animate.stretch_to_fit_width(width).move_to(center), run_time=T_STEP
        )


# ---------------------------------------------------------------------------
# layout audit
# ---------------------------------------------------------------------------

def _iter_texts(mob):
    if isinstance(mob, Text):
        yield mob
        return
    for child in getattr(mob, "submobjects", []):
        yield from _iter_texts(child)


def _box(mob):
    left = mob.get_left()[0]
    right = mob.get_right()[0]
    bottom = mob.get_bottom()[1]
    top = mob.get_top()[1]
    return left, right, bottom, top


def _overlap_area(a, b) -> float:
    width = min(a[1], b[1]) - max(a[0], b[0])
    height = min(a[3], b[3]) - max(a[2], b[2])
    if width <= 0 or height <= 0:
        return 0.0
    return width * height


def _all_ids(mob) -> set[int]:
    ids = {id(mob)}
    for child in getattr(mob, "submobjects", []):
        ids |= _all_ids(child)
    return ids


def _is_visible(mob, visible_ids: set[int]) -> bool:
    if id(mob) in visible_ids:
        return True
    return any(id(child) in visible_ids for child in getattr(mob, "submobjects", []))


def _iter_shapes(mob):
    """Visible non-text mobjects (cells, panels, bars) for clipping checks."""
    if isinstance(mob, Text):
        return
    children = getattr(mob, "submobjects", [])
    if children:
        for child in children:
            yield from _iter_shapes(child)
        return
    try:
        if len(getattr(mob, "points", [])) == 0:
            return
        stroke = float(getattr(mob, "stroke_width", 0) or 0)
        stroke_opacity = float(getattr(mob, "stroke_opacity", 1) or 0)
        fill_opacity = float(getattr(mob, "fill_opacity", 0) or 0)
    except Exception:
        return
    if (stroke > 0 and stroke_opacity > 0.05) or fill_opacity > 0.05:
        yield mob


def _label(text) -> str:
    """Human-readable text of a Text mobject for audit messages."""
    return str(getattr(text, "original_text", None) or getattr(text, "text", ""))


def audit_scene(scene, strict: bool | None = None) -> list[str]:
    """Check the finished frame for overlaps, clipping and covered chrome.

    Writes ``audit/<ClassName>.json`` next to the script. In strict mode a
    non-empty issue list raises :class:`PebbleLayoutError`.
    """
    if strict is None:
        strict = os.environ.get("PEBBLE_LAYOUT_STRICT", "0").strip() == "1"

    scene_mobs = [mob for mob in getattr(scene, "mobjects", []) if mob is not None]
    scene_ids = {id(mob) for mob in scene_mobs}
    visible: set[int] = set()
    for mob in scene_mobs:
        visible |= _all_ids(mob)

    issues: list[str] = []

    # Manim plays a group animation child by child and can leave a copy of a
    # child in scene.mobjects, so elements are de-duplicated by content and
    # geometry instead of by identity.
    texts: list[tuple] = []
    seen_texts: set = set()
    for mob in scene_mobs:
        for text in _iter_texts(mob):
            try:
                if text.width <= 0.02 or text.height <= 0.02:
                    continue
                opacity = getattr(text, "fill_opacity", 1.0)
                if opacity is None or float(opacity) < 0.08:
                    continue
            except Exception:
                continue
            box = _box(text)
            key = (_label(text), tuple(round(float(v), 2) for v in box))
            if key in seen_texts:
                continue
            seen_texts.add(key)
            texts.append((text, box))

    for text, box in texts:
        label = _label(text)[:32]
        if box[0] < -SAFE_WIDTH / 2 or box[1] > SAFE_WIDTH / 2:
            issues.append(
                f"text {label!r} is outside the safe area horizontally "
                f"(x {box[0]:.2f}..{box[1]:.2f})"
            )
        if box[2] < -SAFE_HEIGHT / 2 or box[3] > SAFE_HEIGHT / 2:
            issues.append(
                f"text {label!r} is outside the safe area vertically "
                f"(y {box[2]:.2f}..{box[3]:.2f})"
            )

    for index in range(len(texts)):
        for other in range(index + 1, len(texts)):
            first, second = texts[index][1], texts[other][1]
            area = _overlap_area(first, second)
            if area <= 0:
                continue
            small = min(
                max((first[1] - first[0]) * (first[3] - first[2]), 1e-6),
                max((second[1] - second[0]) * (second[3] - second[2]), 1e-6),
            )
            if area / small > 0.06:
                issues.append(
                    f"text {_label(texts[index][0])[:24]!r} overlaps "
                    f"{_label(texts[other][0])[:24]!r}"
                )

    # Panels and cells must not be clipped by the frame: a structure whose
    # strokes run past the edge is the classic "half a cell visible" defect.
    seen_shapes: set = set()
    for mob in scene_mobs:
        for shape in _iter_shapes(mob):
            box = _box(shape)
            key = (type(shape).__name__, tuple(round(float(v), 2) for v in box))
            if key in seen_shapes:
                continue
            seen_shapes.add(key)
            if box[0] < -FRAME_HALF_W or box[1] > FRAME_HALF_W:
                issues.append(
                    f"{type(shape).__name__} is clipped by the frame horizontally "
                    f"(x {box[0]:.2f}..{box[1]:.2f}); keep it inside "
                    f"{-FRAME_HALF_W + 0.4:.1f}..{FRAME_HALF_W - 0.4:.1f}"
                )
                continue
            if box[2] < -FRAME_HALF_H or box[3] > FRAME_HALF_H:
                issues.append(
                    f"{type(shape).__name__} is clipped by the frame vertically "
                    f"(y {box[2]:.2f}..{box[3]:.2f}); keep it inside "
                    f"{-FRAME_HALF_H + 0.3:.1f}..{FRAME_HALF_H - 0.3:.1f}"
                )

    # Structures share the stage: none may cover the chrome (title, caption,
    # panel headings) or another structure.
    live = [
        s
        for s in _STRUCTURES
        if not getattr(s, "_pebble_nested", False) and _is_visible(s, visible)
    ]
    for structure in live:
        box = _box(structure)
        if box[1] - box[0] <= 0 or box[3] - box[2] <= 0:
            continue
        for text in _RESERVED:
            if id(text) not in scene_ids:
                continue
            tbox = _box(text)
            text_area = max((tbox[1] - tbox[0]) * (tbox[3] - tbox[2]), 1e-6)
            if _overlap_area(tbox, box) / text_area > 0.3:
                issues.append(
                    f"the {type(structure).__name__} covers {_label(text)[:24]!r}; "
                    "move it down, make it smaller, or use the other side of the stage"
                )
    for index, first in enumerate(live):
        for second in live[index + 1:]:
            abox, bbox = _box(first), _box(second)
            area = _overlap_area(abox, bbox)
            if area <= 0:
                continue
            small = min(
                max((abox[1] - abox[0]) * (abox[3] - abox[2]), 1e-6),
                max((bbox[1] - bbox[0]) * (bbox[3] - bbox[2]), 1e-6),
            )
            if area / small > 0.08:
                issues.append(
                    f"{type(first).__name__} overlaps {type(second).__name__}; "
                    "give each structure its own lane or shrink one of them"
                )

    payload = {"scene": type(scene).__name__, "issues": issues, "texts": len(texts)}
    try:
        audit_dir = Path("audit")
        audit_dir.mkdir(exist_ok=True)
        (audit_dir / f"{type(scene).__name__}.json").write_text(
            json.dumps(payload, indent=2), encoding="utf-8"
        )
    except Exception:  # auditing must never break a render on its own
        pass

    if issues and os.environ.get("PEBBLE_AUDIT_DEBUG"):
        with open(os.environ["PEBBLE_AUDIT_DEBUG"], "a", encoding="utf-8") as fh:
            fh.write(f"SCENE {type(scene).__name__}\n")
            for mob in scene_mobs:
                fh.write(
                    f"  {type(mob).__name__} token={getattr(mob, '_pebble_token', None)} "
                    f"box={tuple(round(float(v), 2) for v in _box(mob))} "
                    f"texts={[_label(t) for t in list(_iter_texts(mob))][:3]}\n"
                )

    if issues:
        message = (
            f"layout audit found {len(issues)} issue(s): "
            + "; ".join(issues[:3])
            + ". Keep every element at least 0.4 units inside the 14.2 x 8 frame, "
            "use max_width=5.4 in a lane (8.4 at STAGE), and let the kit place all text."
        )
        if strict:
            raise PebbleLayoutError(message)
        import logging

        logging.getLogger("pebble.layout").warning(message)
    return issues


# ---------------------------------------------------------------------------
# MapViz
# ---------------------------------------------------------------------------

class MapViz(_IntroMixin, VGroup):
    """A hash-map / set panel: key chips with optional values, added one by one."""

    ROW_WIDTH = 4.8
    ROW_HEIGHT = 0.52
    ROW_GAP = 0.1
    HEADER = 0.78

    def __init__(
        self,
        title: str,
        show_values: bool = True,
        max_rows: int = 6,
        at=STAGE,
        max_width: float | None = None,
        max_height: float | None = None,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.show_values = show_values
        self.max_rows = max(2, int(max_rows))
        self.rows: dict = {}
        self.slot_rows: list = []
        self._miss_mob = None
        self.target = np.array([float(at[0]), float(at[1]), 0.0])
        # The panel is only as tall as the keys it holds: a big empty box with
        # one row in it reads as a mistake.
        self.visible_rows = min(2, self.max_rows)

        self.panel = _panel(
            self.ROW_WIDTH + 0.4, self._height_for(self.visible_rows), "default", corner=0.2
        )
        self.heading = _text(title, size=26, color=C_TEXT, weight=MEDIUM)
        self.add(self.panel, self.heading)
        self._empty_hint = None
        if not self.rows:
            self._empty_hint = _text("(empty)", size=22, color=C_MUTED)
            self.add(self._empty_hint)
        self._place_panel()
        # A narrow request (a map inside a compare panel) scales the whole
        # panel down; every later row must be built at that same scale or it
        # drifts up into the heading.
        self._s = 1.0
        _fit(self, _width_for(at, max_width), max_height)
        _clamp_into_frame(self)
        self._s = float(self.panel.height) / max(
            self._height_for(self.visible_rows), 1e-6
        )
        self._place_panel()

    def _height_for(self, rows: int) -> float:
        return self.HEADER + rows * (self.ROW_HEIGHT + self.ROW_GAP) + 0.14

    def _place_panel(self):
        """Anchor the panel at its top edge so it grows downwards when needed."""
        s = getattr(self, "_s", 1.0)
        height = self._height_for(self.visible_rows) * s
        top = self.target[1] + self._height_for(min(2, self.max_rows)) * s / 2
        if top - height < -FRAME_HALF_H + EDGE_MARGIN:
            top = -FRAME_HALF_H + EDGE_MARGIN + height
        self.panel.become(
            _panel(
                (self.ROW_WIDTH + 0.4) * s, height, "default", corner=0.2 * s
            ).move_to(np.array([self.target[0], top - height / 2, 0.0]))
        )
        self.heading.move_to(np.array([self.target[0], top - 0.4 * s, 0.0]))
        if self._empty_hint is not None:
            self._empty_hint.move_to(
                np.array([self.target[0], self.panel.get_center()[1] - 0.15, 0.0])
            )
        if self._miss_mob is not None:
            self._miss_mob.move_to(
                np.array([self.target[0], self.panel.get_bottom()[1] + 0.3, 0.0])
            )
        for slot, row in enumerate(self.slot_rows):
            self._place_row(row, slot)

    def _row_mob(self, key, value):
        bg = RoundedRectangle(
            corner_radius=0.1,
            width=self.ROW_WIDTH,
            height=self.ROW_HEIGHT,
            fill_color=C_BG,
            fill_opacity=0.55,
            stroke_color=PANEL_EDGE,
            stroke_width=1.8,
        )
        key_text = _text(key, size=24, color=C_TEXT)
        key_text.move_to(bg.get_left() + RIGHT * 0.95)
        parts = [bg, key_text]
        value_text = None
        if self.show_values:
            arrow = _text("->", size=22, color=C_MUTED)
            arrow.move_to(bg.get_center() + LEFT * 0.25)
            value_text = _text("?" if value is None else value, size=26, color=C_ACCENT)
            value_text.move_to(bg.get_right() + LEFT * 1.05)
            parts.extend([arrow, value_text])
        row = VGroup(*parts)
        row.key, row.value_text, row.bg = key_text, value_text, bg
        row.state = "default"
        return row

    def _place_row(self, row, slot: int):
        s = getattr(self, "_s", 1.0)
        y = (
            self.panel.get_top()[1]
            - self.HEADER * s
            - self.ROW_HEIGHT * s / 2
            - slot * (self.ROW_HEIGHT + self.ROW_GAP) * s
        )
        row.move_to(np.array([self.target[0], y, 0.0]))

    def put(self, key, value=None):
        key = str(key)
        if key in self.rows:
            row = self.rows[key]
            anims = [_state_anim(row.bg, "active")]
            if self.show_values:
                new = _become(
                    row.value_text,
                    _text(
                        "?" if value is None else value, size=26, color=C_ACCENT
                    ).move_to(row.value_text.get_center()),
                )
                row.value_text = new
                anims.append(Indicate(new, color=C_TEXT, scale_factor=1.1))
            return AnimationGroup(*anims, lag_ratio=0)

        if len(self.slot_rows) >= self.max_rows:
            old_key = next((k for k, r in self.rows.items() if r is self.slot_rows[0]), None)
            old = self.slot_rows.pop(0)
            if old_key is not None:
                self.rows.pop(old_key, None)
            start_anims = [FadeOut(old)]
        else:
            start_anims = []

        start_anims = list(start_anims)
        if self._empty_hint is not None:
            hint = self._empty_hint
            # Not self.remove(): MapViz.remove() deletes a key from the map.
            VGroup.remove(self, hint)
            start_anims.append(FadeOut(hint))
            self._empty_hint = None

        slot = len(self.slot_rows)
        if slot + 1 > self.visible_rows:
            self.visible_rows = min(self.max_rows, slot + 1)
            self._place_panel()
        row = self._row_mob(key, value)
        if getattr(self, "_s", 1.0) != 1.0:
            row.scale(self._s)
        self._place_row(row, slot)
        self.add(row)
        self.rows[key] = row
        self.slot_rows.append(row)
        return AnimationGroup(
            *start_anims, FadeIn(row, shift=DOWN * 0.08), lag_ratio=0
        )

    def hit(self, key):
        row = self.rows.get(str(key))
        if row is None:
            raise ValueError(
                f"{key!r} is not in the map; put it before calling hit()"
            )
        row.state = "good"
        return AnimationGroup(
            _state_anim(row.bg, "good"),
            Indicate(row, color=C_TEXT, scale_factor=1.04),
            lag_ratio=0,
        )

    def miss(self, label="not found"):
        # The caller's words are the message: appending a suffix turns
        # "7 not found" into "7 not found not stored".
        scale = getattr(self, "_s", 1.0)
        new = _text(label, size=22, color=C_BAD)
        if scale != 1.0:
            new.scale(scale)
        new.move_to(
            np.array(
                [self.target[0], self.panel.get_bottom()[1] + 0.3, 0.0]
            )
        )
        anims = [FadeOut(self._miss_mob)] if self._miss_mob is not None else []
        self._miss_mob = new
        self.add(new)
        anims.append(FadeIn(new, shift=UP * 0.05))
        return AnimationGroup(*anims, lag_ratio=0)

    def remove(self, key):
        row = self.rows.pop(str(key), None)
        if row is None:
            raise ValueError(f"{key!r} is not in the map")
        if row in self.slot_rows:
            self.slot_rows.remove(row)
        anims = [FadeOut(row, run_time=T_FAST)]
        if not self.slot_rows and self._empty_hint is None:
            # An emptied map is not a blank box: say so, the way it started.
            self.visible_rows = min(2, self.max_rows)
            self._empty_hint = _text("(empty)", size=22, color=C_MUTED)
            self.add(self._empty_hint)
            self._place_panel()
            anims.append(FadeIn(self._empty_hint))
        return AnimationGroup(*anims, lag_ratio=0)

    def set_state(self, key, state: str):
        row = self.rows.get(str(key))
        if row is None:
            raise ValueError(f"{key!r} is not in the map")
        row.state = state
        return _state_anim(row.bg, state)


# ---------------------------------------------------------------------------
# StackViz / QueueViz
# ---------------------------------------------------------------------------

class StackViz(_IntroMixin, VGroup):
    """A vertical stack of boxes with a title."""

    def __init__(
        self,
        title: str,
        items=(),
        capacity: int = 6,
        at=STAGE,
        max_width: float | None = 4.4,
        max_height: float | None = 4.8,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.capacity = max(1, int(capacity))
        self.title_text = _text(title, size=26, color=C_TEXT, weight=MEDIUM)
        self.title_text.move_to(UP * 2.5)
        self.add(self.title_text)
        self.items: list = []
        self._s = 1.0
        self._box_h = 0.55
        design_title_h = self.title_text.height
        # The given order is push order: the last value ends up on top.
        total = len(items)
        for index, value in enumerate(items):
            self.items.insert(0, self._make_box(value, total - 1 - index))
        _settle(self, at, max_width, max_height)
        # A stack placed in a narrow lane was scaled: later pushes must use the
        # same scale, or they land in the wrong slot with a visible gap.
        self._s = float(self.title_text.height) / max(design_title_h, 1e-6)
        self._box_h *= self._s
        self._layout()

    def _layout(self):
        """Repack the boxes into one column directly under the title."""
        if not self.items:
            return
        top = self.title_text.get_bottom()[1] - 0.45 * self._s
        cx = self.title_text.get_center()[0]
        pitch = self._box_h + 0.12 * self._s
        for slot, group in enumerate(self.items):
            group.move_to(
                np.array([cx, top - slot * pitch - self._box_h / 2, 0.0])
            )

    def _slot_center(self, slot: int) -> np.ndarray:
        top = self.title_text.get_bottom()[1] - 0.45 * self._s
        pitch = self._box_h + 0.12 * self._s
        return np.array(
            [
                self.title_text.get_center()[0],
                top - slot * pitch - self._box_h / 2,
                0.0,
            ]
        )

    def _make_box(self, value, slot: int):
        box = RoundedRectangle(
            corner_radius=0.1,
            width=3.4,
            height=self._box_h,
            fill_color=C_PANEL,
            fill_opacity=0.95,
            stroke_color=DIM_EDGE,
            stroke_width=2.6,
        )
        label = _text(value, size=26)
        label.move_to(box.get_center())
        group = VGroup(box, label)
        group.box, group.label = box, label
        group.move_to(self._slot_center(slot))
        self.add(group)
        return group

    def push(self, value):
        if len(self.items) >= self.capacity:
            raise ValueError(
                f"stack is full (capacity {self.capacity}); pop first or raise capacity"
            )
        # The newest item goes on top (slot 0) and the others step down: a
        # stack that grew downwards contradicted its own narration.
        group = self._make_box(value, 0)
        self.items.insert(0, group)
        anims = [FadeIn(group, shift=UP * 0.25), _state_anim(group.box, "active")]
        for slot, item in enumerate(self.items):
            if item is not group:
                anims.append(item.animate.move_to(self._slot_center(slot)))
        return AnimationGroup(*anims, lag_ratio=0)

    def pop(self):
        if not self.items:
            raise ValueError("stack is empty; nothing to pop")
        group = self.items.pop(0)
        anims = [FadeOut(group, shift=UP * 0.3)]
        # The remaining boxes slide up into the freed slot.
        for slot, item in enumerate(self.items):
            anims.append(item.animate.move_to(self._slot_center(slot)))
        return AnimationGroup(*anims, lag_ratio=0)

    def peek(self):
        if not self.items:
            raise ValueError("stack is empty; nothing to peek")
        return Indicate(self.items[0], color=C_TEXT, scale_factor=1.05)


class QueueViz(_IntroMixin, VGroup):
    """A horizontal queue (or deque) with front/back labels."""

    BOX_W = 1.6
    BOX_H = 0.7
    GAP = 0.1

    def __init__(
        self,
        title: str,
        items=(),
        deque: bool = False,
        at=STAGE,
        max_width: float | None = 8.4,
        max_height: float | None = 3.2,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.deque = deque
        self.title_text = _text(title, size=26, color=C_TEXT, weight=MEDIUM)
        self.title_text.move_to(UP * 1.35)
        self.add(self.title_text)
        self.items: list = []
        self._cx = 0.0
        self._row_y = 0.0
        self.front_label = _text("front", size=20, color=C_MUTED)
        self.back_label = _text("back", size=20, color=C_MUTED)
        for value in items:
            self._make_box(value)
        self._layout()
        _settle(self, at, max_width, max_height)
        self._cx = at[0]
        self._row_y = self.title_text.get_center()[1] - 1.35
        self._layout()

    def _make_box(self, value):
        box = RoundedRectangle(
            corner_radius=0.1,
            width=self.BOX_W,
            height=self.BOX_H,
            fill_color=C_PANEL,
            fill_opacity=0.95,
            stroke_color=DIM_EDGE,
            stroke_width=2.6,
        )
        label = _text(value, size=26)
        label.move_to(box.get_center())
        group = VGroup(box, label)
        group.box, group.label = box, label
        self.add(group)
        self.items.append(group)
        return group

    def _slot_center(self, position: int, count: int | None = None):
        count = max(1, count if count is not None else len(self.items))
        total = count * self.BOX_W + (count - 1) * self.GAP
        start = -total / 2 + self.BOX_W / 2
        return np.array(
            [self._cx + start + position * (self.BOX_W + self.GAP), self._row_y, 0.0]
        )

    def _place_end_labels(self):
        if not self.items:
            return
        base = self.items[0].get_center()
        if len(self.items) == 1:
            self.front_label.move_to(base + DOWN * 0.62 + LEFT * 0.85)
            self.back_label.move_to(base + DOWN * 0.62 + RIGHT * 0.85)
        else:
            self.front_label.next_to(self.items[0], DOWN, buff=0.18)
            self.back_label.next_to(self.items[-1], DOWN, buff=0.18)
        for label in (self.front_label, self.back_label):
            if label not in self:
                self.add(label)

    def _layout(self):
        for position, group in enumerate(self.items):
            group.move_to(self._slot_center(position))
        self._place_end_labels()

    def enqueue(self, value):
        # Reflow immediately and fade the new box in where it belongs: two
        # enqueues can be built before either plays, so an animated reflow would
        # leave the row and its labels at stale positions.
        group = self._make_box(value)
        self._layout()
        return AnimationGroup(
            _state_anim(group.box, "active"),
            FadeIn(group),
            lag_ratio=0,
        )

    def dequeue(self):
        if not self.items:
            raise ValueError("queue is empty; nothing to dequeue")
        group = self.items.pop(0)
        anims = [FadeOut(group, shift=LEFT * 0.4)]
        remaining = len(self.items)
        for position, item in enumerate(self.items):
            anims.append(item.animate.move_to(self._slot_center(position, remaining)))
        if self.items:
            base = self.items[0].get_center()
            if remaining == 1:
                front_target = base + DOWN * 0.62 + LEFT * 0.85
                back_target = base + DOWN * 0.62 + RIGHT * 0.85
            else:
                front_target = self.items[0].get_bottom() + DOWN * 0.35
                back_target = self.items[-1].get_bottom() + DOWN * 0.35
            anims.append(self.front_label.animate.move_to(front_target))
            anims.append(self.back_label.animate.move_to(back_target))
        return AnimationGroup(*anims, lag_ratio=0)

    def push_front(self, value):
        if not self.deque:
            raise ValueError("push_front is only available on a deque (deque=True)")
        group = self._make_box(value)
        self.items.insert(0, group)
        self._layout()
        return AnimationGroup(
            _state_anim(group.box, "active"),
            FadeIn(group, shift=RIGHT * 0.3),
            lag_ratio=0,
        )

    def pop_back(self):
        if not self.deque:
            raise ValueError("pop_back is only available on a deque (deque=True)")
        if not self.items:
            raise ValueError("deque is empty; nothing to pop_back")
        group = self.items.pop()
        return FadeOut(group, shift=RIGHT * 0.4)


# ---------------------------------------------------------------------------
# LinkedListViz
# ---------------------------------------------------------------------------

class LinkedListViz(_IntroMixin, VGroup):
    """Linked-list nodes in a row with arrows between them."""

    RADIUS = 0.55
    SPACING = 1.5

    def __init__(
        self,
        values,
        at=STAGE,
        max_width: float | None = 8.4,
        max_height: float | None = 2.6,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.values = list(values)
        if not self.values:
            raise ValueError("LinkedListViz needs at least one value")
        self.store: dict = {}
        self.nodes: list = []
        self.cells: list = []  # Pointer-compatible
        self.arrows: dict = {}
        self.links: list = []
        self._cx = 0.0
        self._cy = 0.0
        self.spacing = min(
            2.6,
            max(1.1, ((8.4 if max_width is None else max_width) - 2 * self.RADIUS) / max(1, len(self.values) - 1)),
        )
        for value in self.values:
            self._make_node(value)
        self._layout_nodes()
        self._build_arrows()
        _settle(self, at, max_width, max_height)
        self._cx = self.get_center()[0]
        self._cy = self.nodes[0].get_center()[1]

    def _make_node(self, value):
        circle = Circle(
            radius=self.RADIUS,
            fill_color=C_PANEL,
            fill_opacity=0.95,
            stroke_color=DIM_EDGE,
            stroke_width=2.8,
        )
        label = _text(value, size=26)
        label.move_to(circle.get_center())
        node = VGroup(circle, label)
        node.circle, node.label = circle, label
        self.add(node)
        self.nodes.append(node)
        self.cells.append(circle)
        return node

    def _x(self, position: int) -> float:
        offset = (len(self.nodes) - 1) / 2
        return self._cx + (position - offset) * self.spacing

    def _layout_nodes(self):
        for position, node in enumerate(self.nodes):
            node.move_to(np.array([self._x(position), self._cy, 0.0]))

    def _arrow_between(self, first, second):
        return Arrow(
            first.circle.get_right(),
            second.circle.get_left(),
            buff=0.04,
            color=C_MUTED,
            stroke_width=3,
            max_tip_length_to_length_ratio=0.28,
        )

    def _build_arrows(self):
        for position in range(len(self.nodes) - 1):
            arrow = self._arrow_between(self.nodes[position], self.nodes[position + 1])
            arrow.set_z_index(-1)
            self.add(arrow)
            self.arrows[(position, position + 1)] = arrow

    def set_state(self, index_or_list, state: str):
        _style(state)
        indices = (
            list(index_or_list)
            if isinstance(index_or_list, (list, tuple, set))
            else [index_or_list]
        )
        anims = []
        for index in indices:
            _check_index(index, len(self.nodes), "node index")
            anims.extend(_state_anims([self.nodes[index].circle], state))
        if len(anims) == 1:
            return anims[0]
        return AnimationGroup(*anims, lag_ratio=0)

    def pointer(self, name: str, index: int, state: str = "active", level: int = 0) -> Pointer:
        _check_index(index, len(self.cells), "node index")
        return Pointer(self, name, index, state, level)

    def relink(self, i: int, j: int | None):
        """Draw an extra arrow from node i to node j below the row (j=None: null)."""
        _check_index(i, len(self.nodes), "node index")
        start = self.nodes[i].circle.get_bottom() + DOWN * 0.06
        if j is None:
            label = _text("null", size=22, color=C_BAD)
            label.next_to(start, DOWN, buff=0.35)
            end = label.get_top()
            arrow = Arrow(start, end, buff=0.06, color=C_BAD, stroke_width=3,
                          max_tip_length_to_length_ratio=0.2)
            group = VGroup(arrow, label)
        else:
            _check_index(j, len(self.nodes), "node index")
            end = self.nodes[j].circle.get_bottom() + DOWN * 0.06
            arrow = Arrow(
                start,
                end,
                buff=0.06,
                color=C_ACCENT,
                stroke_width=3,
                path_arc=0.9,
                max_tip_length_to_length_ratio=0.12,
            )
            group = VGroup(arrow)
        group.set_z_index(-2)
        self.add(group)
        self.links.append(group)
        return FadeIn(group, run_time=T_STEP)

    def remove(self, index: int):
        _check_index(index, len(self.nodes), "node index")
        node = self.nodes.pop(index)
        self.cells.pop(index)
        anims = [FadeOut(node)]
        for key in [k for k in self.arrows if index in k]:
            anims.append(FadeOut(self.arrows.pop(key)))
        return AnimationGroup(*anims, lag_ratio=0)

    def insert_after(self, index: int, value):
        _check_index(index, len(self.nodes), "node index")
        node = self._make_node(value)
        self.nodes.insert(index + 1, node)
        self.cells.insert(index + 1, node.circle)
        self.values.insert(index + 1, value)
        anims = [FadeOut(arrow) for arrow in self.arrows.values()]
        self.arrows.clear()
        target_positions = []
        for position in range(len(self.nodes)):
            target_positions.append(np.array([self._x(position), self._cy, 0.0]))
        for node_mob, target in zip(self.nodes, target_positions):
            anims.append(node_mob.animate.move_to(target))
        self._build_arrows()
        for arrow in self.arrows.values():
            anims.append(FadeIn(arrow))
        return AnimationGroup(*anims, lag_ratio=0)


# ---------------------------------------------------------------------------
# TreeViz
# ---------------------------------------------------------------------------

class TreeViz(_IntroMixin, VGroup):
    """A binary tree from a LeetCode level-order list (None = missing child)."""

    RADIUS = 0.48

    def __init__(
        self,
        level_order,
        at=STAGE,
        max_width: float | None = 8.4,
        max_height: float | None = 4.4,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.level = list(level_order)
        if not self.level or self.level[0] is None:
            raise ValueError("TreeViz needs a root value as the first element")
        self.store: dict = {}
        self.nodes: dict = {}
        self.edges: dict = {}
        self.notes: dict = {}

        positions = self._positions()
        xstep, ystep = self._steps(
            positions,
            8.4 if max_width is None else max_width,
            4.4 if max_height is None else max_height,
        )
        xs = [x for x, _ in positions.values()]
        mid = (min(xs) + max(xs)) / 2 if xs else 0.0
        points = {}
        for index, (x, depth) in positions.items():
            points[index] = np.array([(x - mid) * xstep, (max(d for _, d in positions.values()) / 2 - depth) * ystep, 0.0])

        for index in sorted(positions):
            self.node_at(index, points[index])
        self._build_edges(points)
        _settle(self, at, max_width, max_height)
        self.node_points = points

    def _positions(self):
        positions: dict[int, tuple[float, int]] = {}
        counter = [0]

        def walk(index: int, depth: int):
            if index >= len(self.level) or self.level[index] is None:
                return
            walk(2 * index + 1, depth + 1)
            positions[index] = (counter[0], depth)
            counter[0] += 1
            walk(2 * index + 2, depth + 1)

        walk(0, 0)
        return positions

    @classmethod
    def _steps(cls, positions, max_width: float, max_height: float) -> tuple[float, float]:
        """Spread the levels so the tree uses the width it is given."""
        xs = [x for x, _ in positions.values()]
        depths = [depth for _, depth in positions.values()]
        slots = max(1, max(xs) - min(xs))
        levels = max(1, max(depths) - min(depths))
        xstep = min(2.3, max(0.6, (max_width - 2 * cls.RADIUS) / slots))
        ystep = min(1.8, max(0.7, (max_height - 2 * cls.RADIUS) / levels))
        return xstep, ystep

    def node_at(self, index, point):
        circle = Circle(
            radius=self.RADIUS,
            fill_color=C_PANEL,
            fill_opacity=0.95,
            stroke_color=DIM_EDGE,
            stroke_width=2.8,
        )
        label = _text(self.level[index], size=28)
        label.move_to(circle.get_center())
        node = VGroup(circle, label)
        node.circle, node.label = circle, label
        node.move_to(point)
        self.add(node)
        self.nodes[index] = node
        return node

    def _build_edges(self, points):
        for index in sorted(points):
            for child in (2 * index + 1, 2 * index + 2):
                if child not in points:
                    continue
                line = Line(
                    self.nodes[index].circle.get_center(),
                    self.nodes[child].circle.get_center(),
                    stroke_width=3,
                    color=DIM_EDGE,
                )
                line.set_z_index(-2)
                self.add(line)
                self.edges[(index, child)] = line
        # keep the nodes above the edges
        for node in self.nodes.values():
            node.set_z_index(1)

    def set_state(self, index, state: str):
        if index not in self.nodes:
            raise ValueError(
                f"node {index!r} is not in this tree (valid: {sorted(self.nodes)})"
            )
        _style(state)
        return _state_anim(self.nodes[index].circle, state)

    def set_edge(self, parent: int, child: int, state: str):
        key = (parent, child)
        if key not in self.edges:
            raise ValueError(f"no edge {key}; valid edges: {sorted(self.edges)}")
        style = _style(state)
        return self.edges[key].animate.set_stroke(
            color=style["stroke"], width=style["stroke_width"] + 1
        )

    def annotate(self, index, text, state: str = "default"):
        if index not in self.nodes:
            raise ValueError(f"node {index!r} is not in this tree")
        style = _style(state)
        note = _text(text, size=20, color=style["stroke"])
        note.next_to(self.nodes[index].circle, DOWN, buff=0.16)
        old = self.notes.get(index)
        if old is not None:
            self.remove(old)
        self.add(note)
        self.notes[index] = note
        return FadeIn(note, shift=UP * 0.05)


# ---------------------------------------------------------------------------
# GraphViz
# ---------------------------------------------------------------------------

class GraphViz(_IntroMixin, VGroup):
    """A graph laid out on a circle, with node tags (distances, visiting order)."""

    def __init__(
        self,
        labels,
        edges,
        directed: bool = False,
        layout: str = "circle",
        positions=None,
        at=STAGE,
        max_width: float | None = 8.4,
        max_height: float | None = 4.4,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.labels = list(labels)
        if not self.labels:
            raise ValueError("GraphViz needs at least one node label")
        self.directed = directed
        self.store: dict = {}
        self.nodes: dict = {}
        self.edges: dict = {}
        self.tags: dict = {}
        self.edge_labels: dict = {}

        if positions is not None:
            points = {
                label: np.array([float(positions[label][0]), float(positions[label][1]), 0.0])
                for label in self.labels
            }
        elif layout == "circle":
            rx = min(3.6, max(1.2, ((8.4 if max_width is None else max_width) / 2) - 0.55))
            ry = min(2.4, max(1.0, ((4.4 if max_height is None else max_height) / 2) - 0.65))
            points = {}
            count = len(self.labels)
            for position, label in enumerate(self.labels):
                angle = PI / 2 - 2 * PI * position / count
                points[label] = np.array(
                    [rx * math.cos(angle), ry * math.sin(angle), 0.0]
                )
        else:
            raise ValueError("layout must be 'circle' or pass positions={label: (x, y)}")

        for label in self.labels:
            circle = Circle(
                radius=0.5,
                fill_color=C_PANEL,
                fill_opacity=0.95,
                stroke_color=DIM_EDGE,
                stroke_width=2.8,
            )
            text = _text(label, size=28)
            text.move_to(circle.get_center())
            node = VGroup(circle, text)
            node.circle, node.label = circle, text
            node.move_to(points[label])
            self.add(node)
            self.nodes[label] = node

        for edge in edges:
            a, b = edge[0], edge[1]
            weight = edge[2] if len(edge) > 2 else None
            self._add_edge(a, b, weight)

        for node in self.nodes.values():
            node.set_z_index(1)
        _settle(self, at, max_width, max_height)
        self.node_points = points

    def _add_edge(self, a, b, weight=None):
        first, second = self.nodes[a], self.nodes[b]
        if self.directed:
            mob = Arrow(
                first.circle.get_center(),
                second.circle.get_center(),
                buff=0.42,
                color=DIM_EDGE,
                stroke_width=3,
                max_tip_length_to_length_ratio=0.12,
            )
        else:
            mob = Line(
                first.circle.get_center(),
                second.circle.get_center(),
                stroke_width=3,
                color=DIM_EDGE,
            )
        mob.set_z_index(-2)
        self.add(mob)
        self.edges[(a, b)] = mob
        if weight is not None:
            label = _text(weight, size=20, color=C_MUTED)
            start = first.circle.get_center()
            end = second.circle.get_center()
            vector = end - start
            length = float(np.linalg.norm(vector)) or 1.0
            # Offset perpendicular to the edge so opposite edges through the
            # middle of the circle do not stack their labels on one point.
            normal = np.array([-vector[1], vector[0], 0.0]) / length
            label.move_to((start + end) / 2 + normal * 0.24)
            label.set_z_index(2)
            self.add(label)
            self.edge_labels[(a, b)] = label

    def set_node(self, label, state: str):
        if label not in self.nodes:
            raise ValueError(f"no node {label!r}; valid: {self.labels}")
        _style(state)
        return _state_anim(self.nodes[label].circle, state)

    def set_edge(self, a, b, state: str):
        key = (a, b) if (a, b) in self.edges else (b, a)
        if key not in self.edges:
            raise ValueError(f"no edge between {a!r} and {b!r}")
        style = _style(state)
        return self.edges[key].animate.set_stroke(
            color=style["stroke"], width=style["stroke_width"] + 1
        )

    def tag(self, label, text):
        if label not in self.nodes:
            raise ValueError(f"no node {label!r}; valid: {self.labels}")
        note = _text(text, size=20, color=C_ACCENT)
        # Push the tag outwards from the middle of the graph: straight down it
        # lands on the edges that pass under a bottom node.
        offset = self.nodes[label].circle.get_center() - self.get_center()
        length = float(np.linalg.norm(offset))
        direction = DOWN if length < 0.2 else offset / length
        note.next_to(self.nodes[label].circle, direction, buff=0.16)
        old = self.tags.get(label)
        if old is not None:
            self.remove(old)
        self.add(note)
        self.tags[label] = note
        return FadeIn(note, shift=UP * 0.06)


# ---------------------------------------------------------------------------
# GridViz
# ---------------------------------------------------------------------------

class GridViz(_IntroMixin, VGroup):
    """A grid of cells (DP tables, matrices) with optional dependency arrows."""

    CELL = 0.78

    def __init__(
        self,
        rows,
        row_labels=None,
        col_labels=None,
        at=STAGE,
        max_width: float | None = 8.2,
        max_height: float | None = 4.2,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.rows = [list(row) for row in rows]
        if not self.rows or not self.rows[0]:
            raise ValueError("GridViz needs a non-empty list of rows")
        self.store: dict = {}
        self.cells: dict = {}
        self.values: dict = {}
        self.links: list = []
        height = len(self.rows)
        width = len(self.rows[0])
        cell = min(
            1.45,
            max(
                0.5,
                min(
                    (8.2 if max_width is None else max_width) / max(1, width) - 0.08,
                    (4.2 if max_height is None else max_height) / max(1, height) - 0.08,
                ),
            ),
        )

        for r in range(height):
            for c in range(width):
                rect = RoundedRectangle(
                    corner_radius=0.08,
                    width=cell,
                    height=cell,
                    fill_color=C_PANEL,
                    fill_opacity=0.95,
                    stroke_color=DIM_EDGE,
                    stroke_width=2.4,
                )
                rect.move_to(np.array([(c - (width - 1) / 2) * (cell + 0.08), ((height - 1) / 2 - r) * (cell + 0.08), 0.0]))
                text = _text(self.rows[r][c], size=25)
                text.move_to(rect.get_center())
                self.cells[(r, c)] = rect
                self.values[(r, c)] = text
                self.add(rect, text)

        if row_labels:
            for r, label in enumerate(row_labels[:height]):
                text = _text(label, size=20, color=C_MUTED)
                text.next_to(self.cells[(r, 0)], LEFT, buff=0.14)
                self.add(text)
        if col_labels:
            for c, label in enumerate(col_labels[:width]):
                text = _text(label, size=20, color=C_MUTED)
                text.next_to(self.cells[(0, c)], UP, buff=0.12)
                self.add(text)

        _settle(self, at, max_width, max_height)

    def _cell(self, key):
        if not isinstance(key, tuple) or key not in self.cells:
            raise ValueError(
                f"cell {key!r} is out of range (rows 0..{len(self.rows) - 1}, "
                f"cols 0..{len(self.rows[0]) - 1})"
            )
        return key

    def set_state(self, keys, state: str):
        _style(state)
        items = list(keys) if isinstance(keys, list) and keys and isinstance(keys[0], tuple) else [keys]
        anims = []
        for key in items:
            self._cell(key)
            anims.extend(_state_anims([self.cells[key]], state))
        if len(anims) == 1:
            return anims[0]
        return AnimationGroup(*anims, lag_ratio=0)

    def set_value(self, key, value):
        key = self._cell(key)
        old = self.values[key]
        new = _text(value, size=25).move_to(old.get_center())
        self.values[key] = new
        return ReplacementTransform(old, new)

    def link(self, src, dst):
        src = self._cell(src)
        dst = self._cell(dst)
        arrow = Arrow(
            self.cells[src].get_center(),
            self.cells[dst].get_center(),
            buff=0.44,
            color=C_ACCENT,
            stroke_width=2.4,
            max_tip_length_to_length_ratio=0.2,
        )
        arrow.set_z_index(-1)
        self.add(arrow)
        self.links.append(arrow)
        return FadeIn(arrow)

    def unlink(self):
        anims = [FadeOut(arrow) for arrow in self.links]
        self.links.clear()
        return AnimationGroup(*anims, lag_ratio=0)


# ---------------------------------------------------------------------------
# BarsViz / HeapViz
# ---------------------------------------------------------------------------

class BarsViz(_IntroMixin, VGroup):
    """Vertical bars for comparisons and sorts; height is proportional to value."""

    def __init__(
        self,
        values,
        at=STAGE,
        max_width: float | None = 8.2,
        max_height: float | None = 4.2,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.values = [float(v) for v in values]
        if not self.values:
            raise ValueError("BarsViz needs at least one value")
        self.store: dict = {}
        self.bars: list = []
        self.labels: list = []
        self.indices: list = []
        count = len(self.values)
        max_value = max(abs(v) for v in self.values) or 1.0
        bar_w = min(2.0, ((8.2 if max_width is None else max_width) / count) - 0.26)
        self._base_y = -1.55
        self._max_height = 3.5
        for position, value in enumerate(self.values):
            height = max(0.12, abs(value) / max_value * self._max_height)
            bar = Rectangle(
                width=bar_w,
                height=height,
                fill_color=C_PANEL,
                fill_opacity=0.95,
                stroke_color=DIM_EDGE,
                stroke_width=2.4,
            )
            x = (position - (count - 1) / 2) * (bar_w + 0.22)
            bar.move_to(np.array([x, self._base_y + height / 2, 0.0]))
            label = _text(f"{value:g}", size=22, color=C_TEXT)
            label.next_to(bar, UP, buff=0.1)
            index = _text(position, size=20, color=C_MUTED)
            index.next_to(bar, DOWN, buff=0.08)
            index.set_y(self._base_y - 0.3)
            self.add(bar, label, index)
            self.bars.append(bar)
            self.labels.append(label)
            self.indices.append(index)
        _settle(self, at, max_width, max_height)

    def _height(self, value) -> float:
        max_value = max(abs(v) for v in self.values) or 1.0
        return max(0.12, abs(value) / max_value * self._max_height)

    def set_state(self, index_or_list, state: str):
        _style(state)
        indices = (
            list(index_or_list)
            if isinstance(index_or_list, (list, tuple, set))
            else [index_or_list]
        )
        anims = []
        for index in indices:
            _check_index(index, len(self.bars), "bar index")
            anims.extend(_state_anims([self.bars[index]], state))
        if len(anims) == 1:
            return anims[0]
        return AnimationGroup(*anims, lag_ratio=0)

    def swap(self, i: int, j: int):
        _check_index(i, len(self.bars))
        _check_index(j, len(self.bars))
        self.values[i], self.values[j] = self.values[j], self.values[i]
        anims = []
        for index in (i, j):
            height = self._height(self.values[index])
            bar = self.bars[index]
            anims.append(
                bar.animate.stretch_to_fit_height(height).move_to(
                    np.array([bar.get_center()[0], self._base_y + height / 2, 0.0])
                )
            )
            old = self.labels[index]
            new = _text(f"{self.values[index]:g}", size=22).next_to(bar, UP, buff=0.1)
            self.labels[index] = new
            anims.append(ReplacementTransform(old, new))
        return AnimationGroup(*anims, lag_ratio=0)


class HeapViz(_IntroMixin, VGroup):
    """A heap as a tree and as an array, side by side."""

    def __init__(
        self,
        values,
        mode: str = "min",
        at=STAGE,
        max_width: float | None = 9.6,
        max_height: float | None = 4.6,
        **kwargs,
    ):
        super().__init__(**kwargs)
        self.values = list(values)
        if not self.values:
            raise ValueError("HeapViz needs at least one value")
        if mode not in {"min", "max"}:
            raise ValueError("mode must be 'min' or 'max'")
        self.mode = mode
        self.store: dict = {}
        self.tree = TreeViz(self.values, max_width=5.6, max_height=4.0)
        self.tree.move_to(LEFT * 3.1 + DOWN * 0.1)
        self.array = ArrayViz(
            self.values,
            show_index=True,
            cell=0.95,
            max_width=4.4,
            max_height=2.2,
        )
        self.array.move_to(RIGHT * 3.3 + DOWN * 0.9)
        self.title_text = _text(f"{mode} heap", size=24, color=C_MUTED)
        self.title_text.move_to(RIGHT * 3.3 + UP * 0.75)
        self.add(self.tree, self.array, self.title_text)
        _settle(self, at, max_width, max_height)

    def set_state(self, index: int, state: str):
        _check_index(index, len(self.values), "heap index")
        _style(state)
        return AnimationGroup(
            self.tree.set_state(index, state),
            self.array.set_state(index, state),
            lag_ratio=0,
        )

    def swap(self, i: int, j: int):
        _check_index(i, len(self.values))
        _check_index(j, len(self.values))
        self.values[i], self.values[j] = self.values[j], self.values[i]
        anims = []
        for index in (i, j):
            value = self.values[index]
            node = self.tree.nodes[index]
            new = _become(node.label, _text(value, size=28).move_to(node.label.get_center()))
            node.label = new
            anims.append(Indicate(new, color=C_TEXT, scale_factor=1.08))

            cell_text = self.array.value_texts[index]
            new_cell = _become(
                cell_text, _text(value, size=32).move_to(cell_text.get_center())
            )
            self.array.value_texts[index] = new_cell
            anims.append(Indicate(new_cell, color=C_TEXT, scale_factor=1.08))
        return AnimationGroup(*anims, lag_ratio=0)


# ---------------------------------------------------------------------------
# StatePanel: variables as chips
# ---------------------------------------------------------------------------

class StatePanel(_IntroMixin, VGroup):
    """Named state chips such as ``need = 7``, updated as the trace advances."""

    def __init__(
        self,
        items: dict,
        side: str = "bottom",
        at=None,
        max_width: float | None = 8.6,
        **kwargs,
    ):
        super().__init__(**kwargs)
        if side not in {"bottom", "left", "right"}:
            raise ValueError("side must be 'bottom', 'left' or 'right'")
        self.side = side
        self.store: dict = {}
        # An explicit anchor keeps a panel in its own lane: two scenes in one
        # comparison would otherwise stack their chips on the same line.
        self._anchor = at
        self._max_width = max_width
        for name, value in items.items():
            self._add(str(name), value)
        self._relayout()
        _fit(self, max_width, None)

    def _chip(self, name, value, state="default"):
        style = _style(state)
        text = _text(_chip_label(name, value), size=24, color=C_TEXT)
        bg = RoundedRectangle(
            corner_radius=0.16,
            width=text.width + 0.5,
            height=max(0.56, text.height + 0.3),
            fill_color=style["fill"],
            fill_opacity=style["fill_opacity"],
            stroke_color=style["stroke"],
            stroke_width=style["stroke_width"],
        )
        text.move_to(bg.get_center())
        chip = VGroup(bg, text)
        chip.bg, chip.text = bg, text
        return chip

    def _add(self, name, value, state="default"):
        chip = self._chip(name, value, state)
        self.add(chip)
        self.store[name] = chip
        return chip

    def _relayout(self):
        chips = list(self.store.values())
        if not chips:
            return
        if self.side == "bottom":
            group = VGroup(*chips).arrange(RIGHT, buff=0.3)
            x = 0.0 if self._anchor is None else float(self._anchor[0])
            y = -2.72 if self._anchor is None else float(self._anchor[1])
            group.move_to(np.array([x, y, 0.0]))
        else:
            group = VGroup(*chips).arrange(DOWN, buff=0.22, aligned_edge=LEFT)
            x = -5.55 if self.side == "left" else 5.55
            y = 1.6
            group.move_to(np.array([x, y, 0.0]))
            if self.side == "right":
                group.align_to(np.array([5.55, 0, 0]), RIGHT)

    def intro(self, *args, fast: bool = False, at=None):
        position = at
        for arg in args:
            if isinstance(arg, bool):
                fast = fast or arg
            elif position is None:
                position = arg
        if position is not None:
            try:
                self.move_to(position)
                _clamp_into_frame(self)
            except Exception:
                pass
        _stamp(self, self)
        return FadeIn(self, shift=UP * 0.1, run_time=0.3 if fast else T_STEP)

    def update(self, name=None, value=None, state: str = "active", **kwargs):
        # Mobject.update(dt, recursive=...) is called by Manim's animation
        # machinery; keep it working while the documented chip API stays
        # update(name, value, state).
        if kwargs or name is None or isinstance(name, (int, float)):
            call = dict(kwargs)
            if isinstance(name, (int, float)):
                call.setdefault("dt", name)
            return super().update(**call)
        name = str(name)
        if name not in self.store:
            chip = self._add(name, value, state)
            self._relayout()
            return FadeIn(chip, shift=UP * 0.08)
        chip = self.store[name]
        new_text = _become(
            chip.text,
            _text(_chip_label(name, value), size=24, color=C_TEXT).move_to(
                chip.text.get_center()
            ),
        )
        chip.text = new_text
        chip.bg.stretch_to_fit_width(new_text.width + 0.5 + 0.02)
        # The chip just changed width: re-arrange so long values never push the
        # neighbouring chips into each other, and keep the row inside the frame.
        self._relayout()
        _fit(self, self._max_width, None)
        return AnimationGroup(
            Indicate(new_text, color=C_TEXT, scale_factor=1.06),
            _state_anim(chip.bg, state),
            lag_ratio=0,
        )

    def set_state(self, name, state: str):
        if name not in self.store:
            raise ValueError(f"{name!r} is not a chip in this panel")
        return _state_anim(self.store[name].bg, state)


# ---------------------------------------------------------------------------
# scene helpers
# ---------------------------------------------------------------------------

CAPTION_Y = -3.5
CAPTION_CHARS = 70


def show_title(scene, text: str):
    """Title at the top with an accent underline (one per scene)."""
    old = getattr(scene, "_pebble_title", None)
    if old is not None:
        scene.remove(old)
    title = _text(text, size=36, color=C_TEXT, weight=MEDIUM)
    title.to_edge(UP, buff=0.3)
    if title.width > 12.0:
        title.scale_to_fit_width(12.0)
        title.to_edge(UP, buff=0.3)
    underline = Line(LEFT, RIGHT, color=C_ACCENT, stroke_width=3)
    underline.set_width(min(1.4, max(0.8, title.width * 0.35)))
    underline.next_to(title, DOWN, buff=0.1)
    old_card = getattr(scene, "_pebble_titlecard", None)
    if old_card is not None:
        scene.remove(old_card)
        scene._pebble_titlecard = None
    scene._pebble_title = VGroup(title, underline)
    _reserve(title, underline)
    scene.play(FadeIn(title, shift=DOWN * 0.08), Create(underline), run_time=T_FAST)


def title_card(scene, title: str, subtitle: str | None = None):
    """Opening card for scene 1."""
    title_mob = _text(title, size=54, color=C_TEXT, weight=MEDIUM)
    if title_mob.width > 12.0:
        title_mob.scale_to_fit_width(12.0)
    title_mob.move_to(UP * 0.55)
    accent = Line(LEFT, RIGHT, color=C_ACCENT, stroke_width=3)
    accent.set_width(min(2.4, max(1.2, title_mob.width * 0.3)))
    accent.next_to(title_mob, DOWN, buff=0.25)
    parts = [title_mob, accent]
    if subtitle:
        sub = _text(subtitle, size=30, color=C_MUTED)
        if sub.width > 11.0:
            sub.scale_to_fit_width(11.0)
        sub.next_to(accent, DOWN, buff=0.35)
        parts.append(sub)
    _reserve(*parts)
    scene.play(
        FadeIn(title_mob, shift=DOWN * 0.1), Create(accent), run_time=T_STEP
    )
    if subtitle:
        scene.play(FadeIn(parts[-1], shift=DOWN * 0.08), run_time=T_FAST)
    scene._pebble_titlecard = VGroup(*parts)


def _caption_mobject(value: str, max_width: float):
    """Build a caption that never ellipsizes a sentence: wrap before cutting.

    A truncated caption ("...in constant ti…") reads like a broken video, so a
    long line is balanced over two lines and only a genuinely over-long caption
    (more than two full lines) is shortened.
    """
    value = " ".join(str(value).split())
    if len(value) > CAPTION_CHARS * 2:
        value = value[: CAPTION_CHARS * 2 - 1].rstrip() + "…"

    single = _text(value, size=26, color=C_TEXT)
    if single.width <= max_width:
        return single

    words = value.split()
    best = None
    fallback = None
    for cut in range(1, len(words)):
        left, right = " ".join(words[:cut]), " ".join(words[cut:])
        two = _text(left + "\n" + right, size=26, color=C_TEXT, line_spacing=1.05)
        if two.height > 1.85:
            break
        if fallback is None or abs(len(left) - len(right)) < fallback[0]:
            fallback = (abs(len(left) - len(right)), two)
        if two.width <= max_width:
            best = two
            if abs(len(left) - len(right)) <= 8:
                break
    chosen = best if best is not None else (fallback[1] if fallback else None)
    if chosen is not None:
        if chosen.width > max_width:
            chosen.scale_to_fit_width(max_width)
        return chosen
    single.scale_to_fit_width(max_width)
    return single


def set_caption(scene, text: str):
    """One-line caption at the bottom; crossfades the previous caption."""
    legend = bool(getattr(scene, "_pebble_legend", False))
    max_width = 8.2 if legend else 11.6
    caption = _caption_mobject(text, max_width)
    x = -1.4 if legend else 0.0
    caption.move_to(np.array([x, CAPTION_Y, 0.0]))
    old = getattr(scene, "_pebble_caption", None)
    scene._pebble_caption = caption
    _reserve(caption)
    anims = [FadeIn(caption)]
    if old is not None:
        anims.insert(0, FadeOut(old))
    scene.play(AnimationGroup(*anims, lag_ratio=0), run_time=T_STEP)


def show_legend(scene):
    """Small colour legend, bottom right (scene 1 only)."""
    entries = []
    for state, label in (
        ("active", "now"),
        ("good", "done"),
        ("bad", "wrong"),
        ("dim", "passed"),
    ):
        style = _style(state)
        swatch = RoundedRectangle(
            corner_radius=0.05,
            width=0.22,
            height=0.22,
            fill_color=style["fill"],
            fill_opacity=1,
            stroke_color=style["stroke"],
            stroke_width=2,
        )
        text = _text(label, size=18, color=C_MUTED)
        text.next_to(swatch, RIGHT, buff=0.1)
        _reserve(text)
        entries.append(VGroup(swatch, text))
    legend = VGroup(*entries).arrange(RIGHT, buff=0.32)
    if legend.width > 5.2:
        legend.scale_to_fit_width(5.2)
    legend.move_to(np.array([3.2, -2.92, 0.0]))
    scene._pebble_legend = True
    scene.play(FadeIn(legend, shift=UP * 0.05), run_time=T_FAST)


def step_tag(scene, n: int, total: int):
    """``Step n of total`` tag at the top right."""
    old = getattr(scene, "_pebble_step", None)
    tag = _text(f"Step {n} of {total}", size=22, color=C_MUTED)
    tag.to_corner(UP + RIGHT, buff=0.32)
    overflow = tag.get_right()[0] - (SAFE_WIDTH / 2 - 0.05)
    if overflow > 0:
        tag.shift(LEFT * overflow)
    scene._pebble_step = tag
    _reserve(tag)
    if old is not None:
        scene.remove(old)
        scene.play(FadeIn(tag), run_time=T_FAST)
    else:
        scene.play(FadeIn(tag, shift=DOWN * 0.05), run_time=T_FAST)


def result_cards(scene, answer: str, time: str, space: str):
    """Closing scene: Answer / Time / Space cards."""
    # A title card and the result cards occupy the same band: if scene 1 style
    # content is still up, take it down so the two can never overlap.
    old_card = getattr(scene, "_pebble_titlecard", None)
    if old_card is not None:
        scene.play(FadeOut(old_card), run_time=T_FAST)
        scene.remove(old_card)
        scene._pebble_titlecard = None
    cards = []
    for label, value, colour in (
        ("Answer", answer, C_GOOD),
        ("Time", time, C_ACCENT),
        ("Space", space, C_ACCENT),
    ):
        card = _panel(3.75, 2.3, "default", corner=0.2)
        card.set_stroke(color=colour, width=2.6)
        heading = _text(label, size=22, color=C_MUTED)
        heading.move_to(card.get_top() + DOWN * 0.4)
        body = _text(value, size=38 if label == "Answer" else 34, color=C_TEXT,
                     weight=MEDIUM)
        if body.width > 3.3:
            body.scale_to_fit_width(3.3)
        body.move_to(card.get_center() + DOWN * 0.28)
        _reserve(heading, body)
        group = VGroup(card, heading, body)
        cards.append(group)
    row = VGroup(*cards).arrange(RIGHT, buff=0.45)
    row.move_to(DOWN * 0.15)
    scene.play(
        LaggedStart(*[FadeIn(card, shift=UP * 0.1) for card in cards], lag_ratio=0.15),
        run_time=T_SLOW,
    )


def compare_panels(
    scene,
    left_title: str,
    right_title: str,
    left_state: str = "bad",
    right_state: str = "good",
):
    """Two framed half-stage panels; returns anchors for structures."""
    anchors = []
    panels = []
    for side, title_text, state in (
        (-1, left_title, left_state),
        (1, right_title, right_state),
    ):
        style = _style(state)
        panel = RoundedRectangle(
            corner_radius=0.2,
            width=6.05,
            height=5.15,
            fill_color=C_PANEL,
            fill_opacity=0.5,
            stroke_color=style["stroke"],
            stroke_width=2.6,
        )
        panel.move_to(np.array([side * 3.2, -0.35, 0.0]))
        heading = _text(title_text, size=26, color=style["stroke"], weight=MEDIUM)
        heading.move_to(panel.get_top() + DOWN * 0.4)
        _reserve(heading)
        group = VGroup(panel, heading)
        panels.append(group)
        # Anchors sit below the heading, in the middle of the free inner area, so
        # a structure built there never covers the panel title.
        anchors.append(
            np.array([side * 3.2, panel.get_top()[1] - 0.85 - 2.0, 0.0])
        )
    scene.play(
        LaggedStart(*[FadeIn(panel, shift=UP * 0.08) for panel in panels], lag_ratio=0.2),
        run_time=T_STEP,
    )
    return anchors[0], anchors[1]


# The reference documents these helpers as ``self.show_title(...)`` etc., so bind
# them onto Manim's Scene class. They keep their module-level names too.
def _install_scene_methods() -> None:
    for helper in (
        show_title,
        title_card,
        set_caption,
        show_legend,
        step_tag,
        result_cards,
        compare_panels,
    ):
        setattr(Scene, helper.__name__, helper)


_install_scene_methods()
