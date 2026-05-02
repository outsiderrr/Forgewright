"""Interactive author-review CLI for a visual experiment batch (T-1.5.8).

CLI:

    python -m generator.visual_review_cli --batch-dir <path> [--web]

For each successful row in `<batch-dir>/results.jsonl` whose
`asset_id_stub` is **already imported** into the manifest (i.e.
`image_import` has run and the image is on disk), the CLI:

  1. Prints metadata (asset_id / target_ref / asset_role / size / file_path).
  2. Opens the image — `open <file_path>` on macOS; non-macOS platforms
     get told to re-run with `--web` (per task spec, no Linux/Windows
     native preview is added).
  3. Prompts:

         [A]ccept   — author approves
         [R]eject   — author rejects (followed by a one-line reason)
         [S]kip     — defer; nothing written to the log

  4. Appends the decision to `<batch-dir>/visual_review_log.jsonl`:

         {asset_id, accepted, reason, reviewed_at, mechanical_check_passed}

The log is the data source for `visual_metrics.acceptance_rate`. Skipped
rows write nothing, so re-running the CLI re-shows them.

`--web` opens a tiny `http.server` on localhost serving thumbnails out
of the repo root — the author still drives A/R/S in the terminal. Pure
HTML; no React/Vue (forge-UI overhaul is a Stage-3 concern).

Authority note (P1.4 decision): the visual AI judge prompt
(`generator/prompts/visual/REVIEW_PROMPT_AI_JUDGE_VISUAL.md`) only
*suggests* — author A/R/S is the final acceptance signal, mirroring the
STAGE_1_ACCEPTANCE R6/R8 lessons.
"""

from __future__ import annotations

import argparse
import http.server
import json
import socketserver
import subprocess
import sys
import textwrap
import threading
import webbrowser
from datetime import datetime, timezone
from pathlib import Path
from typing import IO, Callable

from generator.manifest import DEFAULT_MANIFEST_PATH, load_manifest
from generator.models._generated.image_asset import ImageAsset

WRAP_WIDTH = 88
SEPARATOR = "─" * WRAP_WIDTH


