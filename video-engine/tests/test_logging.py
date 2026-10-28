"""Live logging: one handler set, no secrets on either handler, quiet/verbose."""

from __future__ import annotations

import io
import logging

import pytest

from pebble.logging_setup import (
    CONSOLE_TAG,
    FILE_TAG,
    reset_logging,
    setup_logging,
    stage_banner,
)

SECRET_VALUE = "supersecretvalue123"


@pytest.fixture(autouse=True)
def clean_logging():
    reset_logging()
    yield
    reset_logging()


def _tagged(logger: logging.Logger, tag: str) -> list[logging.Handler]:
    return [handler for handler in logger.handlers if getattr(handler, tag, False)]


def test_repeated_setup_does_not_duplicate_handlers(tmp_path):
    logger = setup_logging(workspace=tmp_path)
    for _ in range(3):
        setup_logging(workspace=tmp_path)

    assert len(_tagged(logger, CONSOLE_TAG)) == 1
    assert len(_tagged(logger, FILE_TAG)) == 1

    setup_logging()
    assert len(_tagged(logger, CONSOLE_TAG)) == 1
    assert _tagged(logger, FILE_TAG) == []


def test_secret_values_are_redacted_on_both_handlers(monkeypatch, tmp_path):
    monkeypatch.setenv("PEBBLE_TEST_SECRET_KEY", SECRET_VALUE)
    stream = io.StringIO()
    setup_logging(workspace=tmp_path, stream=stream)

    logging.getLogger("pebble").warning("talking to the service with %s", SECRET_VALUE)

    console = stream.getvalue()
    file_text = (tmp_path / "pipeline.log").read_text(encoding="utf-8")
    assert SECRET_VALUE not in console
    assert SECRET_VALUE not in file_text
    assert "***" in console


def test_quiet_shows_only_banners_and_warnings(tmp_path):
    stream = io.StringIO()
    setup_logging(stream=stream, quiet=True)
    logger = logging.getLogger("pebble")

    logger.info("chatty detail")
    stage_banner(2, 5, "narrating")
    logger.warning("something failed")
    logger.debug("deep detail")

    output = stream.getvalue()
    assert "chatty detail" not in output
    assert "deep detail" not in output
    assert "== STAGE 2/5 narrating ==" in output
    assert "something failed" in output


def test_default_level_shows_info_but_not_debug(tmp_path):
    stream = io.StringIO()
    setup_logging(stream=stream)

    logging.getLogger("pebble").info("stage detail")
    logging.getLogger("pebble").debug("internal detail")

    output = stream.getvalue()
    assert "stage detail" in output
    assert "internal detail" not in output


def test_verbose_shows_debug_on_console(tmp_path):
    stream = io.StringIO()
    setup_logging(stream=stream, verbose=True)
    logging.getLogger("pebble").debug("internal detail")
    assert "internal detail" in stream.getvalue()


def test_file_handler_keeps_debug_even_when_console_is_quiet(tmp_path):
    stream = io.StringIO()
    setup_logging(workspace=tmp_path, stream=stream, quiet=True)
    logging.getLogger("pebble").debug("only in the file")

    assert "only in the file" not in stream.getvalue()
    assert "only in the file" in (tmp_path / "pipeline.log").read_text(encoding="utf-8")


def test_console_lines_carry_time_and_elapsed(tmp_path):
    stream = io.StringIO()
    setup_logging(stream=stream)
    logging.getLogger("pebble").info("[render 3/9] Scene3_Trace ok  12.4s")

    line = stream.getvalue().strip()
    assert "[render 3/9] Scene3_Trace ok  12.4s" in line
    assert line[:8].count(":") == 2  # HH:MM:SS
    assert "+" in line
