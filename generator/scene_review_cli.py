"""Interactive author-review CLI for a scene experiment batch (T-2.8).

CLI:

    python -m generator.scene_review_cli --batch-dir <path> [--web]

Walks every `success=True` row in `<batch-dir>/scene_results.jsonl` and
prompts the author for one of:

    [A]ccept   — scene passes review
    [R]eject   — scene fails review (followed by a one-line reason)
    [S]kip     — defer; nothing written to the log

Each prompt shows:

  * SceneSetting summary (anchor / chapter / location / NPCs / beats).
  * The graph itself — ASCII by default, mermaid in `--web` mode (a
    minimal http.server renders Mermaid via the GitHub-hosted CDN so
    nothing in the repo depends on a node toolchain).
  * Node text excerpts (narration head + first 2 options).
  * Three validator summaries baked into the row by `scene_experiment`:
    mechanical (T-2.4), topology (T-2.7 2A — pass + condition form),
    sampling (T-2.7 2B — reach_end_count + deadlock_count).

Decisions land in `<batch-dir>/scene_review_log.jsonl`:

    {iter_id, scene_id, schema_pass, topology_pass, sampling_pass,
     mechanical_pass, accepted, reason, reviewed_at}

Resumable: re-running picks up where you left off by skipping any
iter_id already in scene_review_log.jsonl. Skipped (`S`) items write
nothing, so they reappear next run; intentional.

Authority note (ADR-020 §6): the AI judge's advisory recommendation is
*not* the acceptance signal. Author A/R/S is the analysing unit; the
judge runner (scene_ai_judge) decorates this CLI's display when an
AI_JUDGE_REPORT.md is present in the batch dir, but the recommendation
is shown as `advisory:` text only — never used as a default.
"""
from __future__ import annotations

import argparse
import http.server
import json
import socketserver
import sys
import textwrap
import threading
import webbrowser
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import IO, Callable

from generator import graph_view

WRAP_WIDTH = 88
SEPARATOR = "─" * WRAP_WIDTH


# ---------------------------------------------------------------------------
# I/O helpers
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


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def _render_setting(env: dict) -> list[str]:
    fixture = env.get("fixture", {}) or {}
    setting = fixture.get("scene_setting", {}) or {}
    beats = fixture.get("target_beats") or []
    npcs = fixture.get("participating_npcs") or []
    out = ["【SceneSetting】"]
    out.append(
        f"  anchor:        {setting.get('scene_anchor')}  "
        f"chapter={setting.get('chapter_ref')}"
    )
    out.append(f"  primary_loc:   {setting.get('primary_location_ref')}")
    out.append(
        f"  expected_size: {setting.get('expected_node_count_min')}-"
        f"{setting.get('expected_node_count_max')} nodes"
    )
    out.append(f"  npcs:          {', '.join(npcs) if npcs else '(none)'}")
    out.append("  target_beats:")
    for beat in beats:
        out.append(_wrap(f"- {beat}", "    "))
    return out


def _render_validators(env: dict) -> list[str]:
    summaries = env.get("validator_summaries") or {}
    if not summaries:
        return ["【Validator summaries】", "  (not run — scene was a failure row)"]
    mech = summaries.get("mechanical") or {}
    topo = summaries.get("topology") or {}
    samp = summaries.get("sampling") or {}
    out = ["【Validator summaries】"]
    out.append(
        f"  mechanical (T-2.4): {'PASS' if mech.get('pass') else 'FAIL'}  "
        f"error_nodes={mech.get('error_node_count', 0)}  "
        f"errors={mech.get('error_count', 0)}  "
        f"codes={mech.get('error_codes') or '[]'}"
    )
    out.append(
        f"  topology (T-2.7 2A): {'PASS' if topo.get('pass') else 'FAIL'}  "
        f"errors={topo.get('error_count', 0)}  "
        f"warnings={topo.get('warning_count', 0)}  "
        f"codes={topo.get('error_codes') or '[]'}"
    )
    out.append(
        f"  sampling (T-2.7 2B): "
        f"reached={samp.get('reached_end_count', 0)}/"
        f"{samp.get('sample_count', 0)}  "
        f"deadlocks={samp.get('deadlock_count', 0)}  "
        f"avg_path_len={samp.get('avg_path_length', 0):.1f}"
    )
    return out


