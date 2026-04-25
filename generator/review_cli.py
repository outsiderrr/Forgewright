"""Interactive author-review CLI for an experiment batch (T-1.7).

CLI:

    python -m generator.review_cli --batch-dir <path>

Walks every `success=True` row in `results.jsonl` and prompts the author
for one of:

    [A]ccept   — node passes review
    [R]eject   — node fails review (followed by a one-line reason)
    [S]kip     — defer; nothing written to the log

Decisions land in `<batch-dir>/review_log.jsonl`, one JSON object per
line:

    {iter_id, node_id_or_idx, schema_pass, accepted, reason, reviewed_at}

The script is resumable — re-running it picks up where you left off by
skipping any iter_id already present in the existing review_log.jsonl.
Skipped (`S`) items write nothing, so they will reappear on the next run;
that's intentional.

Display is plain text (no rich) so it works inside any terminal the
author happens to land in. Long narration is wrapped to ~88 columns.
"""
from __future__ import annotations

import argparse
import json
import sys
import textwrap
from datetime import datetime, timezone
from pathlib import Path
from typing import IO

WRAP_WIDTH = 88
SEPARATOR = "─" * WRAP_WIDTH


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


def _wrap(text: str, indent: str = "") -> str:
    """Word-wrap a (possibly multi-paragraph) string. CJK is treated by
    `textwrap` as glue characters, so we split on \n first to preserve
    the author's paragraph breaks before re-wrapping each one."""
    out: list[str] = []
    for para in text.split("\n"):
        if not para.strip():
            out.append("")
            continue
        wrapped = textwrap.fill(
            para,
            width=WRAP_WIDTH,
            initial_indent=indent,
            subsequent_indent=indent,
            break_long_words=False,
            break_on_hyphens=False,
        )
        out.append(wrapped)
    return "\n".join(out)


def _render_envelope(envelope: dict, *, position: str) -> str:
    """Render one envelope for human review.

    `position` is a string like "12/20" surfaced in the header so the
    author always knows where they are in the batch.
    """
    fixture = envelope.get("fixture", {})
    requirement = fixture.get("node_requirement", {}) or {}
    context = fixture.get("graph_context", {}) or {}
    result = envelope.get("result", {})
    node = result.get("node") or {}

    parts: list[str] = []
    parts.append(SEPARATOR)
    parts.append(
        f"iter {envelope.get('iter_id')}  "
        f"({position})  "
        f"fixture={envelope.get('fixture_id')}  "
        f"cost=${result.get('total_cost_usd', 0.0):.4f}  "
        f"attempts={len(result.get('attempts', []) or [])}"
    )
    parts.append(SEPARATOR)

    parts.append("【生成要求】")
    parts.append(
        f"  type={requirement.get('node_type')}  "
        f"speaker={requirement.get('expected_speaker_ref')}"
    )
    parts.append(_wrap(f"intent: {requirement.get('narrative_intent', '')}", "  "))

    parts.append("")
    parts.append("【上下文摘要】")
    parts.append(f"  scene_anchor: {context.get('scene_anchor')}")
    location = context.get("location_card") or {}
    if location:
        parts.append(
            f"  location:     {location.get('name', location.get('location_id', '?'))}"
        )
    chars = context.get("involved_characters") or []
    if chars:
        labels = ", ".join(c.get("character_id", "?") for c in chars)
        parts.append(f"  characters:   {labels}")
    parent_chain = context.get("parent_chain") or []
    parts.append(f"  parent_chain: {len(parent_chain)} ancestor(s)")

    parts.append("")
    parts.append("【生成节点 — 玩家可见】")
    parts.append(f"  node_id:  {node.get('node_id')}")
    parts.append(f"  type:     {node.get('type')}")
    parts.append(f"  speaker:  {node.get('speaker_ref')}")
    parts.append("")
    parts.append("  narration:")
    parts.append(_wrap(node.get("narration", "(empty)"), "    "))
    options = node.get("options") or []
    parts.append("")
    if node.get("type") == "end":
        parts.append(f"  options:  (end node — {len(options)} options)")
    else:
        parts.append(f"  options ({len(options)}):")
        for i, opt in enumerate(options, start=1):
            cond = opt.get("condition")
            cond_marker = "  [conditional]" if cond else ""
            parts.append(_wrap(
                f"    {i}. {opt.get('text', '(no text)')}{cond_marker}",
                "        ",
            ).lstrip(" "))

    parts.append("")
    parts.append("【完整 JSON】")
    parts.append(textwrap.indent(
        json.dumps(node, ensure_ascii=False, indent=2),
        "  ",
    ))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# I/O helpers (kept tiny + injectable so the test can drive them)
