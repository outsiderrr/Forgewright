"""Batch experiment harness for `generate_scene` (T-2.8 / ADR-020).

CLI:

    python -m generator.scene_experiment --batch-name <name> --count <N>

Sibling of `generator.experiment` but for scene-level generation. Each
iteration calls `generate_scene` against a built-in fixture set rotated
deterministically (round-robin), so a baseline N=15 batch always hits
each fixture the same number of times — no random surprises when the
author re-runs.

Fixtures start from the《铁誓驿站》canonical scene; the author can fork
this file in L3 to add more scene types. Each fixture supplies a
`(SceneSetting, target_beats, participating_npcs, ontology)` tuple
matching the `generate_scene` contract.

Output lands at `/generator/experiments/<UTC-timestamp>_<batch_name>/`:

  * scene_results.jsonl  — one envelope per iteration, including the
                           assembled graph + topology / sampling
                           validator results so scene_review_cli +
                           scene_metrics can re-display them later
                           without re-running the validators.
  * scene_summary.txt    — schema_pass_rate / topology_pass_rate /
                           sampling_reach_rate / mean_cost /
                           failure_distribution + ADR-020 gross_pass_rate.
  * graph_views/<scene_id>/{mermaid.mmd, dot.gv, ascii.txt} — three
                           visualisations per success scene
                           (U-GPT-7 strong rec).

Budget guard: `generate_scene` already short-circuits on `BudgetExceeded`
and surfaces it as a `failure_reason`. The harness records the failed
row, sets `stopped_early=True`, flushes summary, and returns.
"""
from __future__ import annotations

import argparse
import dataclasses
import json
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from dotenv import load_dotenv

from generator import budget, graph_view
from generator.generate_scene import SceneResult, generate_scene
from generator.llm_provider import LLMProvider
from generator.scene_strategies import SceneSetting
from validator import dialogue_validator, graph_validation, sampling

DEFAULT_COUNT = 15  # ADR-020 baseline protocol: N=15
EXPERIMENTS_ROOT = Path(__file__).parent / "experiments"

# Default sampling parameters for the 2B reach-rate check. ADR-021 §
# completion criteria starts at N=100; we keep that as the default and
# let the author override via env/flag if needed.
_SAMPLING_COUNT = 100
_SAMPLING_SEED = 42  # deterministic so batch reruns produce identical metrics


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class SceneFixture:
    fixture_id: str
    scene_setting: SceneSetting
    target_beats: tuple[str, ...]
    participating_npcs: tuple[str, ...]


# Module-load: the ontology lives at /state/ontology/waystation.json.
# We load once and reuse across iterations — the file is read-only here
# (CLAUDE.md rule 2: no cross-module writes), and a per-iteration reload
# just to be defensive would burn ~5ms × N for nothing.
_ONTOLOGY_PATH = (
    Path(__file__).resolve().parent.parent / "state" / "ontology" / "waystation.json"
)


def _load_ontology() -> dict:
    return json.loads(_ONTOLOGY_PATH.read_text(encoding="utf-8"))


def _build_fixtures() -> list[SceneFixture]:
    """Three Iron-Oath-anchored scene fixtures (round-robin sampled)."""
    base_setting = SceneSetting(
        scene_anchor="scene_waystation_of_iron_oath",
        primary_location_ref="scene_waystation_of_iron_oath",
        chapter_ref=None,
        expected_node_count_min=5,
        expected_node_count_max=12,
    )
    return [
        SceneFixture(
            fixture_id="iron_oath_confession",
            scene_setting=base_setting,
            target_beats=(
                "抵达驿站",
                "Vellin 接待并隐瞒口信",
                "玩家发现破绽",
                "ending：共谋掩护",
                "ending：当面拆穿",
            ),
            participating_npcs=("char_vellin",),
        ),
        SceneFixture(
            fixture_id="iron_oath_patrol_arrives",
            scene_setting=base_setting,
            target_beats=(
                "Vellin 接待玩家",
                "巡逻官 Corvan 推门",
                "三方僵持表态",
                "ending：保护 Vellin",
                "ending：配合调查",
            ),
            participating_npcs=("char_vellin", "char_corvan"),
        ),
        SceneFixture(
            fixture_id="iron_oath_aelwin_letter",
            scene_setting=base_setting,
            target_beats=(
                "Vellin 交出 Aelwin 的信",
                "玩家追问关系",
                "Aelwin 隔窗呼喊（可选）",
                "ending：撕信沉默",
                "ending：携信外出",
            ),
            participating_npcs=("char_vellin", "char_aelwin"),
        ),
    ]


