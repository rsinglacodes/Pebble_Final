"""Validate an LLM generation against the pipeline's structural and safety rules.

Returns a list of human-readable problems; an empty list means the generation is
acceptable. The problems are fed back to the LLM on retry.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from pebble.environment import EnvInfo
from pebble.models import (
    STATE_MISSING,
    STATE_UNVERIFIED,
    STATE_VERIFIED,
    GenerationResult,
    VideoRequest,
)

SCENE_CLASS_RE = re.compile(r"class\s+(Scene\d+_[A-Za-z0-9_]+)\s*\(Scene\)")

ALLOWED_IMPORTS = {
    "manim",
    "math",
    "itertools",
    "collections",
    "heapq",
    "functools",
    "typing",
    "bisect",
    "copy",
    "dataclasses",
    "numpy",
    "string",
}

FORBIDDEN_NAMES = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
    "input",
    "globals",
    "locals",
    "getattr",
    "setattr",
    "delattr",
    "os",
    "sys",
    "subprocess",
    "shutil",
    "socket",
    "requests",
    "urllib",
    "pathlib",
}

LATEX_ONLY_NAMES = {
    "MathTex",
    "Tex",
    "Matrix",
    "IntegerMatrix",
    "DecimalMatrix",
    "DecimalNumber",
    "Integer",
    "Variable",
    "Axes",
    "NumberPlane",
    "NumberLine",
}

FINISH_SCENE = "finish_scene"
KIT_MODULES = {"pebble_kit", "pebble_helpers"}

# Everything the kit provides. A generated script must never redefine these.
KIT_STRUCTURES = {
    "ArrayViz",
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
    "Pointer",
}
KIT_HELPERS = {
    "show_title",
    "title_card",
    "set_caption",
    "show_legend",
    "step_tag",
    "result_cards",
    "compare_panels",
    "audit_scene",
}
KIT_CONSTANTS = {
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
}
KIT_NAMES = KIT_STRUCTURES | KIT_HELPERS | KIT_CONSTANTS

# Anything that reads as source code or pseudocode on screen.
CODE_LINE_RE = re.compile(
    r"(?m)^\s*(def|class|import|from|for|while|if|elif|else|return|yield|try|"
    r"except|finally|raise|with|lambda|assert|print|pass|break|continue)\b"
    r"[^\n]*(:|\(|=)"
)
SUBSCRIPT_RE = re.compile(
    r"\b[A-Za-z_][A-Za-z0-9_]*\s*\[\s*[A-Za-z_][A-Za-z0-9_]*"
    r"(\s*[+\-]\s*\d+)?\s*\]"
)
CALL_SYNTAX_RE = re.compile(r"\b[a-z_][a-z0-9_]*\([^()\n]*\)")
CODE_OPERATORS = ("==", "!=", "+=", "-=", "*=", "/=", "//", "&&", "||")
MIN_TEXT_SIZE = 20

ALLOWED_SOLUTION_SOURCES = {"provided", "corrected", "generated"}
REQUIRED_META_FIELDS = ("problem_summary", "solution_source", "programming_language", "complexity", "validation")

_DUNDER_RE = re.compile(r"^__.+__$")


def scene_class_names(manim_code: str) -> list[str]:
    """Scene class names in source order."""
    return [match.group(1) for match in SCENE_CLASS_RE.finditer(manim_code)]


def validate_manim_code(
    manim_code: str, expected_class_names: list[str], latex_available: bool
) -> list[str]:
    """Shape check used by the render repair loop (same rules as generation).

    The repaired script must parse, keep the safety rules and keep exactly the
    same Scene classes in the same order, otherwise the fix is rejected.
    """
    problems: list[str] = []
    if not (manim_code or "").strip():
        return ["manim_code is empty"]

    if "from manim import *" not in manim_code:
        problems.append("manim_code must contain 'from manim import *'")

    try:
        tree = ast.parse(manim_code)
    except SyntaxError as exc:
        problems.append(f"manim_code is not valid Python: {exc.msg} (line {exc.lineno})")
        return problems

    problems.extend(_check_imports(tree))
    problems.extend(_check_names(tree, latex_available))
    problems.extend(_check_finish_scene(tree, list(expected_class_names)))
    problems.extend(_check_config(tree))
    problems.extend(_check_kit_rules(tree, manim_code))
    problems.extend(_check_no_raw_text(tree))
    problems.extend(_check_kit_methods(tree))
    problems.extend(_check_intro_usage(tree))
    problems.extend(_check_result_scene(tree))
    problems.extend(_check_panel_lanes(tree))
    problems.extend(_check_no_code(manim_code))
    problems.extend(_check_text_sizes(tree))
    problems.extend(_check_caption_length(tree))

    found = scene_class_names(manim_code)
    if found != list(expected_class_names):
        problems.append(
            f"scene classes must stay exactly {list(expected_class_names)} in order, got {found}"
        )

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            subclasses_scene = any(
                (isinstance(base, ast.Name) and base.id == "Scene")
                or (isinstance(base, ast.Attribute) and base.attr == "Scene")
                for base in node.bases
            )
            if subclasses_scene and node.name not in expected_class_names:
                problems.append(
                    f"class '{node.name}' subclasses Scene but is not one of the expected scenes"
                )
    return problems


def _import_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Import):
        return node.names[0].name.split(".")[0]
    if isinstance(node, ast.ImportFrom):
        return (node.module or "").split(".")[0]
    return None


def _check_imports(tree: ast.AST) -> list[str]:
    problems: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            name = _import_name(node)
            if name is None:
                continue
            if name not in ALLOWED_IMPORTS:
                where = getattr(node, "lineno", "?")
                problems.append(f"line {where}: import of '{name}' is not allowed")
    return problems


def _check_names(tree: ast.AST, latex_available: bool) -> list[str]:
    problems: list[str] = []
    for node in ast.walk(tree):
        where = getattr(node, "lineno", "?")
        if isinstance(node, ast.Name):
            if node.id in FORBIDDEN_NAMES:
                problems.append(f"line {where}: use of '{node.id}' is not allowed")
            elif node.id == "Code":
                problems.append(
                    f"line {where}: Manim's Code class is not allowed; draw code with Text lines"
                )
            elif not latex_available and node.id in LATEX_ONLY_NAMES:
                problems.append(
                    f"line {where}: '{node.id}' requires LaTeX, which is not available"
                )
        elif isinstance(node, ast.Attribute):
            attr = node.attr
            if _DUNDER_RE.match(attr) and attr != "__name__":
                problems.append(f"line {where}: access to dunder attribute '{attr}' is not allowed")
            elif attr in FORBIDDEN_NAMES:
                problems.append(f"line {where}: access to '{attr}' is not allowed")
            elif attr == "Code":
                problems.append(
                    f"line {where}: Manim's Code class is not allowed; draw code with Text lines"
                )
            elif not latex_available and attr in LATEX_ONLY_NAMES:
                problems.append(
                    f"line {where}: '{attr}' requires LaTeX, which is not available"
                )
    return problems


def _check_config(tree: ast.AST) -> list[str]:
    """The kit owns the theme; a script must never touch Manim's config."""
    problems: list[str] = []
    for node in ast.walk(tree):
        name = None
        if isinstance(node, ast.Name) and node.id in {"config", "tempconfig"}:
            name = node.id
        elif isinstance(node, ast.Attribute) and node.attr in {"config", "tempconfig"}:
            name = node.attr
        elif isinstance(node, ast.alias) and node.name in {"config", "tempconfig"}:
            name = node.name
        if name:
            problems.append(
                f"line {getattr(node, 'lineno', '?')}: do not use '{name}' - the visual "
                "kit already sets the background, font and colours"
            )
    return problems


