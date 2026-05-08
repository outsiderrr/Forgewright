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

T-2.6 adds `SceneGraphContext` (scene-level sibling of `GraphContext`) +
`assemble_scene_context_block`. It is the structured intermediate
`generate_scene` builds before unpacking it into
`scene_strategies.generate_scene_skeleton_first`. Field names align with
STAGE_2_TASKS §2.8 (active_clocks / location_candidates /
primary_location_ref) so scene-level and node-level contexts share one
shape.

T-3.3 (ADR-024 + F3 修订) adds long-conversation-consistency C-tier on
`SceneGraphContext` only — `prior_scene_summaries` is the prompt-side
window into earlier scenes' digests, capped at 5 entries with a
"recent + chapter/act boundary" heuristic; `token_metrics` records the
post-truncation accounting (count / hashes / token estimate /
truncation_reason) so T-3.5 can write the same numbers into the
content_dependency_index sidecar without re-deriving them. Node-level
`GraphContext` is intentionally untouched — scene-level generation never
wires through node-level context, so injecting summaries there would be
work that nothing reads (F3).
"""
from __future__ import annotations

import hashlib
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

    `extra_user_context` (R2.6) is a free-form markdown blob the
    scene-level fill caller injects between the SceneGraphContext block
    (system_time / active_clocks) and the `## 本次生成要求` requirement
    block. Used to combat context bleed-through observed in T-2.12
    baseline_005 v3 (S2=0 reject — every node's narration kept rewriting
    the opening "推开沉重的橡木门"): fill_skeleton renders summaries of
    previously filled nodes' narration plus a per-node beat-position
    annotation so the LLM stops repeating opening setup. T-1.6 single-node
    callers leave it None and see no change to their prompts.
    """

    node_type: Literal["dialogue", "end"]
    expected_speaker_ref: str | None
    narrative_intent: str
    allowed_targets: list[str] | None = None
    extra_user_context: str | None = None


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

    # R2.6: scene-level fill caller can inject top-level markdown sections
    # here (between the SceneGraphContext block above and the requirement
    # block below) — typically the previously-filled-narration summary +
    # beat-position annotation built by `prompts.scene.fill.render_fill_extras`.
    # Skipped silently when None / empty so T-1.6 single-node callers see
    # no change to their prompt structure.
    if node_requirement.extra_user_context:
        parts.append("")
        parts.append(node_requirement.extra_user_context)

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


# ---------------------------------------------------------------------------
# T-2.6 — scene-level context
# ---------------------------------------------------------------------------


# T-3.3 (ADR-024). Hard cap on how many prior-scene digests reach the
# prompt. The number is taken straight from §3.3 ("每场景 prompt 注入
# ≤ 5 条 prior_scene_summaries（避免 prompt 膨胀）"). When the caller
# supplies more, `truncate_prior_scene_summaries` keeps recent entries
# plus chapter/act boundaries (whichever fit inside the cap).
PRIOR_SCENE_SUMMARY_CAP = 5

# Same 4 chars/token convention used in `generate_node` / `generate_scene`
# / `scene_strategies` so token-budget numbers compare across modules.
# tiktoken would be more accurate but is not currently a project
# dependency; the figure is a *budget guard* not a billing line.
_PROMPT_CHARS_PER_TOKEN = 4


@dataclass
class PriorSceneSummary:
    """One earlier scene's digest, as it travels into the prompt.

    `summary` is the human-authored or LLM-drafted ≤ 200 中文字符 / ≤ 800
    英文字符 prose. Length is enforced by `scene_summary_writer` at
    write-time, not here — this dataclass is the wire format and stays
    permissive so unit tests can construct edge-case fixtures without
    fighting the validator.

    `key_state_paths` lists the ADR-016-namespaced paths the source scene
    actually wrote (extracted from its `effects` / `on_enter_effects`
    bags by `scene_summary_writer`). They land verbatim in the rendered
    prompt block so the LLM can refer back to "what already changed".

    `chapter_id` / `act_id` are optional because not every scene knows
    its parent chapter/act yet (T-3.5 will populate them via the
    content_dependency_index sidecar). When present they participate in
    the boundary-preservation heuristic inside
    `truncate_prior_scene_summaries` — see ADR-024 §"启发式裁剪".
    """

    scene_id: str
    summary: str
    key_state_paths: list[str]
    chapter_id: str | None = None
    act_id: str | None = None


