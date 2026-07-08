"""P-B 回流验收管线（T-3P-3；ADR-039 首版核心闭环）.

P-B 合并器（ingest.py）产出的 scene.json 在**落地前**必须过本模块的验收闸——
它是「结构→提示词包→回流→验收落地播放」核心闭环里"验收"那一环，复用现成的
三层校验器（`validator.validate`）+ 机械预检（`validate_graph_mechanical`，
`generation_source="human"`）+ 逐节点反模式记录（`detect_anti_patterns`），
不新写任何校验语义（/validator 只读调用）。

如实边界（务必与 E2E 报告口径一致，不许夸大）：
  路线 A 下编剧只能填正文（narration / dialogue 行 / options 文本），**触不到**
  结构字段（speaker_ref 由 run_config 锁定、condition/effects 由代码填、monotonic
  对 human 豁免）——所以三层 + 机械预检对"纯正文错误"基本恒 pass。**验收闸守的是
  结构完整性 + 本体一致性**（防管线 bug / 防绕过 P-B 手改 scene.json / 防配置错误），
  对编剧手笔的把关主要落在 ingest 的格式层 E1-E8 + 本模块的 AP 记录。

pass/fail 判定（哪些算硬拦、哪些只记录）：
  - **硬拦（fail）**：schema 层 / graph 层 / 一致性层的**闭合违规**（speaker_ref /
    dialogue[].speaker_ref 未在 character_refs 声明、option_id 重复）/ 机械预检 error。
    这些都是编剧触不到、只可能因管线 bug 或手改 scene.json 冒出来的**结构错误**。
  - **只记录不拦（warning / note）**：
    * AP flag —— 反模式是给编剧/制作人的 QA 信息，不是验收闸（沿 multipass engine.py
      同款处理：flag 记录进报告，不影响 pass/fail）。
    * 一致性层的**本体解析**（`... does not resolve in ontology`）—— 这类 issue 取决于
      **当前加载了哪份本体**（state.ontology 扫 /state/ontology/*.json）。露西等实验
      fixture 引用的 char_lucy / scene_hibo_roadhouse 不在已发布的驿站本体内，是**环境/
      fixture 依赖**的已知假阳性（与 test_reassemble_lucy_adr040.py:118 同口径，作者已在
      T-3P-2 演示物 README 复核）。据此把本体解析 issue 单列为「本体解析待挂」记录，
      不当作管线产坏图的硬 fail——真正的本体守门在正式内容入库时对着已发布本体跑，
      隔离目录 E2E 场景刻意用未发布本体，故此处降级为 note 并在报告写明。

0 LLM。本模块只做只读校验调用 + 报告渲染；落地写盘 / version sidecar = ingest CLI 的
`--land`（ingest.py 消费本模块）。
"""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from validator import Issue, validate, validate_graph_mechanical
from validator.anti_pattern_detector import AntiPatternFlag, detect_anti_patterns

# 一致性层里"本体解析"类 issue 的判据串——consistency_check.py 对所有 ontology
# 解析失败统一用这句尾缀（scene_anchor / character_refs / location_ref /
# StateEffect.ontology_ref / StateCondition.ontology_ref 五处）。闭合违规
# （speaker_ref / dialogue[].speaker_ref / duplicate option_id）不含此串。
_ONTOLOGY_RESOLUTION_MARKER = "does not resolve in ontology"


@dataclass
class MechanicalIssueRow:
    """机械预检一条 error 的报告行（node_id 定位 + code + field_path + message）。"""

    node_id: str
    code: str
    field_path: str
    message: str


@dataclass
class ApFlagRow:
    """一条 AP flag 的报告行（node_id 定位 + AP 检测结果四元组）。"""

    node_id: str
    ap_id: str
    location: str
    excerpt: str
    reason: str