def _uses_structure(tree: ast.AST) -> set[str]:
    """Kit structure classes instantiated somewhere in the script."""
    used: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = func.id if isinstance(func, ast.Name) else None
            if name in KIT_STRUCTURES:
                used.add(name)
    return used


def _check_kit_structure_usage(tree: ast.AST) -> list[str]:
    """Soft: prefer the kit over hand-placed shapes (never fatal)."""
    if _uses_structure(tree):
        return []
    return [
        "the script uses no kit structure: build the visualization with "
        f"{sorted(KIT_STRUCTURES)} instead of hand-placed shapes"
    ]


def _check_kit_rules(tree: ast.AST, manim_code: str = "") -> list[str]:
    """Kit names are provided; never import or redefine them."""
    problems: list[str] = []

    for node in ast.walk(tree):
        where = getattr(node, "lineno", "?")
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name in KIT_NAMES:
                problems.append(
                    f"line {where}: '{node.name}' is provided by the visual kit; "
                    "do not redefine it"
                )
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            module = (
                node.module
                if isinstance(node, ast.ImportFrom)
                else (node.names[0].name if node.names else "")
            )
            root = (module or "").split(".")[0]
            if root in KIT_MODULES:
                problems.append(
                    f"line {where}: the visual kit is already available; do not import "
                    f"from '{root}'"
                )
            for alias in node.names:
                if alias.name in KIT_NAMES | {FINISH_SCENE}:
                    problems.append(
                        f"line {where}: '{alias.name}' is provided by the pipeline; "
                        "do not import it"
                    )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in KIT_NAMES:
                    problems.append(
                        f"line {where}: '{target.id}' is provided by the visual kit; "
                        "do not reassign it"
                    )
    return problems


