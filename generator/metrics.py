"""Metrics over a batch directory produced by `generator.experiment` (T-1.7).

CLI:

    python -m generator.metrics --batch-dir <path>

Programmatic:

    from generator.metrics import compute_metrics
    m = compute_metrics(Path("generator/experiments/<dir>"))

`compute_metrics` is intentionally pure: it reads `results.jsonl` and the
optional `review_log.jsonl` and returns a plain dict. No mutation, no
side effects on stdout. The CLI just pretty-prints what it returns.

Counts use:
  * one row of results.jsonl  = one *iteration*  (one generate_node call)
  * one row of results.jsonl  may contain N "attempts" inside its
    `result.attempts` array (each = one LLM call after retries)
We surface both for clarity (`total_iterations`, `total_llm_calls`).
`schema_pass_rate` and `mean_cost_per_attempt` are reported per *iteration*
because that's the unit the author actually decides on (one node = pass/fail).
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

REJECT_TOP_N = 5


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def compute_metrics(batch_dir: Path) -> dict[str, Any]:
    """Compute schema/cost metrics, augmented with review metrics if present.

    Always returns:
      - total_iterations:         int
      - total_attempts:           int  (alias of total_iterations — spec name)
      - total_llm_calls:          int
      - schema_pass_rate:         float in [0, 1] (None if total_iterations == 0)
      - mean_cost_per_attempt:    float USD       (None if total_iterations == 0)
      - total_cost_usd:           float USD
      - failure_reason_distribution: dict[str, int]

    If review_log.jsonl is present, also includes:
      - reviewed_count:           int
      - acceptance_rate:          float in [0, 1] over decisions actually made
      - reject_reason_top_5:      list[[reason, count]] (truncated to top 5)
    """
    batch_dir = Path(batch_dir)
    results_path = batch_dir / "results.jsonl"
    review_path = batch_dir / "review_log.jsonl"

    results = _read_jsonl(results_path)
    review = _read_jsonl(review_path)

    total_iterations = len(results)
    total_llm_calls = sum(
        len(r.get("result", {}).get("attempts", []) or []) for r in results
    )
    pass_count = sum(1 for r in results if r.get("result", {}).get("success"))
    total_cost = sum(
        float(r.get("result", {}).get("total_cost_usd", 0.0)) for r in results
    )

    if total_iterations == 0:
        schema_pass_rate: float | None = None
        mean_cost: float | None = None
    else:
        schema_pass_rate = pass_count / total_iterations
        mean_cost = total_cost / total_iterations

    failure_reasons = Counter(
        r["result"]["failure_reason"]
        for r in results
        if not r.get("result", {}).get("success")
        and r.get("result", {}).get("failure_reason")
    )

    metrics: dict[str, Any] = {
        "total_iterations": total_iterations,
        "total_attempts": total_iterations,
        "total_llm_calls": total_llm_calls,
        "schema_pass_rate": schema_pass_rate,
        "mean_cost_per_attempt": mean_cost,
        "total_cost_usd": total_cost,
        "failure_reason_distribution": dict(failure_reasons),
    }

    if review:
        # Some entries may be 'skip' (no decision); only A/R count toward
        # acceptance_rate. We surface reviewed_count for transparency.
        decisions = [r for r in review if "accepted" in r]
        accepted = [r for r in decisions if r.get("accepted")]
        rejected = [r for r in decisions if r.get("accepted") is False]
        if decisions:
            metrics["acceptance_rate"] = len(accepted) / len(decisions)
        else:
            metrics["acceptance_rate"] = None
        metrics["reviewed_count"] = len(decisions)
        reasons = Counter(
            (r.get("reason") or "").strip()
            for r in rejected
            if (r.get("reason") or "").strip()
        )
        metrics["reject_reason_top_5"] = reasons.most_common(REJECT_TOP_N)

    return metrics


def _format_metrics(metrics: dict[str, Any]) -> str:
    lines: list[str] = []

    lines.append(f"total_iterations:        {metrics['total_iterations']}")
    lines.append(f"total_attempts:          {metrics['total_attempts']}")
    lines.append(f"total_llm_calls:         {metrics['total_llm_calls']}")
    lines.append(f"total_cost_usd:          ${metrics['total_cost_usd']:.4f}")

    rate = metrics["schema_pass_rate"]
    lines.append(
        f"schema_pass_rate:        {'n/a' if rate is None else f'{rate:.1%}'}"
    )
    mean = metrics["mean_cost_per_attempt"]
    lines.append(
        f"mean_cost_per_attempt:   {'n/a' if mean is None else f'${mean:.4f}'}"
    )

    lines.append("")
    lines.append("failure_reason_distribution:")
    dist = metrics["failure_reason_distribution"]
    if dist:
        for reason, count in sorted(dist.items(), key=lambda kv: -kv[1]):
            lines.append(f"  {reason:<20} {count}")
    else:
        lines.append("  (none)")

    if "acceptance_rate" in metrics:
        lines.append("")
        lines.append(f"reviewed_count:          {metrics['reviewed_count']}")
        rate = metrics["acceptance_rate"]
        lines.append(
            f"acceptance_rate:         "
            f"{'n/a (no decisions)' if rate is None else f'{rate:.1%}'}"
        )
        lines.append("")
        lines.append("reject_reason_top_5:")
        top = metrics.get("reject_reason_top_5", [])
        if top:
            for reason, count in top:
                lines.append(f"  ({count})  {reason}")
        else:
            lines.append("  (none)")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m generator.metrics",
        description="Compute schema/cost/review metrics over a batch dir.",
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

    metrics = compute_metrics(args.batch_dir)
    if args.json:
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    else:
        print(_format_metrics(metrics))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
