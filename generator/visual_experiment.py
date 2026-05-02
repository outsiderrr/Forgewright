"""Batch experiment harness for visual generation (T-1.5.8).

Sibling of `generator.experiment` but for the visual pipeline. One batch
runs `generate_character_sheet` or `generate_scene_background` for a
single target (`target_ref` + `target_type`) at a chosen `asset_role`,
producing N variants. In `manual` mode each successful variant lands as a
prompt package under `content/visuals/_pending/<asset_id_stub>/` (written
by `ManualImportProvider`); in `api` mode the provider returns image bytes
that downstream `image_import` (T-1.5.7) ingests after manual review.

CLI:

    python -m generator.visual_experiment \\
        --batch-name <name> \\
        --target <target_ref> \\
        --target-type <character|location|scene> \\
        --asset-role <character_sheet|scene_background> \\
        --n <N> \\
        --mode <manual|api>

Output lands at `/generator/experiments/<UTC-timestamp>_<batch_name>/`:

  * results.jsonl       — one envelope per variant (success or failure)
  * summary.txt         — counts / success rate / total cost
  * prompt_packages/    — symlink (or copy) of each `_pending/<stub>/` dir,
                          so re-running `image_import` later still finds
                          the original packages even if the author renames
                          things in `_pending/`

Budget guard: `generate_visual` already short-circuits on
`ImageBudgetExceeded` and surfaces it as a `failure_reason`. The harness
records the row, sets `stopped_early=True`, and writes the summary.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Literal

from dotenv import load_dotenv

from generator import image_budget
from generator.generate_visual import (
    VisualGenerationResult,
    generate_character_sheet,
    generate_scene_background,
)
from generator.image_provider import ImageProvider
from generator.visual_context import (
    CharacterSheetRequirement,
    SceneBackgroundRequirement,
)

EXPERIMENTS_ROOT = Path(__file__).parent / "experiments"

# 10 expression labels so an n=10 character batch (e.g. vellin) succeeds
# without the author spelling them out on the CLI. `_check_requirement`
# inside `generate_visual` would otherwise reject n>len(variants).
DEFAULT_EXPRESSIONS: list[str] = [
    "neutral",
    "smile",
    "frown",
    "anger",
    "sorrow",
    "surprise",
    "weariness",
    "fear",
    "determined",
    "contemplative",
]
DEFAULT_POSES: list[str] = ["torso_up"]
DEFAULT_TIMES_OF_DAY: list[str] = ["dusk", "night", "dawn", "midday"]

# review of T-1.5.8 #4.1: batch_name lands in `<ts>_<batch_name>` directory
# names and downstream log filters; an input like `x/../oops` would let an
# accidental keystroke write outside experiments/. Restrict to a
# filename-safe charset and a sane length cap (80 + leading char). The
# pattern intentionally rejects leading dot/dash so a stray flag never
# becomes a directory name.
_BATCH_NAME_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$")


def _validate_batch_name(batch_name: str) -> str:
    if not isinstance(batch_name, str) or not _BATCH_NAME_RE.fullmatch(batch_name):
        raise ValueError(
            "batch_name must match ^[A-Za-z0-9][A-Za-z0-9_.-]{0,80}$ — "
            "letters, digits, '.', '_' or '-' only; no path separators."
        )
    return batch_name


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def _serialise_result(r: VisualGenerationResult) -> dict:
    return {
        "success": r.success,
        "asset_id_stub": r.asset_id_stub,
        "prompt_package_path": (
            str(r.prompt_package_path) if r.prompt_package_path else None
        ),
        # We deliberately don't serialise raw image_bytes (could be MB);
        # length-only is enough to confirm a non-empty payload.
        "image_bytes_size": len(r.image_bytes) if r.image_bytes else 0,
        "failure_reason": r.failure_reason,
        "cost_usd": r.cost_usd,
        "raw_metadata": r.raw_metadata,
    }


def _serialise_envelope(
    *,
    iter_id: int,
    batch_name: str,
    target_ref: str,
    target_type: str,
    asset_role: str,
    mode: str,
    result: VisualGenerationResult,
) -> dict:
    return {
        "iter_id": iter_id,
        "batch_name": batch_name,
        "target_ref": target_ref,
        "target_type": target_type,
        "asset_role": asset_role,
        "mode": mode,
        "result": _serialise_result(result),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def _render_summary(envelopes: Iterable[dict], stopped_early: bool) -> str:
    envs = list(envelopes)
    total = len(envs)
    if total == 0:
        return "no results.\n"

    success = sum(1 for e in envs if e["result"]["success"])
    pending = sum(
        1
        for e in envs
        if e["result"]["success"] and e["result"]["prompt_package_path"]
    )
    cost = sum(float(e["result"]["cost_usd"]) for e in envs)

    lines = [
        f"results:                  {total}",
        f"successful:               {success}",
        f"pending_packages:         {pending}",
        f"success_rate:             {success / total:.1%}  ({success}/{total})",
        f"total_cost_usd:           ${cost:.4f}",
    ]
    if stopped_early:
        lines.append("")
        lines.append("NOTE: stopped early due to image_budget_exceeded.")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Prompt-package mirror
# ---------------------------------------------------------------------------


def _mirror_prompt_package(stub_dir: Path, target: Path) -> None:
    """Symlink stub_dir -> target; fall back to copytree if symlink fails.

    Best-effort. A missing source dir or a hostile filesystem shouldn't
    fail the whole batch — the prompt package mirror is a convenience for
    the author, not a correctness invariant.
    """
    if not stub_dir.exists():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.exists() or target.is_symlink():
        return
    try:
        os.symlink(stub_dir.resolve(), target)
        return
    except OSError:
        pass
    try:
        shutil.copytree(stub_dir, target)
    except OSError:
        pass


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _print_budget_header() -> None:
    daily = image_budget.daily_image_budget_usd()
    used = image_budget.today_total_usd()
    remaining = max(0.0, daily - used)
    print(
        f"[image_budget] daily=${daily:.2f}  used_today=${used:.4f}  "
        f"remaining=${remaining:.4f}"
    )


def run_visual_experiment(
    *,
    batch_name: str,
    target_ref: str,
    target_type: Literal["character", "location", "scene"],
    asset_role: Literal["character_sheet", "scene_background"],
    n: int,
    mode: Literal["manual", "api"],
    provider: ImageProvider,
    expressions: list[str] | None = None,
    poses: list[str] | None = None,
    times_of_day: list[str] | None = None,
    weather: list[str] | None = None,
    out_root: Path = EXPERIMENTS_ROOT,
    timestamp: str | None = None,
    progress: bool = True,
    ontology_path: Path | None = None,
    scene_path: Path | None = None,
    reference_dir: Path | None = None,
) -> Path:
    """Execute one batch and write results to a fresh batch directory.

    Returns the path to the batch dir. Stops at the first
    `budget_exceeded` row (which `generate_visual` returns instead of
    raising) and still flushes results.jsonl + summary.txt.
    """
    if n < 1:
        raise ValueError("n must be >= 1")

    safe_batch_name = _validate_batch_name(batch_name)
    ts = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    # Resolve before joining + after, so a hostile out_root that contains a
    # symlink trick still has to land inside out_root.resolve(). The
    # batch_name regex above already blocks `..` / `/` / `\\`, but defending
    # in depth is cheap.
    out_root_resolved = Path(out_root).resolve()
    batch_dir = (out_root_resolved / f"{ts}_{safe_batch_name}").resolve()
    try:
        batch_dir.relative_to(out_root_resolved)
    except ValueError as exc:  # pragma: no cover — regex makes this unreachable
        raise ValueError(
            f"batch_dir {batch_dir} escapes out_root {out_root_resolved}"
        ) from exc
    batch_dir.mkdir(parents=True, exist_ok=True)
    results_path = batch_dir / "results.jsonl"
    summary_path = batch_dir / "summary.txt"
    packages_dir = batch_dir / "prompt_packages"

    if asset_role == "character_sheet":
        if target_type != "character":
            raise ValueError(
                "asset-role=character_sheet requires target-type=character"
            )
        req = CharacterSheetRequirement(
            target_ref=target_ref,
            n=n,
            expressions=list(expressions) if expressions else list(DEFAULT_EXPRESSIONS),
            poses=list(poses) if poses else list(DEFAULT_POSES),
        )
        results = generate_character_sheet(
            requirement=req,
            provider=provider,
            mode=mode,
            batch_name=batch_name,
            ontology_path=ontology_path,
            reference_dir=reference_dir,
        )
    elif asset_role == "scene_background":
        if target_type not in ("location", "scene"):
            raise ValueError(
                "asset-role=scene_background requires target-type=location|scene"
            )
        req = SceneBackgroundRequirement(
            target_ref=target_ref,
            target_type=target_type,
            n=n,
            times_of_day=list(times_of_day) if times_of_day else list(DEFAULT_TIMES_OF_DAY),
            weather=list(weather) if weather else None,
        )
        results = generate_scene_background(
            requirement=req,
            provider=provider,
            mode=mode,
            batch_name=batch_name,
            ontology_path=ontology_path,
            scene_path=scene_path,
            reference_dir=reference_dir,
        )
    else:
        raise ValueError(f"unknown asset_role {asset_role!r}")

    envelopes: list[dict] = []
    stopped_early = False

    with open(results_path, "w", encoding="utf-8") as fh:
        for idx, r in enumerate(results):
            env = _serialise_envelope(
                iter_id=idx,
                batch_name=batch_name,
                target_ref=target_ref,
                target_type=target_type,
                asset_role=asset_role,
                mode=mode,
                result=r,
            )
            envelopes.append(env)
            fh.write(json.dumps(env, ensure_ascii=False) + "\n")
            fh.flush()

            if progress:
                tag = "ok" if r.success else f"fail({r.failure_reason})"
                print(
                    f"  [{idx + 1}/{len(results)}] {r.asset_id_stub} "
                    f"{tag}  cost=${r.cost_usd:.4f}"
                )

            if r.failure_reason and r.failure_reason.startswith("budget_exceeded"):
                stopped_early = True
                if progress:
                    print(
                        "[image_budget] BudgetExceeded — stopping batch and "
                        "flushing partial results."
                    )

            if r.prompt_package_path:
                _mirror_prompt_package(
                    Path(r.prompt_package_path),
                    packages_dir / r.asset_id_stub,
                )

    summary_path.write_text(
        _render_summary(envelopes, stopped_early=stopped_early), encoding="utf-8"
    )

    if progress:
        print(f"[done] wrote {len(envelopes)} results to {batch_dir}")
        print(f"[done] summary at {summary_path}")

    return batch_dir


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def _build_default_provider(mode: str) -> ImageProvider:
    """Construct the default provider for `mode`. Imported lazily so the
    test suite (which injects FakeImageProvider) doesn't need
    OPENAI_API_KEY when running in `api` mode tests."""
    if mode == "manual":
        from generator.providers.manual_import import ManualImportProvider

        return ManualImportProvider()
    if mode == "api":
        from generator.providers.openai_image import OpenAIImageProvider

        return OpenAIImageProvider()
    raise ValueError(f"unknown mode {mode!r}")


def _csv(value: str | None) -> list[str] | None:
    if value is None:
        return None
    parts = [p.strip() for p in value.split(",") if p.strip()]
    return parts or None


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="python -m generator.visual_experiment",
        description=(
            "Run one visual generation batch (manual or api mode) and "
            "dump results.jsonl + summary.txt + prompt_packages/."
        ),
    )
    parser.add_argument("--batch-name", required=True, help="Label for this batch.")
    parser.add_argument(
        "--target",
        required=True,
        dest="target_ref",
        help="Ontology id of the subject (e.g. char_vellin / scene_X).",
    )
    parser.add_argument(
        "--target-type",
        required=True,
        choices=("character", "location", "scene"),
        help="Target ontology type. Must match --asset-role.",
    )
    parser.add_argument(
        "--asset-role",
        required=True,
        choices=("character_sheet", "scene_background"),
        help=(
            "character_sheet → target-type=character; "
            "scene_background → target-type=location|scene."
        ),
    )
    parser.add_argument(
        "--n",
        required=True,
        type=int,
        help="Number of variants to generate in this batch.",
    )
    parser.add_argument(
        "--mode",
        default="manual",
        choices=("manual", "api"),
        help=(
            "manual = write prompt packages to _pending/ (default; $0); "
            "api = call OpenAI Images API (requires OPENAI_API_KEY)."
        ),
    )
    parser.add_argument(
        "--expressions",
        default=None,
        help=(
            "Optional comma-separated expression labels for character_sheet "
            "(default: 10 built-in labels covering n=10)."
        ),
    )
    parser.add_argument(
        "--poses",
        default=None,
        help=(
            "Optional comma-separated pose labels for character_sheet "
            "(default: torso_up)."
        ),
    )
    parser.add_argument(
        "--times-of-day",
        default=None,
        help=(
            "Optional comma-separated time-of-day labels for "
            "scene_background (default: dusk,night,dawn,midday)."
        ),
    )
    parser.add_argument(
        "--weather",
        default=None,
        help="Optional comma-separated weather labels for scene_background.",
    )
    args = parser.parse_args(argv)

    if args.mode == "api" and args.n > 1:
        # API mode burns real money; surface the cost before launching so
        # an accidental --n 10 doesn't drain the daily cap silently.
        print(
            f"[warn] api mode + n={args.n}: estimated upper bound "
            f"${args.n * 0.17:.2f}; ctrl-C now if unintended.",
            file=sys.stderr,
        )

    _print_budget_header()
    provider = _build_default_provider(args.mode)
    batch_dir = run_visual_experiment(
        batch_name=args.batch_name,
        target_ref=args.target_ref,
        target_type=args.target_type,
        asset_role=args.asset_role,
        n=args.n,
        mode=args.mode,
        provider=provider,
        expressions=_csv(args.expressions),
        poses=_csv(args.poses),
        times_of_day=_csv(args.times_of_day),
        weather=_csv(args.weather),
    )
    print(f"\nbatch dir: {batch_dir}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