def _check_no_code(manim_code: str) -> list[str]:
    """No source code or pseudocode may be drawn: on-screen text is plain words."""
    problems: list[str] = []
    try:
        tree = ast.parse(manim_code)
    except SyntaxError:
        return problems

    # Docstrings are documentation, never drawn: do not scan them for code.
    docstrings: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
        ):
            body = getattr(node, "body", [])
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                docstrings.add(id(body[0].value))

    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        if id(node) in docstrings:
            continue
        value = node.value
        if not value.strip():
            continue
        reason = None
        if CODE_LINE_RE.search(value):
            reason = "a line that reads as code"
        elif SUBSCRIPT_RE.search(value):
            reason = "indexing syntax like name[index]"
        elif CALL_SYNTAX_RE.search(value):
            reason = "function-call syntax"
        elif any(operator in value for operator in CODE_OPERATORS):
            reason = "a programming operator"
        if reason:
            snippet = value.strip().replace("\n", " ")[:48]
            problems.append(
                f"line {getattr(node, 'lineno', '?')}: on-screen text {snippet!r} contains "
                f"{reason}; explain it in plain words and show the state with the kit"
            )
    return problems


def _check_no_raw_text(tree: ast.AST) -> list[str]:
    """All on-screen text must come from the kit, which places it safely."""
    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name not in {"Text", "MarkupText"}:
            continue
        problems.append(
            f"line {getattr(node, 'lineno', '?')}: do not place on-screen text yourself with "
            f"{name}(...); use set_caption, show_title, title_card, step_tag, StatePanel, "
            "result_cards, TreeViz.annotate or GraphViz.tag so the kit lays it out"
        )
    return problems


def _check_caption_length(tree: ast.AST) -> list[str]:
    """Captions are one short line: the kit truncates anything past 70 chars."""
    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name != "set_caption":
            continue
        if not node.args or not isinstance(node.args[0], ast.Constant):
            continue
        text = node.args[0].value
        if not isinstance(text, str):
            continue
        if len(" ".join(text.split())) > 70:
            problems.append(
                f"line {getattr(node, 'lineno', '?')}: caption {text[:40]!r}... is "
                f"{len(' '.join(text.split()))} characters; captions are at most 70 "
                "characters, so split the idea or move it into the narration"
            )
    return problems


def _check_text_sizes(tree: ast.AST) -> list[str]:
    """Text is set by the kit: no font= overrides and no tiny text."""
    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
        if name not in {"Text", "MarkupText", "Tex", "MathTex"}:
            continue
        where = getattr(node, "lineno", "?")
        if any(keyword.arg == "font" for keyword in node.keywords):
            problems.append(
                f"line {where}: do not set font= - the kit already picked the UI font"
            )
        for keyword in node.keywords:
            if keyword.arg != "font_size":
                continue
            size = keyword.value
            if isinstance(size, ast.Constant) and isinstance(size.value, (int, float)):
                if size.value < MIN_TEXT_SIZE:
                    problems.append(
                        f"line {where}: font_size {size.value} is too small; use at "
                        f"least {MIN_TEXT_SIZE}"
                    )
    return problems