@dataclass
class AcceptanceReport:
    """回流验收结果：pass/fail + 分层 issue 清单 + AP flag 清单 + 本体解析待挂。

    passed 只由**硬拦层**决定（schema / graph / 闭合 / 机械 error）；
    ap_flags 与 ontology_resolution 仅记录，不影响 passed。
    """

    graph_id: str
    passed: bool
    schema_errors: list[Issue] = field(default_factory=list)
    graph_errors: list[Issue] = field(default_factory=list)
    # 一致性层拆两半：闭合违规（硬拦）vs 本体解析（记录）
    consistency_closure_errors: list[Issue] = field(default_factory=list)
    consistency_ontology_notes: list[Issue] = field(default_factory=list)
    mechanical_errors: list[MechanicalIssueRow] = field(default_factory=list)
    ap_flags: list[ApFlagRow] = field(default_factory=list)
    node_count: int = 0

    @property
    def blocking_error_count(self) -> int:
        return (
            len(self.schema_errors)
            + len(self.graph_errors)
            + len(self.consistency_closure_errors)
            + len(self.mechanical_errors)
        )

    def one_line_guidance(self) -> str:
        """给编剧 / 作者看得懂的一句话指引（pass 与各类 fail 分别给）。"""
        if self.passed:
            note = ""
            if self.consistency_ontology_notes:
                note = (
                    f"（另有 {len(self.consistency_ontology_notes)} 条本体解析待挂——"
                    "引用了当前未加载的本体条目，属 fixture/环境依赖，不拦落地）"
                )
            if self.ap_flags:
                note += f"（另记录 {len(self.ap_flags)} 条反模式 flag，供编剧复核，不拦落地）"
            return f"验收通过：结构完整、闭合无违规、机械预检干净。{note}"
        parts: list[str] = []
        if self.schema_errors:
            parts.append(f"schema 层 {len(self.schema_errors)} 错（scene.json 结构不合 Schema）")
        if self.graph_errors:
            parts.append(f"graph 层 {len(self.graph_errors)} 错（图论：悬空 / 不可达 / 结局缺失等）")
        if self.consistency_closure_errors:
            parts.append(
                f"一致性闭合 {len(self.consistency_closure_errors)} 错"
                "（说话人未在花名册声明 / option_id 重复）"
            )
        if self.mechanical_errors:
            parts.append(f"机械预检 {len(self.mechanical_errors)} 错（effects / condition 形态违规）")
        return (
            "验收未通过，未落地：" + "；".join(parts) + "。"
            "这些都是编剧改不到的结构字段——问题出在管线或被手改过的 scene.json，"
            "别退回给编剧改正文；核对 design.json / 合并流程 / 是否有人手动动过 scene.json。"
        )


def _split_consistency(cons_issues: list[Issue]) -> tuple[list[Issue], list[Issue]]:
    """一致性层拆分：本体解析 notes（记录）vs 闭合违规 errors（硬拦）。"""
    ontology_notes: list[Issue] = []
    closure_errors: list[Issue] = []
    for issue in cons_issues:
        if _ONTOLOGY_RESOLUTION_MARKER in issue.message:
            ontology_notes.append(issue)
        else:
            closure_errors.append(issue)
    return closure_errors, ontology_notes


def run_acceptance(
    graph: dict[str, Any], *, ontology: dict | None = None
) -> AcceptanceReport:
    """跑完整验收：三层 + 机械（human）+ AP 记录 → AcceptanceReport。

    只读调用 /validator，不改任何图内容。`ontology` 透传给机械预检（当前 human
    路径下机械预检不做 ontology 引用查询，留参数对齐 dialogue_validator 签名 +
    未来多本体场景）。
    """
    graph_id = graph.get("graph_id", "<unknown>")
    nodes = graph.get("nodes")
    node_count = len(nodes) if isinstance(nodes, dict) else 0

    report = validate(graph)  # 三层：schema / graph / cons
    schema_errors = list(report.issues_by_level.get("schema", []))
    graph_errors = list(report.issues_by_level.get("graph", []))
    closure_errors, ontology_notes = _split_consistency(
        list(report.issues_by_level.get("cons", []))
    )

    # 机械预检：human 只豁免 monotonic，其余照跑（ADR-034 D11 对手填内容豁免）
    mech_results = validate_graph_mechanical(
        graph, ontology=ontology, generation_source="human"
    )
    mechanical_errors: list[MechanicalIssueRow] = []
    for nid, result in mech_results.items():
        for issue in result.issues:
            if issue.severity != "error":
                continue
            mechanical_errors.append(
                MechanicalIssueRow(
                    node_id=nid,
                    code=issue.code,
                    field_path=issue.field_path,
                    message=issue.message,
                )
            )

    # AP 预检：flag 记录不拦截（沿 multipass engine.py:475 先例）
    ap_flags: list[ApFlagRow] = []
    if isinstance(nodes, dict):
        for nid, node in nodes.items():
            if not isinstance(node, dict):
                continue
            for flag in detect_anti_patterns(node):
                ap_flags.append(_ap_flag_row(nid, flag))

    passed = not (schema_errors or graph_errors or closure_errors or mechanical_errors)
    return AcceptanceReport(
        graph_id=graph_id,
        passed=passed,
        schema_errors=schema_errors,
        graph_errors=graph_errors,
        consistency_closure_errors=closure_errors,
        consistency_ontology_notes=ontology_notes,
        mechanical_errors=mechanical_errors,
        ap_flags=ap_flags,
        node_count=node_count,
    )


def _ap_flag_row(node_id: str, flag: AntiPatternFlag) -> ApFlagRow:
    return ApFlagRow(
        node_id=node_id,
        ap_id=flag.ap_id,
        location=flag.location,
        excerpt=flag.excerpt,
        reason=flag.reason,
    )


# ---------------------------------------------------------------------------
# 报告渲染（.json 机器可读 + .md 人可读，成对落盘）
# ---------------------------------------------------------------------------


