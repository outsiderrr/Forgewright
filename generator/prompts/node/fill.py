"""Node-level fill prompt（节点级动态填充段）— T-3Y-1 子 goal 2.

构建用户消息中的"本节点上下文"段——动态信息（player_known_info /
foreground_goal / background_seeds / NPC 当前 state / 节点骨架）拼接成纯文本块，
作为单次调用的 user message 主体。

system prompt 是静态文本（system.py）；本模块是 per-call 动态拼接。
"""
from __future__ import annotations

import json
from typing import Any


def render_player_known_info(
    items: list[dict[str, Any]],
    *,
    all_known_info_summary: str | None = None,
) -> str:
    """渲染 player_known_info 注入段.

    Args:
        items: T-3Y 双层结构的结构化部分（relevant_known_info）
        all_known_info_summary: T-3Y 双层结构的自然语言摘要（不入 schema；prompt 层拼接）

    Returns:
        markdown 段："## 玩家已知信息（player_known_info）" + 列表 + 摘要
    """
    lines = ["## 玩家已知信息（player_known_info）"]
    lines.append("")
    if not items:
        lines.append("（玩家暂无已知信息——本节点是首次接触）")
    else:
        lines.append("**结构化清单（relevant_known_info）**：")
        for item in items:
            path = item.get("knowledge_path", "?")
            stage = item.get("stage")
            stage_str = f"（阶段 {stage}）" if stage else ""
            lines.append(f"- `{path}`{stage_str}")
    if all_known_info_summary:
        lines.append("")
        lines.append("**全局背景摘要（all_known_info_summary）**：")
        lines.append(all_known_info_summary)
    lines.append("")
    lines.append("**写作约束**：写 NPC 对白时假设玩家已经知道以上信息；不要让 NPC 重复说一遍。")
    return "\n".join(lines)


def render_foreground_goal(foreground_goal: str | None) -> str:
    """渲染 foreground_goal 段."""
    lines = ["## 本节点的 foreground_goal（前景目标）"]
    lines.append("")
    if not foreground_goal:
        lines.append("（无指定 foreground_goal——本节点为过渡 / 收束节点）")
    else:
        lines.append(f"**`{foreground_goal}`**")
        lines.append("")
        lines.append(
            "**写作约束**：本节点 narration + NPC 对白 + options 的核心信息密度"
            "**必须围绕**此 foreground_goal。"
        )
    return "\n".join(lines)


def render_background_seeds(seeds: list[str]) -> str:
    """渲染 background_seeds 段."""
    lines = ["## 本节点要埋的 background_seeds（背景种子）"]
    lines.append("")
    if not seeds:
        lines.append("（本节点不埋任何种子）")
    else:
        for seed in seeds:
            lines.append(f"- `{seed}`")
        lines.append("")
        lines.append(
            "**写作约束**：seed 必须以**含蓄但有信息量**的方式埋在 narration 或 NPC 对白中——"
            "不要喧宾夺主、不要直接 lecture（说教）；让玩家自己注意到。"
        )
    return "\n".join(lines)


def render_npc_state(
    speaker_ref: str | None,
    npc_state: dict[str, Any] | None,
) -> str:
    """渲染 NPC 当前 state 注入段（含 relationship / dramatic_triggers 等）."""
    lines = ["## NPC 当前 state（来自状态机查询）"]
    lines.append("")
    if speaker_ref is None:
        lines.append("（本节点 speaker_ref=null，无 NPC 主讲——纯旁白节点）")
        return "\n".join(lines)
    lines.append(f"**主讲 NPC**: `{speaker_ref}`")
    if not npc_state:
        lines.append("")
        lines.append("（NPC state 字段未提供——按默认设定写作）")
    else:
        lines.append("")
        lines.append("**state 快照**：")
        lines.append("```json")
        lines.append(json.dumps(npc_state, ensure_ascii=False, indent=2))
        lines.append("```")
    return "\n".join(lines)


def render_node_skeleton(node: dict[str, Any]) -> str:
    """渲染节点骨架段——LLM 不修改的部分."""
    lines = ["## 节点骨架（不要修改 narration / options[].text 之外的字段）"]
    lines.append("")
    lines.append("```json")
    lines.append(json.dumps(node, ensure_ascii=False, indent=2))
    lines.append("```")
    return "\n".join(lines)


def build_node_user_message(
    *,
    node_skeleton: dict[str, Any],
    player_known_info: list[dict[str, Any]],
    foreground_goal: str | None,
    background_seeds: list[str],
    speaker_ref: str | None = None,
    npc_state: dict[str, Any] | None = None,
    all_known_info_summary: str | None = None,
) -> str:
    """拼接 user message 全文.

    Args:
        node_skeleton:        节点骨架 dict（含 node_id / type / speaker_ref / options 骨架）
        player_known_info:    Forward Planner 模块 B 输出（relevant_known_info）
        foreground_goal:      Forward Planner 模块 A 输出
        background_seeds:     Forward Planner 模块 A 输出
        speaker_ref:          NPC ID（可省，从 node_skeleton 推导）
        npc_state:            NPC 状态机当前 state 快照（optional；mini prototype 可省）
        all_known_info_summary: 自然语言摘要（不入 schema；可省）

    Returns:
        合成的 user message markdown 块
    """
    if speaker_ref is None:
        speaker_ref = node_skeleton.get("speaker_ref")

    sections = [
        render_player_known_info(
            player_known_info, all_known_info_summary=all_known_info_summary
        ),
        render_foreground_goal(foreground_goal),
        render_background_seeds(background_seeds),
        render_npc_state(speaker_ref, npc_state),
        render_node_skeleton(node_skeleton),
        "## 任务\n\n请按 system prompt 的输出 JSON 形态返回完成后的 Node 对象。",
    ]
    return "\n\n---\n\n".join(sections)


__all__ = [
    "render_player_known_info",
    "render_foreground_goal",
    "render_background_seeds",
    "render_npc_state",
    "render_node_skeleton",
    "build_node_user_message",
]
