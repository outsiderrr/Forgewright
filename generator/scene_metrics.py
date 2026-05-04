"""Per-batch metrics over a scene experiment directory (T-2.8 / ADR-020).

CLI:

    python -m generator.scene_metrics --batch-dir <path>

Programmatic:

    from generator.scene_metrics import compute_scene_metrics
    m = compute_scene_metrics(Path("generator/experiments/<dir>"))

Returns the ADR-020 baseline-protocol numbers in a flat dict so the
CLI / a future report renderer can both consume the same shape:

  * total_attempts                 — N (count of scene_results.jsonl rows)
  * schema_pass_rate               — success=True / total
  * mechanical_pass_rate           — mechanical.pass / total (= ADR-020
                                     "gross_pass_rate"; we expose both
                                     names for backward compatibility
                                     with scene_experiment summary text)
  * gross_pass_rate                — alias of mechanical_pass_rate
  * topology_pass_rate             — topology.pass / total
  * sampling_reach_rate            — average of per-scene sampling
                                     reach_rate over success scenes
                                     (success scenes only — reach rate
                                      is undefined on failure rows)
  * mean_cost_per_attempt          — total_cost_usd / total
  * total_cost_usd                 — sum of result.total_cost_usd
  * failure_reason_distribution    — Counter on failure rows
  * acceptance_rate / reject_reason_top_5 / reviewed_count — only when
                                     scene_review_log.jsonl exists
                                     (ADR-020 §6: numerator = author
                                      [A]ccept; denominator = scenes
                                      that survived mechanical pre-check
                                      AND were reviewed)

Design intent: pure (no stdout, no mutation) so tests can assert the
return dict directly. The CLI's `_format_metrics` is the only place that
formats lines.
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


def compute_scene_metrics(batch_dir: Path) -> dict[str, Any]:
    batch_dir = Path(batch_dir)
    results_path = batch_dir / "scene_results.jsonl"
    review_path = batch_dir / "scene_review_log.jsonl"

    results = _read_jsonl(results_path)
    review = _read_jsonl(review_path)

    total = len(results)
    schema_pass = sum(1 for r in results if r.get("result", {}).get("success"))
    mech_pass = sum(
        1
        for r in results
        if (r.get("validator_summaries") or {})
        .get("mechanical", {})
        .get("pass")
    )
    topo_pass = sum(
        1
        for r in results
        if (r.get("validator_summaries") or {})
        .get("topology", {})
        .get("pass")
    )

    reach_rates = [
        (r.get("validator_summaries") or {}).get("sampling", {}).get("reach_rate")
        for r in results
        if r.get("result", {}).get("success")
    ]
    reach_rates = [x for x in reach_rates if isinstance(x, (int, float))]

    total_cost = sum(
        float(r.get("result", {}).get("total_cost_usd", 0.0)) for r in results
    )

    if total == 0:
        schema_rate: float | None = None
        mean_cost: float | None = None
        mech_rate: float | None = None
        topo_rate: float | None = None
    else:
        schema_rate = schema_pass / total
        mean_cost = total_cost / total
        mech_rate = mech_pass / total
        topo_rate = topo_pass / total

    sampling_reach_rate = (
        sum(reach_rates) / len(reach_rates) if reach_rates else None
    )

    failure_reasons = Counter(
        r["result"]["failure_reason"]
        for r in results
        if not r.get("result", {}).get("success")
        and r.get("result", {}).get("failure_reason")
    )

    metrics: dict[str, Any] = {
        "total_attempts": total,
        "schema_pass_rate": schema_rate,
        "mechanical_pass_rate": mech_rate,
        "gross_pass_rate": mech_rate,  # ADR-020 §3 alias
        "topology_pass_rate": topo_rate,
        "sampling_reach_rate": sampling_reach_rate,
        "mean_cost_per_attempt": mean_cost,
        "total_cost_usd": total_cost,
        "failure_reason_distribution": dict(failure_reasons),
    }

    if review:
        # ADR-020 §6: denominator = scenes that survived mechanical
        # pre-check AND were reviewed (decision in {accept, reject}).
        # Numerator = author [A]ccept. Skipped rows don't count.
        decisions = [r for r in review if "accepted" in r]
        accepted = [r for r in decisions if r.get("accepted")]
        rejected = [r for r in decisions if r.get("accepted") is False]
        metrics["reviewed_count"] = len(decisions)
        metrics["acceptance_rate"] = (
            len(accepted) / len(decisions) if decisions else None
        )
        reasons = Counter(
            (r.get("reason") or "").strip()
            for r in rejected
            if (r.get("reason") or "").strip()
        )
        metrics["reject_reason_top_5"] = reasons.most_common(REJECT_TOP_N)

    return metrics


# ---------------------------------------------------------------------------
# CLI rendering
# ---------------------------------------------------------------------------


def _fmt_rate(value: float | None) -> str:
    return "n/a" if value is None else f"{value:.1%}"


def _fmt_cost(value: float | None) -> str:
    return "n/a" if value is None else f"${value:.4f}"


def _format_metrics(m: dict[str, Any]) -> str:
    lines: list[str] = []
    lines.append(f"total_attempts:          {m['total_attempts']}")
    lines.append(f"schema_pass_rate:        {_fmt_rate(m['schema_pass_rate'])}")
    lines.append(f"gross_pass_rate:         {_fmt_rate(m['gross_pass_rate'])}")
    lines.append(f"mechanical_pass_rate:    {_fmt_rate(m['mechanical_pass_rate'])}")
    lines.append(f"topology_pass_rate:      {_fmt_rate(m['topology_pass_rate'])}")
    lines.append(f"sampling_reach_rate:     {_fmt_rate(m['sampling_reach_rate'])}")
    lines.append(f"mean_cost_per_attempt:   {_fmt_cost(m['mean_cost_per_attempt'])}")
    lines.append(f"total_cost_usd:          ${m['total_cost_usd']:.4f}")
    lines.append("")
    lines.append("failure_reason_distribution:")
    dist = m["failure_reason_distribution"]
    if dist:
        for reason, count in sorted(dist.items(), key=lambda kv: -kv[1]):
            lines.append(f"  {str(reason):<22} {count}")
    else:
        lines.append("  (none)")
    if "acceptance_rate" in m:
        lines.append("")
        lines.append(f"reviewed_count:          {m['reviewed_count']}")
        lines.append(f"acceptance_rate:         {_fmt_rate(m['acceptance_rate'])}")
        lines.append("")
        lines.append("reject_reason_top_5:")
        top = m.get("reject_reason_top_5") or []
        if top:
            for reason, count in top:
                lines.append(f"  ({count})  {reason}")
        else:
            lines.append("  (none)")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m generator.scene_metrics",
        description=(
            "Compute scene-level batch metrics (ADR-020 baseline protocol)."
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

    metrics = compute_scene_metrics(args.batch_dir)
    if args.json:
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
    else:
        print(_format_metrics(metrics))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
