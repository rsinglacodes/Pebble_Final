"""Cost tracking: hand-computed token math, estimates and the JSONL log."""

from __future__ import annotations

import json

import pytest

from pebble.config import Settings
from pebble.cost import (
    CostTracker,
    append_cost_log,
    read_cost_log,
    summarize_cost_log,
)
from pebble.llm import LLMUsage

SETTINGS = Settings(
    llm_input_price_per_1m=0.25,
    llm_output_price_per_1m=2.00,
    tts_price_per_1m_chars=16.00,
)


def test_token_and_character_math():
    tracker = CostTracker(SETTINGS)
    tracker.record_llm("generate", "deployment", LLMUsage(1_000_000, 1_000_000, 500_000))

    assert tracker.input_tokens == 1_000_000
    assert tracker.output_tokens == 1_000_000
    assert tracker.reasoning_tokens == 500_000
    # 1M in * 0.25 + 1M out * 2.00 = 2.25 ; reasoning is part of the output count
    assert tracker.total_usd == pytest.approx(2.25)

    tracker.record_tts("Scene1_Intro", 500_000, "en-IN-NeerjaNeural")
    assert tracker.tts_characters == 500_000
    # 500k characters at 16.00 per 1M = 8.00
    assert tracker.records[1].unit_usd == pytest.approx(8.0)
    assert tracker.total_usd == pytest.approx(10.25)
    assert tracker.llm_calls == 1


def test_reasoning_tokens_are_not_double_counted():
    tracker = CostTracker(SETTINGS)
    tracker.record_llm("generate", "m", LLMUsage(0, 1_000_000, 900_000))
    assert tracker.total_usd == pytest.approx(2.0)


def test_missing_usage_marks_the_total_as_an_estimate():
    tracker = CostTracker(SETTINGS)
    tracker.record_llm("generate", "m", LLMUsage(1000, 2000))
    assert tracker.is_estimate is False
    tracker.record_llm("repair", "m", None)
    assert tracker.is_estimate is True
    assert tracker.records[-1].input_tokens == 0
    assert "ESTIMATE" in tracker.format_table(60.0)


def test_rows_and_cost_per_minute():
    tracker = CostTracker(SETTINGS)
    tracker.record_llm("generate", "m", LLMUsage(1000, 1000))
    tracker.record_llm("regenerate", "m", LLMUsage(1000, 1000))
    tracker.record_llm("repair", "m", LLMUsage(1000, 1000))
    tracker.record_tts("Scene1", 1000, "voice")

    rows = tracker.rows()
    assert [row["purpose"] for row in rows] == ["generate", "regenerate", "repair", "tts"]
    assert [int(row["calls"]) for row in rows] == [1, 1, 1, 1]

    table = tracker.format_table(120.0)
    assert "generation (first attempt)" in table
    assert "regeneration (after rejection)" in table
    assert "render repairs" in table
    assert "speech synthesis" in table
    assert "TOTAL" in table
    assert "cost per minute of video" in table
    assert tracker.cost_per_minute(120.0) == pytest.approx(tracker.total_usd / 2)

    doc = tracker.to_dict(120.0)
    assert doc["llm_calls"] == 3
    assert doc["total_usd"] == pytest.approx(tracker.total_usd, abs=1e-6)
    assert doc["note"].startswith("excludes blob storage")
    assert doc["is_estimate"] is False


def test_inr_is_optional():
    tracker = CostTracker(SETTINGS)
    tracker.record_llm("generate", "m", LLMUsage(1_000_000, 0))
    assert tracker.total_inr() is None
    assert "INR" not in tracker.format_table(60.0)

    with_inr = CostTracker(Settings(usd_to_inr=84.0))
    with_inr.record_llm("generate", "m", LLMUsage(1_000_000, 0))
    assert with_inr.total_inr() == pytest.approx(0.25 * 84.0)
    assert "INR" in with_inr.format_table(60.0)


def test_unknown_llm_purpose_is_rejected():
    tracker = CostTracker(SETTINGS)
    with pytest.raises(ValueError):
        tracker.record_llm("gossip", "m", LLMUsage(1, 1))


def test_cost_log_line_and_summary(tmp_path):
    log = tmp_path / "cost_log.jsonl"
    append_cost_log(
        log,
        job_id="job_a",
        fingerprint="f" * 64,
        kind="leetcode_problem",
        style="concise",
        video_seconds=90.0,
        total_usd=0.12,
    )
    append_cost_log(
        log,
        job_id="job_b",
        fingerprint="e" * 64,
        kind="algorithm",
        style="detailed",
        video_seconds=30.0,
        total_usd=0.06,
    )

    entries = read_cost_log(log)
    assert len(entries) == 2
    assert set(entries[0]) == {
        "job_id",
        "fingerprint",
        "date",
        "kind",
        "style",
        "video_seconds",
        "total_usd",
    }
    assert json.loads(log.read_text(encoding="utf-8").splitlines()[1])["job_id"] == "job_b"

    summary = summarize_cost_log(entries)
    assert summary["runs"] == 2
    assert summary["total_usd"] == pytest.approx(0.18)
    assert summary["average_usd"] == pytest.approx(0.09)
    assert summary["cost_per_minute_usd"] == pytest.approx(0.18 / 2.0)


def test_missing_cost_log_reads_empty(tmp_path):
    assert read_cost_log(tmp_path / "nope.jsonl") == []
    assert summarize_cost_log([])["average_usd"] == 0.0
