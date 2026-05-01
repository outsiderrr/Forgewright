"""Dev/prod parity smoke (Round 5 C4 soft gate; T-1.5.9 implementation site).

For each of N hand-picked prompts, generate **both** a manual-mode prompt
package (ManualImportProvider) and an API-mode image (OpenAIImageProvider),
then write a side-by-side `parity_report.md` for the author to fill in
visual-drift scores.

Why this exists: ADR-014 commits to GPT-Image both as the manual path
(author pastes prompt into chatgpt.com) **and** as the API path. The two
are assumed to share the same backbone (dev/prod parity). This smoke is
the cheapest test of that assumption — 3 prompts × 1 image each ≈ $0.51
upper-bound, one-shot.

Pass criterion (filled by the author after reviewing): ≥ 2 of 3 pairs
score ≤ 1 on a 0/1/2 drift scale ⇒ assumption holds. Otherwise → recook.

Graceful degradation: with no OPENAI_API_KEY, the API half is skipped and
the report is marked accordingly; the script still exits 0 so CI / dev
runs without keys don't fail. The manual half is unconditional (it's just
filesystem writes).

CLI:
    python -m generator.visual_parity_smoke --prompts <path> [--n 3]

`--prompts <path>`: JSON file with a list of prompt entries. Each entry:
    {
      "prompt_id":     "<short id, alpha+digits+underscore>",
      "prompt":        "<bilingual prompt body, ## English segment included>",
      "asset_kind":    "character_sheet" | "scene_background",
      "target_ref":    "<entity ref>",
      "target_type":   "character" | "location" | "scene",
      "asset_role":    "character_sheet" | "scene_background",
      "asset_id_stub": "img_<...>"
    }

Out-of-scope (per task spec):
    - Batch metrics integration (this is a one-shot script; not part of
      the per-batch experiment metrics pipeline)
    - Author scoring automation (the report has placeholder rows; the
      author fills them in by hand)
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import logging
import os
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from generator.image_provider import ImageProvider, ImageProviderError
from generator.providers import ManualImportProvider, OpenAIImageProvider

_logger = logging.getLogger(__name__)

_DEFAULT_EXPERIMENTS_ROOT = Path("generator/experiments")
_DEFAULT_PENDING_ROOT = Path("content/visuals/_pending")
_DEFAULT_COST_LOG = Path("generator/image_cost_log.jsonl")

_PROMPT_ID_RE = re.compile(r"^[a-zA-Z0-9_]{1,64}$")


@dataclass
class _PairResult:
    prompt_id: str
    asset_kind: str
    manual_path: Path | None
    api_image_path: Path | None
    api_status: str  # "ok" | "skipped: no OPENAI_API_KEY" | "partial fail: <reason>"
    api_cost_usd: float


def run_parity_smoke(
    prompts: list[dict],
    *,
    output_root: Path = _DEFAULT_EXPERIMENTS_ROOT,
    pending_root: Path = _DEFAULT_PENDING_ROOT,
    cost_log_path: Path = _DEFAULT_COST_LOG,
    manual_provider: ImageProvider | None = None,
    api_provider: ImageProvider | None = None,
    api_provider_unavailable_reason: str | None = None,
    now: _dt.datetime | None = None,
) -> dict[str, Any]:
    """Run the parity smoke and return a result summary.

    Args:
        prompts: Pre-validated list of prompt entries (see module docstring
            for the schema; use `validate_prompts` to validate raw JSON).
        output_root: Where the per-run dir is created (default: experiments/).
        pending_root: Where manual prompt packages go (default: _pending/).
        cost_log_path: Where to append the API cost line (default:
            generator/image_cost_log.jsonl). Skipped when no API call ran.
        manual_provider: Defaults to a ManualImportProvider rooted at
            `<pending_root>/parity/`.
        api_provider: Defaults to None ⇒ caller decides. The CLI builds an
            OpenAIImageProvider when OPENAI_API_KEY is set; tests pass a
            fake or None directly.
        api_provider_unavailable_reason: When `api_provider` is None,
            override the per-pair status string. Defaults to "skipped: no
            OPENAI_API_KEY" — matches the dominant cause in practice.
        now: Override timestamp (test seam).

    Returns:
        {
          "run_dir": Path to experiments/parity_smoke_<ts>,
          "report_path": Path to parity_report.md,
          "pair_results": list[_PairResult],
          "api_total_cost_usd": float,
        }
    """
    timestamp = (now or _dt.datetime.now(_dt.timezone.utc)).strftime("%Y%m%dT%H%M%SZ")
    run_dir = output_root / f"parity_smoke_{timestamp}"
    run_dir.mkdir(parents=True, exist_ok=True)
    api_dir = run_dir / "api"
    api_dir.mkdir(exist_ok=True)

    # Manual provider points its pending_root at <pending_root>/parity/ so we
    # don't co-mingle parity smoke output with the real waystation batches in
    # <pending_root>/<asset_id>/. T-1.5.7 image_import scans the waystation
    # tree, not /parity/.
    manual = manual_provider or ManualImportProvider(
        pending_root=pending_root / "parity"
    )
    api = api_provider
    api_unavailable_reason = api_provider_unavailable_reason or (
        "skipped: no OPENAI_API_KEY"
    )

    pair_results: list[_PairResult] = []
    api_total_cost = 0.0

    for entry in prompts:
        # 1. Manual half — unconditional. Errors propagate (it's just FS).
        manual_result = manual.generate(
            prompt=entry["prompt"],
            asset_kind=entry["asset_kind"],
            target_ref=entry["target_ref"],
            target_type=entry["target_type"],
            asset_role=entry["asset_role"],
            asset_id_stub=entry["asset_id_stub"],
            variant_label=entry.get("variant_label", ""),
        )

        # 2. API half — gracefully degrades. Either no provider, or call
        # raised: write the pair entry with the appropriate status and move
        # on so the report still gets all rows.
        if api is None:
            api_status = api_unavailable_reason
            api_image_path: Path | None = None
            api_cost = 0.0
        else:
            api_image_path, api_status, api_cost = _run_api_half(
                api, entry=entry, api_dir=api_dir
            )
            api_total_cost += api_cost

        pair_results.append(
            _PairResult(
                prompt_id=entry["prompt_id"],
                asset_kind=entry["asset_kind"],
                manual_path=manual_result.prompt_package_path,
                api_image_path=api_image_path,
                api_status=api_status,
                api_cost_usd=api_cost,
            )
        )

    report_path = run_dir / "parity_report.md"
    report_path.write_text(
        _render_report(pair_results, run_dir=run_dir, timestamp=timestamp),
        encoding="utf-8",
    )

    if api_total_cost > 0:
        _append_cost_log(
            cost_log_path=cost_log_path,
            timestamp=timestamp,
            run_dir=run_dir,
            pair_results=pair_results,
            api_total_cost=api_total_cost,
        )

    return {
        "run_dir": run_dir,
        "report_path": report_path,
        "pair_results": pair_results,
        "api_total_cost_usd": api_total_cost,
    }


def _run_api_half(
    api: ImageProvider,
    *,
    entry: dict,
    api_dir: Path,
) -> tuple[Path | None, str, float]:
    """Call the API provider; on failure return a status string instead of
    raising. The whole point of the smoke is to surface drift / partial
    success across pairs — one failed call shouldn't kill the report."""
    try:
        result = api.generate(
            prompt=entry["prompt"],
            asset_kind=entry["asset_kind"],
            target_ref=entry["target_ref"],
            target_type=entry["target_type"],
            asset_role=entry["asset_role"],
            asset_id_stub=entry["asset_id_stub"],
            variant_label=entry.get("variant_label", ""),
        )
    except ImageProviderError as exc:
        return None, f"partial fail: {exc}", 0.0
    except Exception as exc:  # pragma: no cover — defensive: SDK surprises
        # Any non-ImageProviderError is a programming bug or SDK shape
        # change. Still don't crash the smoke; the author needs the
        # report to triage.
        _logger.exception("Unexpected error from API provider on %s", entry["prompt_id"])
        return None, f"partial fail: {type(exc).__name__}: {exc}", 0.0

    if result.image_bytes is None:
        return None, "partial fail: API result had no image_bytes", 0.0

    image_path = api_dir / f"{entry['prompt_id']}.png"
    image_path.write_bytes(result.image_bytes)
    return image_path, "ok", result.cost_usd