def _is_finish_scene_call(node: ast.AST) -> bool:
    """True for the statement ``finish_scene(self)``."""
    if not isinstance(node, ast.Expr) or not isinstance(node.value, ast.Call):
        return False
    func = node.value.func
    if not (isinstance(func, ast.Name) and func.id == FINISH_SCENE):
        return False
    args = node.value.args
    return bool(args) and isinstance(args[0], ast.Name) and args[0].id == "self"


def _chain_has_self_wait(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        if isinstance(func, ast.Attribute) and func.attr == "wait":
            return True
    return False


def _check_finish_scene(tree: ast.AST, class_names: list[str]) -> list[str]:
    """The pipeline owns scene endings: one final ``finish_scene(self)`` call."""
    problems: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            if node.name == FINISH_SCENE:
                problems.append(
                    f"line {getattr(node, 'lineno', '?')}: {FINISH_SCENE} is provided by the "
                    "pipeline; do not define it"
                )
        elif isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in KIT_MODULES:
                problems.append(
                    f"line {node.lineno}: {FINISH_SCENE} is provided by the pipeline; "
                    "do not import it"
                )
            for alias in node.names:
                if alias.name.split(".")[-1] == FINISH_SCENE or alias.name in KIT_MODULES:
                    problems.append(
                        f"line {node.lineno}: {FINISH_SCENE} is provided by the pipeline; "
                        "do not import it"
                    )
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == FINISH_SCENE:
                    problems.append(
                        f"line {node.lineno}: do not assign to {FINISH_SCENE}; it is provided "
                        "by the pipeline"
                    )
        elif isinstance(node, ast.While) and _chain_has_self_wait(node):
            problems.append(
                f"line {node.lineno}: a while loop around self.wait is not allowed; "
                f"end the scene with {FINISH_SCENE}(self) instead"
            )

    classes = {
        node.name: node for node in ast.walk(tree) if isinstance(node, ast.ClassDef)
    }
    for name in class_names:
        class_node = classes.get(name)
        if class_node is None:
            continue
        construct = next(
            (
                item
                for item in class_node.body
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name == "construct"
            ),
            None,
        )
        if construct is None:
            problems.append(f"scene {name} has no construct method")
            continue
        last = construct.body[-1] if construct.body else None
        if last is None or not _is_finish_scene_call(last):
            problems.append(
                f"scene {name}: the last statement of construct must be exactly "
                f"{FINISH_SCENE}(self) (do not write your own FadeOut)"
            )
    return problems


def _check_structure(manim_code: str, tree: ast.AST, result: GenerationResult) -> list[str]:
    problems: list[str] = []
    scenes = result.meta.scenes

    matched_names = [m.group(1) for m in SCENE_CLASS_RE.finditer(manim_code)]
    if not matched_names:
        problems.append("no scene class matching 'Scene{N}_{Name}(Scene)' was found")

    numbers: list[int] = []
    for name in matched_names:
        match = re.match(r"Scene(\d+)_", name)
        numbers.append(int(match.group(1)) if match else -1)
    expected = list(range(1, len(matched_names) + 1))
    if numbers != expected:
        problems.append(
            f"scene numbering must be exactly {expected} in order, got {numbers}"
        )

    if len(matched_names) != len(scenes):
        problems.append(
            f"scene count mismatch: script has {len(matched_names)} scene class(es) "
            f"but meta lists {len(scenes)}"
        )
    else:
        for index, (class_name, scene) in enumerate(zip(matched_names, scenes), start=1):
            if scene.class_name != class_name:
                problems.append(
                    f"scene {index}: meta class_name '{scene.class_name}' does not match "
                    f"script class '{class_name}'"
                )
            if not scene.narration.strip():
                problems.append(f"scene {index} ({class_name}): narration is empty")

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            subclasses_scene = any(
                (isinstance(base, ast.Name) and base.id == "Scene")
                or (isinstance(base, ast.Attribute) and base.attr == "Scene")
                for base in node.bases
            )
            if subclasses_scene and node.name not in matched_names:
                problems.append(
                    f"class '{node.name}' subclasses Scene but does not follow the "
                    "Scene{{N}}_{{Name}} naming rule"
                )

    problems.extend(_check_finish_scene(tree, matched_names))
    return problems


def _check_meta(result: GenerationResult) -> list[str]:
    problems: list[str] = []
    meta = result.meta
    for field in REQUIRED_META_FIELDS:
        if not meta.field_present(field):
            problems.append(f"meta field '{field}' is missing")
    if not meta.problem_summary.strip():
        problems.append("meta field 'problem_summary' must not be empty")
    if meta.field_present("solution_source") and meta.solution_source not in ALLOWED_SOLUTION_SOURCES:
        problems.append(
            f"meta solution_source must be one of {sorted(ALLOWED_SOLUTION_SOURCES)}, "
            f"got '{meta.solution_source}'"
        )
    if not meta.programming_language.strip():
        problems.append("meta field 'programming_language' must not be empty")
    if not meta.nested_field_present("complexity", "time") or not meta.complexity.time.strip():
        problems.append("meta field 'complexity.time' is missing or empty")
    if not meta.nested_field_present("complexity", "space") or not meta.complexity.space.strip():
        problems.append("meta field 'complexity.space' is missing or empty")
    if not meta.nested_field_present("validation", "performed"):
        problems.append("meta field 'validation.performed' is missing")
    return problems


def _check_solution_state(
    result: GenerationResult, request: VideoRequest
) -> list[str]:
    problems: list[str] = []
    state = request.solution_state
    source = result.meta.solution_source

    if state == STATE_MISSING and source != "generated":
        problems.append(
            f"solution_state is 'missing' so solution_source must be 'generated', got '{source}'"
        )
    elif state == STATE_VERIFIED and source != "provided":
        problems.append(
            f"solution_state is 'verified' so solution_source must be 'provided', got '{source}'"
        )
    elif state == STATE_UNVERIFIED:
        if source not in {"provided", "corrected"}:
            problems.append(
                f"solution_state is 'unverified' so solution_source must be 'provided' or "
                f"'corrected', got '{source}'"
            )
        if result.meta.validation.performed is not True:
            problems.append(
                "solution_state is 'unverified' so validation.performed must be true"
            )
    return problems


@dataclass
class ValidationProblems:
    """Generation problems split by severity.

    HARD problems make an attempt unusable: the response cannot be rendered or
    it breaks the pipeline contract. SOFT problems are style/layout guidance:
    they are fed back to the model on retries but never fail the job.
    """

    hard: list[str] = field(default_factory=list)
    soft: list[str] = field(default_factory=list)

    @property
    def all(self) -> list[str]:
        return [*self.hard, *self.soft]

    def __bool__(self) -> bool:  # pragma: no cover - convenience
        return bool(self.hard or self.soft)


def validate_generation_split(
    result: GenerationResult, request: VideoRequest, env_info: EnvInfo
) -> ValidationProblems:
    """Every generation problem, split into hard and soft."""
    hard: list[str] = []
    soft: list[str] = []

    manim_code = result.manim_code or ""
    if not manim_code.strip():
        return ValidationProblems(hard=["manim_code is empty"])

    if "from manim import *" not in manim_code:
        hard.append("manim_code must start with 'from manim import *'")

    tree: ast.AST | None = None
    try:
        tree = ast.parse(manim_code)
    except SyntaxError as exc:
        hard.append(f"manim_code is not valid Python: {exc.msg} (line {exc.lineno})")

    if tree is not None:
        # HARD: the script must be safe and structurally correct.
        hard.extend(_check_imports(tree))
        hard.extend(_check_names(tree, env_info.latex_available))
        hard.extend(_check_structure(manim_code, tree, result))
        hard.extend(_check_kit_rules(tree, manim_code))
        # SOFT: presentation rules: guidance for the model, never fatal.
        soft.extend(_check_config(tree))
        soft.extend(_check_no_raw_text(tree))
        soft.extend(_check_kit_structure_usage(tree))
        soft.extend(_check_kit_methods(tree))
        soft.extend(_check_intro_usage(tree))
        soft.extend(_check_result_scene(tree))
        soft.extend(_check_panel_lanes(tree))
        soft.extend(_check_compare_panels_usage(tree, result))
        soft.extend(_check_no_code(manim_code))
        soft.extend(_check_text_sizes(tree))
        soft.extend(_check_caption_length(tree))

    hard.extend(_check_meta(result))
    hard.extend(_check_solution_state(result, request))

    if not (result.solution_code or "").strip():
        hard.append("solution_code is empty")

    return ValidationProblems(hard=hard, soft=soft)


def validate_generation(
    result: GenerationResult, request: VideoRequest, env_info: EnvInfo
) -> list[str]:
    """Every generation problem (hard first); empty list means acceptable."""
    return validate_generation_split(result, request, env_info).all


# ---------------------------------------------------------------------------
# kit methods: the reference is the contract
# ---------------------------------------------------------------------------

PROMPTS_DIR = Path(__file__).resolve().parent / "prompts"
KIT_REFERENCE_PATH = PROMPTS_DIR / "kit_reference.txt"

# Mobject methods a script may always call on a kit structure.
KIT_MOBJECT_METHODS = {
    "animate",
    "copy",
    "get_center",
    "get_left",
    "get_right",
    "get_top",
    "get_bottom",
    "get_width",
    "get_height",
    "next_to",
    "scale",
    "set_opacity",
    "set_z_index",
    "shift",
    "move_to",
    "to_edge",
    "to_corner",
}


@lru_cache(maxsize=1)
def kit_structure_methods() -> dict[str, set[str]]:
    """Structure name -> documented methods, parsed from kit_reference.txt."""
    try:
        text = KIT_REFERENCE_PATH.read_text(encoding="utf-8")
    except OSError:  # pragma: no cover - the file ships with the package
        return {}

    methods: dict[str, set[str]] = {}
    owner: str | None = None
    for line in text.splitlines():
        match = re.match(r"^  ([A-Za-z_][A-Za-z0-9_]*)\(", line)
        if match:
            owner = match.group(1)
            if owner in KIT_STRUCTURES:
                methods.setdefault(owner, {"intro"})
            continue
        if owner in methods and re.match(r"^ {6}\.", line):
            methods[owner].update(re.findall(r"\.(\w+)\(", line))
    return methods


def _check_result_scene(tree: ast.AST) -> list[str]:
    """The closing scene is the result cards: no structures, no chips."""
    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        construct = next(
            (
                item
                for item in node.body
                if isinstance(item, ast.FunctionDef) and item.name == "construct"
            ),
            None,
        )
        if construct is None:
            continue
        calls = [call for call in ast.walk(construct) if isinstance(call, ast.Call)]
        uses_cards = any(
            (isinstance(call.func, ast.Name) and call.func.id == "result_cards")
            or (isinstance(call.func, ast.Attribute) and call.func.attr == "result_cards")
            for call in calls
        )
        if not uses_cards:
            continue
        structures = sorted(
            {
                call.func.id
                for call in calls
                if isinstance(call.func, ast.Name) and call.func.id in KIT_STRUCTURES
            }
        )
        if structures:
            problems.append(
                f"class '{node.name}' uses result_cards and also builds "
                f"{structures}; the closing scene shows the three result cards and "
                "nothing else (move the visualization to an earlier scene)"
            )
    return problems


PANEL_ANCHORS = {"left_at", "right_at"}
LANE_ANCHORS = {"LEFT_LANE", "RIGHT_LANE", "STAGE"}


def _calls_in_scenes(tree: ast.AST) -> list[tuple[str, list[ast.Call]]]:
    """(class name, calls) for every Scene class in the script."""
    found: list[tuple[str, list[ast.Call]]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        calls = [call for call in ast.walk(node) if isinstance(call, ast.Call)]
        found.append((node.name, calls))
    return found


def _check_compare_panels_usage(tree: ast.AST, result: GenerationResult) -> list[str]:
    """Soft: compare_panels is only for the bug-and-fix scene of a correction."""
    if (result.meta.solution_source or "") == "corrected":
        return []
    problems: list[str] = []
    for name, calls in _calls_in_scenes(tree):
        for call in calls:
            func = call.func
            called = func.id if isinstance(func, ast.Name) else getattr(func, "attr", None)
            if called == "compare_panels":
                problems.append(
                    f"class '{name}' uses compare_panels but solution_source is "
                    f"'{result.meta.solution_source or 'empty'}': compare_panels is only "
                    "for the bug-and-fix scene when solution_source is 'corrected'"
                )
    return problems


def _check_panel_lanes(tree: ast.AST) -> list[str]:
    """Inside compare panels every structure uses left_at/right_at only.

    The classic layout defect was a map at a panel anchor and an array at
    LEFT_LANE: both land in the same half of the stage and their text collides.
    """
    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue
        construct = next(
            (
                item
                for item in node.body
                if isinstance(item, ast.FunctionDef) and item.name == "construct"
            ),
            None,
        )
        if construct is None:
            continue
        calls = [call for call in ast.walk(construct) if isinstance(call, ast.Call)]
        uses_panels = any(
            (isinstance(call.func, ast.Name) and call.func.id == "compare_panels")
            or (isinstance(call.func, ast.Attribute) and call.func.attr == "compare_panels")
            for call in calls
        )
        if not uses_panels:
            continue
        lanes = sorted(
            {
                name.id
                for name in ast.walk(construct)
                if isinstance(name, ast.Name) and name.id in LANE_ANCHORS
            }
        )
        if lanes:
            problems.append(
                f"class '{node.name}' uses compare_panels together with {lanes}; "
                "inside a compare scene every structure goes at left_at or "
                "right_at (one per panel), never in a lane"
            )
        for call in calls:
            func = call.func
            name = func.id if isinstance(func, ast.Name) else None
            # StatePanel has no at= anchor (chips sit under the panels), so it is
            # exempt; only the drawn structures must pick a panel.
            if name not in KIT_STRUCTURES or name == "StatePanel":
                continue
            if not any(keyword.arg == "at" for keyword in call.keywords):
                problems.append(
                    f"line {getattr(call, 'lineno', '?')}: {name} in a compare_panels "
                    "scene needs at=left_at or at=right_at; the default anchors it "
                    "in the middle, on top of both panels"
                )
    return problems


def _check_intro_usage(tree: ast.AST) -> list[str]:
    """``.intro()`` returns an Animation: play it, never keep it as the object."""
    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.Call):
            continue
        func = node.value.func
        if isinstance(func, ast.Attribute) and func.attr in {"intro", "to", "hide"}:
            target = node.targets[0]
            name = target.id if isinstance(target, ast.Name) else "this value"
            problems.append(
                f"line {getattr(node, 'lineno', '?')}: '{func.attr}()' returns an "
                f"Animation, so '{name}' is not the structure. Never chain it onto "
                "the constructor: write the structure on its own line "
                f"('{name} = MapViz(...)') and then "
                f"'self.play({name}.{func.attr}(...))'."
            )
    return problems


def _check_kit_methods(tree: ast.AST) -> list[str]:
    """Only documented kit methods exist: catch invented names before rendering."""
    allowed = kit_structure_methods()
    if not allowed:
        return []

    owners: dict[str, str] = {}
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Name)
            and node.value.func.id in allowed
        ):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    owners[target.id] = node.value.func.id

    problems: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Attribute):
            continue
        base = node.func.value
        if not isinstance(base, ast.Name):
            continue
        owner = owners.get(base.id)
        if owner is None:
            continue
        method = node.func.attr
        if method in allowed.get(owner, set()) or method in KIT_MOBJECT_METHODS:
            continue
        problems.append(
            f"line {getattr(node, 'lineno', '?')}: '{method}' is not a method of {owner}; "
            f"use one of {sorted(allowed.get(owner, set()))}"
        )
    return problems
