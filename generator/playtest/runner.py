"""Playtest path simulator (T-3.4 / ADR-022).

For each ``(scene, persona)`` pair, simulate ``n_paths`` walkthroughs
from ``entry_node_id`` to an ``end`` node by asking an LLM to roleplay
the persona at every decision point. Each path records its trace
(node_ids + option_ids + state evolution), the LLM call count, the
cumulative cost, and a per-path duration so the calibration step (1
scene × 1 persona × 5 paths) can derive realistic budget ceilings
before any full 5×20 batch fires.

Reuses /validator/sampling.py's loop shape — per the T-3.4 prompt's
"复用 /validator/sampling.py 路径生成器" directive — but swaps
``random.choice(valid_options)`` for an LLM persona-decision call.
We don't import ``validate_graph_sampling`` itself because that
function bakes in random selection with no strategy hook; the cost of
duplicating the ~30-line loop is lower than modifying validator/ (off-
limits per the task's module boundary).

State APIs come from the public ``state.conditions`` / ``state.effects``
/ ``state.world_state`` modules. ``normalize_effect_op`` is the one
helper we borrow from ``validator.graph_validation`` (already used by
sampling.py the same way).

Concurrency: paths within a ``(scene, persona)`` batch are independent
— :func:`run_paths_async` schedules them with ``asyncio.gather`` over
``asyncio.to_thread`` wrappers so a sync ``LLMProvider`` doesn't block
the loop. The framework still cooperates with single-threaded provider
implementations; we only rely on the GIL releasing during the network
call.

Failure handling: a single path failing on ``ProviderError`` (or a
malformed model response) yields a ``PlaytestPath(error=...)`` row
rather than aborting the batch. ``BudgetExceeded`` propagates out so
the CLI three-way guard can write whatever was completed and abort.
"""
from __future__ import annotations

import asyncio
import dataclasses
import json
import logging
import time
import uuid
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Callable

from generator import budget
from generator.budget import BudgetExceeded
from generator.llm_provider import LLMProvider, ProviderError, StructuredResponse
from generator.playtest.personas import Persona
from state.conditions import evaluate_condition
from state.effects import apply_effect
from state.world_state import WorldState
from validator.graph_validation import normalize_effect_op

_LOG = logging.getLogger(__name__)

# Same heuristic as scene_ai_judge / generate_node — providers do their
# own counting; the pre-call estimate just needs to be in the right
# ballpark for the budget guard.
_CHARS_PER_TOKEN = 4
# Persona decisions return a single option_id + short reasoning; output
# token cap is comfortably small.
_DECISION_OUTPUT_TOKEN_ESTIMATE = 150

# Hard cap on path length. Stage-2 baseline scenes top out at ~10
# nodes; 50 leaves headroom for cycles in long scenes without letting
# a runaway loop chew through the budget.
DEFAULT_MAX_PATH_STEPS = 50


# ---------------------------------------------------------------------------
# Public dataclasses
# ---------------------------------------------------------------------------


@dataclass
class PathStep:
    """One node visit + the option chosen leaving it.

    ``option_id`` records the option the persona chose to LEAVE this
    node. It is ``None`` for the entry node before the persona has
    decided, and ``None`` for the final ``end`` node (which has no
    outgoing options). ``state_after`` is a snapshot of the world
    state right after this node's ``on_enter_effects`` apply, so the
    final step (end node) carries the post-end-on-enter state.

    F20 replay fields (B-review 4.1):
      * ``option_set`` — the full set of valid options the LLM saw at
        this decision (option_id + text + target_node_id).
      * ``raw_choice`` — the provider's raw_text response (the JSON
        the model emitted) so a future replay can compare against the
        canonical schema-parsed ``option_id``.
    """

    node_id: str
    option_id: str | None
    state_after: dict
    valid_option_ids: list[str] = field(default_factory=list)
    reasoning: str | None = None
    option_set: list[dict] = field(default_factory=list)
    raw_choice: str | None = None