def acceptance_report_dict(report: AcceptanceReport) -> dict[str, Any]:
    """AcceptanceReport → 机器可读 dict（写 <scene>.acceptance.json）。"""
    return {
        "graph_id": report.graph_id,
        "passed": report.passed,
        "node_count": report.node_count,
        "blocking_error_count": report.blocking_error_count,
        "guidance": report.one_line_guidance(),
        "schema_errors": [asdict(i) for i in report.schema_errors],
        "graph_errors": [asdict(i) for i in report.graph_errors],
        "consistency_closure_errors": [
            asdict(i) for i in report.consistency_closure_errors
        ],
        "consistency_ontology_notes": [
            asdict(i) for i in report.consistency_ontology_notes
        ],
        "mechanical_errors": [asdict(r) for r in report.mechanical_errors],
        "ap_flags": [asdict(r) for r in report.ap_flags],
    }


def _issue_lines(title: str, issues: list[Issue]) -> list[str]:
    if not issues:
        return [f"### {title}：0", ""]
    lines = [f"### {title}：{len(issues)}", ""]
    for i in issues:
        lines.append(f"- `{i.location}`：{i.message}")
    lines.append("")
    return lines


def render_acceptance_md(report: AcceptanceReport) -> str:
    """AcceptanceReport → 人可读 markdown（写 <scene>.acceptance.md）。"""
    verdict = "✅ 通过（PASS）" if report.passed else "❌ 未通过（FAIL）"
    lines = [
        f"# 回流验收报告：{report.graph_id}",
        "",
        f"**判定**：{verdict}　|　节点数 {report.node_count}　|　硬拦错误 "
        f"{report.blocking_error_count}",
        "",
        f"> {report.one_line_guidance()}",
        "",
        "---",
        "",
        "## 硬拦层（决定 pass/fail）",
        "",
    ]
    lines += _issue_lines("Schema 层", report.schema_errors)
    lines += _issue_lines("Graph 层（图论）", report.graph_errors)
    lines += _issue_lines(
        "一致性层 · 闭合违规（说话人闭合 / option_id 唯一）",
        report.consistency_closure_errors,
    )
    # 机械预检
    if report.mechanical_errors:
        lines += [f"### 机械预检（source=human）：{len(report.mechanical_errors)}", ""]
        for r in report.mechanical_errors:
            lines.append(f"- `{r.node_id}` [{r.code}] `{r.field_path}`：{r.message}")
        lines.append("")
    else:
        lines += ["### 机械预检（source=human）：0", ""]

    lines += [
        "---",
        "",
        "## 只记录层（不影响 pass/fail）",
        "",
    ]
    # 本体解析待挂
    if report.consistency_ontology_notes:
        lines += [
            f"### 本体解析待挂：{len(report.consistency_ontology_notes)}",
            "",
            "> 这些引用未在**当前加载的本体**里解析——属 fixture / 环境依赖（隔离目录 E2E "
            "场景刻意引用未发布本体）。正式内容入库时对着已发布本体重跑才是本体守门；此处不拦落地。",
            "",
        ]
        for i in report.consistency_ontology_notes:
            lines.append(f"- `{i.location}`：{i.message}")
        lines.append("")
    else:
        lines += ["### 本体解析待挂：0", ""]
    # AP flags
    if report.ap_flags:
        lines += [
            f"### 反模式 flag（AP 记录，供编剧复核）：{len(report.ap_flags)}",
            "",
        ]
        for r in report.ap_flags:
            lines.append(
                f"- `{r.node_id}` [{r.ap_id}] `{r.location}`：{r.reason}"
                f"（片段：{r.excerpt}）"
            )
        lines.append("")
    else:
        lines += ["### 反模式 flag（AP 记录）：0", ""]
    return "\n".join(lines)


def acceptance_paths_for(scene_path: Path) -> tuple[Path, Path]:
    """<scene>.json → (<scene>.acceptance.md, <scene>.acceptance.json) 成对 sidecar 路径。"""
    md = scene_path.with_suffix(".acceptance.md")
    js = scene_path.with_suffix(".acceptance.json")
    return md, js


def write_acceptance_report(report: AcceptanceReport, scene_path: Path) -> tuple[Path, Path]:
    """成对写 <scene>.acceptance.md + .json（sidecar，与 version sidecar 同惯例）。

    验收报告是审计物、不是 scene.json 本身——落在 scene 旁边，与 version_recorder
    的 <scene>.version.json sidecar 同一命名族。返回 (md_path, json_path)。
    """
    md_path, json_path = acceptance_paths_for(scene_path)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(render_acceptance_md(report), encoding="utf-8")
    json_path.write_text(
        json.dumps(acceptance_report_dict(report), ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return md_path, json_path


__all__ = [
    "AcceptanceReport",
    "ApFlagRow",
    "MechanicalIssueRow",
    "acceptance_paths_for",
    "acceptance_report_dict",
    "render_acceptance_md",
    "run_acceptance",
    "write_acceptance_report",
]
