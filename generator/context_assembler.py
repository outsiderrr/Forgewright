"""B+ context assembly for single-node generation (T-1.6).

What "B+" means here: the LLM sees the *parent chain only* (up to 3 ancestors
of the node being generated), the scene/location card, the involved character
cards, and current faction-clock values. It does **not** see the rest of the
graph. This is the line we're holding against drifting toward "C" (whole-graph
context), which would explode token cost and make generation unreproducible.

`assemble_context_block` renders the context as a markdown-flavoured prompt
fragment. Stage-0 ontology stubs may leave card fields empty; the renderer
degrades gracefully — every section announces what it's missing rather than
failing the call.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class GraphContext:
    """B+ context window: scene + parent chain + characters + clocks.

    `parent_chain` is at most 3 entries (most-recent-first or oldest-first is a
    caller convention — assemble_context_block treats the list as already
    ordered chronologically: index 0 = oldest of the three ancestors,
    index -1 = the immediate parent).

    `location_candidates` lists 1–3 ontology-defined locations the model is
    allowed to pick its `location_ref` from. `primary_location_ref` is the
    suggested default when the scene has a single dominant location; leave it
    `None` if the caller does not want to bias the choice. Stage 2 §2.8 unified
    this field name with SceneGraphContext so scene-level and node-level
    contexts share one shape.

    `active_clocks` and `system_time` (T-2.5 C-phase, review 4.2) carry
    ADR-017 clock state and the `world.scene_count` / `world.long_rest_count`
    system-time pair into node-level prompts. Both default empty so existing
    T-1.6 callers (`generate_node` solo, no scene scheduler) keep working
    unchanged — the renderer omits the section when both are empty.
    `faction_clocks` (legacy `dict[str, int]`) is preserved so already-passing
    tests don't shift; it renders the legacy "阵营时钟当前值" section.
    """

    scene_anchor: str
    location_candidates: list[dict] = field(default_factory=list)
    primary_location_ref: str | None = None
    parent_chain: list[dict] = field(default_factory=list)
    involved_characters: list[dict] = field(default_factory=list)
    faction_clocks: dict[str, int] = field(default_factory=dict)
    active_clocks: list[dict] = field(default_factory=list)
    system_time: dict | None = None


@dataclass
class NodeRequirement:
    """What the caller wants out of this single generation.

    `allowed_targets` (T-2.5) constrains the legal `option.target_node_id`
    set for this node. `None` (default) = unconstrained (single-node
    generation; T-1.6 backwards compat). Non-None = the caller (typically
    `scene_strategies.fill_skeleton`) has already drawn the graph
    skeleton's edges and any `target_node_id` outside this list will be
    rejected as schema_invalid and re-fed to the LLM.
    """

    node_type: Literal["dialogue", "end"]
    expected_speaker_ref: str | None
    narrative_intent: str
    allowed_targets: list[str] | None = None


def assemble_context_block(
    graph_context: GraphContext,
    node_requirement: NodeRequirement,
) -> str:
    """Render the context + requirement as a structured markdown prompt fragment.

    Order is fixed (scene → location → parent chain → characters → clocks →
    requirement) so prompt hashes are stable across runs with identical inputs.
    """
    parts: list[str] = []

    parts.append("## 场景锚点")
    parts.append(f"- scene_anchor: `{graph_context.scene_anchor}`")

    parts.append("")
    parts.append("## 候选地点")
    if graph_context.location_candidates:
        parts.append(
            "下列是本体已定义的候选地点；`location_ref` **必须**取自其中的"
            " `location_id` 字段，不要发明候选外的地点。"
        )
        if graph_context.primary_location_ref is not None:
            parts.append(f"- 主地点（推荐默认 `location_ref`）：`{graph_context.primary_location_ref}`")
        for cand in graph_context.location_candidates:
            parts.append("```json")
            parts.append(json.dumps(cand, ensure_ascii=False, indent=2))
            parts.append("```")
    else:
        parts.append("（本体桩未提供候选地点——按 scene_anchor 自行推断基本氛围）")

    parts.append("")
    parts.append("## 父链（按时间顺序，最近的父节点在最后）")
    if graph_context.parent_chain:
        for idx, parent in enumerate(graph_context.parent_chain):
            parts.append(f"### 父节点 {idx + 1}")
            parts.append("```json")
            parts.append(json.dumps(parent, ensure_ascii=False, indent=2))
            parts.append("```")
    else:
        parts.append("（无父节点——本节点为入口节点位置）")

    parts.append("")
    parts.append("## 出场角色卡")
    if graph_context.involved_characters:
        for char in graph_context.involved_characters:
            parts.append("```json")
            parts.append(json.dumps(char, ensure_ascii=False, indent=2))
            parts.append("```")
    else:
        parts.append("（本节点无角色卡输入——若有 speaker_ref 请按本体既有设定保守落笔）")

    parts.append("")
    parts.append("## 阵营时钟当前值")
    if graph_context.faction_clocks:
        for clock_id, ticks in sorted(graph_context.faction_clocks.items()):
            parts.append(f"- `{clock_id}`: {ticks}")
    else:
        parts.append("（阶段 0 本体桩未注册任何阵营时钟）")

    # T-2.5 C-phase (review 4.2): scene-level fill prompts must surface
    # active_clocks (ADR-017) and system_time (world.scene_count /
    # world.long_rest_count) so node text reflects current world state.
    # Render only when non-empty — node-level T-1.6 callers leave both
    # blank and don't see this section, keeping their prompt hashes stable.
    if graph_context.active_clocks:
        parts.append("")
        parts.append("## 活跃时钟 (`active_clocks`)")
        parts.append(
            "对白可以暗示压力但不要直接写出 `ticks_filled` 数字；填充节点的"
            " `effects` / `condition` 中的 path 仍需落入 ADR-016 命名空间。"
        )
        for clock in graph_context.active_clocks:
            parts.append("```json")
            parts.append(json.dumps(clock, ensure_ascii=False, indent=2))
            parts.append("```")

    if graph_context.system_time:
        parts.append("")
        parts.append("## 系统时间 (`system_time`)")
        parts.append(
            f"- `world.scene_count`: {graph_context.system_time.get('scene_count', 0)}"
        )
        parts.append(
            f"- `world.long_rest_count`: {graph_context.system_time.get('long_rest_count', 0)}"
        )

    parts.append("")
    parts.append("## 本次生成要求")
    parts.append(f"- 节点类型 (`type`): `{node_requirement.node_type}`")
    if node_requirement.expected_speaker_ref is None:
        parts.append("- 说话者 (`speaker_ref`): `null`（旁白）")
    else:
        parts.append(f"- 说话者 (`speaker_ref`): `{node_requirement.expected_speaker_ref}`")
    parts.append(f"- 叙事意图: {node_requirement.narrative_intent}")
    if node_requirement.node_type == "dialogue":
        parts.append("- `options` 必须非空（3–6 个，覆盖不同性格倾向）")
    else:
        parts.append("- `options` 必须为空数组（end 节点不可继续）")

    if node_requirement.allowed_targets is not None:
        parts.append("")
        parts.append("## target_node_id 硬约束（skeleton-first fill 阶段）")
        if node_requirement.allowed_targets:
            allowed = ", ".join(f"`{t}`" for t in node_requirement.allowed_targets)
            parts.append(
                f"- 本节点每个 `option.target_node_id` **必须**取自下列集合：{allowed}"
            )
            parts.append(
                "- 集合外的 target_node_id = schema_invalid（图骨架已锁定边连接，禁止凭空指向新节点）"
            )
        else:
            parts.append(
                "- 本节点为 end 节点，`options` 必须为空数组（无 target_node_id 可写）"
            )

    return "\n".join(parts)