@dataclass
class PlaytestPath:
    """One persona walkthrough of one scene.

    ``judge_score`` / ``severity_findings`` start unset; the judge
    layer (:mod:`generator.playtest.judge`) populates them after the
    runner finishes. Keeping them on the same dataclass lets the CLI
    write a single ``worst_paths.jsonl`` row.
    """

    path_id: str
    persona_id: str
    scene_id: str
    steps: list[PathStep]
    reached_end: bool
    end_node_id: str | None
    failure_reason: str | None
    llm_calls: int
    cost_usd: float
    duration_seconds: float
    error: str | None = None
    judge_score: float | None = None
    severity_findings: list[dict] = field(default_factory=list)
    judge_dimensions: dict[str, float] = field(default_factory=dict)
    judge_rationale: str | None = None
    critical_count: int = 0
    major_count: int = 0
    minor_count: int = 0


# ---------------------------------------------------------------------------
# Decision schema + prompt
# ---------------------------------------------------------------------------


def _decision_schema(valid_option_ids: list[str]) -> dict:
    """JSON schema for one persona decision call.

    The ``chosen_option_id`` enum is the source of truth — even if the
    model rationalises a different choice in ``reasoning``, structured
    output guarantees we get one of the valid ids back. Empty
    ``valid_option_ids`` is invalid (caller should detect deadlock
    before calling) — we still build a permissive schema so a
    misconfigured caller gets a clean ProviderError instead of a
    schema crash.
    """
    enum = list(valid_option_ids) if valid_option_ids else [""]
    return {
        "type": "object",
        "required": ["chosen_option_id", "reasoning"],
        "properties": {
            "chosen_option_id": {"type": "string", "enum": enum},
            "reasoning": {"type": "string"},
        },
    }


_PERSONA_SYSTEM_PROMPT = (
    "You are a Forgewright playtest bot. You roleplay a single persona "
    "to choose dialogue options in a branching narrative scene. Pick "
    "exactly one option_id from the listed enum. Stay in character; "
    "respond ONLY with the JSON the schema requires. Brief reasoning "
    "(1–2 sentences) is helpful for replay; long monologues are not."
)


def _persona_decision_user_prompt(
    *,
    persona: Persona,
    scene_id: str,
    current_node: dict,
    valid_options: list[dict],
    path_so_far: list[PathStep],
) -> str:
    """Render a per-step decision prompt.

    Includes:
      * persona id / display name / traits / favors+avoids
      * scene id + current node narration + speaker hint
      * valid options (option_id + text + condition summary)
      * compact path-so-far trace (last ≤ 5 nodes; full trace would
        balloon prompt size for long scenes)
    """
    favors = ", ".join(persona.favors) or "(none)"
    avoids = ", ".join(persona.avoids) or "(none)"
    traits = ", ".join(persona.base_traits) or "(none)"
    augmented = persona.augmented_description or "(no augmented description)"

    options_block_parts: list[str] = []
    for opt in valid_options:
        opt_id = opt.get("option_id", "?")
        opt_text = opt.get("text", "")
        # condition summary is informational — option is in `valid` so
        # the condition was satisfied at the runner layer; we surface
        # it so the persona can weigh what the option signals.
        cond = opt.get("condition")
        cond_hint = ""
        if isinstance(cond, dict):
            cond_hint = f"  (gated by: {json.dumps(cond, ensure_ascii=False)[:160]})"
        options_block_parts.append(f"- {opt_id}: {opt_text}{cond_hint}")
    options_block = "\n".join(options_block_parts) or "(none)"

    trace_tail = path_so_far[-5:]
    if trace_tail:
        trace_lines = [
            f"  - {step.node_id} → {step.option_id or '(end)'}"
            for step in trace_tail
        ]
        trace_block = "\n".join(trace_lines)
    else:
        trace_block = "  (this is the entry node — no prior steps)"

    narration = current_node.get("narration") or "(no narration)"
    speaker = current_node.get("speaker_ref") or "(none)"

    return (
        f"## Persona\n"
        f"- persona_id: {persona.persona_id}\n"
        f"- display_name: {persona.display_name}\n"
        f"- base_traits: {traits}\n"
        f"- favors: {favors}\n"
        f"- avoids: {avoids}\n"
        f"- augmented_description: {augmented}\n"
        f"\n"
        f"## Scene\n"
        f"- scene_id: {scene_id}\n"
        f"- current node: {current_node.get('node_id', '?')}\n"
        f"- speaker: {speaker}\n"
        f"\n"
        f"## Narration\n"
        f"{narration}\n"
        f"\n"
        f"## Path so far\n"
        f"{trace_block}\n"
        f"\n"
        f"## Valid options\n"
        f"{options_block}\n"
        f"\n"
        f"Pick one option_id consistent with the persona. Respond with the "
        f"JSON the schema requires (chosen_option_id + brief reasoning)."
    )


