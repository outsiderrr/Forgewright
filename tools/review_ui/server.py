"""FastAPI application factory + uvicorn launch helper for the review UI.

``build_app`` is the composition root: it wires the API router to a
``ReviewDataLoader``, mounts the bundled static directory at ``/static``,
and serves ``index.html`` at ``/``.  The factory is testable on its
own (``TestClient(build_app(...))``); ``cli.py`` is the only place that
reaches for ``uvicorn.run``.
"""
from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from .api import build_router
from .data import ReviewDataLoader

DEFAULT_PORT = 8765
PORT_ENV_VAR = "FORGEWRIGHT_REVIEW_UI_PORT"

STATIC_DIR = Path(__file__).resolve().parent / "static"


def build_app(
    *,
    batch_dir: Path | None,
    scenes_dir: Path | None,
    static_dir: Path | None = None,
) -> FastAPI:
    """Build a FastAPI app rooted on the given batch + scenes directories.

    ``static_dir`` defaults to the bundled ``tools/review_ui/static/``
    folder; override only in tests where the bundle path may differ.
    """
    app = FastAPI(
        title="Forgewright review UI",
        description=(
            "T-3.6a MVP — scene list + graph + validator + author A/R/S "
            "annotation. Read-only review tool; edits happen in JSON + git "
            "(ADR-025)."
        ),
        version="0.1.0",
    )
    loader = ReviewDataLoader(batch_dir=batch_dir, scenes_dir=scenes_dir)
    app.state.loader = loader
    app.include_router(build_router())

    static_root = (static_dir or STATIC_DIR).resolve()
    if static_root.is_dir():
        app.mount(
            "/static",
            StaticFiles(directory=static_root, check_dir=False),
            name="static",
        )
        index_path = static_root / "index.html"

        @app.get("/", include_in_schema=False, response_model=None)
        def index() -> FileResponse | JSONResponse:
            if not index_path.exists():
                return JSONResponse(
                    {"error": "static index.html missing"}, status_code=500
                )
            return FileResponse(index_path)

    return app


def resolve_port(cli_port: int | None = None) -> int:
    """``cli arg > FORGEWRIGHT_REVIEW_UI_PORT > DEFAULT_PORT``."""
    if cli_port is not None:
        return cli_port
    raw = os.environ.get(PORT_ENV_VAR)
    if not raw:
        return DEFAULT_PORT
    try:
        return int(raw)
    except ValueError as exc:
        raise SystemExit(
            f"{PORT_ENV_VAR}={raw!r} is not a valid integer"
        ) from exc
