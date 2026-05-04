"""AI judge runner for scene-level batches (T-2.8 §5 / critique 4.8).

CLI:

    python -m generator.scene_ai_judge --batch-dir <path> [--template <path>]

For each `success=True` row in `<batch-dir>/scene_results.jsonl`, this
runner asks the configured `LLMProvider` to score the assembled graph
twice — once in **lenient** mode and once in **strict** mode — using
the prompt template that T-2.9 lands at
`/generator/prompts/scene/REVIEW_PROMPT_AI_JUDGE_SCENE.md`. Both passes
share the same scoring schema (per-dimension 0/1/2 + advisory
recommendation); the lenient/strict difference is encoded in the
template via `{{PASS_MODE}}` substitution and is the prompt template's
responsibility — this runner just ferries the mode tag.

ADR-020 §6 authority note: the AI judge's `advisory` is **not** the
acceptance signal. The author's [A]/[R] in `scene_review_cli` is what
populates the acceptance-rate numerator. We surface advisory in the
report and feed it to scene_review_cli only as informational context.

Outputs land at:

  * `<batch-dir>/AI_JUDGE_REPORT.md`    — human-readable report
  * `<batch-dir>/AI_JUDGE_REPORT.json`  — machine-readable; picked up
                                          by scene_review_cli for the
                                          advisory display

Cost / safety: every call is gated by `budget.check_and_charge` (ADR-012).
The runner stops on `BudgetExceeded` and writes whatever it has so far.
"""
from __future__ import annotations

import argparse
import json
import logging
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Literal

from dotenv import load_dotenv

from generator import budget
from generator.budget import BudgetExceeded
from generator.llm_provider import LLMProvider, ProviderError, StructuredResponse

_LOG = logging.getLogger(__name__)

# Default template lives next to T-2.9's deliverables. We don't fail at
# import — the runner's error message is more useful than an
# ImportError. Operators pass --template to override.
DEFAULT_TEMPLATE_PATH = (
    Path(__file__).parent / "prompts" / "scene" / "REVIEW_PROMPT_AI_JUDGE_SCENE.md"
)

# Token-count heuristics, same 4-chars/token convention used elsewhere in
# the generator package. The judge response is structured + relatively
# small (≤ 30 dimensions × small score), so the output cap is modest.
_CHARS_PER_TOKEN = 4
_OUTPUT_TOKEN_ESTIMATE = 1200

PassMode = Literal["lenient", "strict"]
Advisory = Literal["accept", "reject", "marginal"]


# Response schema kept loose so the T-2.9 prompt can pick its own
# dimension labels without a code change. We require `dimensions` to be
# a string→number map and `advisory` to land in the canonical 3-value
# enum so downstream aggregation is deterministic.
_JUDGE_RESPONSE_SCHEMA: dict = {
    "type": "object",
    "required": ["scene_id", "dimensions", "advisory"],
    "properties": {
        "scene_id": {"type": "string"},
        "dimensions": {
            "type": "object",
            "additionalProperties": {"type": "number"},
        },
        "advisory": {"type": "string", "enum": ["accept", "reject", "marginal"]},
        "rationale": {"type": "string"},
    },
}


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass
class AIJudgeReport:
    pass1_lenient_scores: dict[str, dict[str, float]] = field(default_factory=dict)
    pass2_strict_scores: dict[str, dict[str, float]] = field(default_factory=dict)
    weakest_dimensions: list[tuple[str, float]] = field(default_factory=list)
    # Informational only; never the ADR-020 §6 acceptance-rate numerator.
    # Author [A]/[R] in scene_review_cli is the binding signal.
    advisory_recommendation: dict[str, Advisory] = field(default_factory=dict)
    rationales: dict[str, dict[str, str]] = field(default_factory=dict)
    total_cost_usd: float = 0.0
    stopped_early: bool = False
    skipped_scenes: list[str] = field(default_factory=list)


# Stable machine-readable disclaimer surfaced in AI_JUDGE_REPORT.json so
# T-2.12 / any future programmatic consumer can verify the file's
# advisory-only authority without parsing the markdown narrative.
_REPORT_METADATA: dict = {
    "advisory_authority": "informational_only",
    "acceptance_source": "scene_review_cli_author_A_R",
    "adr": "ADR-020 §6",
    "schema_version": "1",
}


# ---------------------------------------------------------------------------
# JSONL + serialisation helpers
# ---------------------------------------------------------------------------