# ---------------------------------------------------------------------------
# State helpers (mirrors validator.sampling, public APIs only)
# ---------------------------------------------------------------------------


def _flatten_initial(d: dict, prefix: str = "") -> dict[str, Any]:
    """Same flatten convention as validator.sampling._flatten_initial.

    Accepts either dotted keys (``{"flag.foo": True}``) or nested dicts
    (``{"flag": {"foo": True}}``). Re-implemented here rather than
    imported from a private name in validator.sampling.
    """
    out: dict[str, Any] = {}
    for k, v in d.items():
        path = f"{prefix}.{k}" if prefix else k
        if isinstance(v, dict) and "." not in k:
            out.update(_flatten_initial(v, path))
        else:
            out[path] = v
    return out


def _seed_state(initial_state: dict | None) -> WorldState:
    state = WorldState()
    if not initial_state:
        return state
    for path, value in _flatten_initial(initial_state).items():
        state.set(path, value)
    return state


def _apply_on_enter(state: WorldState, node: dict) -> None:
    for eff in (node.get("on_enter_effects") or []):
        try:
            apply_effect(state, normalize_effect_op(eff))
        except Exception:
            # Same tolerance as validator.sampling — schema-illegal
            # effects are reported by the 2A validator, not here.
            pass


def _apply_option_effects(state: WorldState, effects: Any) -> None:
    if not isinstance(effects, list):
        return
    for eff in effects:
        try:
            apply_effect(state, normalize_effect_op(eff))
        except Exception:
            pass


def _evaluate_or_false(state: WorldState, cond: Any) -> bool:
    if cond is None:
        return True
    if not isinstance(cond, dict):
        return False
    try:
        return evaluate_condition(state, cond)
    except Exception:
        return False


# ---------------------------------------------------------------------------
# One LLM call (budget-gated)
# ---------------------------------------------------------------------------


CallObserver = Callable[[float, int, int], None]
"""Callback invoked after every successful LLM call.

Signature: ``(actual_cost_usd, input_tokens, output_tokens) -> None``.
Used by the CLI three-way guard to bump call/cost counters and
short-circuit on the next path if a ceiling is reached.
"""


