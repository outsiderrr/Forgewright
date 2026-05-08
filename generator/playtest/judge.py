"""LLM-as-judge for playtest paths (T-3.4 / ADR-022 / F10 + F21).

After the runner finishes a ``(scene, persona)`` batch, every
:class:`PlaytestPath` is scored by an LLM judge along four dimensions:

  1. ``narrative_coherence`` — does the trace tell a single coherent
     story given the persona's choices?
  2. ``persona_experience`` — would a player playing this persona
     find the trace satisfying / in-character?
  3. ``pacing`` — does the trace flow at the right speed (no
     premature endings, no padding)?
  4. ``ending_plausibility`` — does the final ``end`` node land
     plausibly given the path that got there?

Each dimension scores 0–25 (sum = ``path_score``, 0–100). The judge
also returns a list of severity findings using the F10 taxonomy:

  * ``critical`` — validator-missed illegal path / state-causal
    contradiction / ontology or character clash / severe player-
    outcome opacity. **Critical findings require author confirmation
    in the worst-scenes report; the runner never auto-passes them.**
  * ``major`` — significant narrative-quality issue (pacing, style,
    plausibility) that doesn't break game state.
  * ``minor`` — copy / phrasing / micro-tuning.

The severity definitions are baked into the prompt verbatim — F10
explicitly forbids relying on the model's natural-language sense of
the words alone.

After judge scoring finishes, :func:`aggregate_scene_summary` produces
the F21 scene-level row used to rank scenes worst-first in
``worst_scenes.md`` / ``worst_scenes.json``.
"""
from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from typing import Any, Callable

from generator import budget
from generator.budget import BudgetExceeded
from generator.llm_provider import LLMProvider, ProviderError, StructuredResponse
from generator.playtest.personas import Persona
from generator.playtest.runner import PathStep, PlaytestPath

JudgeCallObserver = Callable[[float, int, int], None]
"""Same shape as runner.CallObserver: ``(cost, input_tokens, output_tokens)``."""

_LOG = logging.getLogger(__name__)


# Stable rubric version embedded in run_manifest.json so a future
# replay can confirm the same prompt produced the worst-list. Bump this
# any time the dimensions / severity definitions change shape.
JUDGE_RUBRIC_VERSION = "v1"

_CHARS_PER_TOKEN = 4
_OUTPUT_TOKEN_ESTIMATE = 800

_DIMENSION_KEYS: tuple[str, ...] = (
    "narrative_coherence",
    "persona_experience",
    "pacing",
    "ending_plausibility",
)

_SEVERITY_VALUES: tuple[str, ...] = ("critical", "major", "minor")

# Canonical severity definitions — must mirror the prompt text exactly.
_SEVERITY_DEFINITIONS: dict[str, str] = {
    "critical": (
        "validator-missed illegal path, state-causal contradiction, "
        "ontology / character direct clash, severe player-outcome opacity"
    ),
    "major": (
        "significant narrative-quality issue (pacing, style, plausibility) "
        "that does not break game state"
    ),
    "minor": "copy, phrasing, or micro-tuning",
}


JUDGE_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "required": ["path_score", "dimensions", "severity_findings"],
    "properties": {
        "path_score": {"type": "integer", "minimum": 0, "maximum": 100},
        "dimensions": {
            "type": "object",
            "required": list(_DIMENSION_KEYS),
            "properties": {
                key: {"type": "integer", "minimum": 0, "maximum": 25}
                for key in _DIMENSION_KEYS
            },
        },
        "severity_findings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["severity", "description"],
                "properties": {
                    "severity": {
                        "type": "string",
                        "enum": list(_SEVERITY_VALUES),
                    },
                    "description": {"type": "string"},
                },
            },
        },
        "rationale": {"type": "string"},
    },
}


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------


_JUDGE_SYSTEM_PROMPT = (
    "You are the Forgewright playtest judge. Score one persona's "
    "walkthrough of one branching narrative scene against the rubric "
    "below. Respond ONLY with the JSON object the schema requires."
)


