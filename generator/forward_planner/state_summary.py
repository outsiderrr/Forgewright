"""模块 B 状态摘要层（state summary layer）— Forward Planner 子模块 B.

职责（T-3Y 进展报告 §6.2）：
  输入：dialogue_graph 当前路径 + state 状态 + NPC 状态机 state
  输出：actual_player_known_info（玩家在本节点实际已知信息）
        = T-3Y 双层结构里的 relevant_known_info（retrieval 短列表）

T-3Y-1 mini prototype 阶段策略：
  起步用 retrieval 子集——读 graph.player_known_info 顶层声明 + 过滤 state 中已 set 的
  knowledge.* path；完整算法（从 character.knowledge / 检定结果 / NPC 状态机抽取 + summarize）
  推迟到 T-3Y v0.2。

注意（T-3Y 进展报告 §7 拍板 2.2 / 2.3 / 2.4）：
  - NPC 因玩家互动改变的 state（如露西信任度上升 → 玩家可感知）算 player_known_info
  - NPC 静态描述（如头发颜色）不算
  - 检定结果（被动注入 + 主动检定通过的揭示文本）算
  - 不模拟玩家遗忘（默认玩家记住一切）
"""
from __future__ import annotations

from typing import Any


def compute_player_known_info(
    graph: dict[str, Any],
    current_state: dict[str, Any],
) -> list[dict[str, Any]]:
    """计算当前 state 下玩家的 relevant_known_info 短列表（stub）。

    Args:
        graph: 完整 dialogue_graph dict（含顶层 player_known_info 声明列表）
        current_state: 当前 state 总线快照；键为 state path 字符串（如 "knowledge.foo"），
                       值为已 set 的值（typically True / int / list）

    Returns:
        过滤后的 player_known_info 子集——只保留 state 中已 set 且非 falsy 值的条目；
        每条保持原 dict 结构（含 knowledge_path / 可选 stage）
    """
    declared = graph.get("player_known_info", [])
    known: list[dict[str, Any]] = []
    for item in declared:
        path = item.get("knowledge_path")
        if path is None:
            continue
        if path in current_state and current_state[path]:
            known.append(item)
    return known


__all__ = ["compute_player_known_info"]