@dataclass
class TokenMetrics:
    """Post-truncation accounting for the prior_scene_summaries injection.

    Lives on `SceneGraphContext`; T-3.5 will copy the same four fields into
    the per-scene `content_dependency_index` sidecar (ADR-023 / ADR-024).
    Computing it at SceneGraphContext build time means downstream callers
    don't have to re-run the truncation/hashing logic.

      * `prompt_token_estimate` — chars-of-rendered-summary-block / 4.
        Specifically the cost the summaries contribute to the prompt;
        not the full prompt's token count (the rest of the prompt is a
        moving target T-3.3 doesn't try to estimate). Zero when no
        summaries land.
      * `summaries_injected_count` — 0..PRIOR_SCENE_SUMMARY_CAP. The
        LLM-visible count, after truncation.
      * `summary_source_hashes` — SHA-256 of each kept summary's
        `(scene_id, summary, key_state_paths)` triple, in injection
        order. Lets reviewers verify the prompt-bound digest matches
        what's on disk — drift between sidecar and prompt is what the
        ADR-024 metrics hook is meant to surface.
      * `truncation_reason` — one of:
          - `None` (no summaries supplied)
          - `"no_truncation"` (≤ 5 entries; everything kept)
          - `"kept_recent_with_boundary"` (> 5; cap honoured boundaries)
          - `"kept_recent_only"` (> 5; only recency mattered)
    """

    prompt_token_estimate: int = 0
    summaries_injected_count: int = 0
    summary_source_hashes: list[str] = field(default_factory=list)
    truncation_reason: str | None = None


@dataclass
class SceneGraphContext:
    """Scene-level context (T-2.6 / STAGE_2_TASKS §2.8).

    Built by `generate_scene` from the ontology + caller-supplied scene
    setting; unpacked into `scene_strategies.generate_scene_skeleton_first`.
    Field names match the unified vocabulary established in §2.8:

      * `active_clocks` (not `faction_clocks`) — covers world / faction /
        environmental scopes (ADR-017).
      * `location_candidates: list[dict]` (not `location_card: dict`) —
        the LLM picks one `location_id` per node; `primary_location_ref`
        names the dominant location when one exists.
      * `relations_matrix` is the participating-characters' relations
        already filtered down to `narrative_weight in {core, minor}`
        (ADR-018) — `context_only` weights are dropped before reaching
        the prompt because they are anchors, not dramaturgy.

    Both `chapter_ref` and `primary_location_ref` are nullable for early-
    stage scenes that don't have a chosen chapter / dominant location yet.
    `system_time` defaults to a `{scene_count: 0, long_rest_count: 0}`
    fallback when the ontology omits it (Stage 0 stub).

    T-3.3: `prior_scene_summaries` carries the **input** list (caller-
    supplied; can exceed `PRIOR_SCENE_SUMMARY_CAP`). The render layer in
    `scene_strategies` re-runs `truncate_prior_scene_summaries` to pick
    the actually-injected subset — the same call shape used to populate
    `token_metrics` here, so the prompt and the sidecar describe the
    same kept set. `token_metrics` is the post-truncation snapshot
    (count, hashes, token estimate, reason). Both default to empty so
    pre-T-3.3 scene tests keep passing unchanged.
    """

    scene_anchor: str
    chapter_ref: str | None
    location_candidates: list[dict]
    primary_location_ref: str | None
    participating_characters: list[dict]
    relations_matrix: list[dict]
    active_clocks: list[dict]
    system_time: dict
    target_beats: list[str]
    prior_scene_summaries: list[PriorSceneSummary] = field(default_factory=list)
    token_metrics: TokenMetrics = field(default_factory=TokenMetrics)