def _format_severity_block() -> str:
    """Render the severity taxonomy block injected into the prompt.

    F10: definitions written into the prompt, not left to the model's
    natural-language interpretation.
    """
    lines = ["### Severity taxonomy (use exactly these definitions)"]
    for sev in _SEVERITY_VALUES:
        lines.append(f"- **{sev}**: {_SEVERITY_DEFINITIONS[sev]}")
    lines.append(
        "Critical findings will be surfaced for author confirmation; do "
        "not over-flag minor issues as critical."
    )
    return "\n".join(lines)


def _format_step_block(steps: list[PathStep]) -> str:
    """Render the path's step trace as a compact text block.

    The judge receives node_id → option_id → reasoning, which is enough
    to score coherence + persona experience without overflowing the
    prompt budget on long paths.
    """
    if not steps:
        return "(empty path)"
    lines: list[str] = []
    for idx, step in enumerate(steps):
        opt = step.option_id or "(end)"
        reasoning = (step.reasoning or "").strip().replace("\n", " ")
        if reasoning:
            reasoning_clip = reasoning[:160]
            lines.append(
                f"- step {idx}: {step.node_id} → {opt} (reasoning: {reasoning_clip})"
            )
        else:
            lines.append(f"- step {idx}: {step.node_id} → {opt}")
    return "\n".join(lines)


def build_judge_user_prompt(
    *,
    scene: dict,
    persona: Persona,
    path: PlaytestPath,
) -> str:
    """Render the per-path judge prompt.

    Includes:
      * persona id / display_name / traits
      * scene id + entry_node_id + node count
      * path trace (steps with chosen options + reasoning)
      * reach status + final node + any failure_reason
      * severity taxonomy block (F10)
      * the four dimensions with score ranges
    """
    favors = ", ".join(persona.favors) or "(none)"
    avoids = ", ".join(persona.avoids) or "(none)"
    traits = ", ".join(persona.base_traits) or "(none)"
    scene_id = scene.get("graph_id") or path.scene_id or "unknown"
    nodes = scene.get("nodes") or {}
    node_count = len(nodes)
    final_state = path.steps[-1].state_after if path.steps else {}

    return (
        f"## Persona under test\n"
        f"- persona_id: {persona.persona_id}\n"
        f"- display_name: {persona.display_name}\n"
        f"- base_traits: {traits}\n"
        f"- favors: {favors}\n"
        f"- avoids: {avoids}\n"
        f"\n"
        f"## Scene\n"
        f"- scene_id: {scene_id}\n"
        f"- entry_node_id: {scene.get('entry_node_id', '?')}\n"
        f"- node_count: {node_count}\n"
        f"\n"
        f"## Path trace ({len(path.steps)} step(s))\n"
        f"{_format_step_block(path.steps)}\n"
        f"\n"
        f"## Path outcome\n"
        f"- reached_end: {path.reached_end}\n"
        f"- end_node_id: {path.end_node_id or '(none)'}\n"
        f"- failure_reason: {path.failure_reason or '(none)'}\n"
        f"- error: {path.error or '(none)'}\n"
        f"- final_state (compact): "
        f"{json.dumps(final_state, ensure_ascii=False)[:600]}\n"
        f"\n"
        f"## Rubric\n"
        f"Score four dimensions, each 0-25 integer. ``path_score`` "
        f"is the sum (0-100).\n"
        f"- narrative_coherence: does the trace tell a single coherent "
        f"story given the persona's choices?\n"
        f"- persona_experience: would a player playing this persona find "
        f"the trace satisfying and in-character?\n"
        f"- pacing: does the trace flow at the right speed (no premature "
        f"endings, no padding)?\n"
        f"- ending_plausibility: does the final end node land plausibly "
        f"given the path that got there?\n"
        f"\n"
        f"{_format_severity_block()}\n"
        f"\n"
        f"List every finding in ``severity_findings``. Empty list is "
        f"allowed when the path is clean. Provide a ``rationale`` "
        f"summarising the score in ≤ 2 sentences."
    )


# ---------------------------------------------------------------------------
# One judge call (budget-gated)
# ---------------------------------------------------------------------------


