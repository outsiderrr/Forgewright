"""模块 C 协调层（reconcile layer）— Forward Planner 子模块 C.

职责（T-3Y 进展报告 §6.3）：
  输入：模块 A 输出（intent）+ 模块 B 输出（player_known_info）+ skill Precondition（前置条件）
  输出：5 分支判定结果之一——
    - pass            通过 → 可以调 skill 生成节点
    - split_node      前置注入新节点补足锚点
    - weaken_goal     弱化 foreground_goal（编剧意图妥协）
    - rewrite_seeds   往回追溯 seed 分配 → 改 background_seeds 历史
    - unreachable     标 unreachable → 报警给作者

T-3Y-1 mini prototype 阶段策略：
  起步用最简判定——
    - intent.foreground_goal 缺失 → unreachable
    - player_known_info 空 → unreachable
    - 否则 → pass
  完整 4 分支逻辑（split_node / weaken_goal / rewrite_seeds 的判定边界 + 修复算法）
  推迟到 T-3Y v0.2。
"""
from __future__ import annotations

from typing import Any, Literal

ReconcileVerdict = Literal[
    "pass",
    "split_node",
    "weaken_goal",
    "rewrite_seeds",
    "unreachable",
]


def reconcile(
    intent: dict[str, Any],
    player_known_info: list[dict[str, Any]],
    skill_preconditions: list[str] | None = None,
) -> dict[str, Any]:
    """协调编剧意图 + 玩家状态 + skill 前置（stub）。

    Args:
        intent: 模块 A 输出 dict（含 foreground_goal / background_seeds）
        player_known_info: 模块 B 输出短列表（每项含 knowledge_path / 可选 stage）
        skill_preconditions: optional skill 前置条件 ID 列表（T-3Y-1 阶段未消费）

    Returns:
        dict 含两键：
          - 'verdict': ReconcileVerdict（5 枚举之一）
          - 'reason':  str 解释判定原因
    """
    if not intent.get("foreground_goal"):
        return {
            "verdict": "unreachable",
            "reason": "missing foreground_goal（编剧未指定本节点承载的 reveal）",
        }
    if not player_known_info:
        return {
            "verdict": "unreachable",
            "reason": "no relevant_known_info available（玩家状态 retrieval 短列表为空）",
        }
    return {
        "verdict": "pass",
        "reason": "stub: foreground_goal + player_known_info both present",
    }


__all__ = ["ReconcileVerdict", "reconcile"]
