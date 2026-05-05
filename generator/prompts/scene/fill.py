"""Fill-phase prompt extras (R2.6).

Builds the top-level markdown sections that
`scene_strategies.fill_skeleton` injects into each fill call's
`NodeRequirement.extra_user_context`. The blob targets the context
bleed-through observed in T-2.12 baseline_005 v3 (S2=0 reject — every
filled node's narration kept rewriting the opening "推开沉重的橡木门"):

  1. ``## 前面已生成节点的 narration 摘要`` — short preview of every
     sibling node already filled in this scene, so the LLM knows what
     opening environment / character entrance / props have already been
     described and stops repeating them.
  2. ``## 当前节点位置`` — beat tag, index/total, and node role
     (开场/中段/收束) plus per-role guidance on how detailed the
     narration should be.
  3. ``【硬约束 — context bleed-through 防御】`` — explicit do-not list
     for what each node's narration must avoid.

The helpers render plain markdown strings; placement (between the
SceneGraphContext block and the requirement block) is owned by
``context_assembler.assemble_context_block``'s ``extra_user_context``
branch.

Why a separate file: the few-shot block in ``prompts.scene.few_shot`` is
a static fixture; this module assembles per-call dynamic strings. Living
under ``prompts/scene/`` keeps the prompt-text family co-located.
"""
from __future__ import annotations

# Per-node narration preview cap. Long enough to identify which beat the
# node already wrote, short enough that 10–15 entries still fit
# comfortably alongside the rest of the prompt.
_NARRATION_PREVIEW_CHARS = 80
# Hard ceiling on the rendered summary body (excluding the section
# header). When per-node previews already total more than this, we fall
# back to keeping only the most recent N nodes — bleed-through risk is
# loudest from things written one or two nodes ago, so recency wins.
_SUMMARY_TOTAL_CHAR_BUDGET = 2000
_SUMMARY_RECENT_FALLBACK_KEEP = 5


def _preview_line(node_id: str, narration: str) -> str:
    """One line of the summary section: ``- {node_id}: {narration[:80]}...``.

    Newlines inside narration are flattened to spaces so the bullet stays
    on one line in the rendered prompt.
    """
    body = (narration or "").strip().replace("\n", " ")
    if len(body) > _NARRATION_PREVIEW_CHARS:
        body = body[:_NARRATION_PREVIEW_CHARS] + "..."
    return f"- {node_id}: {body}"


def render_previously_filled_summary(
    filled_so_far: list[tuple[str, str]],
) -> str:
    """Render the ``## 前面已生成节点的 narration 摘要`` top-level section.

    ``filled_so_far`` is the ordered list of ``(node_id, narration)``
    pairs for nodes the fill phase has already produced. Empty list →
    empty string (the first fill node skips this section entirely so the
    prompt doesn't include an empty stub the LLM has to step over).

    When the joined preview body would exceed
    ``_SUMMARY_TOTAL_CHAR_BUDGET`` chars, we fall back to the most recent
    ``_SUMMARY_RECENT_FALLBACK_KEEP`` entries. This keeps bleed-through
    defence focused on the immediately preceding nodes (where the LLM is
    most likely to copy-paste setting setup) and prevents the prompt from
    ballooning on long scenes.
    """
    if not filled_so_far:
        return ""

    lines = [_preview_line(nid, narr) for nid, narr in filled_so_far]
    body = "\n".join(lines)
    if len(body) > _SUMMARY_TOTAL_CHAR_BUDGET:
        recent = filled_so_far[-_SUMMARY_RECENT_FALLBACK_KEEP:]
        lines = [_preview_line(nid, narr) for nid, narr in recent]
        body = "\n".join(lines)

    return "## 前面已生成节点的 narration 摘要\n\n" + body


def _node_role(*, index: int, total: int) -> str:
    """开场 (first) / 收束 (last) / 中段 (middle).

    Used both to label this node and to gate which per-role narration
    advice the prompt emphasises. Single-node skeletons (total == 1)
    collapse to 开场 — that's the only sensible role for a lone node.
    """
    if index == 0:
        return "开场"
    if total > 0 and index == total - 1:
        return "收束"
    return "中段"


def render_beat_position(*, beat: str, index: int, total: int) -> str:
    """Render the ``## 当前节点位置`` section + per-role narration tips.

    The role-specific tips follow the same lengths the gold scene
    ``铁誓驿站`` (few-shot reference) uses: opening node carries the
    setting prose, middle nodes are dialogue-led with terse narration,
    and the closing node holds short closure beats.
    """
    role = _node_role(index=index, total=total)
    return (
        "## 当前节点位置\n\n"
        f"- 当前节点 beat tag：`{beat}`\n"
        f"- 在 skeleton 中位置：第 {index + 1}/{total} 个节点\n"
        f"- 节点角色：{role}\n\n"
        "【按位置写 narration 提示】\n\n"
        "- **开场节点**（第 1 个）：narration 可详细描述场景设定 + 角色出场 + 时间氛围"
        "（这是唯一允许 narration 较长的节点）。\n"
        "- **中段节点**：narration 极简（≤ 1 句），只突出本 beat 的新进展；"
        "不要重复开场已描述的内容。\n"
        "- **收束节点**（最后一个）：narration 给出 closure（结局氛围 / 角色态度 / "
        "主题回响），不要重复中段已说的。"
    )


def render_bleed_through_guard() -> str:
    """Render the ``【硬约束 — context bleed-through 防御】`` block.

    Static text — the constraint is per-scene-stable, not per-node, but
    we render it on every fill call so the LLM doesn't drift after
    seeing many response/prompt cycles in a single scene.
    """
    return (
        "【硬约束 — context bleed-through 防御】\n\n"
        "- 本节点 narration 长度严格 ≤ 2 句话\n"
        "- **不要重复**前面节点已描述的场景设定（开场环境 / 主要角色出场 / "
        "时间地点 / 主体物品）\n"
        "- 本节点 narration 只描述**本 beat 的新进展 / 新动作 / 新信息**\n"
        "- 如果本节点是中段或收束节点，narration 可以更简短（1 句即可），"
        "让 dialogue 和 option 承担表达"
    )


def render_fill_extras(
    *,
    filled_so_far: list[tuple[str, str]],
    beat: str,
    index: int,
    total: int,
) -> str:
    """Compose previously_filled + beat_position + bleed-through guard.

    First-node case (``index == 0`` ⇒ ``filled_so_far == []``) emits only
    beat_position + guard — the previously-filled summary is intentionally
    skipped because there's nothing yet, and rendering an empty section
    would just be visual noise the LLM has to step over (R2.6 §3).
    """
    sections: list[str] = []
    summary = render_previously_filled_summary(filled_so_far)
    if summary:
        sections.append(summary)
    sections.append(render_beat_position(beat=beat, index=index, total=total))
    sections.append(render_bleed_through_guard())
    return "\n\n".join(sections)
