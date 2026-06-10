"""TopologyPlan 确定性校验 + 半固定回退（0 LLM）—— 动态拓扑的安全网.

拓扑规划 pass（prompts/node/multipass/topology.py）让 LLM 自决节点数/类型/接线；
本模块用纯代码守住结构底线（DESIGN §6）：

  - validate_topology()：树性、可达、出入度、kind 约束、规模上限——全部确定性检查；
  - fallback_topology()：规划重试后仍不合法时回退到已验证的半固定脚手架
    （ADR-038 v1 形状：开场 → 枢纽 → 软/硬两分支 → end），如实记 fallback。

plan 形态（拓扑规划 pass 的输出契约）：
  {"entry_node_id": str,
   "nodes": [{"node_id", "kind": "choice"|"beats"|"end", "function",
              "reveals": [...], "routes": [{"to","stance"}] (choice), "next": str (beats)}]}
"""
from __future__ import annotations

import re
from typing import Any

MAX_NODES = 12
MIN_NODES = 3
_NODE_ID_RE = re.compile(r"^[a-z][a-z0-9_]*$")


def _outgoing(node: dict[str, Any]) -> list[str]:
    """节点的出边目标列表（choice → routes[].to；beats → [next]；end → []）。"""
    kind = node.get("kind")
    if kind == "choice":
        return [r.get("to", "") for r in node.get("routes") or []]
    if kind == "beats":
        nxt = node.get("next")
        return [nxt] if nxt else []
    return []


def validate_topology(plan: dict[str, Any]) -> list[str]:
    """确定性校验 TopologyPlan；返回错误清单（空 = 合法）。"""
    errors: list[str] = []
    nodes = plan.get("nodes")
    entry = plan.get("entry_node_id")
    if not isinstance(nodes, list) or not nodes:
        return ["nodes 缺失或为空"]
    if not isinstance(entry, str) or not entry:
        return ["entry_node_id 缺失"]

    ids = [n.get("node_id") for n in nodes]
    by_id: dict[str, dict[str, Any]] = {}
    for n in nodes:
        nid = n.get("node_id")
        if not isinstance(nid, str) or not _NODE_ID_RE.match(nid or ""):
            errors.append(f"node_id {nid!r} 不合法（要求小写蛇形 ^[a-z][a-z0-9_]*$）")
            continue
        if nid in by_id:
            errors.append(f"node_id {nid!r} 重复")
        by_id[nid] = n
    if len(by_id) != len(ids):
        return errors  # id 层都坏了，后续图检查没意义

    if entry not in by_id:
        errors.append(f"entry_node_id {entry!r} 不在 nodes 里")
        return errors

    if not (MIN_NODES <= len(nodes) <= MAX_NODES):
        errors.append(f"节点总数 {len(nodes)} 超界（要求 {MIN_NODES}-{MAX_NODES}）")

    # kind 约束 + 出边形态
    n_end = 0
    n_real_fork = 0
    for nid, n in by_id.items():
        kind = n.get("kind")
        routes = n.get("routes") or []
        nxt = n.get("next")
        if kind == "choice":
            if not (1 <= len(routes) <= 4):
                errors.append(f"choice 节点 {nid} 的 routes 数 {len(routes)} 超界（1-4）")
            if nxt:
                errors.append(f"choice 节点 {nid} 不应有 next")
            if len(routes) >= 2:
                n_real_fork += 1
        elif kind == "beats":
            if not nxt:
                errors.append(f"beats 节点 {nid} 缺 next（唯一出边）")
            if routes:
                errors.append(f"beats 节点 {nid} 不应有 routes")
        elif kind == "end":
            n_end += 1
            if routes or nxt:
                errors.append(f"end 节点 {nid} 不应有出边")
        else:
            errors.append(f"节点 {nid} 的 kind {kind!r} 不合法")
        for t in _outgoing(n):
            if t == nid:
                errors.append(f"节点 {nid} 有自环")
            elif t not in by_id:
                errors.append(f"节点 {nid} 的出边目标 {t!r} 不存在")
    if n_end == 0:
        errors.append("至少要有 1 个 end 节点")
    if n_real_fork == 0:
        errors.append("至少要有 1 个 routes ≥ 2 的 choice 节点（真分歧）")

    # 树性：除入口外每个节点恰好 1 条入边；入口 0 条
    incoming: dict[str, int] = {nid: 0 for nid in by_id}
    for n in by_id.values():
        for t in _outgoing(n):
            if t in incoming:
                incoming[t] += 1
    if incoming.get(entry, 0) != 0:
        errors.append(f"入口 {entry} 不应有入边（入度 {incoming.get(entry)}）")
    for nid, deg in incoming.items():
        if nid == entry:
            continue
        if deg != 1:
            errors.append(f"节点 {nid} 入度 {deg} ≠ 1（纯树要求；禁止交叉边/孤立节点）")

    # 可达性（树性已基本保证，BFS 防孤立环）
    seen: set[str] = set()
    frontier = [entry]
    while frontier:
        cur = frontier.pop()
        if cur in seen or cur not in by_id:
            continue
        seen.add(cur)
        frontier.extend(_outgoing(by_id[cur]))
    unreachable = sorted(set(by_id) - seen)
    if unreachable:
        errors.append(f"从入口不可达的节点：{unreachable}")

    return errors


def fallback_topology(scene_spec: dict[str, Any]) -> dict[str, Any]:
    """半固定脚手架（ADR-038 v1 形状）——拓扑规划失败时的确定性回退。

    线索分层的确定性近似：软分支 = required + optional 全量；
    硬分支 = 仅 required（beat prompt 的 situation 再叠加"残缺化"指示，
    不给钥匙/异常类可选线索）。
    """
    required = list(scene_spec.get("required_clues") or [])
    optional = list(scene_spec.get("optional_clues") or [])
    return {
        "entry_node_id": "opening",
        "nodes": [
            {
                "node_id": "opening",
                "kind": "choice",
                "function": "定向开场：建立谁在场/空间/风险与玩家初始姿态；不预先泄露深层线索",
                "reveals": [],
                "routes": [{"to": "hub", "stance": "选择接近方式（殊途同归到枢纽，姿态影响关系）"}],
            },
            {
                "node_id": "hub",
                "kind": "choice",
                "function": "枢纽：把接近方式升格成低压软问 vs 高压施压的真分歧，并路由分支",
                "reveals": [],
                "routes": [
                    {"to": "branch_soft", "stance": "低压软问（有限信任）"},
                    {"to": "branch_hard", "stance": "高压施压（防御切割）"},
                ],
            },
            {
                "node_id": "branch_soft",
                "kind": "beats",
                "function": "低压分支：NPC 在有限信任下交底——完整线索分拍铺开",
                "reveals": required + optional,
                "next": "end_soft",
            },
            {
                "node_id": "branch_hard",
                "kind": "beats",
                "function": (
                    "高压分支：NPC 被逼到防御、只想切断关系——只给能行动的残缺碎片"
                    "（残缺化：不给钥匙/异常类可选线索，必要线索只给残缺记号）"
                ),
                "reveals": required,
                "next": "end_hard",
            },
            {"node_id": "end_soft", "kind": "end", "function": "收束：带完整线索离开", "reveals": []},
            {"node_id": "end_hard", "kind": "end", "function": "收束：带残缺线索离开", "reveals": []},
        ],
    }


__all__ = ["validate_topology", "fallback_topology", "MAX_NODES", "MIN_NODES"]