# ---------------------------------------------------------------------------


def _default_input(prompt: str) -> str:
    # Wrapped so tests can swap in a scripted reader. Using EOFError-friendly
    # input(); KeyboardInterrupt is allowed to propagate so Ctrl-C works.
    return input(prompt)


def _append_review_record(log_path: Path, record: dict) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")
        fh.flush()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# Core loop
# ---------------------------------------------------------------------------


def run_review(
    batch_dir: Path,
    *,
    input_fn=_default_input,
    output: IO[str] = sys.stdout,
) -> int:
    """Review every successful envelope in `batch_dir/results.jsonl`.

    Returns the number of decisions appended to review_log.jsonl during
    this session (skips and already-reviewed don't count).
    """
    results_path = batch_dir / "results.jsonl"
    review_path = batch_dir / "review_log.jsonl"

    if not results_path.exists():
        print(f"error: results.jsonl not found at {results_path}", file=sys.stderr)
        return -1

    envelopes = _read_jsonl(results_path)
    successful = [e for e in envelopes if e.get("result", {}).get("success")]
    already_reviewed_ids = {
        rec["iter_id"] for rec in _read_jsonl(review_path) if "iter_id" in rec
    }

    pending = [e for e in successful if e["iter_id"] not in already_reviewed_ids]
    total_review_targets = len(successful)

    print(
        f"batch:           {batch_dir}\n"
        f"successful rows: {total_review_targets}\n"
        f"already reviewed:{len(already_reviewed_ids & {e['iter_id'] for e in successful})}\n"
        f"pending:         {len(pending)}\n",
        file=output,
    )

    if not pending:
        print("nothing to review.", file=output)
        return 0

    written = 0
    for idx, envelope in enumerate(pending, start=1):
        position = f"{idx}/{len(pending)} pending  · {total_review_targets} total"
        print(_render_envelope(envelope, position=position), file=output)
        print("", file=output)

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
                "iter_id": envelope["iter_id"],
                "node_id_or_idx": envelope.get("result", {}).get("node", {}).get(
                    "node_id"
                ) or envelope["iter_id"],
                "schema_pass": True,
                "accepted": True,
                "reason": None,
                "reviewed_at": _now_iso(),
            }
            _append_review_record(review_path, record)
            written += 1
            print("[review] accepted.\n", file=output)
            continue

        # decision == "reject"
        try:
            reason = input_fn("  reject reason (one line): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[review] interrupted before reason captured; not saved.", file=output)
            break
        record = {
            "iter_id": envelope["iter_id"],
            "node_id_or_idx": envelope.get("result", {}).get("node", {}).get(
                "node_id"
            ) or envelope["iter_id"],
            "schema_pass": True,
            "accepted": False,
            "reason": reason or "(no reason given)",
            "reviewed_at": _now_iso(),
        }
        _append_review_record(review_path, record)
        written += 1
        print(f"[review] rejected: {reason}\n", file=output)

    print(f"[review] session done. {written} decision(s) written to {review_path}",
          file=output)
    return written


def _prompt_decision(input_fn) -> str:
    """Loop until the author types A / R / S (case-insensitive)."""
    while True:
        raw = input_fn("  [A]ccept / [R]eject / [S]kip ? ").strip().lower()
        if raw in ("a", "accept"):
            return "accept"
        if raw in ("r", "reject"):
            return "reject"
        if raw in ("s", "skip"):
            return "skip"
        print("  (please type A, R, or S)")


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m generator.review_cli",
        description="Interactively review the successful generations in a batch.",
    )
    parser.add_argument(
        "--batch-dir",
        required=True,
        type=Path,
        help="Path to /generator/experiments/<timestamp>_<batch_name>/",
    )
    args = parser.parse_args(argv)

    if not args.batch_dir.exists():
        print(f"error: batch-dir does not exist: {args.batch_dir}", file=sys.stderr)
        return 2

    rc = run_review(args.batch_dir)
    return 0 if rc >= 0 else 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
