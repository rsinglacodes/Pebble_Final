"""The kit gallery: one hand-written video that exercises every visual component.

``python run_local.py --kit-gallery`` renders this at low quality, writes
``workspace/kit_gallery/contact_sheet.png`` (12 evenly spaced frames) and prints
the number of layout-audit issues (must be zero). It is the visual regression
check for the kit itself: no LLM involved.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

from pebble.mux import probe_duration
from pebble.renderer import (
    KIT_TEMPLATE,
    HELPER_IMPORT,
    install_runtime,
    read_audit,
)
from pebble.workspace import JobWorkspace

logger = logging.getLogger(__name__)

GALLERY_JOB_ID = "kit_gallery"
SCENE_SECONDS = 4.2
MANIM_TIMEOUT = 600
COLUMNS = 4
FRAME_WIDTH = 560

GALLERY_CLASSES = (
    "Scene1_TitleCard",
    "Scene2_TwoSum",
    "Scene3_Tree",
    "Scene4_Graph",
    "Scene5_List",
    "Scene6_Grid",
    "Scene7_Stack",
    "Scene8_Queue",
    "Scene9_Bars",
    "Scene10_Heap",
    "Scene11_Compare",
    "Scene12_Result",
)

GALLERY_SCRIPT = '''from manim import *


class Scene1_TitleCard(Scene):
    def construct(self):
        self.title_card("Two Sum", "Find two numbers that add up to a target")
        self.show_legend()
        self.set_caption("Hashing turns a search into a lookup")
        self.wait(1.5)
        finish_scene(self)


class Scene2_TwoSum(Scene):
    def construct(self):
        self.show_title("Two Sum")
        self.step_tag(1, 3)
        nums = ArrayViz([2, 7, 11, 15], label="numbers", at=LEFT_LANE, max_width=5.4)
        seen = MapViz("seen", at=RIGHT_LANE, max_width=5.2)
        chips = StatePanel({"target": 9, "need": 7})
        self.play(nums.intro(), seen.intro(), chips.intro())
        i = nums.pointer("i", 0)
        self.play(i.intro())
        self.set_caption("Look at the first number")
        self.wait(0.4)
        self.play(nums.set_state(0, "active"), i.to(1))
        self.play(nums.set_state(0, "dim"), nums.set_state(1, "good"))
        self.play(seen.put("2", 0))
        self.play(chips.update("need", 2))
        self.set_caption("The partner of 7 is already stored")
        self.play(seen.hit("2"), nums.set_state(1, "good"))
        self.wait(0.5)
        finish_scene(self)


class Scene3_Tree(Scene):
    def construct(self):
        self.show_title("Path down a tree")
        tree = TreeViz([3, 9, 20, None, None, 15, 7])
        self.play(tree.intro())
        self.play(tree.set_state(0, "active"))
        self.set_caption("Start at the root")
        self.play(tree.set_state(1, "dim"), tree.set_edge(0, 2, "active"),
                  tree.set_state(2, "active"))
        self.play(tree.annotate(2, "visit 1"))
        self.set_caption("Only the right child is worth exploring")
        self.play(tree.set_state(2, "good"), tree.set_state(5, "active"),
                  tree.set_edge(2, 5, "active"))
        self.play(tree.annotate(5, "visit 2"))
        self.wait(0.5)
        finish_scene(self)


class Scene4_Graph(Scene):
    def construct(self):
        self.show_title("Shortest paths")
        graph = GraphViz(
            ["A", "B", "C", "D"],
            [("A", "B", 4), ("A", "C", 1), ("C", "B", 1), ("B", "D", 2)],
            directed=True,
            at=LEFT_LANE,
            max_width=6.0,
        )
        queue = QueueViz("frontier", ["A"], at=RIGHT_LANE)
        self.play(graph.intro(), queue.intro())
        self.play(graph.tag("A", "0"))
        self.set_caption("Start with distance zero at the source")
        self.play(graph.set_node("A", "good"), graph.set_node("C", "active"),
                  graph.set_edge("A", "C", "active"))
        self.play(graph.tag("C", "1"), queue.enqueue("C"))
        self.set_caption("One step away, so the distance is one")
        self.play(queue.dequeue(), graph.set_node("C", "good"),
                  graph.set_node("B", "active"), graph.set_edge("C", "B", "active"))
        self.play(graph.tag("B", "2"))
        self.wait(0.5)
        finish_scene(self)


class Scene5_List(Scene):
    def construct(self):
        self.show_title("Reversing a list")
        nodes = LinkedListViz([1, 2, 3, 4])
        self.play(nodes.intro())
        prev = nodes.pointer("prev", 0, level=1)
        curr = nodes.pointer("curr", 1)
        self.play(prev.intro(), curr.intro())
        self.set_caption("Keep the previous node while walking forward")
        self.play(nodes.set_state(0, "dim"), nodes.set_state(1, "active"))
        self.play(nodes.relink(1, 0))
        self.set_caption("Point the current node backwards")
        self.play(nodes.relink(2, 1), curr.to(2), prev.to(1))
        self.play(nodes.set_state(1, "good"), nodes.set_state(2, "active"))
        self.wait(0.5)
        finish_scene(self)


class Scene6_Grid(Scene):
    def construct(self):
        self.show_title("Counting paths")
        grid = GridViz(
            [[1, 1, 1], [1, 2, 3], [1, 3, 6]],
            row_labels=["a", "b", "c"],
            col_labels=["0", "1", "2"],
        )
        self.play(grid.intro())
        self.play(grid.set_state((1, 1), "active"),
                  grid.link((0, 1), (1, 1)), grid.link((1, 0), (1, 1)))
        self.set_caption("Each cell adds its two neighbours")
        self.play(grid.set_value((1, 1), 2), grid.set_state((1, 1), "good"))
        self.play(grid.unlink(), grid.set_state([(1, 2), (2, 1)], "active"))
        self.play(grid.link((0, 2), (1, 2)), grid.link((1, 1), (1, 2)))
        self.set_caption("The value depends on the cell above and the one to the left")
        self.play(grid.set_value((1, 2), 3))
        self.wait(0.5)
        finish_scene(self)


class Scene7_Stack(Scene):
    def construct(self):
        self.show_title("A stack")
        stack = StackViz("history", ["open", "edit"])
        self.play(stack.intro())
        self.play(stack.push("save"))
        self.set_caption("The newest item sits on top")
        self.play(stack.peek())
        self.play(stack.pop())
        self.set_caption("Pop removes the most recent item first")
        self.play(stack.push("close"))
        self.wait(0.5)
        finish_scene(self)


class Scene8_Queue(Scene):
    def construct(self):
        self.show_title("A queue")
        queue = QueueViz("line", [1, 2])
        self.play(queue.intro())
        self.play(queue.enqueue(3))
        self.set_caption("New arrivals join at the back")
        self.play(queue.dequeue())
        self.set_caption("Service happens at the front")
        self.play(queue.enqueue(4), queue.enqueue(5))
        self.wait(0.5)
        finish_scene(self)


class Scene9_Bars(Scene):
    def construct(self):
        self.show_title("Comparing heights")
        bars = BarsViz([3, 1, 4])
        self.play(bars.intro())
        self.play(bars.set_state([0, 1], "active"))
        self.set_caption("Three is taller than one, so they swap")
        self.play(bars.swap(0, 1))
        self.play(bars.set_state(1, "good"), bars.set_state(2, "active"))
        self.set_caption("The largest value keeps moving right")
        self.wait(0.5)
        finish_scene(self)


class Scene10_Heap(Scene):
    def construct(self):
        self.show_title("A min heap")
        heap = HeapViz([1, 4, 3])
        self.play(heap.intro())
        self.play(heap.set_state(1, "active"))
        self.set_caption("The child is smaller than its parent")
        self.play(heap.swap(0, 1))
        self.play(heap.set_state(0, "good"))
        self.set_caption("Swap them and the smallest value becomes the root")
        self.wait(0.5)
        finish_scene(self)


class Scene11_Compare(Scene):
    def construct(self):
        self.show_title("Bug and fix")
        left_at, right_at = self.compare_panels("Original", "Corrected")
        wrong = ArrayViz([2, 7, 11, 15], show_index=False, at=left_at, max_width=5.2)
        right = ArrayViz([2, 7, 11, 15], show_index=False, at=right_at, max_width=5.2)
        self.play(wrong.intro(), right.intro())
        self.play(FadeIn(wrong.window(0, 2, "bad")))
        self.set_caption("The last pair is never checked")
        self.play(FadeIn(right.window(2, 3, "good")))
        self.set_caption("The loop has to include the final element")
        self.wait(0.6)
        finish_scene(self)


class Scene12_Result(Scene):
    def construct(self):
        self.show_title("Result")
        self.result_cards("[0, 1]", "O(n)", "O(n)")
        self.set_caption("One pass, one lookup per element")
        self.wait(0.8)
        finish_scene(self)
'''


@dataclass
class GalleryResult:
    workspace: Path
    video: Path
    duration: float
    contact_sheet: Path
    audit_issues: dict[str, list[str]] = field(default_factory=dict)

    @property
    def issue_count(self) -> int:
        return sum(len(issues) for issues in self.audit_issues.values())


def _write_runtime(workspace: JobWorkspace) -> None:
    install_runtime(workspace)
    workspace.animation_path.write_text(GALLERY_SCRIPT, encoding="utf-8")
    workspace.animation_render_path.write_text(
        HELPER_IMPORT + GALLERY_SCRIPT, encoding="utf-8"
    )
    workspace.targets_path.write_text(
        json.dumps({name: SCENE_SECONDS for name in GALLERY_CLASSES}, indent=2),
        encoding="utf-8",
    )


def _render_scene(workspace: JobWorkspace, class_name: str, quality: str) -> Path:
    media_dir = workspace.media_dir / class_name
    cmd = [
        sys.executable,
        "-m",
        "manim",
        "render",
        f"-q{quality}",
        "--disable_caching",
        "--media_dir",
        str(media_dir),
        "-o",
        class_name,
        str(workspace.animation_render_path),
        class_name,
    ]
    completed = subprocess.run(
        cmd,
        cwd=str(workspace.root),
        capture_output=True,
        text=True,
        timeout=MANIM_TIMEOUT,
        env={**__import__("os").environ, "PEBBLE_LAYOUT_STRICT": "1"},
    )
    (workspace.render_logs_dir / f"{class_name}.log").write_text(
        (completed.stdout or "") + "\n--- stderr ---\n" + (completed.stderr or ""),
        encoding="utf-8",
    )
    output = None
    if media_dir.exists():
        matches = [
            path
            for path in media_dir.rglob(f"{class_name}.mp4")
            if "partial_movie_files" not in path.parts
        ]
        output = matches[0] if matches else None
    if completed.returncode != 0 or output is None:
        tail = "\n".join((completed.stderr or completed.stdout or "").splitlines()[-25:])
        raise RuntimeError(f"{class_name} failed to render:\n{tail}")
    return output


def _concat(clips: list[Path], out: Path) -> None:
    listing = out.parent / "concat.txt"
    listing.write_text(
        "\n".join("file '" + str(path.resolve()).replace("'", "'\\''") + "'" for path in clips),
        encoding="utf-8",
    )
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(listing),
            "-c",
            "copy",
            str(out),
        ],
        check=True,
        capture_output=True,
        timeout=300,
    )
    listing.unlink(missing_ok=True)


def contact_sheet(
    video: Path,
    out: Path,
    frames: int = 12,
    columns: int = 4,
    frame_dir: Path | None = None,
) -> Path:
    """Tile evenly spaced frames of ``video`` into one PNG."""
    duration = probe_duration(video)
    directory = frame_dir or (video.parent / "frames")
    directory.mkdir(parents=True, exist_ok=True)
    for stale in directory.glob("sheet_*.png"):
        stale.unlink()
    step = duration / frames
    for index in range(frames):
        timestamp = min(duration - 0.1, step * index + step / 2)
        target = directory / f"sheet_{index:02d}.png"
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-ss",
                f"{timestamp:.2f}",
                "-i",
                str(video),
                "-frames:v",
                "1",
                "-vf",
                f"scale={FRAME_WIDTH}:-1",
                str(target),
            ],
            check=True,
            capture_output=True,
            timeout=120,
        )
    rows = (frames + columns - 1) // columns
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-loglevel",
            "error",
            "-pattern_type",
            "glob",
            "-i",
            str(directory / "sheet_*.png"),
            "-vf",
            f"tile={columns}x{rows}:padding=6:margin=6:color=0x1E293B",
            "-frames:v",
            "1",
            str(out),
        ],
        check=True,
        capture_output=True,
        timeout=180,
    )
    return out


def run_gallery(quality: str = "l", job_id: str = GALLERY_JOB_ID) -> GalleryResult:
    """Render the gallery, stitch it, build the contact sheet, collect audit issues."""
    workspace = JobWorkspace(job_id)
    _write_runtime(workspace)

    clips: list[Path] = []
    issues: dict[str, list[str]] = {}
    for class_name in GALLERY_CLASSES:
        logger.info("[gallery] %s", class_name)
        clip = _render_scene(workspace, class_name, quality)
        destination = workspace.scenes_dir / f"{class_name}.mp4"
        shutil.copyfile(clip, destination)
        clips.append(destination)
        issues[class_name] = read_audit(workspace, class_name)

    video = workspace.root / "gallery.mp4"
    _concat(clips, video)
    sheet = contact_sheet(video, workspace.root / "contact_sheet.png")
    return GalleryResult(
        workspace=workspace.root,
        video=video,
        duration=probe_duration(video),
        contact_sheet=sheet,
        audit_issues=issues,
    )
