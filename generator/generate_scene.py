"""Stage-2 main entry point: full-scene generation (T-2.6).

`generate_scene` is the public-facing function that wraps T-2.5
`scene_strategies.generate_scene_skeleton_first` with the three things the
strategy module deliberately leaves out:

  1. **Ontology assembly** — resolve `participating_npcs` (a list of
     `char_*` IDs) into full character cards, pull `clocks` / `system_time`
     / `location` entities out of the world ontology, and build a
     `SceneGraphContext` (STAGE_2_TASKS §2.8 / context_assembler.py).
  2. **Scene-level budget pre-flight** (ADR-012) — check that today's
     running spend + this scene's estimated cost won't blow
     `DAILY_BUDGET_USD`, and bail out with `failure_reason="budget_exceeded"`
     before any API call. Per-call budget guarding inside the strategy is
     unchanged; we just add an outer "is the whole scene affordable?"
     check so a deeply-budget-constrained run aborts cleanly.
  3. **Mechanical pre-check integration** — after the strategy returns a
     candidate DialogueGraph, run `validator.validate_graph_mechanical`
     (T-2.4 / ADR-020) on it. The strategy's per-node validator only
     covers the schema layer + the dialogue/end ⇄ options invariant; the
     mechanical layer adds the 9-class hard-error check
     (OPT_LEN_OVER / PATH_NS_INVALID / TARGET_UNREACHABLE / etc.) that
     can only be evaluated on a fully-assembled graph. Failures bubble up
     as `failure_reason="mechanical_invalid"` after exhausting the outer
     retry budget.

Failure semantics are deliberately strict — `generate_scene` never raises
to the caller; every failure mode lands in `SceneResult` so the upstream
review CLI / batch runner can record it without try/except.

What this module is NOT:

  * It is not a replacement for `scene_strategies` — the skeleton-first
    strategy is the substrate; this module is the integration layer.
  * It does not call real Gemini. Tests inject a `FakeProvider`; the
    real-API path is `T-2.12` batch territory.
  * It does not extend the schema (CLAUDE.md rule 6) or write to
    `/state/ontology/` (read-only here).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from generator import budget
from generator.budget import BudgetExceeded
from generator.context_assembler import SceneGraphContext
from generator.llm_provider import LLMProvider
from generator.scene_strategies import (
    SceneGenerationResult,
    SceneSetting,
    generate_scene_skeleton_first,
)
from validator import dialogue_validator, schema_check
from validator.dialogue_validator import ValidationIssue

_LOG = logging.getLogger(__name__)

# Per-scene spend cap. The strategy charges per LLM call (skeleton + N
# fills); this is the *aggregate* budget guard. Default $1.50 = 3× the
# node-level $0.50 cap (a 10-node scene at the per-call cap would cost
# ~$5, but realistic estimates for B+ context are well under $0.20/node).
DEFAULT_SCENE_BUDGET_USD = 1.50

# Token-count heuristics for `estimate_scene_cost`. Same 4 chars/token
# convention as generate_node — providers do their own counting; we only
# need a pre-call estimate for the budget guard.
_SKELETON_INPUT_TOKEN_BASE = 2500    # few-shot + scene context
_SKELETON_INPUT_TOKEN_PER_NPC = 400  # one card adds ~400 tokens
_SKELETON_INPUT_TOKEN_PER_BEAT = 30
_SKELETON_OUTPUT_TOKEN_ESTIMATE = 800

_FILL_INPUT_TOKEN_BASE = 3000
_FILL_INPUT_TOKEN_PER_NPC = 400
_FILL_INPUT_TOKEN_PER_BEAT = 30
_FILL_OUTPUT_TOKEN_ESTIMATE = 1500


# ---------------------------------------------------------------------------
# Result type
# ---------------------------------------------------------------------------


@dataclass
class SceneResult:
    """End-to-end outcome of `generate_scene`.

    `failure_reason` enumerates every terminal classification this layer
    can reach:

      * `"budget_exceeded"`        — pre-flight rejection or strategy
                                     budget abort
      * `"skeleton_invalid"`       — strategy phase 1 exhausted
      * `"fill_node_invalid"`      — strategy phase 2 schema/type fail
      * `"fill_target_out_of_skeleton"` — strategy phase 2 allowed_targets
                                          fail (forensic signal, see
                                          critique 4.9 in scene_strategies)
      * `"provider_error"`         — strategy bailed on provider exception
      * `"schema_invalid"`         — assembled graph fails dialogue_graph
                                     schema (rare; per-node validator
                                     usually catches this)
      * `"mechanical_invalid"`     — assembled graph fails T-2.4
                                     mechanical pre-check on every outer
                                     attempt
    """

    success: bool
    graph: dict | None = None
    failure_reason: str | None = None
    failure_node_id: str | None = None
    schema_issues: list[str] = field(default_factory=list)
    mechanical_issues: dict[str, list[ValidationIssue]] = field(default_factory=dict)
    inner_results: list[SceneGenerationResult] = field(default_factory=list)
    total_cost_usd: float = 0.0


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def generate_scene(
    *,
    scene_setting: SceneSetting,
    target_beats: list[str],
    participating_npcs: list[str],
    ontology: dict,
    provider: LLMProvider,
    max_retries: int = 2,
) -> SceneResult:
    """Produce a full DialogueGraph for one scene.

    Flow (1 + max_retries outer attempts):

      1. Pre-flight budget guard (ADR-012). Estimate scene cost from
         (npc_count, beat_count, expected_node_count) and reject early if
         today's running total + estimate > DAILY_BUDGET_USD or estimate
         alone > DEFAULT_SCENE_BUDGET_USD.
      2. Build SceneGraphContext from the ontology.
      3. Call `scene_strategies.generate_scene_skeleton_first`. Strategy-
         internal failures (skeleton_invalid / fill_node_invalid /
         fill_target_out_of_skeleton / provider_error / budget_exceeded)
         propagate immediately — those already exhausted their own retry
         loops, no point trying the same prompts again.
      4. On success, run `validator.schema_check.check` + the T-2.4
         `validate_graph_mechanical` pre-check on the assembled graph.
         If either layer reports issues, retry from step 3 (up to
         max_retries+1 outer attempts in total).
      5. Exhausting outer attempts with mechanical/schema failures
         returns `failure_reason="mechanical_invalid"` (or
         `"schema_invalid"` if the dialogue_graph schema layer was the
         actual blocker — schema gets priority because it's a stronger
         signal that the strategy is malfunctioning).
      6. On final success, write `generation_trace.slot_assignments` to
         every node before returning (ADR-019; T-2.6 must persist abstract
         slot ↔ concrete character mappings — empty dict here because
         阶段 2 doesn't implement dynamic role swapping yet, but the
         field is present so downstream review tooling can rely on it).

    Outer-retry feedback (review 4.1): the strategy's prompts are stable
    per ADR-013, and the `generate_scene_skeleton_first` API has no
    feedback hook today. So this layer only *resamples* — issues from the
    previous attempt are logged via `_LOG.info` so batch-run operators
    have an audit trail, but they don't reach the LLM until
    `scene_strategies` exposes a feedback parameter (out of T-2.6 module
    boundary; tracked as a follow-up). Tests assert the feedback string
    is rendered + logged, not that the LLM acts on it.

    `generate_scene` never raises — every failure mode lands in
    `SceneResult.failure_reason` (review 3.1). The total cost is the sum
    of all inner `SceneGenerationResult.total_cost_usd` accumulated
    across attempts.
    """
    inner_results: list[SceneGenerationResult] = []
    total_cost = 0.0

    # Step 1: cost estimate + scene-level budget pre-flight (ADR-012).
    # Both wrapped — `provider.estimate_cost` and the env-var parse in
    # `_scene_budget_usd` can each raise on a misbehaving provider /
    # malformed env var.
    try:
        expected_node_count = (
            scene_setting.expected_node_count_min
            + scene_setting.expected_node_count_max
        ) // 2
        estimated_cost = estimate_scene_cost(
            npc_count=len(participating_npcs),
            beat_count=len(target_beats),
            expected_node_count=expected_node_count,
            provider=provider,
        )
        _scene_budget_pre_flight(estimated_cost)
    except BudgetExceeded as exc:
        return SceneResult(
            success=False,
            failure_reason="budget_exceeded",
            schema_issues=[f"budget_exceeded: {exc}"],
        )
    except Exception as exc:  # noqa: BLE001 - main contract is "never raise"
        _LOG.exception("scene budget pre-flight raised unexpectedly")
        return SceneResult(
            success=False,
            failure_reason="provider_error",
            schema_issues=[f"pre_flight_failed: {type(exc).__name__}: {exc}"],
        )

    # Step 2: assemble SceneGraphContext from ontology. Wrapped because a
    # malformed ontology dict could raise (KeyError / TypeError) and the
    # outer "never raise" contract must hold.
    try:
        scene_ctx = build_scene_graph_context(
            scene_setting=scene_setting,
            target_beats=target_beats,
            participating_npcs=participating_npcs,
            ontology=ontology,
        )
    except Exception as exc:  # noqa: BLE001
        _LOG.exception("scene context assembly raised unexpectedly")
        return SceneResult(
            success=False,
            failure_reason="provider_error",
            schema_issues=[f"context_assembly_failed: {type(exc).__name__}: {exc}"],
        )

    # Steps 3–6: outer retry loop.
    last_schema_issues: list[str] = []
    last_mechanical_issues: dict[str, list[ValidationIssue]] = {}
    last_layer = "mechanical"

    for attempt_idx in range(1, max_retries + 2):
        # Outer-retry feedback (review 4.1): currently log-only — see
        # docstring + module-level note on the scene_strategies API gap.
        if attempt_idx > 1:
            feedback = _render_outer_retry_feedback(
                last_layer, last_schema_issues, last_mechanical_issues
            )
            _LOG.info(
                "scene outer retry %d: re-sampling after %s failure\n%s",
                attempt_idx,
                last_layer,
                feedback,
            )

        # Step 3: strategy call. Provider/strategy bugs that bypass the
        # internal try/except chain land here.
        try:
            inner = generate_scene_skeleton_first(
                scene_setting=scene_setting,
                target_beats=target_beats,
                participating_npcs=scene_ctx.participating_characters,
                provider=provider,
                max_retries=max_retries,
                active_clocks=scene_ctx.active_clocks,
                system_time=scene_ctx.system_time,
                location_candidates=scene_ctx.location_candidates,
            )
        except Exception as exc:  # noqa: BLE001
            _LOG.exception("scene strategy raised unexpectedly on attempt %d", attempt_idx)
            return SceneResult(
                success=False,
                failure_reason="provider_error",
                schema_issues=[f"strategy_exception: {type(exc).__name__}: {exc}"],
                inner_results=inner_results,
                total_cost_usd=total_cost,
            )
        inner_results.append(inner)
        total_cost += inner.total_cost_usd

        if not inner.success:
            # Strategy-internal failure: don't retry — its own retry loop
            # already exhausted. Propagate verbatim.
            return SceneResult(
                success=False,
                failure_reason=inner.failure_reason,
                failure_node_id=inner.failure_node_id,
                inner_results=inner_results,
                total_cost_usd=total_cost,
            )

        graph = inner.graph
        if graph is None:
            # Defensive: strategy reports success=True but graph=None
            # shouldn't happen; if it does, surface as provider_error
            # rather than letting an AssertionError escape.
            _LOG.warning(
                "scene strategy returned success=True but graph=None on attempt %d",
                attempt_idx,
            )
            return SceneResult(
                success=False,
                failure_reason="provider_error",
                schema_issues=["strategy_returned_success_with_no_graph"],
                inner_results=inner_results,
                total_cost_usd=total_cost,
            )

        # Step 4a: schema layer check on the assembled graph.
        try:
            schema_issues = schema_check.check(graph)
        except Exception as exc:  # noqa: BLE001
            _LOG.exception("schema_check.check raised unexpectedly on attempt %d", attempt_idx)
            return SceneResult(
                success=False,
                failure_reason="schema_invalid",
                schema_issues=[f"schema_check_exception: {type(exc).__name__}: {exc}"],
                inner_results=inner_results,
                total_cost_usd=total_cost,
            )
        if schema_issues:
            last_schema_issues = [
                f"{i.location}: {i.message}" for i in schema_issues
            ]
            last_mechanical_issues = {}
            last_layer = "schema"
            _LOG.info(
                "scene attempt %d: schema layer rejected (%d issues)",
                attempt_idx,
                len(schema_issues),
            )
            continue

        # Step 4b: T-2.4 mechanical pre-check on the assembled graph.
        try:
            mech_results = dialogue_validator.validate_graph_mechanical(
                graph, ontology=ontology
            )
        except Exception as exc:  # noqa: BLE001
            _LOG.exception(
                "validate_graph_mechanical raised unexpectedly on attempt %d",
                attempt_idx,
            )
            return SceneResult(
                success=False,
                failure_reason="mechanical_invalid",
                schema_issues=[f"mechanical_check_exception: {type(exc).__name__}: {exc}"],
                inner_results=inner_results,
                total_cost_usd=total_cost,
            )
        node_issues = {
            nid: [i for i in res.issues if i.severity == "error"]
            for nid, res in mech_results.items()
            if res.has_error
        }
        if node_issues:
            last_schema_issues = []
            last_mechanical_issues = node_issues
            last_layer = "mechanical"
            _LOG.info(
                "scene attempt %d: mechanical pre-check rejected (%d nodes flagged)",
                attempt_idx,
                len(node_issues),
            )
            continue

        # Step 6: both gates passed — attach generation_trace before
        # returning (ADR-019 / review 4.2).
        try:
            graph = _attach_generation_trace(graph, provider=provider)
        except Exception as exc:  # noqa: BLE001
            _LOG.exception(
                "generation_trace attachment failed on attempt %d", attempt_idx
            )
            return SceneResult(
                success=False,
                failure_reason="provider_error",
                schema_issues=[f"trace_attach_failed: {type(exc).__name__}: {exc}"],
                inner_results=inner_results,
                total_cost_usd=total_cost,
            )

        return SceneResult(
            success=True,
            graph=graph,
            inner_results=inner_results,
            total_cost_usd=total_cost,
        )

    # Outer attempts exhausted with schema/mechanical issues.
    failure_reason = "schema_invalid" if last_layer == "schema" else "mechanical_invalid"
    return SceneResult(
        success=False,
        failure_reason=failure_reason,
        schema_issues=last_schema_issues,
        mechanical_issues=last_mechanical_issues,
        inner_results=inner_results,
        total_cost_usd=total_cost,
    )


# ---------------------------------------------------------------------------
# Cost estimation
# ---------------------------------------------------------------------------


def estimate_scene_cost(
    *,
    npc_count: int,
    beat_count: int,
    expected_node_count: int,
    provider: LLMProvider,
) -> float:
    """Rough scene-level cost estimate for the ADR-012 budget guard.

    Models the strategy's call pattern:

      * 1 skeleton call (input ≈ few-shot + scene context; output ≈ 800
        tokens per `_SKELETON_OUTPUT_TOKEN_ESTIMATE`).
      * `expected_node_count` fill calls (input ≈ context + skeleton-
        derived intent; output ≈ 1500 tokens per
        `_FILL_OUTPUT_TOKEN_ESTIMATE`).

    The estimate is intentionally pessimistic — it's a *guard*, not a
    bill. Per-call reconciliation in `budget.reconcile_after_call`
    corrects the running total to actuals after each call returns.
    """
    skeleton_input = (
        _SKELETON_INPUT_TOKEN_BASE
        + npc_count * _SKELETON_INPUT_TOKEN_PER_NPC
        + beat_count * _SKELETON_INPUT_TOKEN_PER_BEAT
    )
    fill_input = (
        _FILL_INPUT_TOKEN_BASE
        + npc_count * _FILL_INPUT_TOKEN_PER_NPC
        + beat_count * _FILL_INPUT_TOKEN_PER_BEAT
    )
    skeleton_cost = provider.estimate_cost(
        skeleton_input, _SKELETON_OUTPUT_TOKEN_ESTIMATE
    )
    per_fill_cost = provider.estimate_cost(
        fill_input, _FILL_OUTPUT_TOKEN_ESTIMATE
    )
    return skeleton_cost + max(0, expected_node_count) * per_fill_cost


# ---------------------------------------------------------------------------
# SceneGraphContext assembly
# ---------------------------------------------------------------------------


def build_scene_graph_context(
    *,
    scene_setting: SceneSetting,
    target_beats: list[str],
    participating_npcs: list[str],
    ontology: dict,
) -> SceneGraphContext:
    """Resolve ontology entries into a SceneGraphContext.

    Pulls character cards by ID (preserving the caller's order), gathers
    location candidates from `entities[type=="location"]`, harvests
    `active_clocks` + `system_time` from the ontology top level, and
    derives `relations_matrix` by filtering the participating
    characters' `relations[]` to `narrative_weight in {core, minor}`
    (ADR-018: `context_only` is dropped before reaching the prompt).

    Missing fields degrade gracefully — characters not found in the
    ontology become a stub `{"id": "<id>"}` so the strategy can still
    render *something*; absent `system_time` falls back to the Stage-0
    `{scene_count: 0, long_rest_count: 0}` zero state.
    """
    entities = _entities(ontology)
    char_index = {
        e["id"]: e
        for e in entities
        if isinstance(e, dict) and e.get("type") == "character" and isinstance(e.get("id"), str)
    }

    participating_characters: list[dict] = []
    for npc_id in participating_npcs:
        card = char_index.get(npc_id)
        if card is not None:
            participating_characters.append(card)
        else:
            participating_characters.append({"id": npc_id})

    location_candidates = [
        e for e in entities
        if isinstance(e, dict) and e.get("type") == "location"
    ]

    relations_matrix: list[dict] = []
    participating_ids = set(participating_npcs)
    for card in participating_characters:
        rels = card.get("relations") if isinstance(card, dict) else None
        if not isinstance(rels, list):
            continue
        for rel in rels:
            if not isinstance(rel, dict):
                continue
            weight = rel.get("narrative_weight")
            if weight not in ("core", "minor"):
                continue
            entry = dict(rel)
            entry["from_character_ref"] = card.get("id")
            # Only surface relations that involve another participating
            # character — pulling in everyone the NPC has ever known
            # would explode the prompt with offstage anchors.
            target = rel.get("target_character_ref")
            if target in participating_ids:
                relations_matrix.append(entry)

    raw_clocks = ontology.get("clocks") if isinstance(ontology, dict) else None
    active_clocks = list(raw_clocks) if isinstance(raw_clocks, list) else []

    raw_st = ontology.get("system_time") if isinstance(ontology, dict) else None
    if isinstance(raw_st, dict):
        system_time = {
            "scene_count": raw_st.get("scene_count", 0),
            "long_rest_count": raw_st.get("long_rest_count", 0),
        }
    else:
        system_time = {"scene_count": 0, "long_rest_count": 0}

    return SceneGraphContext(
        scene_anchor=scene_setting.scene_anchor,
        chapter_ref=scene_setting.chapter_ref,
        location_candidates=location_candidates,
        primary_location_ref=scene_setting.primary_location_ref,
        participating_characters=participating_characters,
        relations_matrix=relations_matrix,
        active_clocks=active_clocks,
        system_time=system_time,
        target_beats=list(target_beats),
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _scene_budget_pre_flight(estimated_cost: float) -> None:
    """Pre-flight budget guard for an entire scene.

    Distinct from `budget.check_and_charge`: this does *not* write a row
    to the cost log. The strategy charges per LLM call internally (each
    via its own `check_and_charge`), so writing a row here would
    double-bill. We just raise BudgetExceeded if either:

      * the estimate alone exceeds DEFAULT_SCENE_BUDGET_USD (the per-
        scene cap), or
      * today's running total plus the estimate would exceed
        DAILY_BUDGET_USD.
    """
    scene_cap = _scene_budget_usd()
    if estimated_cost > scene_cap:
        raise BudgetExceeded(
            f"per-scene budget exceeded: ${estimated_cost:.4f} > ${scene_cap:.4f}"
        )
    daily = budget.daily_budget_usd()
    today = budget.today_total_usd()
    if today + estimated_cost > daily:
        raise BudgetExceeded(
            f"daily budget would be exceeded by this scene: today=${today:.4f} "
            f"+ ${estimated_cost:.4f} > ${daily:.4f}"
        )


def _scene_budget_usd() -> float:
    """Per-scene cap, override-able via `SCENE_BUDGET_USD` env var.

    Documented default $1.50 (STAGE_2_TASKS T-2.6 §3). Operators can
    raise / lower without touching code.
    """
    import os

    raw = os.environ.get("SCENE_BUDGET_USD")
    if raw is None or raw == "":
        return DEFAULT_SCENE_BUDGET_USD
    return float(raw)


def _entities(ontology: Any) -> list[Any]:
    if not isinstance(ontology, dict):
        return []
    raw = ontology.get("entities")
    if not isinstance(raw, list):
        return []
    return raw


# ---------------------------------------------------------------------------
# Outer-retry feedback (review 4.1)
# ---------------------------------------------------------------------------
#
# `generate_scene_skeleton_first` (T-2.5) does not currently expose a
# `outer_feedback` parameter, and that module is outside T-2.6's allowed
# write set. So this layer renders the previous attempt's failure summary
# and writes it to `_LOG.info` — operators reading batch-run logs see the
# audit trail, but the LLM does not see the feedback string until
# scene_strategies grows a feedback hook (follow-up).


def _render_outer_retry_feedback(
    last_layer: str,
    last_schema_issues: list[str],
    last_mechanical_issues: dict[str, list[ValidationIssue]],
) -> str:
    """Format the previous attempt's failures for log + future prompt use.

    Stable, structured text suitable for either
    (a) a human reviewer scanning batch logs, or
    (b) appending to a strategy prompt once scene_strategies exposes a
        feedback hook. Returned string is short (truncated at ~30 issue
        lines) so log lines stay readable.
    """
    lines: list[str] = []
    if last_layer == "schema" and last_schema_issues:
        lines.append("[OUTER_RETRY_FEEDBACK · schema layer rejected last attempt]")
        for issue in last_schema_issues[:30]:
            lines.append(f"  - {issue}")
        if len(last_schema_issues) > 30:
            lines.append(f"  …and {len(last_schema_issues) - 30} more")
    elif last_layer == "mechanical" and last_mechanical_issues:
        total = sum(len(v) for v in last_mechanical_issues.values())
        lines.append(
            f"[OUTER_RETRY_FEEDBACK · mechanical pre-check rejected last attempt: "
            f"{len(last_mechanical_issues)} nodes / {total} issues]"
        )
        printed = 0
        for nid, issues in last_mechanical_issues.items():
            for i in issues:
                if printed >= 30:
                    break
                lines.append(f"  - {nid} {i.field_path}: {i.code} — {i.message}")
                printed += 1
            if printed >= 30:
                break
        if total > printed:
            lines.append(f"  …and {total - printed} more")
    else:
        lines.append("[OUTER_RETRY_FEEDBACK · (no prior issue captured)]")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# generation_trace attachment (review 4.2 / ADR-019)
# ---------------------------------------------------------------------------


def _attach_generation_trace(graph: dict, *, provider: LLMProvider) -> dict:
    """Write `generation_trace.slot_assignments = {}` to every node.

    ADR-019 + SCHEMA_v0.3.md §6: T-2.6 must persist abstract slot →
    concrete character mappings on each generated node. 阶段 2 does
    *not* implement dynamic role swapping, so the map is empty here —
    but the field's *presence* is the contract that matters: downstream
    review tooling and cross-scene re-assembly need to rely on the trace
    being there.

    The six v0.1.x trace keys (source / generated_at / model_id /
    prompt_hash / reviewed_by / reviewed_at) are also normalised:

      * `source` is forced to `"llm"` because every node here came out
        of `scene_strategies` → `generate_node` → LLM. Existing
        `human` traces would only appear on author-imported scenes,
        which don't go through this code path.
      * `generated_at` is UTC ISO 8601 (timezone-aware) at attach time.
      * `model_id` is taken from `provider.model_id` (matching the
        `getattr(..., "unknown")` fallback used in generate_node).
      * `prompt_hash` is set to `None` — T-2.6 doesn't compute per-
        node prompt hashes (the strategy renders prompts internally).
      * `reviewed_by` / `reviewed_at` are `None` (review CLI fills
        these later).

    A shallow copy of the graph + nodes dict is returned so the strategy's
    object is not mutated in place.
    """
    if not isinstance(graph, dict):
        return graph
    nodes = graph.get("nodes")
    if not isinstance(nodes, dict):
        return graph

    now_iso = datetime.now(timezone.utc).isoformat()
    model_id = getattr(provider, "model_id", "unknown")

    new_nodes: dict[str, Any] = {}
    for node_id, node in nodes.items():
        if not isinstance(node, dict):
            new_nodes[node_id] = node
            continue
        node_copy = dict(node)
        existing_trace = node_copy.get("generation_trace")
        if isinstance(existing_trace, dict):
            trace = dict(existing_trace)
        else:
            trace = {}
        trace["source"] = "llm"
        trace.setdefault("generated_at", now_iso)
        trace.setdefault("model_id", model_id)
        trace.setdefault("prompt_hash", None)
        trace.setdefault("reviewed_by", None)
        trace.setdefault("reviewed_at", None)
        if not isinstance(trace.get("slot_assignments"), dict):
            trace["slot_assignments"] = {}
        node_copy["generation_trace"] = trace
        new_nodes[node_id] = node_copy

    new_graph = dict(graph)
    new_graph["nodes"] = new_nodes
    return new_graph


__all__ = [
    "SceneResult",
    "SceneSetting",
    "SceneGraphContext",
    "generate_scene",
    "estimate_scene_cost",
    "build_scene_graph_context",
    "DEFAULT_SCENE_BUDGET_USD",
]