def _call_persona_decision(
    *,
    provider: LLMProvider,
    persona: Persona,
    scene_id: str,
    current_node: dict,
    valid_options: list[dict],
    path_so_far: list[PathStep],
) -> tuple[str, str, float, int, int, str]:
    """Make one budget-gated decision call.

    Returns ``(chosen_option_id, reasoning, actual_cost_usd,
    input_tokens, output_tokens, raw_text)``.
    Raises :class:`BudgetExceeded` so the CLI can stop the batch
    cleanly. Raises :class:`ProviderError` so the caller can decide
    whether to fail the path or skip the step.

    Observer notification was moved out of this function (B-review 3.2):
    the caller (:func:`run_path`) updates path-level counters AND the
    PathStep trace before calling observer, so observer-driven aborts
    leave both consistent.
    """
    user_prompt = _persona_decision_user_prompt(
        persona=persona,
        scene_id=scene_id,
        current_node=current_node,
        valid_options=valid_options,
        path_so_far=path_so_far,
    )
    valid_ids = [str(opt.get("option_id", "")) for opt in valid_options]
    schema = _decision_schema(valid_ids)

    input_tokens_est = max(
        1, len(_PERSONA_SYSTEM_PROMPT + user_prompt) // _CHARS_PER_TOKEN
    )
    output_tokens_est = _DECISION_OUTPUT_TOKEN_ESTIMATE
    estimated_cost = provider.estimate_cost(input_tokens_est, output_tokens_est)

    record_id = budget.check_and_charge(
        estimated_cost,
        model_id=getattr(provider, "model_id", "unknown"),
        input_tokens=input_tokens_est,
        output_tokens=output_tokens_est,
    )

    try:
        response: StructuredResponse = provider.generate_structured(
            _PERSONA_SYSTEM_PROMPT, user_prompt, schema
        )
    except ProviderError:
        budget.refund_estimated(record_id, reason="provider_error")
        raise
    except BaseException:
        budget.refund_estimated(record_id, reason="unexpected_error")
        raise

    actual_cost = provider.estimate_cost(response.input_tokens, response.output_tokens)
    budget.reconcile_after_call(
        record_id,
        actual_input_tokens=response.input_tokens,
        actual_output_tokens=response.output_tokens,
        actual_cost_usd=actual_cost,
    )

    content = response.content or {}
    chosen = content.get("chosen_option_id")
    reasoning = content.get("reasoning") or ""
    if not isinstance(chosen, str) or chosen not in valid_ids:
        # Schema enum should make this unreachable; surface as
        # ProviderError so the path falls into the same handling as
        # transport failures.
        raise ProviderError(
            f"persona decision returned invalid option_id={chosen!r}; "
            f"valid={valid_ids}"
        )
    return (
        chosen,
        reasoning if isinstance(reasoning, str) else "",
        actual_cost,
        response.input_tokens,
        response.output_tokens,
        response.raw_text,
    )


# ---------------------------------------------------------------------------
# Single path simulation
# ---------------------------------------------------------------------------


