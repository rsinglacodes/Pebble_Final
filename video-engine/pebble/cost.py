"""Per-video cost tracking.

One :class:`CostTracker` per pipeline run, passed explicitly to the stages that
spend money (generation, render repairs, speech synthesis). Nothing here is
global, so parallel runs cannot mix their totals.

Prices are USD per 1M units and come from :class:`pebble.config.Settings`
(``LLM_INPUT_PRICE_PER_1M``, ``LLM_OUTPUT_PRICE_PER_1M``,
``TTS_PRICE_PER_1M_CHARS``); the shipped defaults are estimates. Reasoning
tokens are reported separately but are *already* included in the completion
token count, so they are never billed twice.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pebble.config import Settings
from pebble.llm import LLMResponse, LLMUsage
from pebble.workspace import WORKSPACE_ROOT

# One shared append-only log next to the job folders, so --costs can aggregate.
COST_LOG_PATH = WORKSPACE_ROOT / "cost_log.jsonl"

LLM_PURPOSES = ("generate", "regenerate", "repair")
TTS_PURPOSE = "tts"
PURPOSES = LLM_PURPOSES + (TTS_PURPOSE,)

ROW_LABELS = {
    "generate": "generation (first attempt)",
    "regenerate": "regeneration (after rejection)",
    "repair": "render repairs",
    "tts": "speech synthesis",
}

PRICE_NOTE = "excludes blob storage, egress and laptop compute"


@dataclass
class CostRecord:
    purpose: str
    model: str | None = None
    input_tokens: int = 0
    output_tokens: int = 0
    reasoning_tokens: int = 0
    characters: int = 0
    seconds: float = 0.0
    usage_known: bool = True
    scene: str | None = None
    voice: str | None = None
    unit_usd: float = 0.0


def _pay(tokens: int, price_per_1m: float) -> float:
    return tokens / 1_000_000 * price_per_1m


class CostTracker:
    """Accumulates LLM token usage and TTS characters for one video run."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.records: list[CostRecord] = []

    # -- recording ------------------------------------------------------
    def record_llm(
        self,
        purpose: str,
        model: str | None,
        usage: LLMUsage | None,
        seconds: float = 0.0,
    ) -> CostRecord:
        if purpose not in LLM_PURPOSES:
            raise ValueError(
                f"unknown LLM purpose {purpose!r}; expected one of {list(LLM_PURPOSES)}"
            )
        known = usage is not None and usage.known
        input_tokens = int(usage.prompt_tokens or 0) if usage else 0
        output_tokens = int(usage.completion_tokens or 0) if usage else 0
        reasoning_tokens = int(usage.reasoning_tokens or 0) if usage else 0
        record = CostRecord(
            purpose=purpose,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            reasoning_tokens=reasoning_tokens,
            seconds=float(seconds or 0.0),
            usage_known=known,
            unit_usd=_pay(input_tokens, self.settings.llm_input_price_per_1m)
            + _pay(output_tokens, self.settings.llm_output_price_per_1m),
        )
        self.records.append(record)
        return record

    def record_tts(
        self, scene: str | None, characters: int, voice: str | None = None
    ) -> CostRecord:
        count = max(0, int(characters))
        record = CostRecord(
            purpose=TTS_PURPOSE,
            characters=count,
            voice=voice,
            scene=scene,
            unit_usd=_pay(count, self.settings.tts_price_per_1m_chars),
        )
        self.records.append(record)
        return record

    # -- totals ---------------------------------------------------------
    def _by_purpose(self) -> dict[str, dict[str, float]]:
        rows: dict[str, dict[str, float]] = {
            purpose: {
                "calls": 0,
                "input_tokens": 0,
                "output_tokens": 0,
                "reasoning_tokens": 0,
                "characters": 0,
                "usd": 0.0,
            }
            for purpose in PURPOSES
        }
        for record in self.records:
            row = rows[record.purpose]
            row["calls"] += 1
            row["input_tokens"] += record.input_tokens
            row["output_tokens"] += record.output_tokens
            row["reasoning_tokens"] += record.reasoning_tokens
            row["characters"] += record.characters
            row["usd"] += record.unit_usd
        return rows

    @property
    def llm_calls(self) -> int:
        return sum(1 for record in self.records if record.purpose in LLM_PURPOSES)

    @property
    def input_tokens(self) -> int:
        return sum(record.input_tokens for record in self.records)

    @property
    def output_tokens(self) -> int:
        return sum(record.output_tokens for record in self.records)

    @property
    def reasoning_tokens(self) -> int:
        return sum(record.reasoning_tokens for record in self.records)

    @property
    def tts_characters(self) -> int:
        return sum(record.characters for record in self.records)

    @property
    def is_estimate(self) -> bool:
        """True when some LLM call reported no usage, so the total is partial."""
        return any(
            record.purpose in LLM_PURPOSES and not record.usage_known
            for record in self.records
        )

    @property
    def total_usd(self) -> float:
        return sum(record.unit_usd for record in self.records)

    def total_inr(self) -> float | None:
        rate = self.settings.usd_to_inr
        if rate is None:
            return None
        return self.total_usd * rate

    def cost_per_minute(self, video_seconds: float) -> float | None:
        if not video_seconds or video_seconds <= 0:
            return None
        return self.total_usd / (video_seconds / 60.0)

    # -- reporting ------------------------------------------------------
    def rows(self) -> list[dict[str, Any]]:
        by_purpose = self._by_purpose()
        return [
            {"purpose": purpose, "label": ROW_LABELS[purpose], **by_purpose[purpose]}
            for purpose in PURPOSES
        ]

    def to_dict(self, video_seconds: float | None = None) -> dict[str, Any]:
        inr = self.total_inr()
        return {
            "currency": "USD",
            "prices": {
                "llm_input_per_1m_tokens_usd": self.settings.llm_input_price_per_1m,
                "llm_output_per_1m_tokens_usd": self.settings.llm_output_price_per_1m,
                "tts_per_1m_characters_usd": self.settings.tts_price_per_1m_chars,
                "usd_to_inr": self.settings.usd_to_inr,
            },
            "rows": self.rows(),
            "llm_calls": self.llm_calls,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "reasoning_tokens": self.reasoning_tokens,
            "tts_characters": self.tts_characters,
            "total_usd": round(self.total_usd, 6),
            "total_inr": round(inr, 3) if inr is not None else None,
            "cost_per_minute_usd": (
                round(self.cost_per_minute(video_seconds), 6)
                if video_seconds
                else None
            ),
            "is_estimate": self.is_estimate,
            "note": PRICE_NOTE,
        }

    def format_table(self, video_seconds: float | None = None) -> str:
        """A compact fixed-width cost table for the console summary."""
        lines = ["cost"]
        header = (
            f"  {'':<32}{'calls':>6}{'in tok':>11}{'out tok':>11}"
            f"{'chars':>9}{'cost USD':>11}"
        )
        lines.append(header)
        for row in self.rows():
            lines.append(
                f"  {row['label']:<32}{int(row['calls']):>6}"
                f"{int(row['input_tokens']):>11,}{int(row['output_tokens']):>11,}"
                f"{int(row['characters']):>9,}"
                f"{'$' + format(row['usd'], '.4f'):>11}"
            )
        lines.append(
            f"  {'TOTAL':<32}{self.llm_calls:>6}{self.input_tokens:>11,}"
            f"{self.output_tokens:>11,}{self.tts_characters:>9,}"
            f"{'$' + format(self.total_usd, '.4f'):>11}"
        )
        if self.reasoning_tokens:
            lines.append(
                f"  (reasoning tokens included in out tok: {self.reasoning_tokens:,})"
            )
        per_minute = self.cost_per_minute(video_seconds) if video_seconds else None
        if per_minute is not None:
            lines.append(
                f"  {'cost per minute of video':<32}{'':>48}"
                f"{'$' + format(per_minute, '.5f'):>11}"
            )
        inr = self.total_inr()
        if inr is not None:
            lines.append(f"  {'TOTAL (INR)':<32}{'':>48}{'₹' + format(inr, '.2f'):>11}")
        if self.is_estimate:
            lines.append(
                "  ESTIMATE: at least one LLM call reported no token usage, "
                "so the total is a lower bound."
            )
        lines.append(f"  note: {PRICE_NOTE}")
        return "\n".join(lines)