def _render_nodes(graph: dict, max_nodes: int = 6) -> list[str]:
    nodes = graph.get("nodes") or {}
    out = [f"【Nodes ({len(nodes)})】"]
    shown = 0
    for nid, node in nodes.items():
        if shown >= max_nodes:
            out.append(f"  …({len(nodes) - shown} more nodes hidden)")
            break
        speaker = node.get("speaker_ref") or "(narrator)"
        out.append(f"  - {nid}  type={node.get('type')}  speaker={speaker}")
        narration = (node.get("narration") or "").strip()
        if narration:
            head = narration[:80].replace("\n", " ")
            out.append(f"      narration: {head}{'...' if len(narration) > 80 else ''}")
        for opt in (node.get("options") or [])[:2]:
            cond = "[cond] " if opt.get("condition") is not None else ""
            text = (opt.get("text") or "")[:60]
            out.append(f"      • {cond}{text} → {opt.get('target_node_id')}")
        if len(node.get("options") or []) > 2:
            out.append(f"      • …({len(node['options']) - 2} more options)")
        shown += 1
    return out


def _render_ai_judge_advisory(batch_dir: Path, scene_id: str) -> list[str]:
    """Surface the AI judge's advisory recommendation if a report exists.

    Author A/R/S remains the acceptance signal (ADR-020 §6); this is
    informational only.
    """
    report_path = batch_dir / "AI_JUDGE_REPORT.json"
    if not report_path.exists():
        return []
    try:
        data = json.loads(report_path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001 — malformed report is non-fatal for review
        return []
    advisory = (data.get("advisory_recommendation") or {}).get(scene_id)
    if not advisory:
        return []
    return ["【AI judge advisory (informational only)】", f"  recommendation: {advisory}"]


def _render_envelope(env: dict, *, batch_dir: Path, position: str) -> str:
    result = env.get("result", {}) or {}
    graph = result.get("graph") or {}
    scene_id = graph.get("graph_id") or f"iter_{env.get('iter_id')}"

    parts: list[str] = []
    parts.append(SEPARATOR)
    parts.append(
        f"iter {env.get('iter_id')}  ({position})  "
        f"fixture={env.get('fixture_id')}  scene_id={scene_id}  "
        f"cost=${result.get('total_cost_usd', 0.0):.4f}  "
        f"attempts={result.get('inner_attempt_count', 0)}"
    )
    parts.append(SEPARATOR)
    parts.extend(_render_setting(env))
    parts.append("")
    parts.append("【Graph (ASCII)】")
    parts.append(graph_view.render_ascii(graph, max_width=WRAP_WIDTH))
    parts.extend(_render_validators(env))
    parts.append("")
    parts.extend(_render_nodes(graph))
    advisory = _render_ai_judge_advisory(batch_dir, scene_id)
    if advisory:
        parts.append("")
        parts.extend(advisory)
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Web viewer (mermaid via CDN)
# ---------------------------------------------------------------------------


def _build_mermaid_index(envelopes: list[dict]) -> str:
    """Render a tiny HTML page that loads Mermaid from cdn.jsdelivr.net.

    Author still drives A/R/S in the terminal; this page is preview-only.
    Untrusted fields (scene_id, fixture_id) are HTML-escaped; mermaid
    source is rendered inside `<pre class="mermaid">` which Mermaid's
    runtime parses without re-evaluating raw HTML.
    """
    sections: list[str] = []
    for env in envelopes:
        graph = (env.get("result") or {}).get("graph") or {}
        scene_id = graph.get("graph_id") or f"iter_{env.get('iter_id')}"
        fixture_id = env.get("fixture_id") or "?"
        mermaid = graph_view.render_mermaid(graph)
        sections.append(
            f'<section style="margin:24px 0">'
            f'<h3 style="font-family:monospace">'
            f'{escape(str(scene_id))} <small style="color:#888">'
            f'({escape(str(fixture_id))})</small></h3>'
            f'<pre class="mermaid">{escape(mermaid)}</pre>'
            f"</section>"
        )
    return (
        "<!doctype html><meta charset='utf-8'>"
        "<title>Forgewright scene review</title>"
        "<body style='background:#fafafa;font-family:sans-serif'>"
        "<h1>Scene preview</h1>"
        "<p>Decide A/R/S in the terminal — this page is preview-only.</p>"
        + "".join(sections)
        + "<script type='module'>"
        "import mermaid from 'https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.esm.min.mjs';"
        "mermaid.initialize({startOnLoad: true});"
        "</script></body>"
    )


def _start_web_viewer(
    batch_dir: Path, envelopes: list[dict], output: IO[str]
) -> None:
    index_path = batch_dir / "scene_preview.html"
    index_path.write_text(_build_mermaid_index(envelopes), encoding="utf-8")

    handler_cls = http.server.SimpleHTTPRequestHandler
    serve_root = batch_dir.resolve()

    class _RootedHandler(handler_cls):  # type: ignore[misc, valid-type]
        def translate_path(self, path: str) -> str:  # noqa: D401
            from urllib.parse import unquote, urlsplit

            rel = unquote(urlsplit(path).path).lstrip("/")
            candidate = (serve_root / rel).resolve()
            try:
                candidate.relative_to(serve_root)
            except ValueError:
                return str(serve_root / "__forbidden__")
            return str(candidate)

        def list_directory(self, path: str):  # type: ignore[override]
            self.send_error(403, "Directory listing disabled")
            return None

    httpd = socketserver.TCPServer(("127.0.0.1", 0), _RootedHandler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}/scene_preview.html"
    print(f"[web] serving mermaid preview at {url}", file=output)
    try:
        webbrowser.open(url)
    except Exception:  # noqa: BLE001 — best-effort
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


def run_scene_review(
    batch_dir: Path,
    *,
    web: bool = False,
    input_fn: Callable[[str], str] = input,
    output: IO[str] = sys.stdout,
) -> int:
    """Walk every successful scene + prompt A/R/S.

    Returns the number of decisions appended to scene_review_log.jsonl.
    """
    results_path = batch_dir / "scene_results.jsonl"
    review_path = batch_dir / "scene_review_log.jsonl"

    if not results_path.exists():
        print(f"error: scene_results.jsonl not found at {results_path}", file=sys.stderr)
        return -1

    envelopes = _read_jsonl(results_path)
    successful = [e for e in envelopes if e.get("result", {}).get("success")]
    already_reviewed = {
        rec["iter_id"] for rec in _read_jsonl(review_path) if "iter_id" in rec
    }
    pending = [e for e in successful if e.get("iter_id") not in already_reviewed]

    print(
        f"batch:               {batch_dir}\n"
        f"successful scenes:   {len(successful)}\n"
        f"already reviewed:    {len(already_reviewed & {e['iter_id'] for e in successful})}\n"
        f"pending review:      {len(pending)}\n",
        file=output,
    )

    if not pending:
        print("nothing to review.", file=output)
        return 0

    if web:
        _start_web_viewer(batch_dir, pending, output)

    written = 0
    for idx, env in enumerate(pending, start=1):
        position = f"{idx}/{len(pending)} pending  · {len(successful)} total"
        print(_render_envelope(env, batch_dir=batch_dir, position=position), file=output)
        print("", file=output)

        try:
            decision = _prompt_decision(input_fn)
        except (EOFError, KeyboardInterrupt):
            print("\n[review] interrupted; partial progress saved.", file=output)
            break

        if decision == "skip":
            print("[review] skipped (will reappear on next run).\n", file=output)
            continue

        graph = (env.get("result") or {}).get("graph") or {}
        scene_id = graph.get("graph_id") or f"iter_{env.get('iter_id')}"
        summaries = env.get("validator_summaries") or {}
        record = {
            "iter_id": env.get("iter_id"),
            "scene_id": scene_id,
            "schema_pass": True,
            "topology_pass": (summaries.get("topology") or {}).get("pass"),
            "sampling_pass": (summaries.get("sampling") or {}).get("reached_end_count", 0)
            > 0,
            "mechanical_pass": (summaries.get("mechanical") or {}).get("pass"),
            "accepted": decision == "accept",
            "reason": None,
            "reviewed_at": _now_iso(),
        }
        if decision == "reject":
            try:
                reason = input_fn("  reject reason (one line): ").strip()
            except (EOFError, KeyboardInterrupt):
                print(
                    "\n[review] interrupted before reason captured; not saved.",
                    file=output,
                )
                break
            record["reason"] = reason or "(no reason given)"

        _append_review_record(review_path, record)
        written += 1
        if decision == "accept":
            print("[review] accepted.\n", file=output)
        else:
            print(f"[review] rejected: {record['reason']}\n", file=output)

    print(
        f"[review] session done. {written} decision(s) written to {review_path}",
        file=output,
    )
    return written


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m generator.scene_review_cli",
        description=(
            "Interactively review the success scenes in a scene_experiment "
            "batch (T-2.8). Author A/R/S is the acceptance signal; AI judge "
            "advisory is informational only (ADR-020 §6)."
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
            "Spawn a minimal http.server with a mermaid preview "
            "(default: ASCII in-terminal only)."
        ),
    )
    args = parser.parse_args(argv)

    if not args.batch_dir.exists():
        print(f"error: batch-dir does not exist: {args.batch_dir}", file=sys.stderr)
        return 2

    rc = run_scene_review(args.batch_dir, web=args.web)
    return 0 if rc >= 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