def judge_path(
    path: PlaytestPath,
    *,
    scene: dict,
    persona: Persona,
    provider: LLMProvider,
    observer: JudgeCallObserver | None = None,
) -> tuple[PlaytestPath, float]:
    """Score one path; mutates and returns the same :class:`PlaytestPath`.

    Returns ``(path, actual_cost_usd)``.
    Raises :class:`BudgetExceeded` to abort the batch.
    Raises :class:`ProviderError` on transport / decode failure — the
    caller decides whether to skip or abort. (The CLI wraps this in a
    try/except so a single bad path doesn't kill the batch.)

    ``observer`` mirrors the runner's ``CallObserver`` contract:
    ``(cost, input_tokens, output_tokens) -> None``. Lets the CLI
    three-way guard count judge calls toward the batch totals
    without re-reading the cost log.
    """
    user_prompt = build_judge_user_prompt(
        scene=scene, persona=persona, path=path
    )
    input_tokens_est = max(
        1, len(_JUDGE_SYSTEM_PROMPT + user_prompt) // _CHARS_PER_TOKEN
    )
    estimated_cost = provider.estimate_cost(
        input_tokens_est, _OUTPUT_TOKEN_ESTIMATE
    )
    record_id = budget.check_and_charge(
        estimated_cost,
        model_id=getattr(provider, "model_id", "unknown"),
        input_tokens=input_tokens_est,
        output_tokens=_OUTPUT_TOKEN_ESTIMATE,
    )

    try:
        response: StructuredResponse = provider.generate_structured(
            _JUDGE_SYSTEM_PROMPT, user_prompt, JUDGE_RESPONSE_SCHEMA
        )
    except ProviderError:
        budget.refund_estimated(record_id, reason="judge_provider_error")
        raise
    except BaseException:
        budget.refund_estimated(record_id, reason="judge_unexpected_error")
        raise

    actual_cost = provider.estimate_cost(response.input_tokens, response.output_tokens)
    budget.reconcile_after_call(
        record_id,
        actual_input_tokens=response.input_tokens,
        actual_output_tokens=response.output_tokens,
        actual_cost_usd=actual_cost,
    )

    _apply_judge_content_to_path(path, response.content or {})
    # Notify observer after the path is mutated. Letting observer-driven
    # exceptions (BudgetExceeded / GuardTripped from a future per-call
    # guard) propagate is intentional — silent swallow would defeat the
    # safety net (B-review 3.2).
    if observer is not None:
        observer(actual_cost, response.input_tokens, response.output_tokens)
    return path, actual_cost


def _apply_judge_content_to_path(path: PlaytestPath, content: dict) -> None:
    """Project a structured judge response into the :class:`PlaytestPath`.

    Tolerates partial responses: missing ``dimensions`` keys leave the
    path's dim slot blank but still record whatever ``path_score`` was
    returned, so a degraded judge response doesn't poison the whole
    batch.
    """
    raw_score = content.get("path_score")
    try:
        path.judge_score = float(raw_score) if raw_score is not None else None
    except (TypeError, ValueError):
        path.judge_score = None

    dims = content.get("dimensions") or {}
    clean_dims: dict[str, float] = {}
    if isinstance(dims, dict):
        for k in _DIMENSION_KEYS:
            v = dims.get(k)
            try:
                if v is not None:
                    clean_dims[k] = float(v)
            except (TypeError, ValueError):
                continue
    path.judge_dimensions = clean_dims

    findings_raw = content.get("severity_findings") or []
    findings: list[dict] = []
    crit = maj = minr = 0
    if isinstance(findings_raw, list):
        for entry in findings_raw:
            if not isinstance(entry, dict):
                continue
            sev = entry.get("severity")
            desc = entry.get("description") or ""
            if sev not in _SEVERITY_VALUES:
                continue
            if not isinstance(desc, str):
                desc = str(desc)
            findings.append({"severity": sev, "description": desc})
            if sev == "critical":
                crit += 1
            elif sev == "major":
                maj += 1
            elif sev == "minor":
                minr += 1
    path.severity_findings = findings
    path.critical_count = crit
    path.major_count = maj
    path.minor_count = minr

    rationale = content.get("rationale")
    path.judge_rationale = rationale if isinstance(rationale, str) else None


# ---------------------------------------------------------------------------
# Aggregation + ranking
# ---------------------------------------------------------------------------


