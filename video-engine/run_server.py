#!/usr/bin/env python3
"""Start the Pebble HTTP API and its background worker.

    python run_server.py            # 127.0.0.1:8000
    PEBBLE_HOST=0.0.0.0 PEBBLE_PORT=9000 python run_server.py --reload-off

The banner prints names only: never a key, a connection string or a secret.
"""

from __future__ import annotations

import argparse
import os
import sys

from pebble.api import (
    API_KEY_ENV,
    build_runtime,
    configured_api_key,
    set_runtime,
    startup_warnings,
)
from pebble.errors import PebbleError
from pebble.logging_setup import setup_logging, stage_banner
from pebble.storage import BlobStorage

DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="run_server.py", description="Pebble API + background worker"
    )
    parser.add_argument(
        "-v", "--verbose", action="store_true", help="DEBUG lines on the console"
    )
    parser.add_argument("--host", default=os.environ.get("PEBBLE_HOST") or DEFAULT_HOST)
    parser.add_argument(
        "--port", type=int, default=int(os.environ.get("PEBBLE_PORT") or DEFAULT_PORT)
    )
    args = parser.parse_args(argv)

    setup_logging(verbose=args.verbose)

    try:
        runtime = build_runtime()
    except PebbleError as exc:
        print(f"startup failed: {exc}", file=sys.stderr)
        return 2

    set_runtime(runtime)
    runtime.worker.start()

    from pebble.api import app

    stage_banner(1, 1, "serving")
    print("Pebble API")
    print(f"  host        : {args.host}")
    print(f"  port        : {args.port}")
    print(f"  auth        : {'on' if configured_api_key() else 'off'} ({API_KEY_ENV})")
    print(f"  container   : {runtime.storage.container}")
    print(f"  queue depth : {runtime.store.queue_depth()}")
    print(f"  jobs db     : {runtime.store.path}")
    for note in startup_warnings():
        print(f"  WARNING     : {note}")

    import uvicorn

    try:
        uvicorn.run(app, host=args.host, port=args.port, log_level="warning")
    finally:
        runtime.worker.stop()
        runtime.store.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
