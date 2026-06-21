"""文风评审 CLI —— 对组装后的 scene.json 跑 LLM-as-judge 同维打分.

用法（需 .env 配 LLM_API_KEY / LLM_BASE_URL / LLM_MODEL）：

  PYTHONPATH=. python generator/scripts/run_style_judge.py \
      --scene generator/experiments/.../scene.json [--out <dir>]

产物：judge_report.json（机读）+ judge_report.md（人读）落在 --out（默认 = scene.json 同目录）。
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from generator.judge import judge_scene, write_judge_artifacts
from generator.scripts.run_multipass_scene import _make_provider


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="文风评审（LLM-as-judge）")
    parser.add_argument("--scene", type=Path, required=True, help="组装后的 scene.json")
    parser.add_argument("--out", type=Path, default=None, help="产物目录（默认 scene.json 同目录）")
    args = parser.parse_args(argv)

    graph = json.loads(args.scene.read_text(encoding="utf-8"))
    provider = _make_provider()
    if provider is None:
        return 2

    report = judge_scene(provider, graph)
    paths = write_judge_artifacts(report, args.out or args.scene.parent)
    print(f"status={report.status} · 调用 {len(report.call_metas)} 次 · ${report.total_cost_usd:.4f}")
    if report.status == "success":
        gate = {True: "✅", False: "❌", None: "—"}[report.gate_pass]
        print(f"gate {gate} · 均分 {report.dim_means} · AP 违规 {len(report.ap_violations)} 条")
    print(f"report: {paths['md']}")
    return 0 if report.status == "success" else 1


if __name__ == "__main__":
    sys.exit(main())