def log_llm_call(
    logger: logging.Logger,
    purpose: str,
    attempt: int | None,
    response: LLMResponse,
    cost: CostTracker,
) -> None:
    """One INFO line per LLM call, ending with the running total."""
    usage = response.usage
    label = f"LLM {purpose}" + (f" attempt {attempt}" if attempt is not None else "")
    if usage is None or not usage.known:
        tokens = "usage unknown"
    else:
        tokens = f"{int(usage.prompt_tokens or 0):,} in / {int(usage.completion_tokens or 0):,} out"
        if usage.reasoning_tokens:
            tokens += f" ({int(usage.reasoning_tokens):,} reasoning)"
    logger.info(
        "%s: %s, %.1fs, running cost $%.4f%s",
        label,
        tokens,
        response.seconds,
        cost.total_usd,
        " (estimate)" if cost.is_estimate else "",
    )


# ---------------------------------------------------------------------------
# cost_log.jsonl
# ---------------------------------------------------------------------------

COST_LOG_FIELDS = (
    "job_id",
    "fingerprint",
    "date",
    "kind",
    "style",
    "video_seconds",
    "total_usd",
)


def append_cost_log(
    path: Path,
    *,
    job_id: str,
    fingerprint: str,
    kind: str,
    style: str,
    video_seconds: float,
    total_usd: float,
) -> None:
    entry = {
        "job_id": job_id,
        "fingerprint": fingerprint,
        "date": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "kind": kind,
        "style": style,
        "video_seconds": round(float(video_seconds), 3),
        "total_usd": round(float(total_usd), 6),
    }
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def read_cost_log(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    entries: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            entries.append(entry)
    return entries


def summarize_cost_log(entries: list[dict[str, Any]]) -> dict[str, Any]:
    total = sum(float(entry.get("total_usd") or 0.0) for entry in entries)
    seconds = sum(float(entry.get("video_seconds") or 0.0) for entry in entries)
    count = len(entries)
    return {
        "runs": count,
        "total_usd": total,
        "average_usd": total / count if count else 0.0,
        "total_video_seconds": seconds,
        "cost_per_minute_usd": total / (seconds / 60.0) if seconds else 0.0,
    }