# ---------------------------------------------------------------------------
# Validator helpers
# ---------------------------------------------------------------------------


def _summarise_topology(graph: dict, ontology: dict) -> dict:
    """Run T-2.7 2A and reduce to a JSON-serialisable summary.

    Review 4.2: ADR-021 splits 2A into "纯拓扑" (structural reachability /
    deadlock / convergence) **and** "condition 引用形态合法性" (CONDITION_
    FORM_INVALID — path namespace, op enum, leaf vs composite). Earlier
    revisions of this function collapsed both into one `pass` field, so
    a reviewer couldn't tell whether the graph wiring was wrong or just
    a malformed condition slipped through. We now surface both gates
    independently and keep the legacy `pass` (= AND of both) for
    backwards-compat with downstream readers.
    """
    res = graph_validation.validate_graph_topology(graph, ontology=ontology)
    errors = [i for i in res.issues if i.severity == "error"]
    warnings = [i for i in res.issues if i.severity == "warning"]
    condition_form_errors = [i for i in errors if i.code == "CONDITION_FORM_INVALID"]
    pure_topology_errors = [i for i in errors if i.code != "CONDITION_FORM_INVALID"]
    return {
        "pass": not res.has_error,
        "pure_topology_pass": not pure_topology_errors,
        "condition_form_pass": not condition_form_errors,
        "condition_form_issue_count": len(res.condition_form_issues),
        "error_count": len(errors),
        "warning_count": len(warnings),
        "error_codes": sorted({i.code for i in errors}),
        "unreachable_nodes": list(res.unreachable_nodes),
        "deadlock_nodes": list(res.deadlock_nodes),
    }


def _summarise_sampling(graph: dict) -> dict:
    """Run T-2.7 2B sampling and reduce to a JSON-serialisable summary."""
    res = sampling.validate_graph_sampling(
        graph, sample_count=_SAMPLING_COUNT, seed=_SAMPLING_SEED
    )
    return {
        "sample_count": res.sample_count,
        "reached_end_count": res.reached_end_count,
        "deadlock_count": res.deadlock_count,
        "avg_path_length": res.avg_path_length,
        "reach_rate": res.reach_rate,
        "end_distribution": dict(res.end_distribution),
    }


def _summarise_mechanical(graph: dict, ontology: dict) -> dict:
    """Re-run T-2.4 over the assembled graph for the per-iteration record.

    `generate_scene` already gates on this layer pre-success, but the
    review CLI + metrics want a count of issues + per-node hits without
    re-running the validator themselves. We dump a small summary here.
    """
    results = dialogue_validator.validate_graph_mechanical(graph, ontology=ontology)
    error_nodes = {nid: r for nid, r in results.items() if r.has_error}
    error_count = sum(
        len([i for i in r.issues if i.severity == "error"])
        for r in results.values()
    )
    return {
        "pass": not error_nodes,
        "error_node_count": len(error_nodes),
        "error_count": error_count,
        "error_codes": sorted({
            i.code
            for r in results.values()
            for i in r.issues
            if i.severity == "error"
        }),
    }


# ---------------------------------------------------------------------------
# Serialisation
# ---------------------------------------------------------------------------


