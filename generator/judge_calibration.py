"""AI judge vs author [A]/[R]/[S] mini calibration runner (T-3.0 R3.3 / F18).

Runs the scene-level AI judge against a hand-picked subset of an existing
``scene_experiment`` batch and cross-references the result with the
author's ``scene_review_log.jsonl`` decisions. Writes
``judge_calibration_report.md`` describing the bias *shape* — judge too
lenient (false-positive) vs too strict (false-negative) vs marginal.

This is intentionally not a Cohen's kappa run. F18 / HANDOFF_STAGE_2_TO_3
§R2-5 ask for a *report* the author can read before Stage 3 lets
LLM-as-judge participate in playtest critical gates (T-3.4 / ADR-022).
Once enough labels accumulate in Stage 3 mid-/late-period, kappa can
be formalised separately.

CLI:

    python -m generator.judge_calibration \
        --scenes waystation_of_iron_oath__iter01,...__iter06 \
        --baseline-dir generator/experiments/<batch> \
        [--report <md_path>] \
        [--template <prompt.md>]

Author label semantics:

  * ``A`` — author accepted (review_log row with ``accepted=True``)
  * ``R`` — author rejected (review_log row with ``accepted=False``)
  * ``S`` / ``missing`` — author skipped or hasn't reviewed yet
    (no row in scene_review_log.jsonl). Treated identically for
    calibration purposes — the runner records ``no_author_label`` and
    moves on. The author can rerun once labels exist.

AI advisory mapping:

  * ``accept`` → AI says A
  * ``reject`` → AI says R
  * ``marginal`` → AI says M (waffle)

Cost: each calibrated scene costs ~1 strict-pass judge call (≈ $0.04 on
PoloAI / Gemini 2.5 pro). 5 scenes ≈ $0.20 — order of magnitude under
the per-batch budget so the calibration run won't trip the daily gate.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

from generator import scene_ai_judge
from generator.budget import BudgetExceeded
from generator.llm_provider import LLMProvider, ProviderError


# ---------------------------------------------------------------------------
# Public dataclass
# ---------------------------------------------------------------------------


@dataclass
class CalibrationRow:
    """One scene's calibration result. Persisted as a row in the
    rendered report and exposed to tests through ``run_judge_calibration``
    return value."""

    scene_id: str
    author_decision: str  # "A" / "R" / "S" / "missing"
    author_reason: str | None
    ai_advisory: str | None  # "accept" / "reject" / "marginal" / None
    ai_total: float | None  # sum of S1..S10 strict scores (0-20) or None
    ai_dims: dict[str, float] = field(default_factory=dict)
    judge_rationale: str | None = None
    agreement: str = "unknown"


# ---------------------------------------------------------------------------
# JSONL helper (sibling of scene_ai_judge / scene_review_cli)
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


# ---------------------------------------------------------------------------
# Decision mapping
# ---------------------------------------------------------------------------


def _author_decision(record: dict | None) -> tuple[str, str | None]:
    """Map a scene_review_log row to ``("A"/"R"/"S"/"missing", reason)``."""
    if not record:
        return "missing", None
    accepted = record.get("accepted")
    reason = record.get("reason")
    if accepted is True:
        return "A", reason
    if accepted is False:
        return "R", reason
    return "S", reason


def _ai_decision_from_advisory(advisory: str | None) -> str:
    if advisory == "accept":
        return "A"
    if advisory == "reject":
        return "R"
    if advisory == "marginal":
        return "M"
    return "missing"


def _classify_agreement(author: str, ai: str) -> str:
    """Bucket the (author, ai) pair into a calibration outcome.

    Buckets the markdown report groups by — pinned in the unit tests so
    a future refactor can't quietly drop a category.
    """
    if author in ("S", "missing"):
        return "no_author_label"
    if ai == "missing":
        return "no_ai_advisory"
    if ai == "M":
        # Marginal isn't a hard disagreement; bucket by the author's call
        # so the report shows whether judge waffles toward A or R.
        return f"marginal_vs_{author}"
    if author == ai:
        return "agree"
    if author == "A" and ai == "R":
        return "disagree_judge_strict"  # judge over-rejects (false-negative)
    if author == "R" and ai == "A":
        return "disagree_judge_lenient"  # judge over-accepts (false-positive)
    return "unknown"


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def run_judge_calibration(
    *,
    baseline_dir: Path,
    scene_ids: Iterable[str],
    provider: LLMProvider,
    template_text: str,
    report_path: Path,
    progress: bool = True,
) -> tuple[str, list[CalibrationRow]]:
    """Score requested scenes with the AI judge, cross-reference with
    author labels, write the disagreement report.

    Returns ``(report_markdown, rows)``. Best-effort per-scene:

      * ``BudgetExceeded`` mid-run aborts the loop and flushes whatever
        was scored (matching ``scene_ai_judge.run_scene_ai_judge``'s
        contract).
      * ``ProviderError`` on a single scene records a row with
        ``ai_advisory=None`` / ``agreement="provider_error"`` and
        continues to the next scene.
      * Missing scene envelope (scene_id not in batch's
        scene_results.jsonl) yields ``agreement="scene_not_found"``.
    """
    results_path = baseline_dir / "scene_results.jsonl"
    review_path = baseline_dir / "scene_review_log.jsonl"
    if not results_path.exists():
        raise FileNotFoundError(
            f"scene_results.jsonl not found at {results_path}"
        )

    envelopes_by_id: dict[str, dict] = {}
    for env in _read_jsonl(results_path):
        graph = (env.get("result") or {}).get("graph") or {}
        scene_id = graph.get("graph_id") or f"iter_{env.get('iter_id')}"
        envelopes_by_id[scene_id] = env

    review_by_scene: dict[str, dict] = {
        row["scene_id"]: row
        for row in _read_jsonl(review_path)
        if row.get("scene_id")
    }

    scene_id_list = [s.strip() for s in scene_ids if s and s.strip()]
    rows: list[CalibrationRow] = []
    stopped_early = False

    for idx, scene_id in enumerate(scene_id_list, start=1):
        if progress:
            print(
                f"[{idx}/{len(scene_id_list)}] calibrating {scene_id} ...",
                flush=True,
            )
        review_record = review_by_scene.get(scene_id)
        author_decision, author_reason = _author_decision(review_record)

        env = envelopes_by_id.get(scene_id)
        if env is None or not (env.get("result") or {}).get("success"):
            rows.append(CalibrationRow(
                scene_id=scene_id,
                author_decision=author_decision,
                author_reason=author_reason,
                ai_advisory=None,
                ai_total=None,
                ai_dims={},
                judge_rationale=None,
                agreement="scene_not_found",
            ))
            continue

        # B-review 5.1 (T-3.0 C): if the author hasn't decided on this
        # scene yet (skipped or no review row), there's nothing to
        # calibrate against — the judge call would just burn ~$0.04
        # and the report would still bucket as ``no_author_label``.
        # Short-circuit so the runner is cheap to re-run as the author
        # accumulates labels in scene_review_log.jsonl.
        if author_decision in ("S", "missing"):
            if progress:
                print("  [skip] no author label yet; not calling judge.")
            rows.append(CalibrationRow(
                scene_id=scene_id,
                author_decision=author_decision,
                author_reason=author_reason,
                ai_advisory=None,
                ai_total=None,
                ai_dims={},
                judge_rationale=None,
                agreement="no_author_label",
            ))
            continue

        try:
            content, _cost = scene_ai_judge.judge_scene_envelope(
                env,
                pass_mode="strict",
                provider=provider,
                template_text=template_text,
            )
        except BudgetExceeded as exc:
            if progress:
                print(f"  [budget] BudgetExceeded — stopping ({exc}).")
            rows.append(CalibrationRow(
                scene_id=scene_id,
                author_decision=author_decision,
                author_reason=author_reason,
                ai_advisory=None,
                ai_total=None,
                ai_dims={},
                judge_rationale=None,
                agreement="budget_exceeded",
            ))
            stopped_early = True
            break
        except ProviderError as exc:
            if progress:
                print(f"  [provider] error: {exc}")
            rows.append(CalibrationRow(
                scene_id=scene_id,
                author_decision=author_decision,
                author_reason=author_reason,
                ai_advisory=None,
                ai_total=None,
                ai_dims={},
                judge_rationale=None,
                agreement="provider_error",
            ))
            continue

        rows.append(_row_from_judge_content(
            scene_id=scene_id,
            author_decision=author_decision,
            author_reason=author_reason,
            content=content,
        ))

    md = _render_calibration_md(
        rows, batch_name=baseline_dir.name, stopped_early=stopped_early
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(md, encoding="utf-8")
    return md, rows


def _row_from_judge_content(
    *,
    scene_id: str,
    author_decision: str,
    author_reason: str | None,
    content: dict,
) -> CalibrationRow:
    """Project the judge's structured response into a CalibrationRow."""
    ai_advisory = (
        content.get("advisory") if isinstance(content, dict) else None
    )
    ai_dims_raw = (
        (content.get("dimensions") or {}) if isinstance(content, dict) else {}
    )
    ai_dims: dict[str, float] = {}
    for k, v in ai_dims_raw.items():
        try:
            ai_dims[str(k)] = float(v)
        except (TypeError, ValueError):
            continue
    ai_total = sum(ai_dims.values()) if ai_dims else None
    rationale_raw = content.get("rationale") if isinstance(content, dict) else None
    rationale = rationale_raw if isinstance(rationale_raw, str) else None
    ai_decision = _ai_decision_from_advisory(ai_advisory)
    return CalibrationRow(
        scene_id=scene_id,
        author_decision=author_decision,
        author_reason=author_reason,
        ai_advisory=ai_advisory,
        ai_total=ai_total,
        ai_dims=ai_dims,
        judge_rationale=rationale,
        agreement=_classify_agreement(author_decision, ai_decision),
    )


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------