def _read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    with open(path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows


def _scene_id_for(env: dict) -> str:
    graph = (env.get("result") or {}).get("graph") or {}
    return graph.get("graph_id") or f"iter_{env.get('iter_id')}"


def _render_user_prompt(
    template: str,
    *,
    scene_id: str,
    pass_mode: PassMode,
    env: dict,
) -> str:
    """Substitute the canonical placeholder set into the template.

    Unknown `{{KEY}}` placeholders are left untouched — the T-2.9 prompt
    may add fields we don't recognise, and silently dropping them would
    surface as "judge gives nonsense" much later. Stable substitution
    keys (locked):

      * {{SCENE_ID}}            — graph_id (or iter_<n>)
      * {{PASS_MODE}}           — "lenient" | "strict"
      * {{SCENE_JSON}}          — pretty-printed graph
      * {{TARGET_BEATS}}        — comma-joined fixture beats
      * {{PARTICIPATING_NPCS}}  — comma-joined fixture NPCs
      * {{SCENE_ANCHOR}}        — fixture scene_anchor
    """
    fixture = env.get("fixture", {}) or {}
    setting = fixture.get("scene_setting", {}) or {}
    graph = (env.get("result") or {}).get("graph") or {}
    substitutions = {
        "{{SCENE_ID}}": scene_id,
        "{{PASS_MODE}}": pass_mode,
        "{{SCENE_JSON}}": json.dumps(graph, ensure_ascii=False, indent=2),
        "{{TARGET_BEATS}}": ", ".join(fixture.get("target_beats") or []),
        "{{PARTICIPATING_NPCS}}": ", ".join(fixture.get("participating_npcs") or []),
        "{{SCENE_ANCHOR}}": setting.get("scene_anchor", ""),
    }
    rendered = template
    for key, value in substitutions.items():
        rendered = rendered.replace(key, str(value))
    return rendered


# ---------------------------------------------------------------------------
# One judge call
# ---------------------------------------------------------------------------


def _call_judge(
    *,
    template: str,
    scene_id: str,
    pass_mode: PassMode,
    env: dict,
    provider: LLMProvider,
) -> tuple[dict, float]:
    """Make a single budget-gated judge call. Returns (parsed_content, cost).

    Raises BudgetExceeded so callers can stop the batch cleanly.
    Raises ProviderError on transport / decode failures so callers can
    decide whether to skip the scene or abort.
    """
    user_prompt = _render_user_prompt(
        template, scene_id=scene_id, pass_mode=pass_mode, env=env
    )
    system_prompt = (
        "You are the Forgewright scene-level AI judge. Score the scene against "
        "the rubric in the user prompt and respond ONLY with the JSON object "
        "the schema requires. Do not include commentary outside JSON."
    )

    input_tokens_est = max(1, len(system_prompt + user_prompt) // _CHARS_PER_TOKEN)
    output_tokens_est = _OUTPUT_TOKEN_ESTIMATE
    estimated_cost = provider.estimate_cost(input_tokens_est, output_tokens_est)

    record_id = budget.check_and_charge(
        estimated_cost,
        model_id=getattr(provider, "model_id", "unknown"),
        input_tokens=input_tokens_est,
        output_tokens=output_tokens_est,
    )

    response: StructuredResponse = provider.generate_structured(
        system_prompt, user_prompt, _JUDGE_RESPONSE_SCHEMA
    )

    actual_cost = provider.estimate_cost(response.input_tokens, response.output_tokens)
    budget.reconcile_after_call(
        record_id,
        actual_input_tokens=response.input_tokens,
        actual_output_tokens=response.output_tokens,
        actual_cost_usd=actual_cost,
    )
    return response.content, actual_cost


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def _weakest_dimensions(
    strict_scores: dict[str, dict[str, float]], top_n: int = 5
) -> list[tuple[str, float]]:
    """Average each dimension across all scenes; return the lowest top_n.

    A dimension that only appears in some scenes is averaged only over
    the scenes that scored it. Sorting by mean ascending; ties broken by
    dimension name for determinism.
    """
    by_dim: dict[str, list[float]] = {}
    for scene_dims in strict_scores.values():
        for dim, score in scene_dims.items():
            try:
                by_dim.setdefault(dim, []).append(float(score))
            except (TypeError, ValueError):
                continue
    averages = [
        (dim, sum(values) / len(values))
        for dim, values in by_dim.items()
        if values
    ]
    averages.sort(key=lambda kv: (kv[1], kv[0]))
    return averages[:top_n]


# ---------------------------------------------------------------------------
# Report writers
# ---------------------------------------------------------------------------


def _render_markdown_report(report: AIJudgeReport, *, batch_dir: Path) -> str:
    lines: list[str] = []
    lines.append(f"# AI Judge Report — `{batch_dir.name}`")
    lines.append("")
    lines.append(f"_Generated at {datetime.now(timezone.utc).isoformat()}._")
    lines.append("")
    lines.append(
        "**Authority note (ADR-020 §6):** AI judge advisory is *informational*. "
        "Author [A]/[R] in `scene_review_cli` is the acceptance-rate numerator."
    )
    lines.append("")
    lines.append("## Summary")
    scenes_strict = sorted(report.pass2_strict_scores.keys())
    lines.append(f"- scenes scored: {len(scenes_strict)}")
    lines.append(f"- total cost: ${report.total_cost_usd:.4f}")
    if report.stopped_early:
        lines.append("- **stopped early** — BudgetExceeded mid-batch.")
    if report.skipped_scenes:
        lines.append(f"- skipped on provider error: {', '.join(report.skipped_scenes)}")
    lines.append("")

    lines.append("## Weakest dimensions (strict pass average, lower = worse)")
    if report.weakest_dimensions:
        for dim, mean in report.weakest_dimensions:
            lines.append(f"- `{dim}` — {mean:.2f}")
    else:
        lines.append("- (no scenes scored)")
    lines.append("")

    lines.append("## Per-scene advisory")
    if report.advisory_recommendation:
        lines.append("| scene_id | advisory | rationale (strict) |")
        lines.append("|---|---|---|")
        for sid, advisory in sorted(report.advisory_recommendation.items()):
            rationale = (
                report.rationales.get(sid, {}).get("strict", "").replace("|", "/")
            )
            lines.append(f"| `{sid}` | {advisory} | {rationale[:200]} |")
    else:
        lines.append("(no advisory recorded)")
    lines.append("")

    lines.append("## Per-scene scores")
    for sid in scenes_strict:
        lines.append(f"### `{sid}`")
        lenient = report.pass1_lenient_scores.get(sid, {})
        strict = report.pass2_strict_scores.get(sid, {})
        all_dims = sorted(set(lenient.keys()) | set(strict.keys()))
        if not all_dims:
            lines.append("(no dimensions returned)")
            lines.append("")
            continue
        lines.append("| dimension | lenient | strict |")
        lines.append("|---|---|---|")
        for dim in all_dims:
            lines.append(
                f"| `{dim}` | {lenient.get(dim, '—')} | {strict.get(dim, '—')} |"
            )
        lines.append("")
    return "\n".join(lines) + "\n"


def _serialise_report(report: AIJudgeReport) -> dict:
    # Review 4.3: front the JSON with a non-binding metadata block so
    # programmatic consumers (T-2.12, future verification scripts) can't
    # mistake `advisory_recommendation` for an acceptance-rate input.
    # The markdown narrative says the same thing, but only the JSON
    # disclaimer is machine-readable.
    return {
        "metadata": dict(_REPORT_METADATA),
        "pass1_lenient_scores": report.pass1_lenient_scores,
        "pass2_strict_scores": report.pass2_strict_scores,
        "weakest_dimensions": report.weakest_dimensions,
        "advisory_recommendation": report.advisory_recommendation,
        "rationales": report.rationales,
        "total_cost_usd": report.total_cost_usd,
        "stopped_early": report.stopped_early,
        "skipped_scenes": report.skipped_scenes,
    }


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_scene_ai_judge(
    *,
    batch_dir: Path,
    provider: LLMProvider,
    prompt_template_path: Path = DEFAULT_TEMPLATE_PATH,
    progress: bool = True,
) -> AIJudgeReport:
    """Run pass1 lenient + pass2 strict against every success scene.

    Writes `AI_JUDGE_REPORT.md` and `AI_JUDGE_REPORT.json` to
    `batch_dir`. Both files are overwritten on each invocation.
    """
    results_path = batch_dir / "scene_results.jsonl"
    if not results_path.exists():
        raise FileNotFoundError(f"scene_results.jsonl not found at {results_path}")
    if not prompt_template_path.exists():
        raise FileNotFoundError(
            f"prompt template not found at {prompt_template_path}; "
            f"point --template at T-2.9's REVIEW_PROMPT_AI_JUDGE_SCENE.md."
        )

    template = prompt_template_path.read_text(encoding="utf-8")
    envelopes = _read_jsonl(results_path)
    successful = [e for e in envelopes if e.get("result", {}).get("success")]

    report = AIJudgeReport()

    for idx, env in enumerate(successful, start=1):
        scene_id = _scene_id_for(env)
        if progress:
            print(f"[{idx}/{len(successful)}] judging {scene_id} ...", flush=True)
        pass_results: dict[str, dict | None] = {"lenient": None, "strict": None}
        for pass_mode in ("lenient", "strict"):
            try:
                content, cost = _call_judge(
                    template=template,
                    scene_id=scene_id,
                    pass_mode=pass_mode,  # type: ignore[arg-type]
                    env=env,
                    provider=provider,
                )
            except BudgetExceeded as exc:
                if progress:
                    print(f"  [budget] BudgetExceeded — stopping ({exc}).")
                report.stopped_early = True
                _flush_report(report, batch_dir)
                return report
            except ProviderError as exc:
                if progress:
                    print(f"  [provider] error on {pass_mode} pass: {exc}")
                report.skipped_scenes.append(f"{scene_id}:{pass_mode}")
                continue
            report.total_cost_usd += cost
            pass_results[pass_mode] = content

        _record_pass(report, scene_id, "lenient", pass_results["lenient"])
        _record_pass(report, scene_id, "strict", pass_results["strict"])

    report.weakest_dimensions = _weakest_dimensions(report.pass2_strict_scores)
    _flush_report(report, batch_dir)
    return report


def _record_pass(
    report: AIJudgeReport,
    scene_id: str,
    pass_mode: PassMode,
    content: dict | None,
) -> None:
    """Merge one pass's response into the report.

    A missing content (provider error during this pass) leaves the slot
    empty; the markdown render shows `—`. The strict pass's `advisory`
    wins for the per-scene recommendation — strict is the conservative
    default, matching ADR-020's "judge as conservative gate" intent.
    """
    if not isinstance(content, dict):
        return
    dims = content.get("dimensions") or {}
    if isinstance(dims, dict):
        clean: dict[str, float] = {}
        for k, v in dims.items():
            try:
                clean[str(k)] = float(v)
            except (TypeError, ValueError):
                continue
        if pass_mode == "lenient":
            report.pass1_lenient_scores[scene_id] = clean
        else:
            report.pass2_strict_scores[scene_id] = clean
    rationale = content.get("rationale")
    if isinstance(rationale, str) and rationale:
        report.rationales.setdefault(scene_id, {})[pass_mode] = rationale
    advisory = content.get("advisory")
    if pass_mode == "strict" and advisory in ("accept", "reject", "marginal"):
        report.advisory_recommendation[scene_id] = advisory  # type: ignore[assignment]


def _flush_report(report: AIJudgeReport, batch_dir: Path) -> None:
    md_path = batch_dir / "AI_JUDGE_REPORT.md"
    json_path = batch_dir / "AI_JUDGE_REPORT.json"
    md_path.write_text(_render_markdown_report(report, batch_dir=batch_dir), encoding="utf-8")
    json_path.write_text(
        json.dumps(_serialise_report(report), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_default_provider() -> LLMProvider:
    from generator.providers import GeminiProvider

    return GeminiProvider()


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="python -m generator.scene_ai_judge",
        description=(
            "Run the scene-level AI judge (pass1 lenient + pass2 strict) "
            "over every success scene in a batch and write "
            "AI_JUDGE_REPORT.{md,json}. ADR-020 §6: advisory is informational; "
            "author A/R/S in scene_review_cli is the acceptance signal."
        ),
    )
    parser.add_argument(
        "--batch-dir", required=True, type=Path,
        help="Path to /generator/experiments/<timestamp>_<batch_name>/",
    )
    parser.add_argument(
        "--template", type=Path, default=DEFAULT_TEMPLATE_PATH,
        help=(
            "Path to the AI judge prompt template "
            f"(default: {DEFAULT_TEMPLATE_PATH})."
        ),
    )
    args = parser.parse_args(argv)

    if not args.batch_dir.exists():
        print(f"error: batch-dir does not exist: {args.batch_dir}", file=sys.stderr)
        return 2

    provider = _build_default_provider()
    try:
        report = run_scene_ai_judge(
            batch_dir=args.batch_dir,
            provider=provider,
            prompt_template_path=args.template,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(
        f"\n[done] judged {len(report.pass2_strict_scores)} scene(s); "
        f"total cost ${report.total_cost_usd:.4f}; "
        f"reports at {args.batch_dir / 'AI_JUDGE_REPORT.md'}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())


__all__ = [
    "AIJudgeReport",
    "DEFAULT_TEMPLATE_PATH",
    "run_scene_ai_judge",
]
