"""文风评审执行器 —— 按 chunk 调 LLM 打分、聚合、落产物.

工程约束：
  - 走 generator/multipass/calls.structured_call（budget 拦截 ADR-011/012 + 尺寸护栏沿用）；
  - 每 chunk 3-5 节点一次小调用（est_output ≤ 1200，远低于 2000 护栏）；
  - 失败语义对齐引擎：BudgetExceeded / ProviderError 不上抛，落 failure_reason。
产物：judge_report.json（机读）+ judge_report.md（人读，对齐 REVIEW_REPORT 习惯）。
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from generator.budget import BudgetExceeded
from generator.llm_provider import ProviderError
from generator.multipass.calls import structured_call
from generator.judge.taxonomy import (
    GATE_DIM_IDS,
    GATE_THRESHOLD,
    SCORED_DIM_IDS,
    TAXONOMY,
)
from generator.prompts.judge import (
    STYLE_JUDGE_SYSTEM,
    build_judge_schema,
    build_judge_user_prompt,
)

CHUNK_SIZE = 4
_EST_OUTPUT = 1200


@dataclass
class StyleJudgeReport:
    """一次场景评审的全部产物（成功或失败都返回，不上抛）。"""

    status: str  # "success" | "budget_exceeded" | "provider_error"
    scene_id: str
    dim_means: dict[str, float]  # 维度 → 均分（只算 score>0 的适用块）
    dim_mins: dict[str, int]
    gate_pass: bool | None  # None = 失败/无数据
    ap_violations: list[dict[str, Any]]
    notes: list[dict[str, Any]]
    chunk_results: list[dict[str, Any]]
    call_metas: list[dict[str, Any]]
    total_cost_usd: float = 0.0
    failure_reason: str | None = None
    warnings: list[str] = field(default_factory=list)


def _chunks(items: list[Any], size: int) -> list[list[Any]]:
    return [items[i : i + size] for i in range(0, len(items), size)] or [[]]


def judge_scene(
    provider: Any,
    graph: dict[str, Any],
    *,
    scene_id: str | None = None,
    chunk_size: int = CHUNK_SIZE,
) -> StyleJudgeReport:
    """对一个组装后的 dialogue_graph 做同维文风评审。"""
    sid = scene_id or graph.get("graph_id", "scene")
    node_items: list[tuple[str, dict[str, Any]]] = list(graph.get("nodes", {}).items())
    chunks = _chunks(node_items, chunk_size)
    metas: list[dict[str, Any]] = []
    chunk_results: list[dict[str, Any]] = []
    warnings: list[str] = []

    def _fail(status: str, reason: str) -> StyleJudgeReport:
        return StyleJudgeReport(
            status=status,
            scene_id=sid,
            dim_means={},
            dim_mins={},
            gate_pass=None,
            ap_violations=[],
            notes=[],
            chunk_results=chunk_results,
            call_metas=metas,
            total_cost_usd=sum(m.get("actual_cost_usd", 0.0) for m in metas),
            failure_reason=reason,
            warnings=warnings,
        )

    try:
        for ci, chunk in enumerate(chunks, start=1):
            if not chunk:
                continue
            content, meta = structured_call(
                provider,
                system_prompt=STYLE_JUDGE_SYSTEM,
                user_prompt=build_judge_user_prompt(
                    chunk_nodes=chunk,
                    scene_id=sid,
                    chunk_index=ci,
                    chunk_total=len(chunks),
                ),
                json_schema=build_judge_schema(),
                est_output_tokens=_EST_OUTPUT,
                label=f"style_judge_{sid}_chunk{ci}",
            )
            metas.append(meta)
            content["chunk_index"] = ci
            content["node_ids"] = [nid for nid, _ in chunk]
            chunk_results.append(content)
    except BudgetExceeded as e:
        return _fail("budget_exceeded", str(e))
    except ProviderError as e:
        return _fail("provider_error", f"{type(e).__name__}: {e}")

    # 聚合：score=0 表示该块不适用（如无 end 节点的 S7），不计入均分
    per_dim: dict[str, list[int]] = {d: [] for d in SCORED_DIM_IDS}
    violations: list[dict[str, Any]] = []
    notes: list[dict[str, Any]] = []
    for cr in chunk_results:
        for ds in cr.get("dim_scores") or []:
            dim, score = ds.get("dim"), ds.get("score")
            if dim in per_dim and isinstance(score, int) and 1 <= score <= 5:
                per_dim[dim].append(score)
        for v in cr.get("ap_violations") or []:
            violations.append(v)
        for n in cr.get("notes") or []:
            notes.append({**n, "chunk_index": cr["chunk_index"]})

    dim_means = {d: round(sum(v) / len(v), 2) for d, v in per_dim.items() if v}
    dim_mins = {d: min(v) for d, v in per_dim.items() if v}
    missing_gate_dims = [d for d in GATE_DIM_IDS if d not in dim_means]
    if missing_gate_dims:
        warnings.append(f"gate 维度无适用打分数据：{missing_gate_dims}")
    gate_pass = (
        all(dim_means[d] >= GATE_THRESHOLD for d in GATE_DIM_IDS if d in dim_means)
        if dim_means
        else None
    )

    return StyleJudgeReport(
        status="success",
        scene_id=sid,
        dim_means=dim_means,
        dim_mins=dim_mins,
        gate_pass=gate_pass,
        ap_violations=violations,
        notes=notes,
        chunk_results=chunk_results,
        call_metas=metas,
        total_cost_usd=sum(m.get("actual_cost_usd", 0.0) for m in metas),
        warnings=warnings,
    )


def render_judge_md(report: StyleJudgeReport) -> str:
    """人读形态（对齐 REVIEW_REPORT 习惯：总表 + 逐项引句）。"""
    by_id = {d.id: d for d in TAXONOMY}
    lines = [
        f"# 文风评审报告 · {report.scene_id}",
        "",
        f"> 状态：{report.status}"
        + (f"（{report.failure_reason}）" if report.failure_reason else "")
        + f" · 调用 {len(report.call_metas)} 次 · 成本 ${report.total_cost_usd:.4f}",
        "",
    ]
    if report.dim_means:
        gate_txt = {True: "✅ 通过", False: "❌ 未过", None: "—"}[report.gate_pass]
        lines += [
            f"**gate（{'/'.join(GATE_DIM_IDS)} 均分 ≥ {GATE_THRESHOLD:g}）：{gate_txt}**",
            "",
            "| 维度 | 均分 | 最低 | gate |",
            "|---|---|---|---|",
        ]
        for d in SCORED_DIM_IDS:
            if d not in report.dim_means:
                continue
            mark = "◆" if d in GATE_DIM_IDS else ""
            lines.append(
                f"| {d} {by_id[d].name} | {report.dim_means[d]} | {report.dim_mins[d]} | {mark} |"
            )
        lines.append("")
    if report.ap_violations:
        lines += ["## AP 违规检出", ""]
        for v in report.ap_violations:
            lines.append(
                f"- **{v.get('ap_id')}** @ `{v.get('node_id')}`：「{v.get('quote')}」——{v.get('reason')}"
            )
        lines.append("")
    else:
        lines += ["## AP 违规检出", "", "（无）", ""]
    if report.notes:
        lines += ["## 描述性观察（S13 温度 / S14 人称约定）", ""]
        for n in report.notes:
            lines.append(f"- [{n.get('dim')}] {n.get('note')}")
        lines.append("")
    for w in report.warnings:
        lines.append(f"> ⚠️ {w}")
    return "\n".join(lines) + "\n"


def write_judge_artifacts(report: StyleJudgeReport, out_dir: Path) -> dict[str, Path]:
    """落盘 judge_report.json + judge_report.md。"""
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = {
        "json": out_dir / "judge_report.json",
        "md": out_dir / "judge_report.md",
    }
    payload = {
        "status": report.status,
        "scene_id": report.scene_id,
        "dim_means": report.dim_means,
        "dim_mins": report.dim_mins,
        "gate_dims": list(GATE_DIM_IDS),
        "gate_threshold": GATE_THRESHOLD,
        "gate_pass": report.gate_pass,
        "ap_violations": report.ap_violations,
        "notes": report.notes,
        "chunk_results": report.chunk_results,
        "call_metas": report.call_metas,
        "total_cost_usd": report.total_cost_usd,
        "failure_reason": report.failure_reason,
        "warnings": report.warnings,
    }
    paths["json"].write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    paths["md"].write_text(render_judge_md(report), encoding="utf-8")
    return paths


__all__ = [
    "StyleJudgeReport",
    "judge_scene",
    "render_judge_md",
    "write_judge_artifacts",
    "CHUNK_SIZE",
]