def assemble_scene_context_block(
    scene_ctx: SceneGraphContext,
    scene_setting,  # SceneSetting (forward ref — defined in scene_strategies)
) -> str:
    """Render the scene-level context as a markdown preview.

    This is *not* the prompt sent to the LLM — `scene_strategies` owns the
    skeleton/fill prompt rendering. `assemble_scene_context_block` is the
    inspectable counterpart used by `generate_scene` for logging / debug
    surfaces and by the §2.8 sanity test that asserts every contracted
    field actually lands in the assembled context.

    Order is fixed (scene → chapter → location → characters → relations →
    clocks → system_time → beats) so block hashes are stable across runs
    with identical inputs.
    """
    parts: list[str] = []

    parts.append("## 场景设定")
    parts.append(f"- `scene_anchor`: `{scene_ctx.scene_anchor}`")
    if scene_ctx.chapter_ref:
        parts.append(f"- `chapter_ref`: `{scene_ctx.chapter_ref}`")
    else:
        parts.append("- `chapter_ref`: （未指定 chapter）")
    parts.append(
        f"- 节点数预估：{scene_setting.expected_node_count_min}–"
        f"{scene_setting.expected_node_count_max}"
    )

    parts.append("")
    parts.append("## 候选地点 (`location_candidates`)")
    if scene_ctx.primary_location_ref:
        parts.append(f"- 主地点 (`primary_location_ref`): `{scene_ctx.primary_location_ref}`")
    if scene_ctx.location_candidates:
        for cand in scene_ctx.location_candidates:
            parts.append("```json")
            parts.append(json.dumps(cand, ensure_ascii=False, indent=2))
            parts.append("```")
    else:
        parts.append("（本体未给候选地点）")

    parts.append("")
    parts.append("## 出场角色卡 (`participating_characters`)")
    if scene_ctx.participating_characters:
        for card in scene_ctx.participating_characters:
            parts.append("```json")
            parts.append(json.dumps(card, ensure_ascii=False, indent=2))
            parts.append("```")
    else:
        parts.append("（无角色卡——只能用旁白生成）")

    parts.append("")
    parts.append("## 关系矩阵 (`relations_matrix`，已按 narrative_weight 过滤至 core+minor)")
    if scene_ctx.relations_matrix:
        for rel in scene_ctx.relations_matrix:
            parts.append("```json")
            parts.append(json.dumps(rel, ensure_ascii=False, indent=2))
            parts.append("```")
    else:
        parts.append("（无 core/minor 关系——出场角色之间无强制戏剧义务）")

    parts.append("")
    parts.append("## 活跃时钟 (`active_clocks`)")
    if scene_ctx.active_clocks:
        for clock in scene_ctx.active_clocks:
            parts.append("```json")
            parts.append(json.dumps(clock, ensure_ascii=False, indent=2))
            parts.append("```")
    else:
        parts.append("（无活跃时钟）")

    parts.append("")
    parts.append("## 系统时间 (`system_time`)")
    parts.append(
        f"- `world.scene_count`: {scene_ctx.system_time.get('scene_count', 0)}"
    )
    parts.append(
        f"- `world.long_rest_count`: {scene_ctx.system_time.get('long_rest_count', 0)}"
    )

    parts.append("")
    parts.append("## 节拍序列 (`target_beats`)")
    if scene_ctx.target_beats:
        for idx, beat in enumerate(scene_ctx.target_beats, start=1):
            parts.append(f"{idx}. {beat}")
    else:
        parts.append("（调用方未给节拍序列；strategy 会按 scene_anchor 自行推断）")

    # T-3.3 (ADR-024): debug surface for the long-conversation-consistency
    # injection. Mirrors what the strategy actually feeds the LLM
    # (post-truncation), so a sidecar audit can compare on-disk hashes
    # against the rendered block here. Skipped silently when no summaries
    # were supplied so pre-T-3.3 fixture goldens stay byte-identical.
    if scene_ctx.prior_scene_summaries:
        kept, _ = truncate_prior_scene_summaries(scene_ctx.prior_scene_summaries)
        parts.append("")
        parts.append(render_prior_scene_summaries_block(kept))

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# T-3.3 — long-conversation-consistency C-tier helpers (ADR-024)
# ---------------------------------------------------------------------------


