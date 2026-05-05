"""Batch experiment harness for `generate_node` (T-1.7).

CLI:

    python -m generator.experiment --batch-name <name> --count <N>

Runs N single-node generations against a small built-in fixture set that
covers the four shapes the author cares about:

  * dialogue_entry_vellin   — entry-position dialogue (no parent chain)
  * dialogue_middle_corvan  — mid-graph dialogue with a parent chain
  * dialogue_middle_aelwin  — mid-graph dialogue, different speaker
  * end_silent              — end node (narrator, no speaker)

Sampling is deterministic round-robin so a 20-run batch always hits each
fixture 5 times — no random seed surprises when the author re-runs.

Output lands at `/generator/experiments/<UTC-timestamp>_<batch_name>/`:

  * results.jsonl — one envelope per iteration (see _serialise_envelope)
  * summary.txt   — schema pass-rate, mean cost, failure reason histogram

Budget guard: each iteration calls `generate_node`, which already catches
`BudgetExceeded` internally and surfaces it as a `failure_reason`. When we
see one, we stop the loop, flush what we have, and exit non-zero so the
author notices.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

from generator import budget
from generator.context_assembler import GraphContext, NodeRequirement
from generator.generate_node import GenerationResult, generate_node
from generator.llm_provider import LLMProvider

DEFAULT_COUNT = 20
EXPERIMENTS_ROOT = Path(__file__).parent / "experiments"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class Fixture:
    fixture_id: str
    graph_context: GraphContext
    node_requirement: NodeRequirement


_LOCATION_CANDIDATES = [
    {
        "location_id": "scene_waystation_of_iron_oath",
        "name": "铁誓驿站",
        "summary": "铁誓卫队在山道上的中转驿站，黄昏时分山风呼啸；外人罕至。",
    },
    {
        "location_id": "scene_eastern_pasture_ruin",
        "name": "牧人废屋",
        "summary": "驿站东侧约半日马程的废弃牧人小屋，眼下藏着逃兵 Aelwin。",
    },
]
_PRIMARY_LOCATION_REF = "scene_waystation_of_iron_oath"

_VELLIN = {
    "character_id": "char_vellin",
    "summary": "驿站管事，旧识；隐瞒着一封逃兵的口信。",
}
_CORVAN = {
    "character_id": "char_corvan",
    "summary": "巡逻官，旧识；正在追查逃兵 Aelwin 的下落。",
}
_AELWIN = {
    "character_id": "char_aelwin",
    "summary": "三年前的少年兵旧识，已自卫队逃亡。",
}


def _parent_arrival() -> dict:
    """A pared-down version of the canonical entry node, used as a synthetic
    parent for mid-graph fixtures. Keeping it minimal (narration excerpt
    only) so the LLM gets shape, not a wall of duplicate text."""
    return {
        "node_id": "arrival_waystation",
        "type": "dialogue",
        "narration": "你推门走入驿站，Vellin 在柜台后；她瞳孔一缩又强笑接待你。",
        "speaker_ref": "char_vellin",
        "location_ref": "scene_waystation_of_iron_oath",
        "options": [
            {
                "option_id": "opt_confront_letter",
                "text": "[按住那叠纸] 你手上沾的不是酒。",
                "target_node_id": "vellin_confession",
                "condition": None,
                "effects": [],
                "unavailable_behavior": "hide",
            },
        ],
    }


def _parent_confession() -> dict:
    return {
        "node_id": "vellin_confession",
        "type": "dialogue",
        "narration": "Vellin 把信合上，低声请求你装作从没来过——明早巡逻官将搜驿站。",
        "speaker_ref": "char_vellin",
        "location_ref": "scene_waystation_of_iron_oath",
        "options": [
            {
                "option_id": "opt_promise_silence",
                "text": "Hael 活该。我什么都没看见。",
                "target_node_id": "end_silent_ally",
                "condition": None,
                "effects": [],
                "unavailable_behavior": "hide",
            },
        ],
    }


def _build_fixtures() -> list[Fixture]:
    return [
        Fixture(
            fixture_id="dialogue_entry_vellin",
            graph_context=GraphContext(
                scene_anchor="scene_waystation_of_iron_oath",
                location_candidates=_LOCATION_CANDIDATES,
                primary_location_ref=_PRIMARY_LOCATION_REF,
                parent_chain=[],
                involved_characters=[_VELLIN],
                faction_clocks={},
            ),
            node_requirement=NodeRequirement(
                node_type="dialogue",
                expected_speaker_ref="char_vellin",
                narrative_intent="入口节点：Vellin 接待来客，建立场景张力，"
                "让玩家在『过路客 / 介入者』之间表态",
            ),
        ),
        Fixture(
            fixture_id="dialogue_middle_corvan",
            graph_context=GraphContext(
                scene_anchor="scene_waystation_of_iron_oath",
                location_candidates=_LOCATION_CANDIDATES,
                primary_location_ref=_PRIMARY_LOCATION_REF,
                parent_chain=[_parent_arrival()],
                involved_characters=[_CORVAN, _VELLIN],
                faction_clocks={},
            ),
            node_requirement=NodeRequirement(
                node_type="dialogue",
                expected_speaker_ref="char_corvan",
                narrative_intent="巡逻官 Corvan 推门而入，外部压力到场；"
                "玩家需在掩护 Vellin 与配合调查之间二选一",
            ),
        ),
        Fixture(
            fixture_id="dialogue_middle_aelwin",
            graph_context=GraphContext(
                # narrative_intent below moves the action to 牧人废屋 — the
                # primary_location_ref must match, otherwise the prompt's
                # "推荐默认 location_ref" would push Aelwin's scene back into
                # the waystation (review 4.2, T-2.0 R4).
                scene_anchor="scene_waystation_of_iron_oath",
                location_candidates=_LOCATION_CANDIDATES,
                primary_location_ref="scene_eastern_pasture_ruin",
                parent_chain=[_parent_arrival(), _parent_confession()],
                involved_characters=[_AELWIN, _VELLIN],
                faction_clocks={},
            ),
            node_requirement=NodeRequirement(
                node_type="dialogue",
                expected_speaker_ref="char_aelwin",
                narrative_intent="玩家潜行抵达牧人废屋，与逃兵 Aelwin 对视；"
                "Aelwin 试探玩家立场，给出 3-6 个反映性格倾向的选项",
            ),
        ),
        Fixture(
            fixture_id="end_silent",
            graph_context=GraphContext(
                scene_anchor="scene_waystation_of_iron_oath",
                location_candidates=_LOCATION_CANDIDATES,
                primary_location_ref=_PRIMARY_LOCATION_REF,
                parent_chain=[_parent_confession()],
                involved_characters=[],
                faction_clocks={},
            ),
            node_requirement=NodeRequirement(
                node_type="end",
                expected_speaker_ref=None,
                narrative_intent="共谋分支收尾：以书信回响代替直接交代，"
                "options 必须为空数组",
            ),
        ),
    ]


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def _serialise_graph_context(ctx: GraphContext) -> dict:
    return {
        "scene_anchor": ctx.scene_anchor,
        "location_candidates": list(ctx.location_candidates),
        "primary_location_ref": ctx.primary_location_ref,
        "parent_chain": list(ctx.parent_chain),
        "involved_characters": list(ctx.involved_characters),
        "faction_clocks": dict(ctx.faction_clocks),
    }


def _serialise_requirement(req: NodeRequirement) -> dict:
    return {
        "node_type": req.node_type,
        "expected_speaker_ref": req.expected_speaker_ref,
        "narrative_intent": req.narrative_intent,
    }


def _serialise_result(result: GenerationResult) -> dict:
    return {
        "success": result.success,
        "node": result.node,
        "failure_reason": result.failure_reason,
        "attempts": [dataclasses.asdict(a) for a in result.attempts],
        "total_cost_usd": result.total_cost_usd,
    }


def _serialise_envelope(
    *, iter_id: int, fixture: Fixture, result: GenerationResult
) -> dict:
    return {
        "iter_id": iter_id,
        "fixture_id": fixture.fixture_id,
        "fixture": {
            "graph_context": _serialise_graph_context(fixture.graph_context),
            "node_requirement": _serialise_requirement(fixture.node_requirement),
        },
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
        return "no iterations completed.\n"

    pass_count = sum(1 for e in envs if e["result"]["success"])
    pass_rate = pass_count / total
    total_cost = sum(e["result"]["total_cost_usd"] for e in envs)
    mean_cost = total_cost / total
    reasons = Counter(
        e["result"]["failure_reason"] for e in envs if not e["result"]["success"]
    )

    lines: list[str] = []
    lines.append(f"iterations:        {total}")
    lines.append(f"schema_pass_rate:  {pass_rate:.1%}  ({pass_count}/{total})")
    lines.append(f"total_cost_usd:    ${total_cost:.4f}")
    lines.append(f"mean_cost_per_iter:${mean_cost:.4f}")
    lines.append("")
    lines.append("failure_reason_distribution:")
    if reasons:
        for reason, count in reasons.most_common():
            lines.append(f"  {reason:<20} {count}")
    else:
        lines.append("  (none)")
    if stopped_early:
        lines.append("")
        lines.append("NOTE: batch stopped early due to budget_exceeded.")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Runner
# ---------------------------------------------------------------------------


def _print_budget_header() -> None:
    daily = budget.daily_budget_usd()
    used = budget.today_total_usd()
    remaining = max(0.0, daily - used)
    print(
        f"[budget] daily=${daily:.2f}  used_today=${used:.4f}  "
        f"remaining=${remaining:.4f}"
    )


def run_experiment(
    *,
    batch_name: str,
    count: int,
    provider: LLMProvider,
    out_root: Path = EXPERIMENTS_ROOT,
    fixtures: list[Fixture] | None = None,
    timestamp: str | None = None,
    progress: bool = True,
) -> Path:
    """Execute `count` generations and write results to a fresh batch dir.

    Returns the path to the batch dir. Stops early (and still flushes)
    on the first `budget_exceeded` failure.
    """
    if count < 1:
        raise ValueError("count must be >= 1")

    fixtures = fixtures if fixtures is not None else _build_fixtures()
    if not fixtures:
        raise ValueError("fixtures must be non-empty")

    ts = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch_dir = out_root / f"{ts}_{batch_name}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    results_path = batch_dir / "results.jsonl"
    summary_path = batch_dir / "summary.txt"

    envelopes: list[dict] = []
    stopped_early = False

    with open(results_path, "w", encoding="utf-8") as fh:
        for iter_id in range(count):
            fixture = fixtures[iter_id % len(fixtures)]
            if progress:
                print(
                    f"[{iter_id + 1}/{count}] fixture={fixture.fixture_id} ...",
                    end=" ",
                    flush=True,
                )
            result = generate_node(
                graph_context=fixture.graph_context,
                node_requirement=fixture.node_requirement,
                provider=provider,
            )
            envelope = _serialise_envelope(
                iter_id=iter_id, fixture=fixture, result=result
            )
            envelopes.append(envelope)
            fh.write(json.dumps(envelope, ensure_ascii=False) + "\n")
            fh.flush()

            if progress:
                tag = "ok" if result.success else f"fail({result.failure_reason})"
                print(f"{tag}  cost=${result.total_cost_usd:.4f}")

            if result.failure_reason == "budget_exceeded":
                stopped_early = True
                if progress:
                    print(
                        "[budget] BudgetExceeded — stopping batch and "
                        "flushing partial results."
                    )
                break

    summary_path.write_text(
        _render_summary(envelopes, stopped_early=stopped_early), encoding="utf-8"
    )

    if progress:
        print(f"[done] wrote {len(envelopes)} results to {batch_dir}")
        print(f"[done] summary at {summary_path}")

    return batch_dir


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _build_default_provider() -> LLMProvider:
    """Construct the LLM_PROVIDER-selected provider. Imported lazily so the
    test suite (which uses FakeProvider) doesn't need any provider env var
    set at module-import time."""
    from generator.providers import get_default_provider

    return get_default_provider()


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="python -m generator.experiment",
        description="Run a batch of generate_node iterations and dump results.",
    )
    parser.add_argument("--batch-name", required=True, help="Label for this batch.")
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_COUNT,
        help=f"Number of iterations to run (default {DEFAULT_COUNT}).",
    )
    args = parser.parse_args(argv)

    _print_budget_header()
    provider = _build_default_provider()
    batch_dir = run_experiment(
        batch_name=args.batch_name,
        count=args.count,
        provider=provider,
    )
    print(f"\nbatch dir: {batch_dir}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