# ---------------------------------------------------------------------------
# Pure helpers
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_review_record(log_path: Path, record: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        fh.flush()


def _wrap(text: str, indent: str = "") -> str:
    out: list[str] = []
    for para in (text or "").split("\n"):
        if not para.strip():
            out.append("")
            continue
        out.append(
            textwrap.fill(
                para,
                width=WRAP_WIDTH,
                initial_indent=indent,
                subsequent_indent=indent,
                break_long_words=False,
                break_on_hyphens=False,
            )
        )
    return "\n".join(out)


def _render_asset(env: dict, asset: ImageAsset, *, position: str) -> str:
    """Render one asset header for human review."""
    result = env.get("result", {}) or {}
    raw = result.get("raw_metadata") or {}
    parts: list[str] = []
    parts.append(SEPARATOR)
    parts.append(
        f"asset_id={asset.asset_id}  ({position})  "
        f"role={asset.asset_role}  size={asset.width}x{asset.height}"
    )
    parts.append(SEPARATOR)
    parts.append(f"  target_ref:    {asset.target_ref}")
    parts.append(f"  target_type:   {asset.target_type}")
    parts.append(f"  variant:       {raw.get('variant_label', '(?)')}")
    parts.append(f"  file_path:     {asset.file_path}")
    parts.append(f"  source_mode:   {asset.source_mode}")
    parts.append(f"  has_alpha:     {asset.has_alpha}")
    parts.append(f"  format:        {asset.format}")
    if asset.style_reference_id:
        parts.append(f"  style_ref:     {asset.style_reference_id}")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Default viewer — macOS `open`; non-macOS raises so caller falls back to --web
# ---------------------------------------------------------------------------


def _default_viewer(file_path: str) -> None:
    """Open an image in the platform's default viewer.

    macOS uses `/usr/bin/open` directly so we don't accidentally inherit
    PATH-shadowed binaries. Non-macOS platforms raise — task spec is to
    point the author at `--web` rather than YAGNI a Linux/Windows
    fallback.
    """
    if sys.platform == "darwin":
        try:
            subprocess.run(["/usr/bin/open", file_path], check=False)
        except FileNotFoundError:
            subprocess.run(["open", file_path], check=False)
        return
    raise RuntimeError(
        f"native preview not supported on {sys.platform!r}; re-run with --web"
    )


# ---------------------------------------------------------------------------
# Web viewer (minimal http.server)
# ---------------------------------------------------------------------------


def _build_index_html(pending: list[tuple[dict, ImageAsset]]) -> str:
    items: list[str] = []
    for env, asset in pending:
        # `file_path` is repo-relative ("content/visuals/<sub>/<id>.png").
        # When the http.server is rooted at the repo, this URL resolves.
        items.append(
            f'<section style="margin:24px 0">'
            f'<h3 style="font-family:monospace">{asset.asset_id}</h3>'
            f'<p style="font-family:monospace">'
            f'target={asset.target_ref} | role={asset.asset_role} | '
            f'size={asset.width}x{asset.height}</p>'
            f'<img src="/{asset.file_path}" '
            f'style="max-width:512px;border:1px solid #ccc"/>'
            f"</section>"
        )
    return (
        "<!doctype html><meta charset='utf-8'>"
        "<title>Forgewright visual review</title>"
        "<body style='background:#fafafa'>"
        "<h1 style='font-family:sans-serif'>Visual review thumbnails</h1>"
        "<p style='font-family:sans-serif'>Decide A/R/S in the terminal — "
        "this page is preview-only.</p>"
        + "".join(items)
        + "</body>"
    )


def _start_web_viewer(
    batch_dir: Path,
    pending: list[tuple[dict, ImageAsset]],
    serve_root: Path,
    output: IO[str],
) -> None:
    """Generate batch_dir/index.html, start http.server in serve_root, open
    browser. The httpd thread is a daemon — process exit kills it without
    needing a tear-down hook in the review loop."""
    index_path = batch_dir / "index.html"
    index_path.write_text(_build_index_html(pending), encoding="utf-8")

    handler_cls = http.server.SimpleHTTPRequestHandler
    cwd = Path.cwd().resolve()

    class _RootedHandler(handler_cls):  # type: ignore[misc, valid-type]
        def translate_path(self, path: str) -> str:  # noqa: D401
            # Force the server root onto serve_root regardless of process
            # CWD, so the author can launch the CLI from anywhere.
            from urllib.parse import unquote

            rel = unquote(path).lstrip("/").split("?", 1)[0].split("#", 1)[0]
            return str((serve_root / rel).resolve())

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _RootedHandler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()

    try:
        rel_index = index_path.resolve().relative_to(cwd).as_posix()
    except ValueError:
        rel_index = index_path.as_posix()
    url = f"http://127.0.0.1:{port}/{rel_index}"
    print(f"[web] serving thumbnails at {url}", file=output)
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001 — best-effort, must not fail the review
        pass


# ---------------------------------------------------------------------------
# Core loop
# ---------------------------------------------------------------------------


def _prompt_decision(input_fn: Callable[[str], str]) -> str:
    while True:
        raw = input_fn("  [A]ccept / [R]eject / [S]kip ? ").strip().lower()
        if raw in ("a", "accept"):
            return "accept"
        if raw in ("r", "reject"):
            return "reject"
        if raw in ("s", "skip"):
            return "skip"
        print("  (please type A, R, or S)")


def run_visual_review(
    batch_dir: Path,
    *,
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    web: bool = False,
    web_serve_root: Path | None = None,
    viewer: Callable[[str], None] | None = None,
    input_fn: Callable[[str], str] = input,
    output: IO[str] = sys.stdout,
) -> int:
    """Walk every successful + already-imported asset and prompt A/R/S.

    Returns the number of decisions appended to visual_review_log.jsonl
    during this session (skips and already-reviewed don't count).
    """
    results_path = batch_dir / "results.jsonl"
    review_path = batch_dir / "visual_review_log.jsonl"

    if not results_path.exists():
        print(f"error: results.jsonl not found at {results_path}", file=sys.stderr)
        return -1

    envelopes = _read_jsonl(results_path)
    successful = [e for e in envelopes if e.get("result", {}).get("success")]

    manifest = load_manifest(manifest_path)
    already_reviewed = {
        rec["asset_id"] for rec in _read_jsonl(review_path) if "asset_id" in rec
    }

    pending: list[tuple[dict, ImageAsset]] = []
    skipped_unimported = 0
    for env in successful:
        stub = env.get("result", {}).get("asset_id_stub")
        if not stub:
            continue
        if stub in already_reviewed:
            continue
        asset = manifest.assets.get(stub)
        if asset is None:
            # Mechanical-check status unknown — author hasn't run
            # `image_import` for this stub yet. Don't review what isn't
            # imported; surface the count so the author knows to import first.
            skipped_unimported += 1
            continue
        pending.append((env, asset))

    print(
        f"batch:               {batch_dir}\n"
        f"successful rows:     {len(successful)}\n"
        f"already reviewed:    {len(already_reviewed)}\n"
        f"awaiting import:     {skipped_unimported}\n"
        f"pending review:      {len(pending)}\n",
        file=output,
    )

    if not pending:
        print("nothing to review.", file=output)
        return 0

    if web:
        serve_root = web_serve_root if web_serve_root is not None else Path.cwd()
        _start_web_viewer(batch_dir, pending, serve_root, output)

    if viewer is None:
        viewer = _default_viewer

    written = 0
    for idx, (env, asset) in enumerate(pending, start=1):
        position = f"{idx}/{len(pending)}"
        print(_render_asset(env, asset, position=position), file=output)
        print("", file=output)

        try:
            viewer(asset.file_path)
        except RuntimeError as exc:
            print(f"  [viewer] {exc}", file=output)
        except Exception as exc:  # noqa: BLE001 — viewer failure is non-fatal
            print(f"  [viewer] failed: {exc}", file=output)

        try:
            decision = _prompt_decision(input_fn)
        except (EOFError, KeyboardInterrupt):
            print("\n[review] interrupted; partial progress saved.", file=output)
            break

        if decision == "skip":
            print("[review] skipped (will reappear on next run).\n", file=output)
            continue

        if decision == "accept":
            record = {
                "asset_id": asset.asset_id,
                "accepted": True,
                "reason": None,
                "reviewed_at": _now_iso(),
                "mechanical_check_passed": True,
            }
            _append_review_record(review_path, record)
            written += 1
            print("[review] accepted.\n", file=output)
            continue

        # reject
        try:
            reason = input_fn("  reject reason (one line): ").strip()
        except (EOFError, KeyboardInterrupt):
            print(
                "\n[review] interrupted before reason captured; not saved.",
                file=output,
            )
            break
        record = {
            "asset_id": asset.asset_id,
            "accepted": False,
            "reason": reason or "(no reason given)",
            "reviewed_at": _now_iso(),
            "mechanical_check_passed": True,
        }
        _append_review_record(review_path, record)
        written += 1
        print(f"[review] rejected: {reason}\n", file=output)

    print(
        f"[review] session done. {written} decision(s) written to {review_path}",
        file=output,
    )
    return written


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m generator.visual_review_cli",
        description=(
            "Interactively review the imported assets in a visual "
            "experiment batch (mechanical check already passed via "
            "image_import; this is the author A/R/S step)."
        ),
    )
    parser.add_argument(
        "--batch-dir",
        required=True,
        type=Path,
        help="Path to /generator/experiments/<timestamp>_<batch_name>/",
    )
    parser.add_argument(
        "--web",
        action="store_true",
        help=(
            "Spawn a minimal http.server on localhost serving thumbnails; "
            "non-macOS platforms must use this since native `open` is "
            "macOS-only."
        ),
    )
    args = parser.parse_args(argv)

    if not args.batch_dir.exists():
        print(f"error: batch-dir does not exist: {args.batch_dir}", file=sys.stderr)
        return 2

    rc = run_visual_review(args.batch_dir, web=args.web)
    return 0 if rc >= 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
