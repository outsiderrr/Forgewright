"""CLI entry point: ``python -m tools.review_ui [...]``.

Resolves the batch / scenes directories, builds the app, and hands it
off to uvicorn.  Defaults try to be useful in the common case
(``--batch-dir`` autodetects the most recent
``generator/experiments/<timestamp>_<name>/``; ``--scenes-dir`` defaults
to ``./content/``).
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import uvicorn

from .server import PORT_ENV_VAR, build_app, resolve_port


def _autodetect_batch_dir() -> Path | None:
    root = Path.cwd() / "generator" / "experiments"
    if not root.is_dir():
        return None
    candidates = [c for c in root.iterdir() if c.is_dir()]
    if not candidates:
        return None
    candidates.sort(key=lambda c: c.name, reverse=True)
    return candidates[0]


def _autodetect_scenes_dir() -> Path | None:
    candidate = Path.cwd() / "content"
    return candidate if candidate.is_dir() else None


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m tools.review_ui",
        description=(
            "Forgewright review UI MVP (T-3.6a; ADR-025). Serves a "
            "FastAPI + vanilla HTML/JS app on localhost so the author "
            "can browse a scene_experiment batch, view the dialogue "
            "graph, inspect validator findings, and record [A]/[R] "
            "decisions."
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=None,
        help=(
            "TCP port (default: env "
            f"{PORT_ENV_VAR} or 8765)."
        ),
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Bind address (default: 127.0.0.1; localhost-only is the ADR-025 deployment shape).",
    )
    parser.add_argument(
        "--batch-dir",
        type=Path,
        default=None,
        help=(
            "Path to a generator/experiments/<batch>/ directory. "
            "Default: most recent under ./generator/experiments/."
        ),
    )
    parser.add_argument(
        "--scenes-dir",
        type=Path,
        default=None,
        help="Path to the final scenes directory (default: ./content/).",
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable uvicorn reload (development only).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    batch_dir = args.batch_dir or _autodetect_batch_dir()
    scenes_dir = args.scenes_dir or _autodetect_scenes_dir()
    if batch_dir is not None and not batch_dir.is_dir():
        print(f"error: --batch-dir not a directory: {batch_dir}", file=sys.stderr)
        return 2
    if scenes_dir is not None and not scenes_dir.is_dir():
        print(f"error: --scenes-dir not a directory: {scenes_dir}", file=sys.stderr)
        return 2
    port = resolve_port(args.port)
    print(
        f"[review_ui] batch_dir = {batch_dir}\n"
        f"[review_ui] scenes_dir = {scenes_dir}\n"
        f"[review_ui] serving http://{args.host}:{port}/",
        file=sys.stderr,
    )
    app = build_app(batch_dir=batch_dir, scenes_dir=scenes_dir)
    uvicorn.run(app, host=args.host, port=port, log_level="info", reload=args.reload)
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
