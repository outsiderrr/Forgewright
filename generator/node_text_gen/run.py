"""Run node generation（跑节点级文本生成）— T-3Y-1 子 goal 2.

端到端最小路径：render prompt → provider.generate → 解析 JSON → 返回 dict.
生产路径（goal 3 dry-run）会在此之上加 budget / retry / 错误处理。

T-3Y-1 mini prototype 阶段保持极简——单次调用、无 retry、JSON 解析失败抛 ValueError.
"""
from __future__ import annotations

import json
from typing import Any, Protocol

from generator.node_text_gen.render import render_node_prompt


class _NodeProvider(Protocol):
    """节点级生成所需的最小 provider 契约（mini prototype 用）.

    实现侧：T-3Y-1 单元测试用 MockLLMProvider；goal 3 dry-run 用
    generator.providers.poloai 适配 GPT-5.5-pro.
    """

    def generate(self, *, system: str, user: str) -> str: ...


def run_node_generation(
    *,
    provider: _NodeProvider,
    node_skeleton: dict[str, Any],
    player_known_info: list[dict[str, Any]],
    foreground_goal: str | None,
    background_seeds: list[str],
    speaker_ref: str | None = None,
    npc_state: dict[str, Any] | None = None,
    all_known_info_summary: str | None = None,
) -> dict[str, Any]:
    """跑一次节点生成流水线.

    Args:
        provider:             实现 generate(system, user) -> str 的 LLM provider
        node_skeleton:        节点骨架
        player_known_info:    Forward Planner 模块 B 输出
        foreground_goal:      Forward Planner 模块 A 输出
        background_seeds:     Forward Planner 模块 A 输出
        其余 kwargs:          见 render_node_prompt

    Returns:
        provider 返回的 JSON 字符串解析为 dict

    Raises:
        ValueError: provider 返回非 valid JSON 时
    """
    prompt = render_node_prompt(
        node_skeleton=node_skeleton,
        player_known_info=player_known_info,
        foreground_goal=foreground_goal,
        background_seeds=background_seeds,
        speaker_ref=speaker_ref,
        npc_state=npc_state,
        all_known_info_summary=all_known_info_summary,
    )
    raw = provider.generate(system=prompt["system"], user=prompt["user"])
    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(
            f"provider 返回非 valid JSON：{e.msg} (line {e.lineno}, col {e.colno})；"
            f"raw 前 200 字符 = {raw[:200]!r}"
        ) from e


__all__ = ["run_node_generation"]