def truncate_prior_scene_summaries(
    summaries: list[PriorSceneSummary],
) -> tuple[list[PriorSceneSummary], str | None]:
    """Cap the prior_scene_summaries list at `PRIOR_SCENE_SUMMARY_CAP`.

    Returns ``(kept, truncation_reason)``. Truncation strategy follows
    ADR-024 §"启发式裁剪":

      1. ``len <= 5`` → keep all; reason ``"no_truncation"``.
      2. Otherwise, **boundary scenes are preserved first** — every
         entry whose `chapter_id` or `act_id` differs from the
         previous non-`None` value is pinned. Remaining slots (up to
         the cap) are filled with the most-recent **non-boundary**
         entries.
      3. If boundaries themselves overflow the cap (rare; only when
         the history spans many short chapters), the most-recent
         boundaries win and older ones are dropped.

    Reason classification in the > 5 path: ``"kept_recent_with_boundary"``
    when *any* boundary survived the cap, else ``"kept_recent_only"``.
    Empty input → ``(_, None)`` so a missing-summaries scene doesn't
    look like it was actively truncated.
    """
    if not summaries:
        return [], None
    n = len(summaries)
    if n <= PRIOR_SCENE_SUMMARY_CAP:
        return list(summaries), "no_truncation"

    boundary_indices: set[int] = set()
    prev_chapter: str | None = None
    prev_act: str | None = None
    for idx, summary in enumerate(summaries):
        chapter_id = summary.chapter_id
        act_id = summary.act_id
        is_boundary = False
        if chapter_id is not None and chapter_id != prev_chapter:
            is_boundary = True
        if act_id is not None and act_id != prev_act:
            is_boundary = True
        if is_boundary:
            boundary_indices.add(idx)
        if chapter_id is not None:
            prev_chapter = chapter_id
        if act_id is not None:
            prev_act = act_id

    if len(boundary_indices) >= PRIOR_SCENE_SUMMARY_CAP:
        # Even boundaries overflow the cap — keep the most recent
        # ``PRIOR_SCENE_SUMMARY_CAP`` boundaries, drop older ones.
        kept_indices = sorted(
            sorted(boundary_indices, reverse=True)[:PRIOR_SCENE_SUMMARY_CAP]
        )
    else:
        # Boundaries fit; fill remaining slots with the most-recent
        # non-boundary entries so the LLM still sees the freshest
        # narrative beats alongside the structural anchors.
        needed = PRIOR_SCENE_SUMMARY_CAP - len(boundary_indices)
        non_boundary = [i for i in range(n) if i not in boundary_indices]
        fill = sorted(non_boundary, reverse=True)[:needed]
        kept_indices = sorted(boundary_indices | set(fill))

    kept = [summaries[i] for i in kept_indices]
    saw_boundary_in_kept = bool(boundary_indices & set(kept_indices))
    reason = (
        "kept_recent_with_boundary"
        if saw_boundary_in_kept
        else "kept_recent_only"
    )
    return kept, reason


def render_prior_scene_summaries_block(
    kept_summaries: list[PriorSceneSummary],
) -> str:
    """Render the ``## 前置场景概要`` markdown section.

    Caller should pass the *post-truncation* list (the output of
    `truncate_prior_scene_summaries`). Empty input returns an empty
    string so the strategy can use a simple ``if rendered: parts.append``
    check without a section-header gap.

    Format (one bullet per kept summary, in caller-supplied order):

        ## 前置场景概要（按时间顺序）

        - [scene_id] {summary}; 关键状态写入：path1, path2

    Newlines inside ``summary`` are flattened to spaces so each bullet
    stays single-line in the rendered prompt.
    """
    if not kept_summaries:
        return ""
    parts: list[str] = ["## 前置场景概要（按时间顺序）", ""]
    for summary in kept_summaries:
        body = (summary.summary or "").strip().replace("\n", " ")
        if summary.key_state_paths:
            paths = ", ".join(summary.key_state_paths)
        else:
            paths = "（无）"
        parts.append(f"- [{summary.scene_id}] {body}; 关键状态写入：{paths}")
    return "\n".join(parts)


def _summary_source_hash(summary: PriorSceneSummary) -> str:
    """SHA-256 of a stable serialisation of the summary's user-visible bits.

    `chapter_id` / `act_id` are intentionally excluded — they're used by
    the truncation heuristic but don't reach the prompt body, so a
    sidecar consumer cross-checking "what the LLM actually saw" only
    needs the prompt-visible triple `(scene_id, summary, key_state_paths)`
    to hash.
    """
    raw = (
        summary.scene_id
        + "\x1f"
        + summary.summary
        + "\x1f"
        + "\x1e".join(summary.key_state_paths)
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def compute_prior_summary_token_metrics(
    summaries: list[PriorSceneSummary],
) -> TokenMetrics:
    """Compute the post-truncation `TokenMetrics` view for a summary list.

    Internally calls `truncate_prior_scene_summaries` so both the
    metrics-on-context and the strategy-side render share identical
    truncation logic. `prompt_token_estimate` is the rendered block's
    char count divided by `_PROMPT_CHARS_PER_TOKEN` (the same crude
    convention used elsewhere in the generator); zero when no summary
    actually lands.
    """
    kept, reason = truncate_prior_scene_summaries(summaries)
    if not kept:
        return TokenMetrics(
            prompt_token_estimate=0,
            summaries_injected_count=0,
            summary_source_hashes=[],
            truncation_reason=reason,
        )
    rendered = render_prior_scene_summaries_block(kept)
    estimate = max(0, len(rendered) // _PROMPT_CHARS_PER_TOKEN)
    hashes = [_summary_source_hash(s) for s in kept]
    return TokenMetrics(
        prompt_token_estimate=estimate,
        summaries_injected_count=len(kept),
        summary_source_hashes=hashes,
        truncation_reason=reason,
    )
