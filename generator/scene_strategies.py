"""Skeleton-first scene generation strategy (T-2.5).

Implements the **C** generation strategy from
`/docs/HANDOFF_STAGE_1_TO_2.md` (default-adopted in Wave 2): split
scene-level generation into two LLM phases.

  Phase 1 — `generate_skeleton`: ask the LLM for a graph **skeleton**
            (5–15 nodes' ids/types/beats/speakers + the edge list, no
            narration / option text). One structured-output call,
            up to `max_retries` retries on schema/structural failure.
  Phase 2 — `fill_skeleton`: iterate skeleton nodes in deterministic
            order; for each, call the existing T-1.6
            `generate_node` with `NodeRequirement.allowed_targets =
            skeleton.get_allowed_targets(node_id)`. The fill phase
            reuses the node-level retry loop, the budget guard, and
            the schema/graph subset validator unchanged.

Why two phases instead of one big call:

  * single-call generation of a 10-node graph blows past one provider
    response token cap and entangles structural choices with prose
    quality — a single failed `Option.text` length check forces a
    full-graph regeneration.
  * allowed_targets (critique 4.9) is the load-bearing constraint
    that lets the fill phase stay within the planned topology — without
    it the LLM tends to invent target_node_ids, which breaks graph
    closure invariants and is expensive to re-fed.

What this module is NOT:

  * It's not `generate_scene`. T-2.6 owns the public-facing main
    function (with budget pre-charge, ontology assembly, mechanical
    pre-check integration). This module is purely the skeleton/fill
    orchestration primitives that T-2.6 calls into.
  * It does not assemble `SceneGraphContext`. T-2.6 owns the scene
    context dataclass + render. We accept a duck-typed `scene_context`
    dict here so callers can wire things up without circular imports.
  * It does not run real Gemini API. All callers inject an
    `LLMProvider` (FakeProvider in tests, GeminiProvider in T-2.12
    实证 batch).
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from typing import Any, Literal

from generator import budget
from generator.budget import BudgetExceeded
from generator.context_assembler import GraphContext, NodeRequirement
from generator.generate_node import (
    AttemptRecord,
    GenerationResult,
    _is_request_not_sent,
    generate_node,
)
from generator.llm_provider import LLMProvider, ProviderError, StructuredResponse
from generator.prompts.scene.few_shot import (
    SceneFewShotPair,
    load_iron_oath_scene_few_shot,
    render_scene_few_shot_block,
)
from generator.prompts.scene.fill import render_fill_extras
from generator.prompts.scene.system import SCENE_SYSTEM_PROMPT

_LOG = logging.getLogger(__name__)

# Same heuristic as generate_node — providers do their own counting; we
# only need a pre-call estimate for the budget guard.
_CHARS_PER_TOKEN = 4
# Skeleton response is structurally light (no narration / no option text)
# but lists ~10 nodes + edges, so 800 tokens is a comfortable upper bound.
_SKELETON_OUTPUT_TOKEN_ESTIMATE = 800

# Cache the rendered few-shot block so prompt hashes stay stable across
# retries / fill calls (the few-shot is identical in both phases — only
# the per-call requirement tail differs).
_SCENE_FEW_SHOT_BLOCK: str | None = None


def _scene_few_shot_block() -> str:
    global _SCENE_FEW_SHOT_BLOCK
    if _SCENE_FEW_SHOT_BLOCK is None:
        _SCENE_FEW_SHOT_BLOCK = render_scene_few_shot_block(
            load_iron_oath_scene_few_shot()
        )
    return _SCENE_FEW_SHOT_BLOCK


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass
class SceneSetting:
    """Per-scene settings the caller controls.

    Defined here (rather than in T-2.6's generate_scene.py) so this
    module's public function signatures don't have a phantom forward
    reference. T-2.6 reuses this dataclass — see
    `/docs/STAGE_2_TASKS.md` §T-2.6 §1 (canonical fields).
    """

    scene_anchor: str
    primary_location_ref: str
    chapter_ref: str | None = None
    expected_node_count_min: int = 5
    expected_node_count_max: int = 15


@dataclass
class SkeletonNode:
    """One node in the graph skeleton (no narration / no option text)."""

    node_id: str
    type: Literal["dialogue", "end"]
    beat: str
    speaker_ref: str | None
    expected_branch_count: int  # 0 for end nodes; 3–6 for dialogue


@dataclass
class GraphSkeleton:
    """Whole-scene skeleton: nodes + directed edges + entry / end markers.

    `edges` is the canonical edge list — one tuple per directed edge from
    a parent dialogue node to a child node (the child can be either
    dialogue or end). `get_allowed_targets` is the load-bearing helper
    fill_skeleton uses to inject NodeRequirement.allowed_targets.
    """

    nodes: list[SkeletonNode]
    edges: list[tuple[str, str]]
    entry_node_id: str
    end_node_ids: list[str]

    def get_allowed_targets(self, node_id: str) -> list[str]:
        """Return the unique legal `option.target_node_id` set for a fill call.

        Empty list means "this node is an end node" — the schema layer
        already enforces empty options for end nodes; the empty-list
        signal is consumed by `_check_allowed_targets` as an extra
        defensive check.

        Order is preserved (first occurrence wins) so prompt hashes stay
        deterministic for the same skeleton.
        """
        seen: set[str] = set()
        ordered: list[str] = []
        for from_id, to_id in self.edges:
            if from_id != node_id:
                continue
            if to_id in seen:
                continue
            seen.add(to_id)
            ordered.append(to_id)
        return ordered

    def node_by_id(self, node_id: str) -> SkeletonNode:
        for n in self.nodes:
            if n.node_id == node_id:
                return n
        raise KeyError(node_id)


@dataclass
class SkeletonResult:
    """Result of the phase-1 skeleton call."""

    success: bool
    skeleton: GraphSkeleton | None = None
    failure_reason: str | None = None  # "skeleton_invalid" | "budget_exceeded" | "provider_error"
    attempts: list[AttemptRecord] = field(default_factory=list)
    total_cost_usd: float = 0.0


@dataclass
class FillResult:
    """Result of the phase-2 fill call."""

    success: bool
    graph: dict | None = None
    failure_reason: str | None = None  # "fill_node_invalid" | "fill_target_out_of_skeleton" | "budget_exceeded" | "provider_error"
    failure_node_id: str | None = None
    fill_attempts: dict[str, list[AttemptRecord]] = field(default_factory=dict)
    total_cost_usd: float = 0.0


@dataclass
class SceneGenerationResult:
    """End-to-end outcome of `generate_scene_skeleton_first`."""

    success: bool
    graph: dict | None = None
    skeleton: GraphSkeleton | None = None
    failure_reason: str | None = None  # "skeleton_invalid" | "fill_node_invalid" | "fill_target_out_of_skeleton" | "budget_exceeded" | "provider_error"
    failure_node_id: str | None = None
    skeleton_attempts: list[AttemptRecord] = field(default_factory=list)
    fill_attempts: dict[str, list[AttemptRecord]] = field(default_factory=dict)
    total_cost_usd: float = 0.0


# ---------------------------------------------------------------------------
# Skeleton response schema (inline; not a Pydantic model)
# ---------------------------------------------------------------------------
#
# Skeleton is an internal, throwaway structure — it never lands in
# /content/ or /state/. Encoding it as a dedicated JSON Schema in
# /schema/ would be premature abstraction (CLAUDE.md rule 3:
# "frameworks remain neutral until two real consumers exist"). The
# inline schema below is what the LLM sees as `response_schema` and what
# `_parse_skeleton_response` validates against.

_SKELETON_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "required": ["nodes", "edges", "entry_node_id", "end_node_ids"],
    "properties": {
        "nodes": {
            "type": "array",
            "minItems": 5,
            "maxItems": 15,
            "items": {
                "type": "object",
                "required": [
                    "node_id",
                    "type",
                    "beat",
                    "speaker_ref",
                    "expected_branch_count",
                ],
                "properties": {
                    "node_id": {"type": "string"},
                    "type": {"type": "string", "enum": ["dialogue", "end"]},
                    "beat": {"type": "string"},
                    "speaker_ref": {"type": ["string", "null"]},
                    "expected_branch_count": {
                        "type": "integer",
                        "minimum": 0,
                        "maximum": 6,
                    },
                },
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "array",
                "minItems": 2,
                "maxItems": 2,
                "items": {"type": "string"},
            },
        },
        "entry_node_id": {"type": "string"},
        "end_node_ids": {
            "type": "array",
            "minItems": 2,
            "maxItems": 5,
            "items": {"type": "string"},
        },
    },
}


# ---------------------------------------------------------------------------
# Phase 1 — skeleton
# ---------------------------------------------------------------------------


def generate_skeleton(
    *,
    scene_setting: SceneSetting,
    target_beats: list[str],
    participating_npcs: list[dict],
    provider: LLMProvider,
    max_retries: int = 2,
    active_clocks: list[dict] | None = None,
    system_time: dict | None = None,
    location_candidates: list[dict] | None = None,
) -> SkeletonResult:
    """Phase 1: ask LLM for a structural-only skeleton.

    Total attempts = 1 + max_retries (default 3). Same retry / budget /
    refund discipline as `generate_node`:

      * `budget.check_and_charge` is called *before* every API call.
      * `BudgetExceeded` aborts the loop with failure_reason="budget_exceeded".
      * `ProviderError` aborts; refund applied iff `_is_request_not_sent`.
      * Skeleton structural failures (parse / closure / etc.) are
        validator_errors that get re-fed on the next attempt.
      * Three structural failures → failure_reason="skeleton_invalid".
    """
    base_user_prompt = _build_skeleton_user_prompt(
        scene_setting=scene_setting,
        target_beats=target_beats,
        participating_npcs=participating_npcs,
        active_clocks=active_clocks or [],
        system_time=system_time or {"scene_count": 0, "long_rest_count": 0},
        location_candidates=location_candidates or [],
    )

    attempts: list[AttemptRecord] = []
    total_cost = 0.0
    last_validator_errors: list[str] = []

    for attempt_idx in range(1, max_retries + 2):
        if attempt_idx == 1:
            user_prompt = base_user_prompt
        else:
            user_prompt = base_user_prompt + _retry_feedback(last_validator_errors)

        # ---- Pre-call budget guard. ----
        input_tokens_est = max(
            1, len(SCENE_SYSTEM_PROMPT + user_prompt) // _CHARS_PER_TOKEN
        )
        output_tokens_est = _SKELETON_OUTPUT_TOKEN_ESTIMATE
        estimated_cost = provider.estimate_cost(input_tokens_est, output_tokens_est)
        try:
            record_id = budget.check_and_charge(
                estimated_cost,
                model_id=getattr(provider, "model_id", "unknown"),
                input_tokens=input_tokens_est,
                output_tokens=output_tokens_est,
            )
        except BudgetExceeded as exc:
            attempts.append(
                AttemptRecord(
                    attempt_index=attempt_idx,
                    raw_text=None,
                    validator_errors=[f"budget_exceeded: {exc}"],
                    cost_usd=0.0,
                )
            )
            return SkeletonResult(
                success=False,
                failure_reason="budget_exceeded",
                attempts=attempts,
                total_cost_usd=total_cost,
            )

        # ---- LLM call. ----
        try:
            response: StructuredResponse = provider.generate_structured(
                SCENE_SYSTEM_PROMPT, user_prompt, _SKELETON_RESPONSE_SCHEMA
            )
        except ProviderError as exc:
            if _is_request_not_sent(exc):
                budget.refund_estimated(record_id, reason="request_not_sent")
                attempts.append(
                    AttemptRecord(
                        attempt_index=attempt_idx,
                        raw_text=None,
                        validator_errors=[f"provider_error: {exc}"],
                        cost_usd=0.0,
                    )
                )
                return SkeletonResult(
                    success=False,
                    failure_reason="provider_error",
                    attempts=attempts,
                    total_cost_usd=total_cost,
                )
            _LOG.info(
                "skeleton request_sent_failure refund deferred (record_id=%s, error=%s)",
                record_id,
                exc,
            )
            attempts.append(
                AttemptRecord(
                    attempt_index=attempt_idx,
                    raw_text=None,
                    validator_errors=[f"provider_error: {exc}"],
                    cost_usd=estimated_cost,
                )
            )
            total_cost += estimated_cost
            return SkeletonResult(
                success=False,
                failure_reason="provider_error",
                attempts=attempts,
                total_cost_usd=total_cost,
            )

        actual_cost = provider.estimate_cost(response.input_tokens, response.output_tokens)
        budget.reconcile_after_call(
            record_id,
            actual_input_tokens=response.input_tokens,
            actual_output_tokens=response.output_tokens,
            actual_cost_usd=actual_cost,
        )
        total_cost += actual_cost

        skeleton, errors = _parse_skeleton_response(response.content)
        attempts.append(
            AttemptRecord(
                attempt_index=attempt_idx,
                raw_text=response.raw_text,
                validator_errors=errors,
                cost_usd=actual_cost,
                finish_reason=response.finish_reason,
            )
        )
        if not errors and skeleton is not None:
            return SkeletonResult(
                success=True,
                skeleton=skeleton,
                attempts=attempts,
                total_cost_usd=total_cost,
            )
        last_validator_errors = errors

    return SkeletonResult(
        success=False,
        failure_reason="skeleton_invalid",
        attempts=attempts,
        total_cost_usd=total_cost,
    )


# ---------------------------------------------------------------------------
# Phase 2 — fill
# ---------------------------------------------------------------------------


def fill_skeleton(
    *,
    skeleton: GraphSkeleton,
    scene_context: dict,
    provider: LLMProvider,
    max_retries: int = 2,
) -> FillResult:
    """Phase 2: fill every skeleton node with narration + options.

    Each fill call goes through the existing `generate_node` (T-1.6) with
    `NodeRequirement.allowed_targets` populated from
    `skeleton.get_allowed_targets(node_id)`. `generate_node` already owns
    its own retry loop, budget guard, and schema validator — the fill
    orchestrator just maps results back into a DialogueGraph dict.

    `scene_context` is a duck-typed dict carrying the per-scene fields
    `generate_node` needs:

      * `scene_anchor: str`
      * `location_candidates: list[dict]` (1–3 entries)
      * `primary_location_ref: str | None`
      * `involved_characters: list[dict]` (one card per participating npc)
      * `active_clocks: list[dict]`
      * `character_refs: list[str]` (used to seed the DialogueGraph
        envelope; defaults to all `id`s found in `involved_characters`)

    Failure semantics:

      * If any node's generate_node fails with `failure_reason ==
        "schema_invalid"` AND every attempt's validator_errors include
        an "allowed_targets" complaint → bubble up
        `fill_target_out_of_skeleton` (critique 4.9 forensic signal).
      * Other schema_invalid → `fill_node_invalid`.
      * Budget / provider errors propagate as-is.
    """
    fill_attempts: dict[str, list[AttemptRecord]] = {}
    total_cost = 0.0
    filled_nodes: dict[str, dict] = {}
    # R2.6: running list of (node_id, narration) for nodes already filled
    # in this scene. Each subsequent fill prompt embeds a summary of this
    # list so the LLM can see what setting / characters / props the
    # opening already described and stop repeating them. T-2.12 baseline_005
    # v3 reject rationale (S2=0 重复 beat) traced directly to this gap.
    filled_so_far: list[tuple[str, str]] = []
    total_nodes = len(skeleton.nodes)

    # Iterate in skeleton.nodes order (entry first if the skeleton is
    # well-formed — the assembled DialogueGraph respects entry_node_id
    # explicitly so order here is only for debuggability).
    for index, skel_node in enumerate(skeleton.nodes):
        extra_context = render_fill_extras(
            filled_so_far=filled_so_far,
            beat=skel_node.beat,
            index=index,
            total=total_nodes,
        )
        node_req = NodeRequirement(
            node_type=skel_node.type,
            expected_speaker_ref=skel_node.speaker_ref,
            narrative_intent=_intent_from_beat(skel_node),
            allowed_targets=skeleton.get_allowed_targets(skel_node.node_id),
            extra_user_context=extra_context,
        )
        graph_ctx = _graph_context_from_scene_context(
            scene_context, current_node=skel_node, skeleton=skeleton
        )
        result: GenerationResult = generate_node(
            graph_context=graph_ctx,
            node_requirement=node_req,
            provider=provider,
            max_retries=max_retries,
        )
        fill_attempts[skel_node.node_id] = list(result.attempts)
        total_cost += result.total_cost_usd

        if not result.success:
            failure_reason = result.failure_reason or "fill_node_invalid"
            # Translate node-level failure_reason into scene-level vocabulary.
            if failure_reason == "schema_invalid":
                if _every_attempt_violated_allowed_targets(result.attempts):
                    failure_reason = "fill_target_out_of_skeleton"
                else:
                    failure_reason = "fill_node_invalid"
            return FillResult(
                success=False,
                failure_reason=failure_reason,
                failure_node_id=skel_node.node_id,
                fill_attempts=fill_attempts,
                total_cost_usd=total_cost,
            )

        # Force-fix node_id in case the LLM renamed the node — the
        # skeleton owns the canonical id, so we overwrite. The schema
        # layer accepts any node_id matching the pattern; the outer
        # graph closure enforces ID matching during graph assembly.
        node_dict = dict(result.node or {})
        node_dict["node_id"] = skel_node.node_id
        filled_nodes[skel_node.node_id] = node_dict
        # Capture this node's narration for the next iter's bleed-through
        # summary. Non-string narrations (shouldn't happen post-validation,
        # but be defensive) are stored as empty so the summary line still
        # carries the node_id without crashing on str ops.
        narration = node_dict.get("narration")
        filled_so_far.append(
            (skel_node.node_id, narration if isinstance(narration, str) else "")
        )

    graph = _assemble_dialogue_graph(skeleton, filled_nodes, scene_context)
    return FillResult(
        success=True,
        graph=graph,
        fill_attempts=fill_attempts,
        total_cost_usd=total_cost,
    )


# ---------------------------------------------------------------------------
# Public main function
# ---------------------------------------------------------------------------


def generate_scene_skeleton_first(
    *,
    scene_setting: SceneSetting,
    target_beats: list[str],
    participating_npcs: list[dict],
    provider: LLMProvider,
    max_retries: int = 2,
    active_clocks: list[dict] | None = None,
    system_time: dict | None = None,
    location_candidates: list[dict] | None = None,
) -> SceneGenerationResult:
    """End-to-end skeleton-first scene generation.

    Wires phase-1 + phase-2 together and produces a single
    `SceneGenerationResult`. T-2.6's `generate_scene` will wrap this
    again with budget pre-charge, ontology assembly, and mechanical
    pre-check (T-2.4) integration — those are explicitly out-of-scope
    for T-2.5.
    """
    skel_res = generate_skeleton(
        scene_setting=scene_setting,
        target_beats=target_beats,
        participating_npcs=participating_npcs,
        provider=provider,
        max_retries=max_retries,
        active_clocks=active_clocks,
        system_time=system_time,
        location_candidates=location_candidates,
    )
    if not skel_res.success:
        return SceneGenerationResult(
            success=False,
            failure_reason=skel_res.failure_reason,
            skeleton_attempts=skel_res.attempts,
            total_cost_usd=skel_res.total_cost_usd,
        )

    assert skel_res.skeleton is not None  # success path guarantees this

    scene_context: dict[str, Any] = {
        "scene_anchor": scene_setting.scene_anchor,
        "location_candidates": location_candidates or [],
        "primary_location_ref": scene_setting.primary_location_ref,
        "involved_characters": list(participating_npcs),
        "active_clocks": active_clocks or [],
        # C-phase (review 4.2): forward system_time verbatim so fill
        # prompts see what the skeleton phase saw. Pass None through (don't
        # fall back to a stub `{scene_count: 0, ...}`) so callers who
        # explicitly omit system_time get a *missing* section rather than
        # an inert "0 / 0" header that would still claim authority.
        "system_time": system_time,
        "character_refs": [
            npc["id"] for npc in participating_npcs if isinstance(npc, dict) and "id" in npc
        ],
    }

    fill_res = fill_skeleton(
        skeleton=skel_res.skeleton,
        scene_context=scene_context,
        provider=provider,
        max_retries=max_retries,
    )

    return SceneGenerationResult(
        success=fill_res.success,
        graph=fill_res.graph,
        skeleton=skel_res.skeleton,
        failure_reason=fill_res.failure_reason,
        failure_node_id=fill_res.failure_node_id,
        skeleton_attempts=skel_res.attempts,
        fill_attempts=fill_res.fill_attempts,
        total_cost_usd=skel_res.total_cost_usd + fill_res.total_cost_usd,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _build_skeleton_user_prompt(
    *,
    scene_setting: SceneSetting,
    target_beats: list[str],
    participating_npcs: list[dict],
    active_clocks: list[dict],
    system_time: dict,
    location_candidates: list[dict],
) -> str:
    """Render the skeleton-phase user prompt.

    Includes the same scene-level context as fill phase (so the model
    sees consistent ontology) plus a clear instruction that this call
    only wants the structural skeleton — no narration, no option text.
    """
    parts: list[str] = [_scene_few_shot_block(), "", "## 当前任务", "### 场景设定"]
    parts.append(f"- `scene_anchor`: `{scene_setting.scene_anchor}`")
    parts.append(f"- 主地点 (`primary_location_ref`): `{scene_setting.primary_location_ref}`")
    if scene_setting.chapter_ref:
        parts.append(f"- 所属 chapter: `{scene_setting.chapter_ref}`")
    parts.append(
        f"- 节点数预估：{scene_setting.expected_node_count_min}–"
        f"{scene_setting.expected_node_count_max}"
    )

    parts.append("")
    parts.append("### 节拍序列 (`target_beats`)")
    if target_beats:
        for idx, beat in enumerate(target_beats, start=1):
            parts.append(f"{idx}. {beat}")
    else:
        parts.append("（调用方未给节拍序列——按 scene_anchor 自行推断 5–7 拍）")

    parts.append("")
    parts.append("### 候选地点 (`location_candidates`)")
    if location_candidates:
        for cand in location_candidates:
            parts.append("```json")
            parts.append(json.dumps(cand, ensure_ascii=False, indent=2))
            parts.append("```")
    else:
        parts.append("（本体未给候选地点；fill 阶段将用 scene_anchor 兜底）")

    parts.append("")
    parts.append("### 出场角色卡 (`participating_npcs`)")
    if participating_npcs:
        for card in participating_npcs:
            parts.append("```json")
            parts.append(json.dumps(card, ensure_ascii=False, indent=2))
            parts.append("```")
    else:
        parts.append("（无角色卡——只能用旁白生成）")

    parts.append("")
    parts.append("### 阵营时钟 (`active_clocks`)")
    if active_clocks:
        for clock in active_clocks:
            parts.append("```json")
            parts.append(json.dumps(clock, ensure_ascii=False, indent=2))
            parts.append("```")
    else:
        parts.append("（无活跃时钟）")

    parts.append("")
    parts.append("### 系统时间 (`system_time`)")
    parts.append(f"- `world.scene_count`: {system_time.get('scene_count', 0)}")
    parts.append(f"- `world.long_rest_count`: {system_time.get('long_rest_count', 0)}")

    parts.append("")
    parts.append("### 本次输出要求（**仅图骨架；不要写任何 narration / option text**）")
    parts.append(
        "请输出一个 JSON 对象，schema 如下："
    )
    parts.append("```json")
    parts.append(
        json.dumps(
            {
                "nodes": [
                    {
                        "node_id": "<^[a-z][a-z0-9_]*$>",
                        "type": "<dialogue|end>",
                        "beat": "<对应的 target_beats 节拍标签>",
                        "speaker_ref": "<char_xxx 或 null>",
                        "expected_branch_count": "<dialogue 3–6；end 0>",
                    }
                ],
                "edges": [["<from_node_id>", "<to_node_id>"]],
                "entry_node_id": "<入口节点 id>",
                "end_node_ids": ["<3–5 个 end 节点 id>"],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    parts.append("```")
    parts.append(
        "结构性约束："
        "(a) `entry_node_id` 必须在 `nodes` 中；"
        "(b) `end_node_ids` 必须全部在 `nodes` 中且 `type==\"end\"`；"
        "(c) 每条 edge 的 from / to 都必须在 `nodes` 中；"
        "(d) `type==\"end\"` 节点没有出边（不能作为 edges[].0）；"
        "(e) `type==\"dialogue\"` 节点的出边数 = `expected_branch_count`（3–6）；"
        "(f) 每个非 entry 节点必须有至少一条入边（图必须可达）。"
    )
    parts.append(
        "**只输出 JSON 本身**，禁止前后包裹任何说明或代码围栏。"
    )

    return "\n".join(parts)


def _retry_feedback(errors: list[str]) -> str:
    """Tail appended on retry attempts. Mirrors generate_node._retry_feedback."""
    bullet_list = "\n".join(f"- {e}" for e in errors)
    return (
        "\n\n---\n\n"
        "上次生成失败，错误如下：\n"
        f"{bullet_list}\n\n"
        "请基于以上错误修正后重新输出**完整**骨架 JSON。"
    )


def _parse_skeleton_response(
    response_content: Any,
) -> tuple[GraphSkeleton | None, list[str]]:
    """Validate the skeleton response against structural invariants.

    `response_schema` already enforces top-level field shapes via
    Gemini's response_schema enforcement; we re-check here in
    provider-neutral terms so a non-Gemini provider that returns a
    parsed-but-malformed dict still gets caught.
    """
    if not isinstance(response_content, dict):
        return None, [
            f"top-level skeleton output is {type(response_content).__name__}, expected JSON object"
        ]

    errors: list[str] = []
    raw_nodes = response_content.get("nodes")
    raw_edges = response_content.get("edges")
    entry_node_id = response_content.get("entry_node_id")
    end_node_ids = response_content.get("end_node_ids")

    if not isinstance(raw_nodes, list) or not raw_nodes:
        errors.append("/nodes: must be a non-empty array")
    if not isinstance(raw_edges, list):
        errors.append("/edges: must be an array")
    if not isinstance(entry_node_id, str) or not entry_node_id:
        errors.append("/entry_node_id: must be a non-empty string")
    if not isinstance(end_node_ids, list) or not end_node_ids:
        errors.append("/end_node_ids: must be a non-empty array")

    if errors:
        return None, errors

    nodes: list[SkeletonNode] = []
    seen_ids: set[str] = set()
    for idx, item in enumerate(raw_nodes):
        if not isinstance(item, dict):
            errors.append(f"/nodes/{idx}: must be an object")
            continue
        nid = item.get("node_id")
        ntype = item.get("type")
        beat = item.get("beat")
        speaker = item.get("speaker_ref")
        branch = item.get("expected_branch_count")
        if not isinstance(nid, str) or not nid:
            errors.append(f"/nodes/{idx}/node_id: must be a non-empty string")
            continue
        if nid in seen_ids:
            errors.append(f"/nodes/{idx}/node_id: duplicate id {nid!r}")
            continue
        seen_ids.add(nid)
        if ntype not in ("dialogue", "end"):
            errors.append(f"/nodes/{idx}/type: must be 'dialogue' or 'end'")
        if not isinstance(beat, str) or not beat:
            errors.append(f"/nodes/{idx}/beat: must be a non-empty string")
        if speaker is not None and not isinstance(speaker, str):
            errors.append(f"/nodes/{idx}/speaker_ref: must be string or null")
        if not isinstance(branch, int) or branch < 0 or branch > 6:
            errors.append(
                f"/nodes/{idx}/expected_branch_count: must be int in [0, 6]"
            )
        nodes.append(
            SkeletonNode(
                node_id=nid,
                type=ntype if ntype in ("dialogue", "end") else "dialogue",
                beat=beat if isinstance(beat, str) else "",
                speaker_ref=speaker if isinstance(speaker, str) else None,
                expected_branch_count=branch if isinstance(branch, int) else 0,
            )
        )

    edges: list[tuple[str, str]] = []
    for idx, item in enumerate(raw_edges):
        if (
            not isinstance(item, list)
            or len(item) != 2
            or not all(isinstance(x, str) for x in item)
        ):
            errors.append(f"/edges/{idx}: must be a [from_id, to_id] pair of strings")
            continue
        edges.append((item[0], item[1]))

    if errors:
        return None, errors

    # Closure invariants
    id_to_type = {n.node_id: n.type for n in nodes}
    if entry_node_id not in id_to_type:
        errors.append(
            f"/entry_node_id: {entry_node_id!r} not in nodes"
        )
    for end_id in end_node_ids:
        if not isinstance(end_id, str) or end_id not in id_to_type:
            errors.append(f"/end_node_ids: {end_id!r} not in nodes")
        elif id_to_type.get(end_id) != "end":
            errors.append(
                f"/end_node_ids: {end_id!r} listed but its type is "
                f"{id_to_type.get(end_id)!r}"
            )
    # Count *unique* outgoing targets per node — the option count
    # (`expected_branch_count`) is independent of unique edge count: a
    # 3-option node can have 2 unique outgoing targets when two options
    # share a follow-up node (gold scene `arrival_waystation` does this).
    out_targets: dict[str, set[str]] = {nid: set() for nid in id_to_type}
    in_count: dict[str, int] = {nid: 0 for nid in id_to_type}
    for from_id, to_id in edges:
        if from_id not in id_to_type:
            errors.append(f"/edges: from_id {from_id!r} not in nodes")
            continue
        if to_id not in id_to_type:
            errors.append(f"/edges: to_id {to_id!r} not in nodes")
            continue
        out_targets[from_id].add(to_id)
        in_count[to_id] = in_count.get(to_id, 0) + 1

    for n in nodes:
        unique_out = len(out_targets.get(n.node_id, set()))
        if n.type == "end" and unique_out != 0:
            errors.append(
                f"/nodes ({n.node_id}): end nodes must have no outgoing edges"
            )
        if n.type == "dialogue":
            if unique_out < 1 or unique_out > 6:
                errors.append(
                    f"/nodes ({n.node_id}): dialogue node has "
                    f"{unique_out} unique outgoing target(s); expected 1–6"
                )
        if n.node_id != entry_node_id and in_count.get(n.node_id, 0) == 0:
            errors.append(
                f"/nodes ({n.node_id}): unreachable (no incoming edges and not entry)"
            )

    if errors:
        return None, errors

    return (
        GraphSkeleton(
            nodes=nodes,
            edges=edges,
            entry_node_id=entry_node_id if isinstance(entry_node_id, str) else "",
            end_node_ids=[
                e for e in (end_node_ids or []) if isinstance(e, str)
            ],
        ),
        [],
    )


def _intent_from_beat(skel_node: SkeletonNode) -> str:
    """Derive `narrative_intent` for a fill-phase generate_node call."""
    if skel_node.type == "end":
        return f"按节拍 `{skel_node.beat}` 写 ending 节点的余韵收尾"
    return (
        f"按节拍 `{skel_node.beat}` 推进，给出 "
        f"{skel_node.expected_branch_count} 个体现性格倾向的选项"
    )


def _graph_context_from_scene_context(
    scene_context: dict, *, current_node: SkeletonNode, skeleton: GraphSkeleton
) -> GraphContext:
    """Project the scene-level context into a node-level GraphContext.

    Parent chain is left empty here — the fill phase generates each node
    in isolation; the model's coherence comes from the (cached) scene
    few-shot block plus the (per-call) skeleton-derived narrative intent.
    Reading sibling fills' outputs as 'parent chain' would create
    order-dependence and break determinism, which is why skeleton-first
    deliberately doesn't do it.

    C-phase (review 4.2): `active_clocks` and `system_time` are forwarded
    so each fill prompt sees the same clock state and world-time pair the
    skeleton phase saw. `faction_clocks` is left empty — the legacy
    `dict[str, int]` shape isn't a faithful reduction of an ADR-017 clock
    (which carries scope / ticks_total / advance_rule), so we render the
    full dicts via the new `active_clocks` section instead.
    """
    return GraphContext(
        scene_anchor=scene_context.get("scene_anchor", ""),
        location_candidates=list(scene_context.get("location_candidates") or []),
        primary_location_ref=scene_context.get("primary_location_ref"),
        parent_chain=[],
        involved_characters=list(scene_context.get("involved_characters") or []),
        faction_clocks={},
        active_clocks=list(scene_context.get("active_clocks") or []),
        system_time=scene_context.get("system_time") or None,
    )


def _every_attempt_violated_allowed_targets(
    attempts: list[AttemptRecord],
) -> bool:
    """Return True iff every recorded attempt with validator_errors had at
    least one allowed_targets violation among them.

    The phrase "not in skeleton allowed_targets" is the canonical marker
    emitted by `generate_node._check_allowed_targets`. We deliberately
    look only at attempts that actually produced validator_errors (so a
    single budget_exceeded / provider_error attempt mixed in doesn't
    flip the classification).
    """
    saw_any = False
    for att in attempts:
        if not att.validator_errors:
            continue
        saw_any = True
        if not any("not in skeleton allowed_targets" in e for e in att.validator_errors):
            return False
    return saw_any


def _assemble_dialogue_graph(
    skeleton: GraphSkeleton, filled_nodes: dict[str, dict], scene_context: dict
) -> dict:
    """Wrap filled nodes into a DialogueGraph envelope (schema v0.1.1)."""
    character_refs = list(scene_context.get("character_refs") or [])
    return {
        "schema_version": "0.1.1",
        "graph_id": _derive_graph_id(scene_context.get("scene_anchor", "scene")),
        "entry_node_id": skeleton.entry_node_id,
        "scene_anchor": scene_context.get("scene_anchor", ""),
        "character_refs": character_refs,
        "nodes": filled_nodes,
    }


def _derive_graph_id(scene_anchor: str) -> str:
    """Convert a scene_anchor into a deterministic graph_id.

    Per ADR-016 character/location id pattern conventions; scene_anchor
    is already snake_case slug-like, so we just strip a `scene_`/`loc_`
    prefix if present to keep graph_ids short.
    """
    for prefix in ("scene_", "loc_"):
        if scene_anchor.startswith(prefix):
            return scene_anchor[len(prefix):]
    return scene_anchor or "scene"
