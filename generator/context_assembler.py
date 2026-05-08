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

    **Schema alignment** (PR #44 review §3.1, B-phase finding 🔴):
    `truncation_reason` matches `content_dependency_index.schema.json`'s
    enum exactly; `summary_source_hashes` carry the `sha256:` prefix the
    schema requires. Drift between this dataclass and the sidecar
    schema would force T-3.5 to translate at write time — instead we
    align here once.

      * `prompt_token_estimate` — chars-of-rendered-prompt-text / 4.
        Computed by `compute_prior_summary_token_metrics`; the caller
        passes `additional_chars` (system prompt + scene context block
        chars) so the estimate reflects the full SceneGraphContext-side
        prompt the LLM will see, not just the summary block. Per-node
        fill prompts add variance that's only knowable at fill time;
        T-3.5 may refine this number at sidecar-write time once those
        prompts have been rendered.
      * `summaries_injected_count` — 0..PRIOR_SCENE_SUMMARY_CAP. The
        LLM-visible count, after truncation.
      * `summary_source_hashes` — `sha256:<hex>` digest of each kept
        summary's `(scene_id, summary, key_state_paths)` triple, in
        injection order. Lets reviewers verify the prompt-bound digest
        matches what's on disk.
      * `truncation_reason` — non-nullable, one of (per schema enum):
          - `"none"` — no truncation (≤ 5 entries or empty input)
          - `"summaries_over_5"` — input > 5; cap-driven truncation
            (boundary preservation collapses to this bucket; the
            boundary signal can be reconstructed from
            `summary_source_hashes` if needed)
          - `"token_budget"` — reserved for a future token-budget gate
          - `"manual_override"` — reserved for an author-pinned subset
    """

    prompt_token_estimate: int = 0
    summaries_injected_count: int = 0
    summary_source_hashes: list[str] = field(default_factory=list)
    truncation_reason: str = "none"


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
) -> tuple[list[PriorSceneSummary], str]:
    """Cap the prior_scene_summaries list at `PRIOR_SCENE_SUMMARY_CAP`.

    Returns ``(kept, truncation_reason)``. The reason matches
    `content_dependency_index.schema.json`'s enum exactly (PR #44
    review §3.1):

      * ``"none"`` — empty input, or ``len <= 5`` (no cap-driven drop).
      * ``"summaries_over_5"`` — input > 5 entries; this single bucket
        covers both boundary-preserving and recency-only paths because
        the schema only distinguishes the cap-trigger reason. The
        boundary signal collapses but stays reconstructable from
        `summary_source_hashes` if a downstream tool needs it.
      * ``"token_budget"`` / ``"manual_override"`` are reserved for
        future T-3.5 paths (token-budget gate, author-pinned subset).

    Truncation strategy follows ADR-024 §"启发式裁剪":

      1. ``len <= 5`` → keep all; reason ``"none"``.
      2. Otherwise, **boundary scenes are preserved first** — every
         entry whose `chapter_id` or `act_id` differs from the
         previous non-`None` value is pinned. Remaining slots (up to
         the cap) are filled with the most-recent **non-boundary**
         entries.
      3. If boundaries themselves overflow the cap (rare; only when
         the history spans many short chapters), the most-recent
         boundaries win and older ones are dropped.
    """
    if not summaries:
        return [], "none"
    n = len(summaries)
    if n <= PRIOR_SCENE_SUMMARY_CAP:
        return list(summaries), "none"

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
    return kept, "summaries_over_5"


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
    """`sha256:<hex>` digest of a stable serialisation of the summary's
    user-visible bits.

    The ``sha256:`` prefix matches the pattern
    ``content_dependency_index.schema.json`` enforces on
    `summary_source_hashes` items (PR #44 review §3.1).

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
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


# ---------------------------------------------------------------------------
# T-3.5 — GenerationDependencyTrace (ADR-023 / F5)
# ---------------------------------------------------------------------------


@dataclass
class GenerationDependencyTrace:
    """Over-approx accumulator for dep_index sidecar writes (ADR-023 / F5).

    Live trace populated by `generate_scene` while it resolves the
    SceneGraphContext + walks the assembled graph's effects. T-3.5's
    `dep_index_writer.write_sidecar` consumes this dataclass and projects
    it into the on-disk `<scene>.deps.json` shape (sorted lists for
    `set` fields, `sha256:`-prefixed prompt-template hash, etc.).

    Why a separate accumulator (not a method on SceneGraphContext): the
    sidecar's read-side fields (`ontology_ids_read` / `state_paths_read`
    / `visual_asset_ids_referenced` / `clock_ids_referenced`) are
    over-approxed at *context-assembly* time — i.e. before the LLM runs.
    The write-side field (`state_paths_written`) is exact, derived from
    the assembled graph's effect bags after generation succeeds. Both
    feeds end up in the same dataclass so the writer has one input.

    `prompt_template_files` is a list of source paths the writer hashes
    into `prompt_template_hash` (sha256 of concatenated bytes; ADR-023
    field). The list is the *files actually rendered into the prompt for
    this scene* — typically `prompts/scene/system.py` + `prompts/scene/
    fill.py` + `prompts/scene/few_shot.py`. Order matters: the hash is
    over the concatenated bytes in caller-supplied order so re-running
    with the same prompt set produces a stable hash.

    `scene_history_referenced` mirrors the on-disk schema field — it is
    populated from `prior_scene_summaries[*].scene_id` after truncation,
    so the sidecar records the IDs the LLM actually saw (not the full
    pre-truncation input).
    """

    ontology_ids_read: set[str] = field(default_factory=set)
    state_paths_read: set[str] = field(default_factory=set)
    state_paths_written: set[str] = field(default_factory=set)
    visual_asset_ids_referenced: set[str] = field(default_factory=set)
    clock_ids_referenced: set[str] = field(default_factory=set)
    prompt_template_files: list = field(default_factory=list)
    scene_history_referenced: list[str] = field(default_factory=list)


def accumulate_scene_context_trace(
    trace: GenerationDependencyTrace,
    scene_ctx: SceneGraphContext,
) -> None:
    """Populate `trace` from a fully-built `SceneGraphContext`.

    Conservative over-approx (ADR-023 §F5): every entity that *reached*
    the prompt is recorded — even if the LLM ultimately ignored it,
    `dep_propagate` should still mark this scene stale if that entity
    later changes. Caller is expected to invoke this once after
    `build_scene_graph_context` returns and before any per-graph
    accumulation (`accumulate_written_paths_from_graph`).

    Field-by-field mapping:
      * `participating_characters[*].id` → `ontology_ids_read`
      * `location_candidates[*].id` → `ontology_ids_read`
      * `primary_location_ref` (when set) → `ontology_ids_read`
      * `chapter_ref` (when set) → `ontology_ids_read`
      * `active_clocks[*].id` → `ontology_ids_read` + `clock_ids_referenced`
      * `participating_characters[*].visual_assets[*].asset_id` →
        `visual_asset_ids_referenced`
      * `relations_matrix[*]` → only contributes the target_character_ref
        ID to `ontology_ids_read`; the relation itself isn't a separate
        ontology entity.
      * Each character's `state_path_slug` synthesises a
        `relationship.<slug>.*` namespace anchor read — only when the
        slug is present, since the prompt text exposes the slug to the
        model. We record `relationship.<slug>` as a *prefix* anchor;
        actual concrete paths come out of the assembled graph.

    `state_paths_read` from this helper is a coarse anchor set — the
    model's read-side decisions get further refined when the graph
    lands (the sidecar's read-side over-approx is intentionally broader
    than the write-side exact list).
    """
    for character in scene_ctx.participating_characters or []:
        if not isinstance(character, dict):
            continue
        cid = character.get("id")
        if isinstance(cid, str) and cid:
            trace.ontology_ids_read.add(cid)
        for asset in character.get("visual_assets") or []:
            if not isinstance(asset, dict):
                continue
            asset_id = asset.get("asset_id")
            if isinstance(asset_id, str) and asset_id:
                trace.visual_asset_ids_referenced.add(asset_id)

    for location in scene_ctx.location_candidates or []:
        if not isinstance(location, dict):
            continue
        lid = location.get("id")
        if isinstance(lid, str) and lid:
            trace.ontology_ids_read.add(lid)

    if isinstance(scene_ctx.primary_location_ref, str) and scene_ctx.primary_location_ref:
        trace.ontology_ids_read.add(scene_ctx.primary_location_ref)

    if isinstance(scene_ctx.chapter_ref, str) and scene_ctx.chapter_ref:
        trace.ontology_ids_read.add(scene_ctx.chapter_ref)

    for clock in scene_ctx.active_clocks or []:
        if not isinstance(clock, dict):
            continue
        clock_id = clock.get("id")
        if isinstance(clock_id, str) and clock_id:
            trace.ontology_ids_read.add(clock_id)
            trace.clock_ids_referenced.add(clock_id)

    for relation in scene_ctx.relations_matrix or []:
        if not isinstance(relation, dict):
            continue
        target = relation.get("target_character_ref")
        if isinstance(target, str) and target:
            trace.ontology_ids_read.add(target)


def accumulate_written_paths_from_graph(
    trace: GenerationDependencyTrace,
    graph: dict,
) -> None:
    """Pull every `effects[*].path` and `on_enter_effects[*].path` from
    `graph` into `trace.state_paths_written`.

    The write-side field is exact (effect bags are part of the produced
    DialogueGraph), unlike the read-side over-approx. Paths are added
    to the set as-is — the dep_index schema regex on the writer side
    rejects bare-namespace / out-of-namespace paths before landing in
    the sidecar, so a malformed path here surfaces at sidecar-write
    time rather than being silently dropped. We also fold the same
    paths into `state_paths_read` since a write at minimum implies the
    namespace is in the prompt's reachable set (sidecar consumers do
    not need the read/write disjointness).
    """
    if not isinstance(graph, dict):
        return
    nodes = graph.get("nodes")
    if not isinstance(nodes, dict):
        return
    for node in nodes.values():
        if not isinstance(node, dict):
            continue
        for eff in node.get("on_enter_effects") or []:
            _add_path(trace, eff)
        for option in node.get("options") or []:
            if not isinstance(option, dict):
                continue
            for eff in option.get("effects") or []:
                _add_path(trace, eff)


def _add_path(trace: GenerationDependencyTrace, effect_obj) -> None:
    if not isinstance(effect_obj, dict):
        return
    path = effect_obj.get("path")
    if not isinstance(path, str) or not path:
        return
    trace.state_paths_written.add(path)
    trace.state_paths_read.add(path)


def compute_prior_summary_token_metrics(
    summaries: list[PriorSceneSummary],
    *,
    additional_chars: int = 0,
) -> TokenMetrics:
    """Compute the post-truncation `TokenMetrics` view for a summary list.

    Internally calls `truncate_prior_scene_summaries` so both the
    metrics-on-context and the strategy-side render share identical
    truncation logic.

    ``additional_chars`` (PR #44 review §4.1, B-phase finding 🟡) is
    the caller-supplied character count of *the rest of the prompt the
    LLM will see* — typically ``len(SCENE_SYSTEM_PROMPT) +
    len(rendered_scene_context_block)``. The returned
    ``prompt_token_estimate`` covers ``additional_chars`` *plus* the
    summary block's chars, divided by `_PROMPT_CHARS_PER_TOKEN`. Per-
    node fill prompt variance is not captured here; T-3.5 may refine at
    sidecar-write time once the actual prompts have been rendered.
    Callers that don't have a baseline (unit tests) can omit
    ``additional_chars`` and get the summary-only estimate.
    """
    kept, reason = truncate_prior_scene_summaries(summaries)
    rendered = render_prior_scene_summaries_block(kept) if kept else ""
    total_chars = max(0, additional_chars) + len(rendered)
    estimate = total_chars // _PROMPT_CHARS_PER_TOKEN
    hashes = [_summary_source_hash(s) for s in kept]
    return TokenMetrics(
        prompt_token_estimate=estimate,
        summaries_injected_count=len(kept),
        summary_source_hashes=hashes,
        truncation_reason=reason,
    )