def run_path(
    scene: dict,
    persona: Persona,
    *,
    provider: LLMProvider,
    initial_state: dict | None = None,
    max_steps: int = DEFAULT_MAX_PATH_STEPS,
    observer: CallObserver | None = None,
    path_id: str | None = None,
) -> PlaytestPath:
    """Walk one path of ``scene`` driven by ``persona`` decisions.

    Returns a :class:`PlaytestPath` with the trace + accounting fields
    filled in. ``judge_score`` / ``severity_findings`` are left empty
    for the judge stage to populate. Raises :class:`BudgetExceeded`
    so the caller can abort the batch — every other failure mode
    (ProviderError, missing target, deadlock) is captured as
    ``failure_reason`` / ``error`` on the returned path.
    """
    pid = path_id or uuid.uuid4().hex[:12]
    nodes = scene.get("nodes") or {}
    entry = scene.get("entry_node_id")
    scene_id = scene.get("graph_id") or "unknown"
    started = time.monotonic()
    if not isinstance(entry, str) or entry not in nodes:
        return PlaytestPath(
            path_id=pid,
            persona_id=persona.persona_id,
            scene_id=scene_id,
            steps=[],
            reached_end=False,
            end_node_id=None,
            failure_reason="entry_node_id missing or invalid",
            llm_calls=0,
            cost_usd=0.0,
            duration_seconds=time.monotonic() - started,
        )

    state = _seed_state(initial_state)
    node_id = entry
    steps: list[PathStep] = []
    _apply_on_enter(state, nodes[entry])
    # Entry step: state_after captures the post-on_enter snapshot.
    # option_id stays None until the persona picks an option to leave
    # this node, at which point we mutate this same step in place.
    steps.append(
        PathStep(
            node_id=entry,
            option_id=None,
            state_after=deepcopy(state.as_dict()),
            valid_option_ids=[],
        )
    )

    success = False
    failure_reason: str | None = None
    error: str | None = None
    llm_calls = 0
    cost_usd = 0.0
    end_node_id: str | None = None

    for _step in range(max_steps):
        node = nodes.get(node_id) or {}
        if node.get("type") == "end":
            success = True
            end_node_id = node_id
            # End node was appended at the end of the previous
            # iteration with on_enter already applied; option_id stays
            # None because end nodes have no outgoing options.
            break
        options = node.get("options") or []
        valid: list[dict] = []
        for opt in options:
            if not isinstance(opt, dict):
                continue
            if _evaluate_or_false(state, opt.get("condition")):
                valid.append(opt)
        if not valid:
            failure_reason = "no valid option at non-end node (deadlock)"
            break

        valid_ids = [str(opt.get("option_id", "?")) for opt in valid]
        # F20 replay metadata (B-review 4.1): freeze the option set the
        # LLM saw at this node, in render order. Truncate text to keep
        # worst_paths.jsonl rows bounded but still meaningful.
        option_set = [
            {
                "option_id": str(opt.get("option_id", "")),
                "text": (opt.get("text") or "")[:240],
                "target_node_id": opt.get("target_node_id"),
            }
            for opt in valid
        ]
        try:
            (
                chosen_id,
                reasoning,
                call_cost,
                in_tok,
                out_tok,
                raw_text,
            ) = _call_persona_decision(
                provider=provider,
                persona=persona,
                scene_id=scene_id,
                current_node={**node, "node_id": node_id},
                valid_options=valid,
                path_so_far=steps,
            )
        except BudgetExceeded:
            # Re-raise: the CLI batch loop catches this and writes
            # whatever progress is available.
            raise
        except ProviderError as exc:
            error = f"ProviderError @ {node_id}: {exc}"
            failure_reason = "provider_error"
            break

        llm_calls += 1
        cost_usd += call_cost
        # Update the step we are LEAVING with the persona's choice
        # (B-review 4.2: option_id belongs to the step the persona is
        # leaving, not the target). This also persists the F20 replay
        # fields before we hand off to the observer / move on.
        steps[-1].option_id = chosen_id
        steps[-1].valid_option_ids = valid_ids
        steps[-1].reasoning = reasoning
        steps[-1].option_set = option_set
        steps[-1].raw_choice = raw_text

        # Notify observer AFTER path-level counters and the leaving
        # step have been updated. If the observer raises (e.g. a
        # future per-call guard), the path's recorded state is
        # internally consistent.
        if observer is not None:
            observer(call_cost, in_tok, out_tok)

        chosen_opt = next((o for o in valid if o.get("option_id") == chosen_id), None)
        if chosen_opt is None:  # pragma: no cover — schema should prevent
            error = f"chosen option_id {chosen_id!r} not in valid set"
            failure_reason = "invalid_option_choice"
            break

        _apply_option_effects(state, chosen_opt.get("effects"))
        target = chosen_opt.get("target_node_id")
        if not isinstance(target, str) or target not in nodes:
            failure_reason = (
                f"option {chosen_id!r}.target_node_id {target!r} missing or invalid"
            )
            break
        node_id = target
        # Apply on_enter BEFORE snapshotting state — this fixes B-review
        # 4.2's second concern: the end node's on_enter_effects now
        # land in final state_after.
        _apply_on_enter(state, nodes[node_id])
        steps.append(
            PathStep(
                node_id=node_id,
                option_id=None,
                state_after=deepcopy(state.as_dict()),
                valid_option_ids=[],
            )
        )
    else:
        failure_reason = f"exceeded max_path_steps={max_steps}"

    return PlaytestPath(
        path_id=pid,
        persona_id=persona.persona_id,
        scene_id=scene_id,
        steps=steps,
        reached_end=success,
        end_node_id=end_node_id,
        failure_reason=failure_reason,
        llm_calls=llm_calls,
        cost_usd=cost_usd,
        duration_seconds=time.monotonic() - started,
        error=error,
    )


# ---------------------------------------------------------------------------
# Async batch wrapper
# ---------------------------------------------------------------------------


