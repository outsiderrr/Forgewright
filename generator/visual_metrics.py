"""Per-batch metrics over a visual experiment directory (T-1.5.8).

CLI:

    python -m generator.visual_metrics --batch-dir <path>

Programmatic:

    from generator.visual_metrics import compute_visual_metrics
    m = compute_visual_metrics(Path("generator/experiments/<dir>"))

Data sources (all log-driven; we never scan `_pending/` or `_rejected/`,
per GPT-5.5 L2 critique 4.7):

  * `<batch-dir>/results.jsonl`           — visual_experiment envelopes
  * `/generator/import_log.jsonl`         — image_import per-asset log
                                            (T-1.5.7), filtered by batch_name
  * `<batch-dir>/visual_review_log.jsonl` — author A/R/S decisions
                                            (visual_review_cli)
  * `/generator/image_cost_log.jsonl`     — per-call cost log (T-1.5.5),
                                            filtered by batch_name

`mechanical_check_pass_rate` is computed over imported + rejected from
import_log; manual-mode batches with no import yet show as `None`.
`acceptance_rate` is over **imported** denominators (the unit the author
actually decided on), so a half-reviewed batch reports a lower bound — by
design.

`parity_smoke_status` is a forward-compat field (default "not_ran"); the
T-1.5.9 parity smoke job will overwrite the per-batch status when it
runs.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter
from pathlib import Path
from typing import Any

from generator import image_cost_log, import_log

REJECT_TOP_N = 5


# ---------------------------------------------------------------------------
# JSONL helpers (no directory scans by design)
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


def _image_cost_log_path() -> Path:
    """Mirror `image_cost_log._log_path()` without poking the private symbol.

    We re-derive the path here so that test fixtures setting
    `FORGEWRIGHT_IMAGE_COST_LOG` still drive metrics — same env-override
    contract as the writer side.
    """
    override = os.environ.get("FORGEWRIGHT_IMAGE_COST_LOG")
    if override:
        return Path(override)
    return image_cost_log.DEFAULT_LOG_PATH


def _read_image_cost_rows(batch_name: str | None) -> list[dict]:
    path = _image_cost_log_path()
    if not path.exists():
        return []
    out: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if batch_name is not None and rec.get("batch_name") != batch_name:
                continue
            out.append(rec)
    return out


def _resolve_batch_name(results: list[dict], batch_dir: Path) -> str | None:
    """Determine the batch_name to filter logs by.

    Prefer the value embedded in result envelopes (visual_experiment writes
    it on every row). Fall back to parsing the dir name
    `<timestamp>_<batch_name>` so an old / hand-written batch dir still
    works. Returns None only if both fail (caller treats as "filter
    nothing", i.e. no rows match).
    """
    for r in results:
        name = r.get("batch_name")
        if isinstance(name, str) and name:
            return name
    parts = batch_dir.name.split("_", 1)
    if len(parts) == 2 and parts[1]:
        return parts[1]
    return None


# ---------------------------------------------------------------------------
# Public entry-point
# ---------------------------------------------------------------------------


def compute_visual_metrics(batch_dir: Path) -> dict[str, Any]:
    """Compute the per-batch metrics dict described in the module docstring.

    Always returns the same set of keys; values are `None` when the
    relevant data isn't available yet (e.g. batch has been generated but
    no `image_import` has run, so `mechanical_check_pass_rate` is None).
    """
    batch_dir = Path(batch_dir)
    results_path = batch_dir / "results.jsonl"
    review_path = batch_dir / "visual_review_log.jsonl"

    results = _read_jsonl(results_path)
    review = _read_jsonl(review_path)
    batch_name = _resolve_batch_name(results, batch_dir)

    # ---- attempt counts (from results.jsonl) ----
    total_attempted = len(results)
    total_pending_packages = sum(
        1
        for r in results
        if r.get("result", {}).get("success")
        and r.get("result", {}).get("prompt_package_path")
    )

    # ---- mechanical check (from import_log.jsonl) ----
    # review of T-1.5.8 #3.2: the documented author flow runs
    # `image_import --all-pending` without `--batch-name`, so T-1.5.7
    # writes `batch_name: null` for those rows. Filtering only by
    # `batch_name == this_batch` would then count them as 0 imports
    # → an arbitrarily 0 mechanical_check_pass_rate / acceptance_rate.
    # Fall back to correlating via the asset_id_stub set in this batch's
    # results.jsonl: an unbatched import row whose stub appears in this
    # batch's results is this batch's row. Rows tagged with a *different*
    # batch_name still don't bleed in.
    result_stubs = {
        r.get("result", {}).get("asset_id_stub")
        for r in results
        if r.get("result", {}).get("asset_id_stub")
    }
    all_import_rows = import_log.read_all() if (batch_name or result_stubs) else []
    import_rows: list[dict] = []
    for row in all_import_rows:
        row_batch = row.get("batch_name")
        if batch_name is not None and row_batch == batch_name:
            import_rows.append(row)
            continue
        if row_batch in (None, "") and row.get("asset_id_stub") in result_stubs:
            import_rows.append(row)
    imported_rows = [r for r in import_rows if r.get("status") == "imported"]
    rejected_rows = [r for r in import_rows if r.get("status") == "rejected"]
    total_imported = len(imported_rows)
    total_rejected = len(rejected_rows)

    if total_imported + total_rejected > 0:
        mech_pass = total_imported / (total_imported + total_rejected)
    else:
        mech_pass = None

    rejected_reasons = Counter()
    for r in rejected_rows:
        reason = (r.get("rejected_reason") or "").strip()
        if reason:
            rejected_reasons[reason] += 1
        for code in r.get("validation_errors") or []:
            if code:
                rejected_reasons[f"validation_error:{code}"] += 1
    rejected_reason_top_5 = rejected_reasons.most_common(REJECT_TOP_N)

    # ---- acceptance (from visual_review_log.jsonl) ----
    decisions = [r for r in review if "accepted" in r]
    accepted = [r for r in decisions if r.get("accepted") is True]
    rev_rejected = [r for r in decisions if r.get("accepted") is False]
    if total_imported > 0 and decisions:
        acceptance_rate = len(accepted) / total_imported
    else:
        acceptance_rate = None

    reject_reason_top_5 = Counter(
        (r.get("reason") or "").strip()
        for r in rev_rejected
        if (r.get("reason") or "").strip()
    ).most_common(REJECT_TOP_N)

    # ---- cost (from image_cost_log.jsonl, batch-filtered) ----
    cost_rows = _read_image_cost_rows(batch_name)
    total_cost = sum(float(r.get("cost_usd", 0.0)) for r in cost_rows)

    return {
        "batch_name": batch_name,
        "total_assets_attempted": total_attempted,
        "total_pending_packages_generated": total_pending_packages,
        "total_imported": total_imported,
        "total_rejected": total_rejected,
        "mechanical_check_pass_rate": mech_pass,
        "rejected_reason_top_5": rejected_reason_top_5,
        "acceptance_rate": acceptance_rate,
        "reviewed_count": len(decisions),
        "reject_reason_top_5": reject_reason_top_5,
        "total_cost_usd": total_cost,
        # Forward-compat slot for T-1.5.9 visual_parity_smoke; T-1.5.8
        # leaves it "not_ran" so the T-1.5.10 acceptance report has a
        # uniform field shape to read whether parity ran or not.
        "parity_smoke_status": "not_ran",
    }


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _format_metrics(m: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"batch_name:                       {m['batch_name']}")
    lines.append(f"total_assets_attempted:           {m['total_assets_attempted']}")
    lines.append(
        f"total_pending_packages_generated: {m['total_pending_packages_generated']}"
    )
    lines.append(f"total_imported:                   {m['total_imported']}")
    lines.append(f"total_rejected:                   {m['total_rejected']}")
    rate = m["mechanical_check_pass_rate"]
    lines.append(
        "mechanical_check_pass_rate:       "
        + ("n/a" if rate is None else f"{rate:.1%}")
    )
    lines.append(f"reviewed_count:                   {m['reviewed_count']}")
    rate = m["acceptance_rate"]
    lines.append(
        "acceptance_rate:                  "
        + ("n/a" if rate is None else f"{rate:.1%}")
    )
    lines.append(f"total_cost_usd:                   ${m['total_cost_usd']:.4f}")
    lines.append(f"parity_smoke_status:              {m['parity_smoke_status']}")

    lines.append("")
    lines.append("rejected_reason_top_5 (mechanical):")
    if m["rejected_reason_top_5"]:
        for reason, count in m["rejected_reason_top_5"]:
            lines.append(f"  ({count})  {reason}")
    else:
        lines.append("  (none)")

    lines.append("")
    lines.append("reject_reason_top_5 (author):")
    if m["reject_reason_top_5"]:
        for reason, count in m["reject_reason_top_5"]:
            lines.append(f"  ({count})  {reason}")
    else:
        lines.append("  (none)")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m generator.visual_metrics",
        description=(
            "Compute mechanical-check + author-acceptance metrics for a "
            "visual experiment batch from the structured log files."
        ),
    )
    parser.add_argument(
        "--batch-dir",
        required=True,
        type=Path,
        help="Path to /generator/experiments/<timestamp>_<batch_name>/",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit machine-readable JSON instead of the human report.",
    )
    args = parser.parse_args(argv)

    if not args.batch_dir.exists():
        print(f"error: batch-dir does not exist: {args.batch_dir}", file=sys.stderr)
        return 2

    metrics = compute_visual_metrics(args.batch_dir)
    if args.json:
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    else:
        print(_format_metrics(metrics))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