def validate_prompts(raw: Any) -> list[dict]:
    """Validate the JSON body of a `--prompts` file and return it."""
    if not isinstance(raw, list) or not raw:
        raise ValueError(
            f"--prompts must contain a non-empty JSON list of prompt entries"
            f" (got {type(raw).__name__})"
        )
    required = {
        "prompt_id",
        "prompt",
        "asset_kind",
        "target_ref",
        "target_type",
        "asset_role",
        "asset_id_stub",
    }
    for i, entry in enumerate(raw):
        if not isinstance(entry, dict):
            raise ValueError(f"prompt entry [{i}] is not an object")
        missing = required - entry.keys()
        if missing:
            raise ValueError(
                f"prompt entry [{i}] missing required fields: {sorted(missing)}"
            )
        if not _PROMPT_ID_RE.fullmatch(entry["prompt_id"]):
            # Used as a filesystem segment for the API image; reject anything
            # that could escape the run dir.
            raise ValueError(
                f"prompt_id {entry['prompt_id']!r} must match {_PROMPT_ID_RE.pattern}"
            )
    return raw


def _render_report(
    pairs: list[_PairResult],
    *,
    run_dir: Path,
    timestamp: str,
) -> str:
    skipped_count = sum(1 for p in pairs if p.api_status.startswith("skipped"))
    fail_count = sum(1 for p in pairs if p.api_status.startswith("partial fail"))
    ok_count = sum(1 for p in pairs if p.api_status == "ok")

    header = (
        f"# parity_report.md — {timestamp}\n"
        "\n"
        f"**Run dir**: `{run_dir}`\n"
        f"**Pairs**: {len(pairs)} (api ok: {ok_count}, "
        f"skipped: {skipped_count}, partial fail: {fail_count})\n"
        "\n"
        "## What this is\n"
        "\n"
        "Round 5 C4 soft gate — checks the ADR-014 dev/prod parity assumption "
        "(GPT-Image via chatgpt.com == GPT-Image via API). For each prompt, "
        "the manual mode wrote a prompt package; the author should generate "
        "the manual image at chatgpt.com, drop it into the manual dir, then "
        "score the pair below 0/1/2 (0 = identical, 1 = minor drift, 2 = "
        "noticeable drift).\n"
        "\n"
        "**Pass criterion**: ≥ 2 of 3 pairs score ≤ 1 ⇒ assumption holds. "
        "Otherwise → recook (investigate model parity, possibly cap API "
        "quality at the chatgpt-equivalent tier).\n"
        "\n"
    )

    rows = ["## Pairs\n"]
    for p in pairs:
        rows.append(f"### `{p.prompt_id}`  ({p.asset_kind})\n")
        rows.append(f"- **manual prompt package**: `{p.manual_path}`\n")
        if p.api_image_path is not None:
            rows.append(f"- **api image**: `{p.api_image_path}`\n")
        else:
            rows.append("- **api image**: _(none — see status)_\n")
        rows.append(f"- **api status**: {p.api_status}\n")
        if p.api_cost_usd > 0:
            rows.append(f"- **api cost**: ${p.api_cost_usd:.4f}\n")
        rows.append("- **author drift score (0/1/2)**: _TBD_\n")
        rows.append("- **author note**: _TBD_\n")
        rows.append("\n")

    summary = [
        "## Summary (author fills)\n",
        "\n",
        "- pairs scored ≤ 1: _TBD_\n",
        "- assumption holds (≥ 2 of 3)? _TBD_\n",
        "- next action: _TBD_\n",
    ]

    return "".join([header, *rows, *summary])