def _serialise_setting(s: SceneSetting) -> dict:
    return {
        "scene_anchor": s.scene_anchor,
        "primary_location_ref": s.primary_location_ref,
        "chapter_ref": s.chapter_ref,
        "expected_node_count_min": s.expected_node_count_min,
        "expected_node_count_max": s.expected_node_count_max,
    }


def _serialise_envelope(
    *,
    iter_id: int,
    fixture: SceneFixture,
    result: SceneResult,
    ontology: dict,
) -> dict:
    """Build one results.jsonl row.

    On success we serialise the full graph plus topology / sampling /
    mechanical summaries so review_cli can show them without re-loading
    the validator. On failure those fields are absent.
    """
    env: dict = {
        "iter_id": iter_id,
        "fixture_id": fixture.fixture_id,
        "fixture": {
            "scene_setting": _serialise_setting(fixture.scene_setting),
            "target_beats": list(fixture.target_beats),
            "participating_npcs": list(fixture.participating_npcs),
        },
        "result": {
            "success": result.success,
            "failure_reason": result.failure_reason,
            "failure_node_id": result.failure_node_id,
            "graph": result.graph,
            "schema_issues": list(result.schema_issues),
            "mechanical_issues_count": sum(
                len(v) for v in result.mechanical_issues.values()
            ),
            "total_cost_usd": result.total_cost_usd,
            "inner_attempt_count": len(result.inner_results),
        },
        "validator_summaries": None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    if result.success and isinstance(result.graph, dict):
        env["validator_summaries"] = {
            "mechanical": _summarise_mechanical(result.graph, ontology),
            "topology": _summarise_topology(result.graph, ontology),
            "sampling": _summarise_sampling(result.graph),
        }
    return env


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------


def _render_summary(envelopes: Iterable[dict], stopped_early: bool) -> str:
    envs = list(envelopes)
    total = len(envs)
    if total == 0:
        return "no iterations completed.\n"

    schema_pass = sum(1 for e in envs if e["result"]["success"])
    topo_pass = sum(
        1
        for e in envs
        if (e.get("validator_summaries") or {}).get("topology", {}).get("pass")
    )
    mech_pass = sum(
        1
        for e in envs
        if (e.get("validator_summaries") or {}).get("mechanical", {}).get("pass")
    )
    sampling_reaches = [
        (e.get("validator_summaries") or {}).get("sampling", {}).get("reach_rate")
        for e in envs
    ]
    sampling_reaches = [r for r in sampling_reaches if isinstance(r, (int, float))]
    avg_reach = sum(sampling_reaches) / len(sampling_reaches) if sampling_reaches else 0.0

    total_cost = sum(float(e["result"]["total_cost_usd"]) for e in envs)
    mean_cost = total_cost / total

    reasons = Counter(
        e["result"]["failure_reason"] for e in envs if not e["result"]["success"]
    )

    lines: list[str] = []
    lines.append(f"iterations:            {total}")
    lines.append(f"schema_pass_rate:      {schema_pass / total:.1%}  ({schema_pass}/{total})")
    # ADR-020 gross_pass_rate: 通过机械预检的场景数 / 总尝试场景数.
    lines.append(f"gross_pass_rate:       {mech_pass / total:.1%}  ({mech_pass}/{total})")
    lines.append(f"topology_pass_rate:    {topo_pass / total:.1%}  ({topo_pass}/{total})")
    lines.append(f"sampling_reach_rate:   {avg_reach:.1%}  (avg over success scenes)")
    lines.append(f"total_cost_usd:        ${total_cost:.4f}")
    lines.append(f"mean_cost_per_iter:    ${mean_cost:.4f}")
    lines.append("")
    lines.append("failure_reason_distribution:")
    if reasons:
        for reason, count in reasons.most_common():
            lines.append(f"  {str(reason):<22} {count}")
    else:
        lines.append("  (none)")
    if stopped_early:
        lines.append("")
        lines.append("NOTE: batch stopped early due to budget_exceeded.")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Graph view dump
# ---------------------------------------------------------------------------


def _dump_graph_views(graph: dict, dest_dir: Path) -> None:
    """Write three views per success scene. Failures must not break the batch."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    try:
        (dest_dir / "mermaid.mmd").write_text(
            graph_view.render_mermaid(graph), encoding="utf-8"
        )
        (dest_dir / "dot.gv").write_text(
            graph_view.render_dot(graph), encoding="utf-8"
        )
        (dest_dir / "ascii.txt").write_text(
            graph_view.render_ascii(graph), encoding="utf-8"
        )
    except Exception as exc:  # noqa: BLE001 — view rendering is best-effort
        (dest_dir / "render_error.txt").write_text(
            f"render failed: {type(exc).__name__}: {exc}\n", encoding="utf-8"
        )


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


def run_scene_experiment(
    *,
    batch_name: str,
    count: int,
    provider: LLMProvider,
    out_root: Path = EXPERIMENTS_ROOT,
    fixtures: list[SceneFixture] | None = None,
    ontology: dict | None = None,
    timestamp: str | None = None,
    progress: bool = True,
) -> Path:
    """Execute `count` scene generations and write results to a fresh batch dir."""
    if count < 1:
        raise ValueError("count must be >= 1")
    fixtures = fixtures if fixtures is not None else _build_fixtures()
    if not fixtures:
        raise ValueError("fixtures must be non-empty")
    ontology = ontology if ontology is not None else _load_ontology()

    ts = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch_dir = out_root / f"{ts}_{batch_name}"
    batch_dir.mkdir(parents=True, exist_ok=True)
    results_path = batch_dir / "scene_results.jsonl"
    summary_path = batch_dir / "scene_summary.txt"
    views_root = batch_dir / "graph_views"

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
            result = generate_scene(
                scene_setting=fixture.scene_setting,
                target_beats=list(fixture.target_beats),
                participating_npcs=list(fixture.participating_npcs),
                ontology=ontology,
                provider=provider,
            )
            # graph_id from scene_strategies is derived solely from
            # scene_anchor; multi-iter batches over the same fixture (or
            # different fixtures sharing an anchor) collide downstream:
            # graph_views/<id>/ overwrites between iters, scene_ai_judge
            # keys by id (5 scenes -> 1 dict entry), scene_review_cli
            # iterates by id (author can only [A]/[R] one of N). Suffix
            # iter so each scene has a unique id from JSONL onward.
            if result.success and isinstance(result.graph, dict):
                base_graph_id = result.graph.get("graph_id")
                if base_graph_id:
                    result.graph["graph_id"] = f"{base_graph_id}__iter{iter_id:02d}"
            envelope = _serialise_envelope(
                iter_id=iter_id, fixture=fixture, result=result, ontology=ontology
            )
            envelopes.append(envelope)
            fh.write(json.dumps(envelope, ensure_ascii=False) + "\n")
            fh.flush()

            if result.success and isinstance(result.graph, dict):
                scene_id = result.graph.get("graph_id") or f"iter_{iter_id}"
                _dump_graph_views(result.graph, views_root / scene_id)

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
    """Construct the LLM_PROVIDER-selected provider lazily so test fixtures
    (FakeProvider) don't need any provider env var set at import time."""
    from generator.providers import get_default_provider

    return get_default_provider()


def main(argv: list[str] | None = None) -> int:
    load_dotenv()

    parser = argparse.ArgumentParser(
        prog="python -m generator.scene_experiment",
        description="Run a batch of generate_scene iterations and dump results.",
    )
    parser.add_argument("--batch-name", required=True, help="Label for this batch.")
    parser.add_argument(
        "--count",
        type=int,
        default=DEFAULT_COUNT,
        help=f"Number of scene iterations to run (default {DEFAULT_COUNT}).",
    )
    args = parser.parse_args(argv)

    _print_budget_header()
    provider = _build_default_provider()
    batch_dir = run_scene_experiment(
        batch_name=args.batch_name,
        count=args.count,
        provider=provider,
    )
    print(f"\nbatch dir: {batch_dir}")
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
