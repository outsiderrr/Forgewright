"""Render node prompt（渲染节点级提示词）— T-3Y-1 子 goal 2.

合成 {system, user} 两段——
  - system 来自 generator.prompts.node.system.NODE_SYSTEM_PROMPT（静态）
  - user   由 generator.prompts.node.fill.build_node_user_message 动态拼接
"""
from __future__ import annotations

from typing import Any

from generator.prompts.node.fill import build_node_user_message
from generator.prompts.node.system import NODE_SYSTEM_PROMPT


def render_node_prompt(
    *,
    node_skeleton: dict[str, Any],
    player_known_info: list[dict[str, Any]],
    foreground_goal: str | None,
    background_seeds: list[str],
    speaker_ref: str | None = None,
    npc_state: dict[str, Any] | None = None,
    all_known_info_summary: str | None = None,
) -> dict[str, str]:
    """渲染节点级 prompt（system + user）.

    Args:
        node_skeleton:        节点骨架 dict
        player_known_info:    Forward Planner 模块 B 输出
        foreground_goal:      Forward Planner 模块 A 输出
        background_seeds:     Forward Planner 模块 A 输出
        speaker_ref:          NPC ID（可省，从 node_skeleton 推导）
        npc_state:            NPC 状态机当前 state 快照（可省）
        all_known_info_summary: 自然语言摘要（不入 schema；可省）

    Returns:
        dict {'system': str, 'user': str}
    """
    user = build_node_user_message(
        node_skeleton=node_skeleton,
        player_known_info=player_known_info,
        foreground_goal=foreground_goal,
        background_seeds=background_seeds,
        speaker_ref=speaker_ref,
        npc_state=npc_state,
        all_known_info_summary=all_known_info_summary,
    )
    return {"system": NODE_SYSTEM_PROMPT, "user": user}


__all__ = ["render_node_prompt"]