def _render_calibration_md(
    rows: list[CalibrationRow],
    *,
    batch_name: str,
    stopped_early: bool = False,
) -> str:
    n_total = len(rows)
    n_agree = sum(1 for r in rows if r.agreement == "agree")
    n_lenient = sum(1 for r in rows if r.agreement == "disagree_judge_lenient")
    n_strict = sum(1 for r in rows if r.agreement == "disagree_judge_strict")
    n_marginal = sum(1 for r in rows if r.agreement.startswith("marginal_vs_"))
    n_no_label = sum(1 for r in rows if r.agreement == "no_author_label")
    n_unavail = sum(
        1
        for r in rows
        if r.agreement
        in ("no_ai_advisory", "scene_not_found", "provider_error", "budget_exceeded")
    )

    lines: list[str] = []
    lines.append(f"# Judge calibration report — `{batch_name}`")
    lines.append("")
    lines.append(f"_Generated at {datetime.now(timezone.utc).isoformat()}._")
    lines.append("")
    lines.append(
        "**T-3.0 R3.3 / F18 mini calibration**: AI judge advisory vs author "
        "`[A]/[R]/[S]` for a hand-picked subset of the batch. Goal — surface "
        "judge bias *shape* (lenient vs strict vs marginal) before Stage 3 "
        "lets LLM-as-judge participate in playtest critical gates "
        "(T-3.4 / ADR-022). Not a formal Cohen's kappa run."
    )
    lines.append("")
    lines.append("## Summary")
    lines.append(f"- scenes calibrated:               {n_total}")
    lines.append(f"- agree (judge ≡ author):          {n_agree}")
    lines.append(f"- disagree (judge too lenient):    {n_lenient}")
    lines.append(f"- disagree (judge too strict):     {n_strict}")
    lines.append(f"- judge marginal:                  {n_marginal}")
    lines.append(f"- author label missing / skipped:  {n_no_label}")
    lines.append(f"- judge unavailable / error:       {n_unavail}")
    if stopped_early:
        lines.append("")
        lines.append("**stopped early** — BudgetExceeded mid-batch.")
    lines.append("")

    lines.append("## Per-scene table")
    lines.append("")
    lines.append(
        "| scene_id | author | ai_advisory | ai_total | agreement | "
        "author_reason | judge_rationale |"
    )
    lines.append("|---|---|---|---|---|---|---|")
    for r in rows:
        ai = r.ai_advisory or "—"
        total = f"{r.ai_total:.0f}/20" if r.ai_total is not None else "—"
        author_reason = (r.author_reason or "").replace("|", "/").replace(
            "\n", " "
        )[:80]
        rationale = (r.judge_rationale or "").replace("|", "/").replace(
            "\n", " "
        )[:120]
        lines.append(
            f"| `{r.scene_id}` | {r.author_decision} | {ai} | {total} | "
            f"{r.agreement} | {author_reason} | {rationale} |"
        )
    lines.append("")

    lines.append("## How to read")
    lines.append("")
    lines.append(
        "- **agree** — judge advisory matches your decision. Calibration "
        "win."
    )
    lines.append(
        "- **disagree_judge_lenient** — judge said `accept`, you rejected. "
        "If this dominates, judge will let bad scenes through Stage 3 "
        "playtest critical gates (T-3.4 / ADR-022). Tighten judge prompt or "
        "raise advisory threshold."
    )
    lines.append(
        "- **disagree_judge_strict** — judge said `reject`, you accepted. "
        "If this dominates, judge will block valid scenes. Loosen prompt or "
        "lower threshold."
    )
    lines.append(
        "- **marginal_vs_A / marginal_vs_R** — judge waffled. Useful "
        "calibration signal in borderline scenes; not a hard disagreement."
    )
    lines.append(
        "- **no_author_label** — author hasn't `[A]/[R]`-d this scene yet "
        "(or skipped it). Re-run after `scene_review_cli` for a verdict."
    )
    lines.append(
        "- **scene_not_found / provider_error / budget_exceeded** — "
        "calibration couldn't get a verdict; investigate the batch dir."
    )
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_default_provider() -> LLMProvider:
    from generator.providers import get_default_provider

    return get_default_provider()


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="python -m generator.judge_calibration",
        description=(
            "Mini calibration: AI judge advisory vs author [A]/[R]/[S] for a "
            "hand-picked subset of an existing scene_experiment batch (T-3.0 "
            "R3.3 / F18). Writes judge_calibration_report.md."
        ),
    )
    parser.add_argument(
        "--scenes",
        required=True,
        help=(
            "Comma-separated scene_id list "
            "(e.g. 'waystation__iter00,waystation__iter05')."
        ),
    )
    parser.add_argument(
        "--baseline-dir",
        required=True,
        type=Path,
        help=(
            "Path to /generator/experiments/<batch>/ — must contain "
            "scene_results.jsonl + scene_review_log.jsonl."
        ),
    )
    parser.add_argument(
        "--report",
        type=Path,
        default=None,
        help=(
            "Output path for the report markdown. "
            "Default: <baseline-dir>/judge_calibration_report.md."
        ),
    )
    parser.add_argument(
        "--template",
        type=Path,
        default=scene_ai_judge.DEFAULT_TEMPLATE_PATH,
        help=(
            "AI judge prompt template "
            f"(default: {scene_ai_judge.DEFAULT_TEMPLATE_PATH})."
        ),
    )
    args = parser.parse_args(argv)

    if not args.baseline_dir.exists():
        print(
            f"error: baseline-dir does not exist: {args.baseline_dir}",
            file=sys.stderr,
        )
        return 2
    if not args.template.exists():
        print(
            f"error: prompt template not found: {args.template}",
            file=sys.stderr,
        )
        return 2

    scene_ids = [s.strip() for s in args.scenes.split(",") if s.strip()]
    if not scene_ids:
        print("error: --scenes is empty after parse", file=sys.stderr)
        return 2

    template_text = args.template.read_text(encoding="utf-8")
    report_path = (
        args.report or args.baseline_dir / "judge_calibration_report.md"
    )

    provider = _build_default_provider()
    try:
        md, rows = run_judge_calibration(
            baseline_dir=args.baseline_dir,
            scene_ids=scene_ids,
            provider=provider,
            template_text=template_text,
            report_path=report_path,
        )
    except FileNotFoundError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    print(md)
    print(f"\n[done] {len(rows)} scene(s) calibrated; report at {report_path}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())


__all__ = [
    "CalibrationRow",
    "run_judge_calibration",
]
