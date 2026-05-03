"""第二层校验 2A：纯拓扑 + condition 引用形态合法性 (ADR-021)。

包装现有 `graph_check.check`（保留向后兼容；v1.0 §2.7），并叠加 `TopologyIssue`
接口，新增 ADR-021 §2A 范围下的检查项。

2A 范围（仅本层职责）：
  - 结构拓扑（不可达 / 死锁 / 收敛）
  - condition 引用形态合法性（ADR-016 path 命名空间 / op 枚举 / 叶 vs 复合互斥）
  - 同时活跃 clocks 软上限 warning（ADR-017 D9）

condition satisfiability **不在本层** —— 归 2B sampling（ADR-021 决策核心；见
`/validator/sampling.py`）。把启发式包装成 condition-aware "已完成" 会误导阶段 2 验收。
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal

import networkx as nx

from . import graph_check  # 保留向后兼容；现有导出不动
from .graph_check import check as graph_check_layer  # noqa: F401  (re-export)
from .report import Issue

__all__ = [
    "TopologyIssue",
    "TopologyResult",
    "validate_graph_topology",
    "normalize_effect_op",
    "STATE_PATH_NAMESPACES",
    "ACTIVE_CLOCKS_SOFT_LIMIT",
    "graph_check",
    "graph_check_layer",
]

# ADR-016：state path 命名空间表（阶段 2 起 path 命名必须落入这五个之一）
STATE_PATH_NAMESPACES: tuple[str, ...] = (
    "world",
    "faction",
    "relationship",
    "flag",
    "player",
)

# ADR-017 D9：同时活跃 clocks 软上限（schema 层不写；T-2.7 实测倒推真实上限）
ACTIVE_CLOCKS_SOFT_LIMIT = 10

# state_condition.schema.json 叶/复合枚举
_CONDITION_LEAF_OPS: frozenset[str] = frozenset(
    ["eq", "neq", "gt", "gte", "lt", "lte", "has", "has_not"]
)
_CONDITION_COMPOSITE_KEYS: frozenset[str] = frozenset(["all_of", "any_of", "not"])
_CONDITION_LEAF_REQUIRED: frozenset[str] = frozenset(["op", "path", "value"])

# state_effect.schema.json + ADR-017 tick_effects.effect_op 公用枚举
_EFFECT_OPS: frozenset[str] = frozenset(["set", "inc", "dec", "add", "remove"])

# Legacy graph_check 报告 → TopologyIssue.code 的关键字映射 (review 4.1).
# 旧 graph_check 用 message 文本编码错误类型；本表把每条文本映射到一个
# 稳定的 code，便于下游（T-2.8 / T-2.13）按 code 聚合而非匹配文本。
_LEGACY_MESSAGE_CODES: tuple[tuple[str, str], ...] = (
    ("does not exist in", "DANGLING_TARGET"),
    ("is not in nodes map", "ENTRY_NOT_IN_NODES"),
    ("unreachable from entry", "NEVER_REACHED"),
    ("has no terminal node", "NO_END_NODE"),
    ("end node(s) but none are", "END_UNREACHABLE"),
    ("strongly-connected component", "DIALOGUE_LOOP"),
)


@dataclass(frozen=True)
class TopologyIssue:
    severity: Literal["error", "warning"]
    code: str
    node_id: str | None
    option_id: str | None
    message: str


@dataclass
class TopologyResult:
    issues: list[TopologyIssue] = field(default_factory=list)
    unreachable_nodes: list[str] = field(default_factory=list)
    deadlock_nodes: list[str] = field(default_factory=list)
    convergence_groups: list[list[str]] = field(default_factory=list)
    condition_form_issues: list[tuple[str, str]] = field(default_factory=list)

    @property
    def has_error(self) -> bool:
        return any(i.severity == "error" for i in self.issues)


def normalize_effect_op(effect: dict) -> dict:
    """统一 `StateEffect.op` 与 `tick_effects.effect_op` 映射 (ADR-017 critique §9)。

    输入接受两种形态之一（不写两套语义代码）：
      - StateEffect 形态：``{"op": ..., "path": ..., "value": ...}``
      - tick_effect 形态：``{"effect_op": ..., "path": ..., "value": ..., "at_tick": ...}``

    输出：StateEffect 形态（``{"op", "path", "value"}``），可直接喂给
    ``state.effects.apply_effect``。
    """
    if not isinstance(effect, dict):
        raise TypeError(f"effect must be a dict, got {type(effect).__name__}")
    if "op" in effect and "effect_op" in effect:
        if effect["op"] != effect["effect_op"]:
            raise ValueError(
                "effect has both 'op' and 'effect_op' with different values: "
                f"{effect['op']!r} vs {effect['effect_op']!r}"
            )
    if "op" in effect:
        return {"op": effect["op"], "path": effect.get("path"), "value": effect.get("value")}
    if "effect_op" in effect:
        return {
            "op": effect["effect_op"],
            "path": effect.get("path"),
            "value": effect.get("value"),
        }
    raise ValueError("effect dict requires 'op' or 'effect_op' key")


def _is_mapping(x: Any) -> bool:
    return isinstance(x, dict)


def _path_namespace_ok(path: Any) -> bool:
    if not isinstance(path, str) or not path:
        return False
    head = path.split(".", 1)[0]
    return head in STATE_PATH_NAMESPACES


def _legacy_code_for(message: str) -> str:
    for needle, code in _LEGACY_MESSAGE_CODES:
        if needle in message:
            return code
    return "LEGACY_GRAPH_ISSUE"


def _map_legacy_issue(
    issue: Issue,
    severity: Literal["error", "warning"],
) -> TopologyIssue:
    """Map a legacy graph_check ``Issue`` into a ``TopologyIssue`` (review 4.1).

    location 形态：``"node_id"`` / ``"node_id/option_id"`` / ``"root"`` /
    ``"a,b,c"`` (SCC 节点列表)。前两种解出 node_id / option_id；其余保留为 None。
    """
    msg = issue.message
    loc = issue.location or ""
    code = _legacy_code_for(msg)
    node_id: str | None
    option_id: str | None
    if code == "DANGLING_TARGET" and "/" in loc:
        node_id, option_id = loc.split("/", 1)
    elif code == "DIALOGUE_LOOP":
        node_id = loc or None  # comma-joined SCC list
        option_id = None
    elif loc == "root" or "," in loc:
        node_id = None
        option_id = None
    else:
        node_id = loc or None
        option_id = None
    return TopologyIssue(
        severity=severity,
        code=code,
        node_id=node_id,
        option_id=option_id,
        message=msg,
    )


def _check_condition_form(
    cond: Any,
    *,
    allow_null: bool = True,
) -> list[str]:
    """Form-only check：path 命名空间 + op 枚举 + 叶/复合互斥 + 必填字段齐全。

    返回人话错误列表；空列表表示 OK。**不检查 condition satisfiability**——那归 2B。

    ``allow_null``：顶层调用允许 None（"无条件"）；递归到 composite 子节点（all_of /
    any_of 项 / not 子）时禁止 None（review 4.2）。
    """
    if cond is None:
        if allow_null:
            return []
        return ["condition cannot be null in this position"]
    if not isinstance(cond, dict):
        return [f"condition must be object, got {type(cond).__name__}"]

    leaf_keys = {k for k in _CONDITION_LEAF_REQUIRED if k in cond}
    composite_keys = {k for k in _CONDITION_COMPOSITE_KEYS if k in cond}
    if leaf_keys and composite_keys:
        return [
            f"condition mixes leaf keys {sorted(leaf_keys)} with composite "
            f"keys {sorted(composite_keys)} (D4 互斥)"
        ]

    issues: list[str] = []
    if composite_keys:
        if len(composite_keys) > 1:
            issues.append(
                f"condition has multiple composite keys {sorted(composite_keys)}; "
                f"must be exactly one of all_of / any_of / not"
            )
            return issues
        key = next(iter(composite_keys))
        if key in ("all_of", "any_of"):
            children = cond.get(key)
            if not isinstance(children, list) or not children:
                issues.append(f"condition.{key} must be a non-empty array")
            else:
                for i, child in enumerate(children):
                    issues.extend(
                        f"{key}[{i}]: {sub}"
                        for sub in _check_condition_form(child, allow_null=False)
                    )
        else:  # "not" — review 4.2 修复 not:null 漏检
            child = cond.get("not")
            issues.extend(
                f"not: {sub}"
                for sub in _check_condition_form(child, allow_null=False)
            )
        return issues

    # leaf form — review 4.2 修复缺 value 漏检
    missing = sorted(_CONDITION_LEAF_REQUIRED - set(cond.keys()))
    if missing:
        issues.append(
            f"leaf condition missing required key(s): {missing}"
        )
    if "op" in cond:
        op = cond.get("op")
        if not isinstance(op, str) or op not in _CONDITION_LEAF_OPS:
            issues.append(
                f"condition.op {op!r} not in leaf op enum "
                f"{sorted(_CONDITION_LEAF_OPS)}"
            )
    if "path" in cond:
        path = cond.get("path")
        if not _path_namespace_ok(path):
            issues.append(
                f"condition.path {path!r} not in ADR-016 namespaces "
                f"{STATE_PATH_NAMESPACES}; path must start with one of these "
                f"prefixes"
            )
    return issues


def _clock_is_active(clock: Any) -> bool:
    """ADR-017 D9 软上限的保守活跃判定 (review 4.3).

    True iff ``ticks_filled > 0`` 或 ``advance_rule.type`` 已定义。

    范围注记：2A 上下文不足以判断 ``advance_rule`` 是否真正命中（事件触发归
    运行时），但 ADR-017 D9 软上限是状态空间预警——宁高勿低估。任何定义良好
    的 ``advance_rule`` 在生命周期内会触发，故视作可激活。T-2.7 实测倒推后
    由 ADR-017 v0.2 修订真实上限。
    """
    if not isinstance(clock, dict):
        return False
    ticks_filled = clock.get("ticks_filled")
    if isinstance(ticks_filled, int) and ticks_filled > 0:
        return True
    advance_rule = clock.get("advance_rule")
    if isinstance(advance_rule, dict):
        rule_type = advance_rule.get("type")
        if isinstance(rule_type, str) and rule_type:
            return True
    return False


def _check_effects_form(effects: Any) -> list[str]:
    """Form-only check on effects array. ADR-016 path namespace + op enum."""
    if effects is None:
        return []
    if not isinstance(effects, list):
        return [f"effects must be array, got {type(effects).__name__}"]
    issues: list[str] = []
    for i, eff in enumerate(effects):
        if not isinstance(eff, dict):
            issues.append(f"effects[{i}] must be object, got {type(eff).__name__}")
            continue
        # tolerate either StateEffect.op or tick_effects.effect_op
        op = eff.get("op", eff.get("effect_op"))
        if not isinstance(op, str) or op not in _EFFECT_OPS:
            issues.append(
                f"effects[{i}].op {op!r} not in {sorted(_EFFECT_OPS)}"
            )
        path = eff.get("path")
        if not _path_namespace_ok(path):
            issues.append(
                f"effects[{i}].path {path!r} not in ADR-016 namespaces "
                f"{STATE_PATH_NAMESPACES}"
            )
    return issues


def validate_graph_topology(
    graph: dict,
    *,
    ontology: dict | None = None,
) -> TopologyResult:
    """2A 纯拓扑 + condition / effect 形态合法性校验 (ADR-021).

    检查项（不含 condition satisfiability — 那归 2B）：
      - 来自 legacy graph_check（v1.0 §2.7 包装；review 4.1）：
        * NEVER_REACHED / DANGLING_TARGET / ENTRY_NOT_IN_NODES /
          NO_END_NODE / END_UNREACHABLE / DIALOGUE_LOOP（warning）
      - A2 DEAD_END_NODE：非 end 节点入度可达，但 option 中无任何 condition=null
                           （启发式；condition 满足性归 2B）
      - A3 CONDITION_FORM_INVALID：option.condition / effects / on_enter_effects 字段
                                    形态非法（path 命名空间 / op 枚举 / 叶 vs 复合互斥
                                    / leaf 必填字段）
      - A4 CONVERGENCE：warning，多路径汇合点（入度 > 1 且非 entry）
      - ACTIVE_CLOCKS_OVER_SOFT_LIMIT：warning，传入 ontology 时活跃 clocks 数 > 10
                                        (ADR-017 D9)

    **范围注记 (ADR-021)**：把 condition satisfiability 包装成 "condition-aware
    已完成" 会误导阶段 2 验收。本层产物组合 2B sampling 双报，方为 ADR-021 完成。
    """
    issues: list[TopologyIssue] = []
    nodes = graph.get("nodes")
    entry = graph.get("entry_node_id")

    # === 包装 legacy graph_check（review 4.1）===
    # 旧 graph_check.check 的 5 类 error + SCC warning 都映射成 TopologyIssue，
    # 让新 2A 双报对结构非法图不再 false pass。dangling target / no end /
    # end-unreachable 等约束由 legacy 主导；新 2A 在其上叠加 A2/A3/A4。
    legacy_errors, legacy_warnings = graph_check.check(graph)
    for legacy in legacy_errors:
        issues.append(_map_legacy_issue(legacy, severity="error"))
    for legacy in legacy_warnings:
        issues.append(_map_legacy_issue(legacy, severity="warning"))

    if not _is_mapping(nodes) or not isinstance(entry, str):
        return TopologyResult(issues=issues)

    dg = nx.DiGraph()
    for node_id in nodes:
        dg.add_node(node_id)
    for node_id, node in nodes.items():
        if not _is_mapping(node):
            continue
        for opt in (node.get("options") or []):
            if not _is_mapping(opt):
                continue
            target = opt.get("target_node_id")
            if isinstance(target, str) and target in nodes:
                dg.add_edge(node_id, target)

    # NEVER_REACHED — legacy 已主导报告（review 4.1）；本字段对外保留以便下游聚合
    if entry in nodes:
        reachable = nx.descendants(dg, entry) | {entry}
    else:
        reachable = set()
    unreachable: list[str] = sorted(set(nodes) - reachable)

    # A2 DEAD_END_NODE — 启发式：非 end 节点入度可达，且 option 全部 conditional
    deadlock_nodes: list[str] = []
    for nid, node in nodes.items():
        if not _is_mapping(node):
            continue
        if nid not in reachable:
            continue  # A1 已报
        if node.get("type") == "end":
            continue
        opts = node.get("options") or []
        if not isinstance(opts, list) or not opts:
            deadlock_nodes.append(nid)
            issues.append(
                TopologyIssue(
                    severity="error",
                    code="DEAD_END_NODE",
                    node_id=nid,
                    option_id=None,
                    message=(
                        f"non-end node {nid!r} has no options; cannot progress "
                        f"(2A heuristic; condition satisfiability checked in 2B)"
                    ),
                )
            )
            continue
        unconditional_count = sum(
            1
            for o in opts
            if _is_mapping(o) and o.get("condition") is None
        )
        if unconditional_count == 0:
            deadlock_nodes.append(nid)
            issues.append(
                TopologyIssue(
                    severity="error",
                    code="DEAD_END_NODE",
                    node_id=nid,
                    option_id=None,
                    message=(
                        f"non-end node {nid!r} has {len(opts)} option(s), all "
                        f"conditional; no unconditional fallback (2A heuristic; "
                        f"condition satisfiability checked in 2B)"
                    ),
                )
            )

    # A3 CONDITION_FORM_INVALID — option.condition / effects / on_enter_effects
    condition_form_issues: list[tuple[str, str]] = []
    for nid, node in nodes.items():
        if not _is_mapping(node):
            continue
        for opt in (node.get("options") or []):
            if not _is_mapping(opt):
                continue
            opt_id = str(opt.get("option_id", "?"))
            cond_issues = _check_condition_form(opt.get("condition"))
            if cond_issues:
                condition_form_issues.append((nid, opt_id))
            for problem in cond_issues:
                issues.append(
                    TopologyIssue(
                        severity="error",
                        code="CONDITION_FORM_INVALID",
                        node_id=nid,
                        option_id=opt_id,
                        message=problem,
                    )
                )
            for problem in _check_effects_form(opt.get("effects")):
                issues.append(
                    TopologyIssue(
                        severity="error",
                        code="CONDITION_FORM_INVALID",
                        node_id=nid,
                        option_id=opt_id,
                        message=f"option.{problem}",
                    )
                )
        for problem in _check_effects_form(node.get("on_enter_effects")):
            issues.append(
                TopologyIssue(
                    severity="error",
                    code="CONDITION_FORM_INVALID",
                    node_id=nid,
                    option_id=None,
                    message=f"on_enter_{problem}",
                )
            )

    # A4 CONVERGENCE — 多路径汇合 (warning, informational)
    convergence_groups: list[list[str]] = []
    for nid in sorted(nodes):
        if nid == entry:
            continue
        if nid not in reachable:
            continue
        in_deg = dg.in_degree(nid)
        if in_deg > 1:
            preds = sorted(dg.predecessors(nid))
            convergence_groups.append([nid] + preds)
            issues.append(
                TopologyIssue(
                    severity="warning",
                    code="CONVERGENCE",
                    node_id=nid,
                    option_id=None,
                    message=(
                        f"node {nid!r} reached from {len(preds)} predecessors "
                        f"{preds} (informational; multi-path convergence)"
                    ),
                )
            )

    # ACTIVE_CLOCKS_OVER_SOFT_LIMIT — ADR-017 D9 (review 4.3)
    # 活跃判定保守化：ticks_filled > 0 OR advance_rule.type 已定义。
    # 详 _clock_is_active 文档（不低估状态空间预警）。
    if isinstance(ontology, dict):
        clocks = ontology.get("clocks") or []
        if isinstance(clocks, list):
            active_count = sum(1 for c in clocks if _clock_is_active(c))
            if active_count > ACTIVE_CLOCKS_SOFT_LIMIT:
                issues.append(
                    TopologyIssue(
                        severity="warning",
                        code="ACTIVE_CLOCKS_OVER_SOFT_LIMIT",
                        node_id=None,
                        option_id=None,
                        message=(
                            f"{active_count} active clocks exceed soft limit "
                            f"{ACTIVE_CLOCKS_SOFT_LIMIT} (ADR-017 D9; T-2.7 "
                            f"empirical re-tune pending)"
                        ),
                    )
                )

    return TopologyResult(
        issues=issues,
        unreachable_nodes=unreachable,
        deadlock_nodes=deadlock_nodes,
        convergence_groups=convergence_groups,
        condition_form_issues=condition_form_issues,
    )
