"""Live terminal logging: compact console lines, a full file log, no secrets.

``setup_logging`` is idempotent: every call removes the handlers it installed
before, so repeated setup (tests, a pipeline run after a CLI run) never
duplicates lines. A filter rewrites the *values* of secret-looking environment
variables to ``***`` on both handlers, so a stray repr or error message cannot
leak a key.
"""

from __future__ import annotations

import logging
import os
import sys
import time
from pathlib import Path
from typing import Any, Iterable, TextIO

LOGGER_NAME = "pebble"

CONSOLE_TAG = "_pebble_console"
FILE_TAG = "_pebble_file"

SECRET_NAME_MARKERS = ("KEY", "SECRET", "TOKEN", "PASSWORD", "CONNECTION")
MIN_SECRET_LENGTH = 4
REDACTED = "***"

NOISY_LOGGERS = ("openai", "httpx", "httpcore", "urllib3", "azure", "manim")

_START = time.time()


class SecretFilter(logging.Filter):
    """Replace every secret env *value* found in a message with ***."""

    def __init__(self, secrets: Iterable[str]) -> None:
        super().__init__()
        # Longest first, so a key that contains another value is fully hidden.
        self._secrets = sorted(
            {value for value in secrets if value and len(value) >= MIN_SECRET_LENGTH},
            key=len,
            reverse=True,
        )

    def filter(self, record: logging.LogRecord) -> bool:
        if not self._secrets:
            return True
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover - a broken format string must not crash
            return True
        cleaned = message
        for secret in self._secrets:
            if secret in cleaned:
                cleaned = cleaned.replace(secret, REDACTED)
        if cleaned != message:
            record.msg = cleaned
            record.args = ()
        return True


class LevelFilter(logging.Filter):
    """Console policy: banners always show; quiet only shows warnings and up."""

    def __init__(self, quiet: bool = False, verbose: bool = False) -> None:
        super().__init__()
        self.quiet = quiet
        self.verbose = verbose

    def filter(self, record: logging.LogRecord) -> bool:
        if getattr(record, "banner", False):
            return True
        if self.verbose:
            return True
        if self.quiet:
            return record.levelno >= logging.WARNING
        return record.levelno >= logging.INFO


class CompactFormatter(logging.Formatter):
    """``21:07:42  +  12.4s  [render 3/9] Scene3_Trace ok``"""

    def __init__(self, start: float | None = None) -> None:
        super().__init__()
        self.start = _START if start is None else start

    def format(self, record: logging.LogRecord) -> str:
        stamp = time.strftime("%H:%M:%S", time.localtime(record.created))
        try:
            message = record.getMessage()
        except Exception:  # pragma: no cover
            message = str(record.msg)
        if record.exc_info:
            message = f"{message}\n{self.formatException(record.exc_info)}"
        if getattr(record, "banner", False):
            return f"{stamp}  {message}"
        elapsed = max(0.0, record.created - self.start)
        return f"{stamp}  +{elapsed:6.1f}s  {message}"


def secret_values(environ: dict[str, str] | None = None) -> list[str]:
    """Values of env vars whose name looks secret, for the redaction filter.

    Kept inside this module and never logged: the filter only uses the values to
    replace them with ``***``.
    """
    source = os.environ if environ is None else environ
    values: list[str] = []
    for name, value in source.items():
        upper = name.upper()
        if not any(marker in upper for marker in SECRET_NAME_MARKERS):
            continue
        if value and len(value) >= MIN_SECRET_LENGTH:
            values.append(value)
    return values


def _resolve_log_path(workspace: Any) -> Path:
    if hasattr(workspace, "pipeline_log_path"):
        return Path(workspace.pipeline_log_path)
    path = Path(workspace)
    if path.suffix == ".log":
        return path
    return path / "pipeline.log"


def setup_logging(
    workspace: Any = None,
    verbose: bool = False,
    quiet: bool = False,
    stream: TextIO | None = None,
) -> logging.Logger:
    """Install one console handler (and one file handler when a workspace is given)."""
    for name in NOISY_LOGGERS:
        logging.getLogger(name).setLevel(logging.WARNING)

    # Libraries that never set their own level inherit the root logger's. Manim
    # installs a RichHandler on the root at import time, so without this the SDK
    # and manim's own chatter stream straight to the terminal. Pebble's logger
    # has propagate=False, so its output is untouched.
    logging.getLogger().setLevel(logging.WARNING)

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False

    for handler in list(logger.handlers):
        if getattr(handler, CONSOLE_TAG, False) or getattr(handler, FILE_TAG, False):
            logger.removeHandler(handler)
            handler.close()

    secrets = secret_values()

    console = logging.StreamHandler(stream if stream is not None else sys.stderr)
    console.setLevel(logging.NOTSET)
    console.addFilter(LevelFilter(quiet=quiet, verbose=verbose))
    console.addFilter(SecretFilter(secrets))
    console.setFormatter(CompactFormatter())
    setattr(console, CONSOLE_TAG, True)
    logger.addHandler(console)

    if workspace is not None:
        path = _resolve_log_path(workspace)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            file_handler = logging.FileHandler(path, encoding="utf-8")
        except OSError:  # pragma: no cover - a read-only workspace must not crash a run
            file_handler = None
        if file_handler is not None:
            file_handler.setLevel(logging.DEBUG)
            file_handler.addFilter(SecretFilter(secrets))
            file_handler.setFormatter(
                logging.Formatter("%(asctime)s %(levelname)-7s %(name)s: %(message)s")
            )
            setattr(file_handler, FILE_TAG, True)
            logger.addHandler(file_handler)

    return logger


def stage_banner(index: int, total: int, stage: str) -> None:
    """Log a stage banner that survives --quiet."""
    logging.getLogger(LOGGER_NAME).info(
        "== STAGE %d/%d %s ==", index, total, stage, extra={"banner": True}
    )


def reset_logging() -> None:
    """Remove Pebble's handlers (used by tests)."""
    logger = logging.getLogger(LOGGER_NAME)
    for handler in list(logger.handlers):
        if getattr(handler, CONSOLE_TAG, False) or getattr(handler, FILE_TAG, False):
            logger.removeHandler(handler)
            handler.close()
