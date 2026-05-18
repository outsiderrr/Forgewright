"""模块 A 剧本意图层（intent layer）— Forward Planner 子模块 A.

职责（T-3Y 进展报告 §6.1）：
  输入：dialogue_graph 整体结构 + chapter outline + 角色弧光设计
  输出：每节点的 intended_foreground_goal（编剧期望节点目的）+
        intended_background_seeds（编剧期望埋下的种子）

T-3Y-1 mini prototype 阶段策略：
  直接从节点字段读 foreground_goal / background_seeds（编剧已在 schema 写明）；
  完整推导算法（从场景 scene_reveals / scene_seeds → 节点分配 + 角色弧光）推迟到 T-3Y v0.2。
"""
from __future__ import annotations

from typing import Any


def compute_intent(graph: dict[str, Any], node_id: str) -> dict[str, Any]:
    """计算单节点的剧本意图（stub）。

    Args:
        graph: 完整 dialogue_graph dict（含 nodes map + 顶层场景级字段）
        node_id: 要计算意图的节点 ID

    Returns:
        dict 含两键：
          - 'foreground_goal': str | None    本节点承载的 reveal + stage（如 'R1.stage_2'）
          - 'background_seeds': list[str]    本节点要埋的 seed_id 列表

        节点不存在或字段缺失 → 返回空意图（foreground_goal=None, background_seeds=[]）
    """
    nodes = graph.get("nodes", {})
    if node_id not in nodes:
        return {"foreground_goal": None, "background_seeds": []}

    node = nodes[node_id]
    foreground_goal = node.get("foreground_goal")
    background_seeds = list(node.get("background_seeds", []))
    return {
        "foreground_goal": foreground_goal,
        "background_seeds": background_seeds,
    }


__all__ = ["compute_intent"]
