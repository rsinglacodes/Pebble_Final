"""The generation stage: prompt -> LLM -> parse -> validate -> workspace files."""

from __future__ import annotations

import json
import logging

from pebble.config import Settings
from pebble.cost import CostTracker, log_llm_call
from pebble.environment import EnvInfo
from pebble.errors import GenerationError
from pebble.llm import LLMClient
from pebble.models import GenerationResult, VideoRequest
from pebble.parsing import parse_response
from pebble.prompt_builder import build_prompt
from pebble.styles import get_style
from pebble.validators import validate_generation_split
from pebble.workspace import JobWorkspace

logger = logging.getLogger(__name__)

RETRY_HEADER = "YOUR PREVIOUS RESPONSE WAS REJECTED."
RETRY_FOOTER = (
    "Return the COMPLETE response again in the required format, fixing these problems."
)


def _retry_prompt(base_prompt: str, problems: list[str]) -> str:
    listed = "\n".join(f"- {problem}" for problem in problems)
    return (
        f"{base_prompt}\n\n{RETRY_HEADER} Problems:\n{listed}\n{RETRY_FOOTER}"
    )


def _finalize(
    result: GenerationResult,
    request: VideoRequest,
    workspace: JobWorkspace,
    style_name: str,
) -> GenerationResult:
    """Restore the provided solution, write the workspace files and return."""
    # The pipeline never trusts the LLM to copy a provided solution verbatim.
    if result.meta.solution_source == "provided":
        result.solution_code = request.raw_solution_code
    result.style_name = style_name

    workspace.animation_path.write_text(result.manim_code, encoding="utf-8")
    generation_doc = {
        "fingerprint": request.request_fingerprint(),
        "request_kind": request.request_kind,
        "solution_state": request.solution_state,
        "style": style_name,
        "meta": result.meta.model_dump(),
        "solution": result.solution_code,
        "generation_warnings": list(result.generation_warnings),
    }
    workspace.generation_path.write_text(
        json.dumps(generation_doc, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return result


def generate(
    request: VideoRequest,
    workspace: JobWorkspace,
    settings: Settings,
    env_info: EnvInfo,
    cost: CostTracker | None = None,
) -> GenerationResult:
    """Run up to MAX_GENERATION_ATTEMPTS, returning a validated GenerationResult."""
    style_name, _ = get_style(request.preferences_or_default.explanation_style)
    base_prompt = build_prompt(request, env_info)
    client = LLMClient(settings)

    all_problems: list[str] = []
    attempts = settings.max_generation_attempts
    # Best attempt so far: (hard count, soft count) plus the accepted result.
    best: tuple[int, int, GenerationResult] | None = None

    for attempt in range(1, attempts + 1):
        prompt = base_prompt if attempt == 1 else _retry_prompt(base_prompt, all_problems)

        response = client.call_llm(prompt)
        purpose = "generate" if attempt == 1 else "regenerate"
        if cost is not None:
            cost.record_llm(
                purpose,
                settings.azure_deployment or "unknown",
                response.usage,
                response.seconds,
            )
            log_llm_call(logger, purpose, attempt, response, cost)

        prompt_path, response_path = workspace.attempt_paths(attempt)
        prompt_path.write_text(prompt, encoding="utf-8")
        response_path.write_text(response.text, encoding="utf-8")

        try:
            result = parse_response(response.text)
        except Exception as exc:
            all_problems = [str(exc)]
            logger.warning("attempt %d/%d parse failed: %s", attempt, attempts, exc)
            continue

        problems = validate_generation_split(result, request, env_info)
        if not problems.hard and not problems.soft:
            logger.info(
                "generation succeeded on attempt %d/%d (%d scenes)",
                attempt,
                attempts,
                len(result.meta.scenes),
            )
            return _finalize(result, request, workspace, style_name)

        if not problems.hard:
            # Only style guidance: remember it, keep retrying, never fatal.
            result.generation_warnings = problems.soft
            if best is None or len(problems.soft) < best[1]:
                best = (0, len(problems.soft), result)
            logger.warning(
                "attempt %d/%d has %d soft problem(s) (not fatal); first: %s",
                attempt,
                attempts,
                len(problems.soft),
                "; ".join(problems.soft[:3]),
            )
        else:
            logger.warning(
                "attempt %d/%d rejected with %d hard problem(s); first: %s",
                attempt,
                attempts,
                len(problems.hard),
                "; ".join(problems.hard[:3]),
            )

        all_problems = problems.all

    if best is not None:
        hard_free = best[2]
        logger.warning(
            "accepting attempt with %d generation warning(s): %s",
            len(hard_free.generation_warnings),
            "; ".join(hard_free.generation_warnings[:3]),
        )
        return _finalize(hard_free, request, workspace, style_name)

    raise GenerationError(
        f"Generation failed after {attempts} attempt(s); "
        f"last problems: " + "; ".join(all_problems),
        problems=all_problems,
    )
