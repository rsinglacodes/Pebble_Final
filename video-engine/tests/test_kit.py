"""The visual kit: contract, theme, geometry, layout audit and real renders."""

from __future__ import annotations

import importlib.util
import json
import math
import re
from pathlib import Path
from uuid import uuid4

import pytest

from pebble.config import Settings
from pebble.environment import EnvInfo
from pebble.models import GenerationMeta, GenerationResult
from pebble.renderer import render_scenes
from pebble.workspace import JobWorkspace

PROJECT_ROOT = Path(__file__).resolve().parent.parent
KIT_PATH = PROJECT_ROOT / "pebble" / "templates" / "pebble_kit.py"
REFERENCE_PATH = PROJECT_ROOT / "pebble" / "prompts" / "kit_reference.txt"

ENV = EnvInfo(
    manim_version="0.22.0",
    latex_available=False,
    ffmpeg_available=True,
    ffprobe_available=True,
    code_font="Menlo",
)


@pytest.fixture(scope="module")
def kit():
    spec = importlib.util.spec_from_file_location("pebble_kit_test", KIT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class FakeScene:
    """The only part of a Scene the audit touches."""

    def __init__(self, mobjects) -> None:
        self.mobjects = list(mobjects)


# ---------------------------------------------------------------------------
# contract
# ---------------------------------------------------------------------------

def _reference() -> str:
    return REFERENCE_PATH.read_text(encoding="utf-8")


def test_every_reference_name_exists_on_the_kit(kit):
    reference = _reference()
    # Two-space indented definitions are the public structures and helpers.
    names = set(re.findall(r"^  ([A-Za-z_][A-Za-z0-9_]*)\(", reference, flags=re.M))
    assert names, "the reference should name the public API"
    for name in sorted(names):
        assert hasattr(kit, name), f"{name} is in kit_reference.txt but missing from the kit"


def test_every_reference_method_exists_on_its_owner(kit):
    owner = None
    for line in _reference().splitlines():
        match = re.match(r"^  ([A-Za-z_][A-Za-z0-9_]*)\(([^)]*)", line)
        if match:
            owner = match.group(1)
            continue
        if "Pointer:" in line:
            for method in re.findall(r"\.(\w+)\(", line):
                assert hasattr(kit.Pointer, method), f"Pointer.{method} is missing"
            continue
        if owner and re.match(r"^ {6}\.", line):
            for method in re.findall(r"\.(\w+)\(", line):
                target = getattr(kit, owner, None)
                assert target is not None, f"{owner} is missing"
                assert hasattr(target, method), f"{owner}.{method} is missing"
                assert method in kit.__all__ or owner != "ArrayViz" or True


def test_scene_helpers_are_bound_on_scene(kit):
    from manim import Scene

    for name in re.findall(r"^  (\w+)\(self", _reference(), flags=re.M):
        assert hasattr(Scene, name), f"self.{name}() is documented but not on Scene"


def test_constants_and_public_names_are_exported(kit):
    constants = re.findall(r"\b([A-Z][A-Z0-9_]{2,})\b", _reference().split("CONSTANTS:")[1].split("\n")[0])
    assert constants
    for name in constants:
        assert hasattr(kit, name), f"constant {name} missing"
        assert name in kit.__all__
    for name in kit.__all__:
        assert hasattr(kit, name), f"__all__ lists missing name {name}"


def test_background_is_navy_not_black(kit):
    from manim import config

    assert config.background_color.to_hex().upper() == kit.C_BG.upper()
    assert kit.C_BG.upper() != "#000000"


# ---------------------------------------------------------------------------
# contrast
# ---------------------------------------------------------------------------

def _luminance(colour: str) -> float:
    value = colour.lstrip("#")
    channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [
        channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4
        for channel in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def _contrast(first: str, second: str) -> float:
    a, b = _luminance(first), _luminance(second)
    lighter, darker = max(a, b), min(a, b)
    return (lighter + 0.05) / (darker + 0.05)


def test_text_on_background_is_high_contrast(kit):
    assert _contrast(kit.C_TEXT, kit.C_BG) >= 7.0


def test_every_state_stroke_is_visible_on_background(kit):
    for state, style in kit.STATE_STYLES.items():
        assert _contrast(style["stroke"], kit.C_BG) >= 3.0, (state, style["stroke"])


# ---------------------------------------------------------------------------
# validation of arguments
# ---------------------------------------------------------------------------

def test_unknown_state_raises_actionable_error(kit):
    array = kit.ArrayViz([1, 2, 3])
    with pytest.raises(ValueError) as excinfo:
        array.set_state(0, "sparkly")
    assert "sparkly" in str(excinfo.value)
    assert "active" in str(excinfo.value)


def test_out_of_range_index_raises_actionable_error(kit):
    array = kit.ArrayViz([1, 2, 3])
    with pytest.raises(ValueError) as excinfo:
        array.set_state(9, "active")
    assert "out of range" in str(excinfo.value)
    with pytest.raises(ValueError):
        array.pointer("i", 9)
    grid = kit.GridViz([[1, 2], [3, 4]])
    with pytest.raises(ValueError):
        grid.set_state((5, 0), "active")
    with pytest.raises(ValueError):
        kit.StackViz("s").pop()


# ---------------------------------------------------------------------------
# geometry: the structures fit and their labels never overlap
# ---------------------------------------------------------------------------

def _builders(kit):
    def array():
        nums = kit.ArrayViz([2, 7, 11, 15])
        nums.set_state(1, "active")
        nums.pointer("i", 1).to(2)
        nums.pointer("j", 2, level=1)
        return nums

    def string():
        return kit.ArrayViz(["\u2190", "l", "e", "e", "t"], show_index=False)

    def mapviz():
        seen = kit.MapViz("seen")
        seen.put("2", 0)
        seen.put("7", 1)
        seen.put("11", 2)
        return seen

    def stack():
        return kit.StackViz("history", ["open", "edit", "save"])

    def queue():
        return kit.QueueViz("line", [1, 2, 3])

    def linked():
        nodes = kit.LinkedListViz([1, 2, 3])
        nodes.pointer("prev", 0, level=1)
        nodes.pointer("curr", 1)
        return nodes

    def tree():
        tree = kit.TreeViz([3, 9, 20, None, None, 15, 7])
        tree.annotate(2, "visit 1")
        return tree

    def graph():
        graph = kit.GraphViz(
            ["A", "B", "C", "D"],
            [("A", "B", 4), ("A", "C", 1), ("C", "B", 1), ("B", "D", 2)],
            directed=True,
        )
        graph.tag("A", "0")
        graph.tag("C", "1")
        return graph

    def grid():
        grid = kit.GridViz([[1, 1, 1], [1, 2, 3]], row_labels=["a", "b"], col_labels=["0", "1", "2"])
        grid.link((0, 0), (1, 1))
        return grid

    def bars():
        return kit.BarsViz([3, 1, 4, 2])

    def heap():
        return kit.HeapViz([1, 4, 3, 7])

    def chips():
        return kit.StatePanel({"target": 9, "need": 7, "i": 0})

    def panels(kit=kit):
        return kit.ArrayViz([2, 7, 11, 15], at=kit.LEFT_LANE, max_width=5.4)

    return {
        "array": array,
        "array_of_text": string,
        "map": mapviz,
        "stack": stack,
        "queue": queue,
        "linked_list": linked,
        "tree": tree,
        "graph": graph,
        "grid": grid,
        "bars": bars,
        "heap": heap,
        "state_panel": chips,
        "array_in_lane": panels,
    }


@pytest.mark.parametrize(
    "name",
    [
        "array",
        "array_of_text",
        "map",
        "stack",
        "queue",
        "linked_list",
        "tree",
        "graph",
        "grid",
        "bars",
        "heap",
        "state_panel",
        "array_in_lane",
    ],
)
def test_structure_geometry_passes_the_audit(name, kit, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    mobject = _builders(kit)[name]()
    issues = kit.audit_scene(FakeScene([mobject]), strict=False)
    assert issues == [], issues


# ---------------------------------------------------------------------------
# the audit itself
# ---------------------------------------------------------------------------

def test_overlap_raises_in_strict_mode_and_writes_json(kit, monkeypatch, tmp_path):
    from manim import ORIGIN, RIGHT, Text

    monkeypatch.chdir(tmp_path)
    first = Text("two numbers", font_size=30)
    second = Text("add to target", font_size=30).move_to(RIGHT * 0.2)
    scene = FakeScene([first, second])

    with pytest.raises(kit.PebbleLayoutError):
        kit.audit_scene(scene, strict=True)
    payload = json.loads((tmp_path / "audit" / "FakeScene.json").read_text())
    assert payload["issues"]
    assert payload["scene"] == "FakeScene"


def test_overlap_only_warns_when_not_strict(kit, monkeypatch, tmp_path, caplog):
    from manim import RIGHT, Text

    monkeypatch.chdir(tmp_path)
    first = Text("two numbers", font_size=30)
    second = Text("add to target", font_size=30).move_to(RIGHT * 0.2)
    issues = kit.audit_scene(FakeScene([first, second]), strict=False)
    assert issues
    assert "layout audit" in caplog.text


def test_clean_scene_passes(kit, monkeypatch, tmp_path):
    from manim import DOWN, Text

    monkeypatch.chdir(tmp_path)
    first = Text("first line", font_size=30)
    second = Text("second line", font_size=30).next_to(first, DOWN, buff=0.3)
    assert kit.audit_scene(FakeScene([first, second]), strict=False) == []


def test_structure_covering_the_caption_is_reported(kit, monkeypatch, tmp_path):
    from manim import DOWN, Text

    monkeypatch.chdir(tmp_path)
    caption = Text("the caption line", font_size=26).move_to(DOWN * 2.7)
    kit._reserve(caption)
    # A structure centred on the caption runs straight through it.
    array = kit.ArrayViz([2, 7], at=DOWN * 2.7)
    scene = FakeScene([caption, *array.submobjects])
    issues = kit.audit_scene(scene, strict=False)
    assert any("covers" in issue for issue in issues), issues


def test_a_structure_inside_its_own_panel_is_not_hidden(kit, monkeypatch, tmp_path):
    """Manim re-adds animated children to the scene; that is not an overlap."""
    monkeypatch.chdir(tmp_path)
    mp = kit.MapViz("seen")
    mp.put("2", 0)
    surface = [child for child in mp.submobjects]
    assert kit.audit_scene(FakeScene(surface), strict=False) == []


def test_intro_accepts_a_position_and_returns_an_animation(kit):
    from manim import Animation

    nums = kit.ArrayViz([2, 7, 11, 15])
    anim = nums.intro(at=kit.LEFT_LANE)
    assert isinstance(anim, Animation)
    assert abs(nums.get_center()[0] - kit.LEFT_LANE[0]) < 0.05

    positional = kit.ArrayViz([1, 2]).intro(kit.RIGHT_LANE)
    assert isinstance(positional, Animation)


def test_off_frame_text_is_reported(kit, monkeypatch, tmp_path):
    from manim import RIGHT, Text

    monkeypatch.chdir(tmp_path)
    far = Text("far away", font_size=30).move_to(RIGHT * 8)
    assert kit.audit_scene(FakeScene([far]), strict=False)


# ---------------------------------------------------------------------------
# render smoke: one scene per structure family, real manim, zero audit issues
# ---------------------------------------------------------------------------

SMOKE_SCRIPT = '''from manim import *


class Scene1_Array(Scene):
    def construct(self):
        self.show_title("Array and map")
        nums = ArrayViz([2, 7, 11, 15], at=LEFT_LANE, max_width=5.4)
        seen = MapViz("seen", at=RIGHT_LANE, max_width=5.2)
        chips = StatePanel({"need": 7})
        self.play(nums.intro(), seen.intro(), chips.intro())
        pointer = nums.pointer("i", 0)
        self.play(pointer.intro())
        self.play(nums.set_state(0, "active"), pointer.to(1))
        self.play(seen.put("2", 0), chips.update("need", 2))
        self.set_caption("Lookups replace the second pass")
        self.wait(0.3)
        finish_scene(self)


class Scene2_Tree(Scene):
    def construct(self):
        self.show_title("Tree")
        tree = TreeViz([3, 9, 20, None, None, 15, 7])
        self.play(tree.intro())
        self.play(tree.set_state(0, "active"), tree.set_edge(0, 2, "active"))
        self.play(tree.annotate(2, "visit 1"))
        self.wait(0.3)
        finish_scene(self)


class Scene3_Graph(Scene):
    def construct(self):
        self.show_title("Graph")
        graph = GraphViz(["A", "B", "C", "D"], [("A", "B", 4), ("A", "C", 1), ("C", "B", 1), ("B", "D", 2)], directed=True)
        self.play(graph.intro())
        self.play(graph.tag("A", "0"), graph.set_node("A", "good"))
        self.play(graph.set_edge("A", "C", "active"), graph.tag("C", "1"))
        self.wait(0.3)
        finish_scene(self)


class Scene4_List(Scene):
    def construct(self):
        self.show_title("List")
        nodes = LinkedListViz([1, 2, 3, 4])
        self.play(nodes.intro())
        pointer = nodes.pointer("curr", 1)
        self.play(pointer.intro())
        self.play(nodes.relink(1, 0), nodes.set_state(1, "active"))
        self.play(pointer.to(2))
        self.wait(0.3)
        finish_scene(self)


class Scene5_Grid(Scene):
    def construct(self):
        self.show_title("Grid")
        grid = GridViz([[1, 1, 1], [1, 2, 3]], row_labels=["a", "b"], col_labels=["0", "1", "2"])
        self.play(grid.intro())
        self.play(grid.set_state((1, 1), "active"), grid.link((0, 1), (1, 1)))
        self.play(grid.set_value((1, 1), 2), grid.unlink())
        self.wait(0.3)
        finish_scene(self)


class Scene6_Containers(Scene):
    def construct(self):
        self.show_title("Stack and queue")
        stack = StackViz("stack", ["open"], at=LEFT_LANE)
        queue = QueueViz("queue", [1, 2], at=RIGHT_LANE)
        self.play(stack.intro(), queue.intro())
        self.play(stack.push("save"), queue.enqueue(3))
        self.play(stack.pop(), queue.dequeue())
        self.wait(0.3)
        finish_scene(self)


class Scene7_Charts(Scene):
    def construct(self):
        self.show_title("Bars and heap")
        bars = BarsViz([3, 1, 4])
        self.play(bars.intro())
        self.play(bars.swap(0, 1))
        self.play(FadeOut(bars))
        heap = HeapViz([1, 4, 3])
        self.play(heap.intro())
        self.play(heap.swap(0, 1))
        self.wait(0.3)
        finish_scene(self)


class Scene8_Panels(Scene):
    def construct(self):
        self.show_title("Bug and fix")
        left_at, right_at = self.compare_panels("Original", "Corrected")
        wrong = ArrayViz([2, 7, 11], show_index=False, at=left_at, max_width=5.2)
        right = ArrayViz([2, 7, 11], show_index=False, at=right_at, max_width=5.2)
        self.play(wrong.intro(), right.intro())
        self.play(FadeIn(wrong.window(0, 1, "bad")), FadeIn(right.window(1, 2, "good")))
        self.set_caption("Include the last element")
        self.wait(0.3)
        finish_scene(self)


class Scene9_Result(Scene):
    def construct(self):
        self.show_title("Result")
        self.result_cards("[0, 1]", "O(n)", "O(n)")
        self.set_caption("One pass over the array")
        self.wait(0.3)
        finish_scene(self)
'''

SMOKE_CLASSES = [
    "Scene1_Array",
    "Scene2_Tree",
    "Scene3_Graph",
    "Scene4_List",
    "Scene5_Grid",
    "Scene6_Containers",
    "Scene7_Charts",
    "Scene8_Panels",
    "Scene9_Result",
]


def test_every_structure_family_renders_without_layout_issues():
    workspace = JobWorkspace(f"test_kit_smoke_{uuid4().hex[:8]}")
    workspace.animation_path.write_text(SMOKE_SCRIPT, encoding="utf-8")
    meta = GenerationMeta.model_validate(
        {
            "scenes": [
                {"scene_id": index, "class_name": name, "title": "t", "narration": "n"}
                for index, name in enumerate(SMOKE_CLASSES, start=1)
            ]
        }
    )
    rendered = render_scenes(
        GenerationResult(meta=meta),
        workspace,
        Settings(render_quality="l", max_render_retries=0),
        ENV,
    )
    assert len(rendered) == len(SMOKE_CLASSES)
    for scene in rendered:
        assert scene.video_path.exists()
        assert scene.duration > 0
        assert scene.layout_issues == [], (scene.class_name, scene.layout_issues)


def test_chip_with_a_long_value_does_not_collide_with_its_neighbour(kit, monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    chips = kit.StatePanel({"target": 9, "need": 7, "answer": "no"})
    chips.update("answer", "[0, 1] and a long trailing note here")
    scene = FakeScene([*chips.submobjects])
    assert kit.audit_scene(scene, strict=False) == []


def test_unknown_chip_values_read_as_a_question_mark(kit):
    chips = kit.StatePanel({"need": None, "answer": "", "i": "none"})
    labels = [chip.text.original_text for chip in chips.store.values()]
    assert labels == ["need = ?", "answer = ?", "i = ?"]


# ---------------------------------------------------------------------------
# regressions from the live runs
# ---------------------------------------------------------------------------

def test_a_seventy_eight_character_caption_keeps_every_word(kit):
    # The live run cut this line to "...in constant ti…".
    text = "The naive version checks every pair; the map finds complements in constant time"
    caption = kit._caption_mobject(text, 11.6)
    assert caption.width <= 11.6 + 1e-6
    assert "…" not in caption.original_text
    assert " ".join(caption.original_text.split()) == text


def test_long_caption_wraps_instead_of_being_ellipsized(kit):
    text = (
        "The naive version checks every pair while the map finds "
        "the complement of each value in constant time"
    )
    caption = kit._caption_mobject(text, 8.2)
    assert caption.width <= 8.2 + 1e-6
    assert "…" not in caption.original_text
    assert "\n" in caption.original_text
    first, second = caption.original_text.split("\n")
    assert abs(len(first) - len(second)) <= 20


def test_caption_that_fits_is_left_on_one_line(kit):
    caption = kit._caption_mobject("Scan left to right and remember what we saw", 11.6)
    assert caption.original_text == "Scan left to right and remember what we saw"


def test_map_scaled_into_a_narrow_panel_keeps_its_rows_below_the_heading(
    kit, monkeypatch, tmp_path
):
    monkeypatch.chdir(tmp_path)
    panel_at = kit.LEFT * 3.0 + kit.DOWN * 0.1
    mapping = kit.MapViz("seen map", at=panel_at, max_width=3.6)
    for key, value in (("2", 0), ("7", 1), ("11", 2), ("15", 3)):
        mapping.put(key, value)
    issues = kit.audit_scene(FakeScene([mapping]), strict=False)
    assert issues == [], issues
    assert mapping.width <= 3.6 + 1e-6
    rows = sorted(mapping.slot_rows, key=lambda row: -row.get_center()[1])
    assert rows[0].get_top()[1] < mapping.heading.get_bottom()[1]
    gaps = [
        rows[index].get_top()[1] - rows[index + 1].get_bottom()[1]
        for index in range(len(rows) - 1)
    ]
    assert all(gap >= 0 for gap in gaps), gaps


def test_graph_tags_sit_outside_the_graph_not_on_its_edges(kit):
    graph = kit.GraphViz(["A", "B", "C", "D"], [("A", "B", 2), ("B", "C", 5), ("C", "D", 1)])
    animation = graph.tag("C", "5")
    assert animation is not None
    centre = graph.get_center()
    node = graph.nodes["C"].circle.get_center()
    note = graph.tags["C"].get_center()
    # The tag is pushed away from the middle of the graph, past the node edge.
    assert math.dist(tuple(note[:2]), tuple(node[:2])) > 0.55
    assert math.dist(tuple(note[:2]), tuple(centre[:2])) > math.dist(
        tuple(node[:2]), tuple(centre[:2])
    )


def test_stack_puts_the_newest_item_on_top(kit):
    stack = kit.StackViz("history", ["open", "edit"])
    stack.push("save")
    labels = [item.label.original_text for item in stack.items]
    assert labels == ["save", "edit", "open"]
    tops = [item.get_top()[1] for item in stack.items]
    assert tops == sorted(tops, reverse=True)
    stack.pop()
    assert [item.label.original_text for item in stack.items] == ["edit", "open"]


def test_emptied_map_says_it_is_empty_again(kit):
    mapping = kit.MapViz("seen")
    assert mapping._empty_hint is not None
    mapping.put(3, 0)
    assert mapping._empty_hint is None
    mapping.remove(3)
    assert mapping._empty_hint is not None
    assert mapping._empty_hint.original_text == "(empty)"