async def run_paths_async(
    scene: dict,
    persona: Persona,
    *,
    n_paths: int,
    provider: LLMProvider,
    initial_state: dict | None = None,
    max_steps: int = DEFAULT_MAX_PATH_STEPS,
    observer: CallObserver | None = None,
    concurrency: int = 1,
) -> list[PlaytestPath]:
    """Run ``n_paths`` paths for one persona concurrently.

    ``concurrency`` defaults to 1 (sequential) since most providers
    rate-limit aggressively; T-3.5 will land a ``RateLimitedProvider``
    wrapper that lets the CLI safely raise this. Each path is wrapped
    in ``asyncio.to_thread`` so a sync provider doesn't block the
    loop.

    Propagates :class:`BudgetExceeded` from the first path that trips
    the daily / per-call gate; pending tasks are cancelled before the
    exception bubbles out. Per-path :class:`ProviderError` is captured
    on the path's ``error`` field — the batch keeps going.
    """
    if n_paths <= 0:
        return []
    sem = asyncio.Semaphore(max(1, concurrency))

    async def _one(idx: int) -> PlaytestPath:
        async with sem:
            return await asyncio.to_thread(
                run_path,
                scene,
                persona,
                provider=provider,
                initial_state=initial_state,
                max_steps=max_steps,
                observer=observer,
                path_id=f"{persona.persona_id}-{idx:03d}-{uuid.uuid4().hex[:6]}",
            )

    tasks = [asyncio.create_task(_one(i)) for i in range(n_paths)]
    try:
        results = await asyncio.gather(*tasks, return_exceptions=False)
    except BudgetExceeded:
        for t in tasks:
            if not t.done():
                t.cancel()
        # Drain so cancelled tasks don't leak warnings; we discard their
        # results since we're aborting the batch anyway.
        await asyncio.gather(*tasks, return_exceptions=True)
        raise
    return list(results)


def run_paths(
    scene: dict,
    persona: Persona,
    *,
    n_paths: int,
    provider: LLMProvider,
    initial_state: dict | None = None,
    max_steps: int = DEFAULT_MAX_PATH_STEPS,
    observer: CallObserver | None = None,
    concurrency: int = 1,
) -> list[PlaytestPath]:
    """Sync wrapper around :func:`run_paths_async`.

    The CLI calls this directly so ``main()`` stays synchronous.
    Tests prefer :func:`run_path` (single path) or call
    :func:`run_paths_async` from ``asyncio.run``.
    """
    return asyncio.run(
        run_paths_async(
            scene,
            persona,
            n_paths=n_paths,
            provider=provider,
            initial_state=initial_state,
            max_steps=max_steps,
            observer=observer,
            concurrency=concurrency,
        )
    )


def path_to_jsonl_dict(path: PlaytestPath) -> dict:
    """Project a :class:`PlaytestPath` to its JSONL row form.

    Used by the CLI to write ``worst_paths.jsonl``. Steps' state
    snapshots are kept verbose (full ``as_dict()`` per step) so the
    author can replay manually.
    """
    return {
        "path_id": path.path_id,
        "persona_id": path.persona_id,
        "scene_id": path.scene_id,
        "reached_end": path.reached_end,
        "end_node_id": path.end_node_id,
        "failure_reason": path.failure_reason,
        "llm_calls": path.llm_calls,
        "cost_usd": path.cost_usd,
        "duration_seconds": path.duration_seconds,
        "error": path.error,
        "judge_score": path.judge_score,
        "judge_dimensions": path.judge_dimensions,
        "judge_rationale": path.judge_rationale,
        "severity_findings": list(path.severity_findings),
        "critical_count": path.critical_count,
        "major_count": path.major_count,
        "minor_count": path.minor_count,
        "steps": [dataclasses.asdict(step) for step in path.steps],
    }


__all__ = [
    "CallObserver",
    "DEFAULT_MAX_PATH_STEPS",
    "PathStep",
    "PlaytestPath",
    "path_to_jsonl_dict",
    "run_path",
    "run_paths",
    "run_paths_async",
]