def _append_cost_log(
    *,
    cost_log_path: Path,
    timestamp: str,
    run_dir: Path,
    pair_results: list[_PairResult],
    api_total_cost: float,
) -> None:
    cost_log_path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "timestamp": timestamp,
        "source": "visual_parity_smoke",
        "run_dir": str(run_dir),
        "n_api_calls": sum(1 for p in pair_results if p.api_status == "ok"),
        "total_cost_usd": round(api_total_cost, 6),
    }
    with cost_log_path.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(record, ensure_ascii=False) + "\n")


def _build_default_api_provider() -> tuple[ImageProvider | None, str | None]:
    """Return (provider, None) if OPENAI_API_KEY is set, else (None, reason).

    Wraps construction so a missing env var degrades gracefully instead of
    raising — this is the contract surface for the CLI."""
    if not os.environ.get("OPENAI_API_KEY"):
        return None, "skipped: no OPENAI_API_KEY"
    try:
        return OpenAIImageProvider(), None
    except ImageProviderError as exc:
        return None, f"skipped: provider construction failed: {exc}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="visual_parity_smoke",
        description=(
            "Generate manual + API images for N prompts and write a "
            "side-by-side parity report. Round 5 C4 soft gate."
        ),
    )
    parser.add_argument(
        "--prompts",
        type=Path,
        required=True,
        help="JSON file with a list of prompt entries (see module docstring).",
    )
    parser.add_argument(
        "--n",
        type=int,
        default=3,
        help=(
            "Maximum number of prompts to run (default: 3). If the file "
            "has more, the first --n are used; fewer is OK too."
        ),
    )
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(message)s")

    if not args.prompts.is_file():
        print(f"error: --prompts path not found: {args.prompts}", file=sys.stderr)
        return 2

    try:
        raw = json.loads(args.prompts.read_text(encoding="utf-8"))
        prompts = validate_prompts(raw)
    except (json.JSONDecodeError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2

    if args.n < 1:
        print("error: --n must be >= 1", file=sys.stderr)
        return 2
    selected = prompts[: args.n]

    api, reason = _build_default_api_provider()
    result = run_parity_smoke(
        selected,
        api_provider=api,
        api_provider_unavailable_reason=reason,
    )

    print(f"parity smoke done → {result['report_path']}")
    print(
        f"pairs: {len(result['pair_results'])}  "
        f"api total cost: ${result['api_total_cost_usd']:.4f}"
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
