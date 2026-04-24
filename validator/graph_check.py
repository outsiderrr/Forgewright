"""第二层：图论校验。

用 networkx.DiGraph 构造对话图（节点 = nodes 映射；边 = 每个 option.target_node_id），
对结构做拓扑校验——条件性可达性（ADR-009 第三层，模拟层）不在此范围。

必抓错误：
  - entry_node_id 不在 nodes 中
  - 任何 option.target_node_id 指向不存在节点（悬空引用）
  - 从 entry 不可达的节点
  - 没有 type="end" 节点
  - 有 end 节点但从 entry 均不可达

警告（非错误，阶段 0 不强制）：
  - 纯 dialogue 的非平凡强连通子图（不含任何 end 节点）
"""
from __future__ import annotations

from typing import Any

import networkx as nx

from .report import Issue


def _is_mapping(x: Any) -> bool:
    return isinstance(x, dict)


def check(graph: dict) -> tuple[list[Issue], list[Issue]]:
    errors: list[Issue] = []
    warnings: list[Issue] = []

    nodes = graph.get("nodes")
    entry = graph.get("entry_node_id")

    if not _is_mapping(nodes):
        return errors, warnings
    if not isinstance(entry, str):
        return errors, warnings

    dg = nx.DiGraph()
    for node_id in nodes:
        dg.add_node(node_id)
    for node_id, node in nodes.items():
        if not _is_mapping(node):
            continue
        options = node.get("options") or []
        if not isinstance(options, list):
            continue
        for opt in options:
            if not _is_mapping(opt):
                continue
            target = opt.get("target_node_id")
            if not isinstance(target, str):
                continue
            if target in nodes:
                dg.add_edge(node_id, target)
            else:
                opt_id = opt.get("option_id", "?")
                errors.append(
                    Issue(
                        level="graph",
                        location=f"{node_id}/{opt_id}",
                        message=(
                            f"option.target_node_id {target!r} does not exist in "
                            f"nodes map (dangling reference from {node_id})"
                        ),
                    )
                )

    if entry not in nodes:
        errors.append(
            Issue(
                level="graph",
                location="root",
                message=(
                    f"entry_node_id {entry!r} is not in nodes map; reachability "
                    f"checks skipped"
                ),
            )
        )
        return errors, warnings

    reachable = nx.descendants(dg, entry) | {entry}
    unreachable = set(nodes) - reachable
    for node_id in sorted(unreachable):
        errors.append(
            Issue(
                level="graph",
                location=node_id,
                message=f"node unreachable from entry node {entry!r}",
            )
        )

    end_ids = {nid for nid, node in nodes.items()
               if _is_mapping(node) and node.get("type") == "end"}
    if not end_ids:
        errors.append(
            Issue(
                level="graph",
                location="root",
                message='graph has no terminal node (type == "end")',
            )
        )
    else:
        if not (end_ids & reachable):
            errors.append(
                Issue(
                    level="graph",
                    location="root",
                    message=(
                        f"graph has {len(end_ids)} end node(s) but none are "
                        f"reachable from entry {entry!r}"
                    ),
                )
            )

    for scc in nx.strongly_connected_components(dg):
        is_nontrivial = len(scc) >= 2 or (
            len(scc) == 1 and dg.has_edge(next(iter(scc)), next(iter(scc)))
        )
        if not is_nontrivial:
            continue
        if any(n in end_ids for n in scc):
            continue
        warnings.append(
            Issue(
                level="graph",
                location=",".join(sorted(scc)),
                message=(
                    "dialogue-only strongly-connected component contains no end "
                    "node (possible dead loop; stage 0 warning only)"
                ),
            )
        )

    return errors, warnings
