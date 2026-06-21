"""Phase 2 文风层 A/B 评估 —— 带锚点 vs 不带锚点对照（结构层版本固定）.

设计：generator/experiments/aesthetic_layer/DESIGN_2026-06-12_phase2_style_layer.md §5
  - 同一 spec 跑两臂：anchored（FORGEWRIGHT_STYLE_ANCHORS=on）/ plain（=off）；
    两臂规则段一致，只差锚点注入——避免混合归因（Phase 1 教训）。
  - 每臂生成后立即 judge 同维打分；最后产 AB_REPORT.md（judge 分数对照 +
    成本/输入 token 增量实测 + 作者审阅入口清单）。

用法（需 .env；预算量级 ~$3-4.5，handoff §4 预批 $4-6）：

  PYTHONPATH=. python generator/scripts/run_style_ab.py \
      --specs generator/experiments/multipass_structure/specs/lucy.json \
              generator/experiments/multipass_structure/specs/whitcroft.json \
              generator/experiments/multipass_structure/specs/vick.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from datetime import date
from pathlib import Path
from typing import Any

from generator.judge import judge_scene, write_judge_artifacts
from generator.judge.taxonomy import GATE_DIM_IDS, SCORED_DIM_IDS, TAXONOMY
from generator.multipass import SceneRunConfig, run_multipass_scene
from generator.multipass.engine import write_artifacts
from generator.prompts.style import ANCHORS_ENV_VAR
from generator.scripts.run_multipass_scene import _make_provider

GENERATOR_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_OUT = GENERATOR_ROOT / "experiments" / "aesthetic_layer"

ARMS = (("anchored", "on"), ("plain", "off"))


def _avg_input_tokens(call_metas: list[dict[str, Any]]) -> float:
    if not call_metas:
        return 0.0
    return sum(m.get("input_tokens", 0) for m in call_metas) / len(call_metas)


def _run_one(provider, payload: dict, arm_env: str) -> tuple[Any, Any]:
    os.environ[ANCHORS_ENV_VAR] = arm_env
    config = SceneRunConfig(
        graph_id=payload["config"]["graph_id"],
        scene_anchor=payload["config"]["scene_anchor"],
        speaker_ref=payload["config"]["speaker_ref"],
        character_refs=payload["config"]["character_refs"],
        npc_name=payload["config"].get("npc_name", "NPC"),
    )
    result = run_multipass_scene(provider, payload["spec"], config)
    judge = judge_scene(provider, result.graph) if result.graph is not None else None
    return result, judge


def _report_md(rows: list[dict[str, Any]]) -> str:
    by_id = {d.id: d for d in TAXONOMY}
    lines = [
        "# Phase 2 文风层 A/B 评估报告（带锚点 vs 不带锚点）",
        "",
        f"> 日期：{date.today().isoformat()} · 结构层固定（main 8eb04d8 行为）· "
        "两臂仅差锚点注入（规则段一致）",
        "",
        "## 总表",
        "",
        "| spec | 臂 | 节点 | 生成成本 | judge 成本 | 硬校验 | AP flag | judge gate | 均输入 tok/调用 |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in rows:
        gate = {True: "✅", False: "❌", None: "—"}.get(r["judge_gate"])
        lines.append(
            f"| {r['spec']} | {r['arm']} | {r['nodes']} | ${r['gen_cost']:.4f} | "
            f"${r['judge_cost']:.4f} | {'✅' if r['hard_pass'] else '❌'} | {r['ap_flags']} | "
            f"{gate} | {r['avg_input_tokens']:.0f} |"
        )
    lines += ["", "## judge 同维分数对照（均分；◆ = gate 维度）", ""]
    header = "| 维度 | " + " | ".join(f"{r['spec']}/{r['arm']}" for r in rows) + " |"
    lines += [header, "|" + "---|" * (len(rows) + 1)]
    for dim in SCORED_DIM_IDS:
        mark = "◆" if dim in GATE_DIM_IDS else ""
        cells = " | ".join(str(r["dim_means"].get(dim, "—")) for r in rows)
        lines.append(f"| {dim} {by_id[dim].name}{mark} | {cells} |")
    lines += [
        "",
        "## 锚点输入 token 增量（实测）",
        "",
    ]
    by_spec: dict[str, dict[str, dict]] = {}
    for r in rows:
        by_spec.setdefault(r["spec"], {})[r["arm"]] = r
    for spec, arms in by_spec.items():
        if "anchored" in arms and "plain" in arms:
            delta_tok = arms["anchored"]["avg_input_tokens"] - arms["plain"]["avg_input_tokens"]
            delta_cost = arms["anchored"]["gen_cost"] - arms["plain"]["gen_cost"]
            lines.append(
                f"- {spec}：每调用均输入 +{delta_tok:.0f} token；单场景生成成本差 "
                f"{'+' if delta_cost >= 0 else ''}{delta_cost:.4f} USD"
            )
    lines += [
        "",
        "## 作者审阅入口（剧本式 markdown）",
        "",
    ]
    for r in rows:
        lines.append(f"- {r['spec']}/{r['arm']}：`{r['scene_md']}`")
    lines += ["", "（作者审后回填：少改即可用判定 + 保底专名相似对裁量。）", ""]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="文风层 A/B 评估（带/不带锚点）")
    parser.add_argument("--specs", type=Path, nargs="+", required=True)
    parser.add_argument("--out-root", type=Path, default=None)
    args = parser.parse_args(argv)

    provider = _make_provider()
    if provider is None:
        return 2
    out_root = args.out_root or (DEFAULT_OUT / f"{date.today().isoformat()}_ab")

    rows: list[dict[str, Any]] = []
    exit_code = 0
    for spec_path in args.specs:
        payload = json.loads(spec_path.read_text(encoding="utf-8"))
        spec_name = spec_path.stem
        for arm, env_val in ARMS:
            t0 = time.time()
            result, judge = _run_one(provider, payload, env_val)
            out_dir = out_root / spec_name / arm
            paths = write_artifacts(result, out_dir)
            jm: dict[str, Any] = {}
            j_cost = 0.0
            j_gate = None
            if judge is not None:
                write_judge_artifacts(judge, out_dir)
                jm, j_cost, j_gate = judge.dim_means, judge.total_cost_usd, judge.gate_pass
            m = result.metrics
            rows.append(
                {
                    "spec": spec_name,
                    "arm": arm,
                    "nodes": m.get("node_count", 0),
                    "gen_cost": m.get("total_cost_usd", 0.0),
                    "judge_cost": j_cost,
                    "hard_pass": m.get("hard_pass", False),
                    "ap_flags": m.get("ap_flag_count", 0),
                    "judge_gate": j_gate,
                    "dim_means": jm,
                    "avg_input_tokens": _avg_input_tokens(result.call_metas),
                    "scene_md": str(paths.get("scene_md", "")),
                }
            )
            ok = result.status == "success" and (judge is None or judge.status == "success")
            if not ok:
                exit_code = 1
            print(
                f"[{spec_name}/{arm}] {result.status} · {m.get('node_count', 0)} 节点 · "
                f"gen ${m.get('total_cost_usd', 0.0):.4f} + judge ${j_cost:.4f} · "
                f"{time.time() - t0:.0f}s"
                + (f" · ⚠️ {result.failure_reason}" if result.failure_reason else "")
            )

    out_root.mkdir(parents=True, exist_ok=True)
    report_path = out_root / "AB_REPORT.md"
    report_path.write_text(_report_md(rows), encoding="utf-8")
    (out_root / "ab_rows.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    total = sum(r["gen_cost"] + r["judge_cost"] for r in rows)
    print(f"\n总成本 ${total:.4f} · 报告: {report_path}")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