@dataclass
class SceneAggregate:
    """One scene's worst-list summary row.

    ``scene_quality_score`` is a single rank-friendly composite of the
    three intuitive measures (mean / min / critical_count). The
    formula is intentionally simple and explained in the markdown
    report so the author can sanity-check its ordering.
    """

    scene_id: str
    n_paths: int
    n_paths_judged: int
    n_paths_failed: int
    mean_path_score: float | None
    min_path_score: float | None
    max_path_score: float | None
    critical_count: int
    major_count: int
    minor_count: int
    scene_quality_score: float | None
    worst_path_summaries: list[dict] = field(default_factory=list)
    critical_findings: list[dict] = field(default_factory=list)


def _path_sort_key(path: PlaytestPath) -> tuple:
    """Sort tuple: lowest score / most criticals / failed first.

    A path with no judge_score (judge crashed) sorts to the worst end
    by treating its score as -1; a critical-heavy path with an okay
    score is ranked above a critical-light one with the same score.
    """
    score = path.judge_score if path.judge_score is not None else -1.0
    return (
        0 if path.error else 1,            # error paths first (worst)
        score,                              # ascending: low score = worse
        -path.critical_count,               # more criticals = worse → larger negative first
        -path.major_count,
        -path.minor_count,
        path.path_id,                       # tie-break for determinism
    )


def rank_paths_worst_first(paths: list[PlaytestPath]) -> list[PlaytestPath]:
    """Sort paths so worst comes first.

    Stable: identical paths keep their input order. Used both by the
    full ``worst_paths.jsonl`` writer and the per-scene worst-N
    summariser.
    """
    return sorted(paths, key=_path_sort_key)


def aggregate_scene_summary(
    scene_id: str,
    paths: list[PlaytestPath],
    *,
    worst_paths_top_n: int = 10,
) -> SceneAggregate:
    """Roll a list of paths up into a scene-level summary.

    ``worst_paths_top_n`` controls how many paths' compact summaries
    are embedded in the scene aggregate (used by the markdown
    rendering). Critical findings are surfaced at the scene level
    regardless of which path they came from so the author can confirm
    them in one pass.
    """
    n_paths = len(paths)
    judged = [p for p in paths if p.judge_score is not None]
    failed = [p for p in paths if p.error or p.failure_reason]
    scores = [p.judge_score for p in judged if p.judge_score is not None]
    mean_score = sum(scores) / len(scores) if scores else None
    min_score = min(scores) if scores else None
    max_score = max(scores) if scores else None
    crit = sum(p.critical_count for p in paths)
    maj = sum(p.major_count for p in paths)
    minr = sum(p.minor_count for p in paths)

    if mean_score is not None and min_score is not None:
        # Composite intuition:
        #   start from mean, dock 5 points per critical,
        #   add a half-weighted "min path" pull so a single
        #   catastrophic path still hurts the scene.
        composite = mean_score - 5.0 * crit + 0.3 * (min_score - mean_score)
    else:
        composite = None

    ranked = rank_paths_worst_first(paths)
    worst_summaries: list[dict] = []
    for p in ranked[:worst_paths_top_n]:
        worst_summaries.append(
            {
                "path_id": p.path_id,
                "persona_id": p.persona_id,
                "judge_score": p.judge_score,
                "critical_count": p.critical_count,
                "major_count": p.major_count,
                "minor_count": p.minor_count,
                "reached_end": p.reached_end,
                "failure_reason": p.failure_reason,
                "error": p.error,
            }
        )
    critical_findings: list[dict] = []
    for p in paths:
        for finding in p.severity_findings:
            if finding.get("severity") == "critical":
                critical_findings.append(
                    {
                        "path_id": p.path_id,
                        "persona_id": p.persona_id,
                        "description": finding.get("description", ""),
                    }
                )

    return SceneAggregate(
        scene_id=scene_id,
        n_paths=n_paths,
        n_paths_judged=len(judged),
        n_paths_failed=len(failed),
        mean_path_score=mean_score,
        min_path_score=min_score,
        max_path_score=max_score,
        critical_count=crit,
        major_count=maj,
        minor_count=minr,
        scene_quality_score=composite,
        worst_path_summaries=worst_summaries,
        critical_findings=critical_findings,
    )


def render_worst_scenes_markdown(
    aggregates: list[SceneAggregate],
    *,
    playtest_id: str,
) -> str:
    """Render the F21 ``worst_scenes.md`` from per-scene aggregates.

    Scenes are ordered worst-first (lowest ``scene_quality_score``).
    Critical findings get a dedicated callout block — the markdown is
    the artifact the author reads to confirm critical issues.
    """
    ranked = sorted(
        aggregates,
        key=lambda a: (
            a.scene_quality_score if a.scene_quality_score is not None else -1e9,
            -a.critical_count,
            a.scene_id,
        ),
    )
    lines: list[str] = []
    lines.append(f"# Playtest worst-scenes report — `{playtest_id}`")
    lines.append("")
    lines.append(
        "Scene quality score = mean(path_score) − 5·critical_count + "
        "0.3·(min_path_score − mean_path_score). Lower = worse."
    )
    lines.append("")
    lines.append(
        "**Critical findings require author confirmation (ADR-022 / F10).** "
        "The LLM judge surfaces them; the author signs off in this report."
    )
    lines.append("")
    lines.append("## Summary table")
    lines.append("")
    lines.append(
        "| scene_id | quality | mean | min | max | critical | major | minor | judged/total |"
    )
    lines.append("|---|---|---|---|---|---|---|---|---|")
    for agg in ranked:
        q = (
            f"{agg.scene_quality_score:.1f}"
            if agg.scene_quality_score is not None
            else "—"
        )
        mean_s = f"{agg.mean_path_score:.1f}" if agg.mean_path_score is not None else "—"
        min_s = f"{agg.min_path_score:.0f}" if agg.min_path_score is not None else "—"
        max_s = f"{agg.max_path_score:.0f}" if agg.max_path_score is not None else "—"
        lines.append(
            f"| `{agg.scene_id}` | {q} | {mean_s} | {min_s} | {max_s} | "
            f"{agg.critical_count} | {agg.major_count} | {agg.minor_count} | "
            f"{agg.n_paths_judged}/{agg.n_paths} |"
        )
    lines.append("")

    lines.append("## Critical findings (author confirmation required)")
    lines.append("")
    has_critical = any(agg.critical_findings for agg in ranked)
    if not has_critical:
        lines.append("(no critical findings)")
    else:
        for agg in ranked:
            if not agg.critical_findings:
                continue
            lines.append(f"### `{agg.scene_id}`")
            for finding in agg.critical_findings:
                desc = finding.get("description", "").replace("\n", " ")
                lines.append(
                    f"- path `{finding['path_id']}` "
                    f"(persona `{finding['persona_id']}`): {desc}"
                )
            lines.append("")
    lines.append("")

    lines.append("## Worst paths per scene")
    lines.append("")
    for agg in ranked:
        lines.append(f"### `{agg.scene_id}`")
        if not agg.worst_path_summaries:
            lines.append("(no paths)")
            lines.append("")
            continue
        lines.append(
            "| rank | path_id | persona | score | critical | major | minor | end | failure |"
        )
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for rank, summary in enumerate(agg.worst_path_summaries, start=1):
            score = (
                f"{summary['judge_score']:.0f}"
                if summary.get("judge_score") is not None
                else "—"
            )
            failure = (summary.get("failure_reason") or summary.get("error") or "—")
            failure = str(failure).replace("|", "/").replace("\n", " ")[:80]
            lines.append(
                f"| {rank} | `{summary['path_id']}` | "
                f"`{summary['persona_id']}` | {score} | "
                f"{summary['critical_count']} | {summary['major_count']} | "
                f"{summary['minor_count']} | "
                f"{'yes' if summary.get('reached_end') else 'no'} | "
                f"{failure} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def render_worst_scenes_json(
    aggregates: list[SceneAggregate],
    *,
    playtest_id: str,
) -> dict:
    """JSON sibling of :func:`render_worst_scenes_markdown`.

    Same data, programmatically consumable. T-3.6b's review UI
    integration reads this directly to render the playtest panel.
    """
    return {
        "playtest_id": playtest_id,
        "rubric_version": JUDGE_RUBRIC_VERSION,
        "scenes": [asdict(agg) for agg in aggregates],
    }


__all__ = [
    "JUDGE_RESPONSE_SCHEMA",
    "JUDGE_RUBRIC_VERSION",
    "JudgeCallObserver",
    "SceneAggregate",
    "aggregate_scene_summary",
    "build_judge_user_prompt",
    "judge_path",
    "rank_paths_worst_first",
    "render_worst_scenes_json",
    "render_worst_scenes_markdown",
]
