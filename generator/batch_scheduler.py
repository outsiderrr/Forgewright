"""Batch generation scheduler with SceneSpec DAG (T-3.5; ADR-026 / F4 / F12 / F13 / F14).

Per ADR-026: a worker pool that drives `generate_scene` over many scenes
with topology-aware concurrency. The pool reads a list of `SceneSpec`,
arranges them into a topological **layer** sequence (so a scene's
generation never starts before its declared `depends_on_scene_ids`
finish), and runs each layer through an asyncio Queue with N concurrent
workers. Provider rate limiting is delegated to
`generator._rate_limit.RateLimitedProvider` (F14) so the same RPM
ceiling applies to skeleton + every fill call inside one scene.

Module boundaries (CLAUDE.md rule 2 / T-3.5 prompt §模块边界):

  * **Allowed**: this file (new), `dep_index_writer.py` (T-3.5; this
    PR), `_rate_limit.py` (T-3.5; this PR), `generate_scene.py`
    (extended), `context_assembler.py` (extended).
  * **Forbidden**: `chapter_assembler.py` (T-3.9 helper — call only),
    `version_recorder.py` (T-3.8a helper — call only), schema, state,
    engine, validator. The shared lock factory below mutates ontology
    *via* `chapter_assembler` rather than touching the file directly.
  * **Not depended on**: `playtest/` modules (F13 — playtest and
    scheduler are decoupled).

Layer-wise stats (BS-8 v1.0 addition) are surfaced in the
`batch_summary.md` so an operator can see at a glance how a DAG with N
layers behaved relative to a flat list — useful for tuning
`depends_on_scene_ids` density.

CLI (BS-9):

    python -m generator.batch_scheduler <scenes_spec.json> \\
        [--concurrent-n 3] [--rpm 60] [--dry-run] [--out-root <dir>]

`<scenes_spec.json>` is a JSON file shaped like::

    {
      "out_root": "/path/to/batch/dir/parent",
      "ontology_path": "state/ontology/waystation.json",
      "scenes": [
        {
          "scene_setting": {"scene_anchor": ..., ...},
          "target_beats": [...],
          "participating_npcs": [...],
          "scene_path": "content/<dir>/scene.json",
          "chapter_id": "chap_arrival",
          "act_id": "act_one",
          "depends_on_scene_ids": ["other_scene_id", ...],
          "sequence_group": "main",
          "prior_summary_paths": ["content/.../scene.summary.json", ...]
        },
        ...
      ]
    }

`--dry-run` prints the resolved layer plan + cost estimate and exits 0
without instantiating a real provider — safe to run before committing
budget.
"""

from __future__ import annotations

import argparse
import asyncio
import contextlib
import dataclasses
import fcntl
import json
import logging
import os
import sys
import threading
import time
from collections import Counter, defaultdict
from collections.abc import Callable, Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from generator import budget
from generator._rate_limit import (
    DEFAULT_RPM,
    RateLimitedProvider,
    resolve_rpm,
)
from generator.context_assembler import PriorSceneSummary
from generator.generate_scene import SceneResult, estimate_scene_cost, generate_scene
from generator.llm_provider import LLMProvider
from generator.scene_strategies import SceneSetting

_LOG = logging.getLogger(__name__)

# Default worker count. Mirrors STAGE_3_TASKS §2.4 / ADR-026 §"配置".
# Operators override via `FORGEWRIGHT_BATCH_CONCURRENT_N`; CLI flag
# `--concurrent-n` wins above that.
DEFAULT_CONCURRENT_N = 3

OntologyLockFactory = Callable[[Path], AbstractContextManager[None]]


# ---------------------------------------------------------------------------
# SceneSpec (BS-1; ADR-026 / F4)
# ---------------------------------------------------------------------------


@dataclass
class SceneSpec:
    """One unit of work for the batch scheduler.

    Wraps the bare arguments `generate_scene` needs plus the DAG
    metadata (`depends_on_scene_ids` / `sequence_group`) that drives
    layer assignment.

    Field semantics:
      * `scene_id` — opaque identifier the scheduler uses for layer
        bookkeeping. Must be unique within a batch. Defaults to the
        scene_anchor when not explicitly set; callers that batch
        multiple scenes against the same anchor (e.g. T-2.12-style
        `__iter` reruns) must override to keep the DAG sane.
      * `scene_setting` / `target_beats` / `participating_npcs` —
        forwarded verbatim to `generate_scene`.
      * `scene_path` — where to land `scene.json`. Sibling sidecars
        (`<scene>.deps.json` / `<scene>.version.json`) are derived from
        the same parent.
      * `chapter_id` / `act_id` — passed to `assign_scene_to_chapter`
        (T-3.9 helper). Both can be `None` to land in the unassigned
        bucket.
      * `depends_on_scene_ids` — IDs of other scenes (in the same
        batch) whose generation must complete before this one starts.
        Topological layer assignment uses these edges.
      * `sequence_group` — soft within-layer ordering hint. Scenes in
        the same `sequence_group` run in declaration order on the
        same layer (the scheduler sorts a layer's queue by group +
        declaration index so a downstream-reading consumer sees
        identical timing for the same input). When omitted the scenes
        are unordered within their layer.
      * `prior_summary_paths` — optional list of
        `<scene>.summary.json` files produced by `scene_summary_writer`
        (T-3.3) whose `PriorSceneSummary` payloads should be loaded
        and forwarded as `generate_scene(prior_scene_summaries=...)`.
    """

    scene_id: str
    scene_setting: SceneSetting
    target_beats: list[str]
    participating_npcs: list[str]
    scene_path: Path
    chapter_id: str | None = None
    act_id: str | None = None
    depends_on_scene_ids: list[str] = field(default_factory=list)
    sequence_group: str | None = None
    prior_summary_paths: list[Path] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Layer planner (BS-1)
# ---------------------------------------------------------------------------


@dataclass
class LayerPlan:
    """Resolved DAG layer sequence + cycle / unknown-dep diagnostics."""

    layers: list[list[SceneSpec]]
    unknown_dependencies: dict[str, list[str]]
    cycle_remaining: list[str]


def plan_layers(specs: Iterable[SceneSpec]) -> LayerPlan:
    """Group `specs` into Kahn-style topological layers.

    Each layer is the set of specs whose `depends_on_scene_ids` are
    fully satisfied by *prior* layers. Within one layer, specs are
    sorted by `(sequence_group or "", declaration_index)` so the
    runtime ordering is reproducible.

    Diagnostics:
      * `unknown_dependencies` — specs that name a `depends_on_scene_id`
        that doesn't exist in the batch; we record the offending IDs
        but **do not** fail planning (the scheduler is permissive so
        the operator sees a layer plan and the unknown deps in the
        same dry-run).
      * `cycle_remaining` — IDs the planner couldn't place even after
        all known deps cleared (i.e., participants in a dependency
        cycle). Cycle members surface in `LayerPlan.cycle_remaining`
        and are *not* scheduled — they'd otherwise wait forever.
    """
    spec_list = list(specs)
    seen_ids: set[str] = set()
    for s in spec_list:
        if not s.scene_id:
            raise ValueError("SceneSpec must declare a non-empty scene_id")
        if s.scene_id in seen_ids:
            raise ValueError(f"duplicate SceneSpec.scene_id: {s.scene_id!r}")
        seen_ids.add(s.scene_id)

    declaration_index = {s.scene_id: i for i, s in enumerate(spec_list)}

    # Filter out unknown deps so the layer planner only counts edges
    # that actually point inside the batch. The unknown deps are
    # surfaced separately for operator diagnostics.
    unknown_dependencies: dict[str, list[str]] = {}
    effective_deps: dict[str, list[str]] = {}
    for s in spec_list:
        unknown = [d for d in s.depends_on_scene_ids if d not in seen_ids]
        if unknown:
            unknown_dependencies[s.scene_id] = unknown
        effective_deps[s.scene_id] = [
            d for d in s.depends_on_scene_ids if d in seen_ids
        ]

    remaining: dict[str, set[str]] = {
        s.scene_id: set(effective_deps[s.scene_id]) for s in spec_list
    }
    by_id: dict[str, SceneSpec] = {s.scene_id: s for s in spec_list}

    layers: list[list[SceneSpec]] = []
    placed: set[str] = set()
    while True:
        ready = [
            sid
            for sid, deps in remaining.items()
            if sid not in placed and deps.issubset(placed)
        ]
        if not ready:
            break
        ready_sorted = sorted(
            ready,
            key=lambda sid: (
                by_id[sid].sequence_group or "",
                declaration_index[sid],
            ),
        )
        layers.append([by_id[sid] for sid in ready_sorted])
        placed.update(ready)

    cycle_remaining = sorted(set(remaining) - placed)
    return LayerPlan(
        layers=layers,
        unknown_dependencies=unknown_dependencies,
        cycle_remaining=cycle_remaining,
    )


# ---------------------------------------------------------------------------
# Shared ontology lock (BS-7; F6 注脚)
# ---------------------------------------------------------------------------


def make_shared_ontology_lock_factory() -> OntologyLockFactory:
    """Create a `LockFactory` shared across the worker pool.

    `chapter_assembler` already supports `lock_factory` injection. The
    scheduler-level factory adds (a) a `threading.Lock` so the N
    workers serialise inside one Python process and (b) `fcntl.flock`
    on a sibling `<ontology>.lock` so a CLI invocation overlapping the
    batch also serialises. Same recipe `chapter_assembler` uses by
    default — we just make sure every worker hits the *same* mutex
    object.
    """
    proc_lock = threading.Lock()

    @contextlib.contextmanager
    def factory(ontology_path: Path) -> Iterator[None]:
        lock_path = ontology_path.with_suffix(ontology_path.suffix + ".lock")
        lock_path.parent.mkdir(parents=True, exist_ok=True)
        fd = os.open(lock_path, os.O_WRONLY | os.O_CREAT, 0o644)
        try:
            with proc_lock:
                fcntl.flock(fd, fcntl.LOCK_EX)
                try:
                    yield
                finally:
                    fcntl.flock(fd, fcntl.LOCK_UN)
        finally:
            os.close(fd)

    return factory


# ---------------------------------------------------------------------------
# Batch result + per-scene record (BS-8)
# ---------------------------------------------------------------------------


@dataclass
class SceneOutcome:
    """One row per SceneSpec in the BatchResult."""

    scene_id: str
    success: bool
    layer_idx: int
    elapsed_seconds: float
    cost_usd: float
    scene_path: Path
    failure_reason: str | None = None
    failure_metadata: dict | None = None
    chapter_assignment: dict | None = None
    dep_index_path: Path | None = None
    version_sidecar_path: Path | None = None


@dataclass
class LayerStats:
    layer_idx: int
    scene_count: int
    started_at: str
    finished_at: str
    elapsed_seconds: float
    success_count: int
    failure_count: int


@dataclass
class BatchResult:
    """Aggregate outcome of one scheduler run."""

    batch_dir: Path
    outcomes: list[SceneOutcome]
    layer_stats: list[LayerStats]
    plan: LayerPlan
    total_cost_usd: float
    started_at: str
    finished_at: str

    @property
    def success_rate(self) -> float:
        if not self.outcomes:
            return 0.0
        return sum(1 for o in self.outcomes if o.success) / len(self.outcomes)


# ---------------------------------------------------------------------------
# Scene-spec parsing (BS-9)
# ---------------------------------------------------------------------------


def load_scene_specs(spec_doc: dict) -> tuple[list[SceneSpec], Path | None, Path]:
    """Parse a scenes_spec.json document into runtime objects.

    Returns `(scene_specs, ontology_path, default_out_root)`. The
    scheduler keeps spec-level ergonomics close to the dict shape so
    the CLI can stay thin — JSON in, runtime objects out.
    """
    raw_scenes = spec_doc.get("scenes")
    if not isinstance(raw_scenes, list) or not raw_scenes:
        raise ValueError(
            "scenes_spec must include a non-empty `scenes` array"
        )
    out_root = Path(spec_doc.get("out_root") or "generator/experiments")
    ontology_path_raw = spec_doc.get("ontology_path")
    ontology_path = Path(ontology_path_raw) if ontology_path_raw else None

    specs: list[SceneSpec] = []
    for idx, raw in enumerate(raw_scenes):
        if not isinstance(raw, dict):
            raise ValueError(
                f"scenes[{idx}] must be an object, got {type(raw).__name__}"
            )
        setting_raw = raw.get("scene_setting")
        if not isinstance(setting_raw, dict):
            raise ValueError(
                f"scenes[{idx}].scene_setting must be an object"
            )
        setting = SceneSetting(
            scene_anchor=str(setting_raw["scene_anchor"]),
            primary_location_ref=str(setting_raw["primary_location_ref"]),
            chapter_ref=setting_raw.get("chapter_ref"),
            expected_node_count_min=int(
                setting_raw.get("expected_node_count_min", 5)
            ),
            expected_node_count_max=int(
                setting_raw.get("expected_node_count_max", 15)
            ),
        )
        scene_id = raw.get("scene_id") or setting.scene_anchor
        scene_path_raw = raw.get("scene_path")
        if not scene_path_raw:
            raise ValueError(
                f"scenes[{idx}].scene_path is required (where to write "
                f"scene.json + sidecars)"
            )
        spec = SceneSpec(
            scene_id=str(scene_id),
            scene_setting=setting,
            target_beats=[str(b) for b in (raw.get("target_beats") or [])],
            participating_npcs=[
                str(n) for n in (raw.get("participating_npcs") or [])
            ],
            scene_path=Path(scene_path_raw),
            chapter_id=raw.get("chapter_id"),
            act_id=raw.get("act_id"),
            depends_on_scene_ids=[
                str(d) for d in (raw.get("depends_on_scene_ids") or [])
            ],
            sequence_group=raw.get("sequence_group"),
            prior_summary_paths=[
                Path(p) for p in (raw.get("prior_summary_paths") or [])
            ],
        )
        specs.append(spec)
    return specs, ontology_path, out_root


def load_prior_summaries(paths: Iterable[Path]) -> list[PriorSceneSummary]:
    """Inflate `PriorSceneSummary` objects from on-disk sidecars.

    Tolerates absent files (logged at INFO) — a missing summary is a
    soft constraint; the scene generation can still proceed without
    that prior context. Malformed JSON / missing required fields raise
    so the operator notices.
    """
    summaries: list[PriorSceneSummary] = []
    for path in paths:
        if not path.exists():
            _LOG.info("prior_summary_path missing, skipping: %s", path)
            continue
        with path.open("r", encoding="utf-8") as f:
            payload = json.load(f)
        if not isinstance(payload, dict):
            raise ValueError(
                f"prior_summary at {path} must be an object, got "
                f"{type(payload).__name__}"
            )
        summaries.append(
            PriorSceneSummary(
                scene_id=str(payload["scene_id"]),
                summary=str(payload["summary"]),
                key_state_paths=[
                    str(p) for p in (payload.get("key_state_paths") or [])
                ],
                chapter_id=payload.get("chapter_id"),
                act_id=payload.get("act_id"),
            )
        )
    return summaries


# ---------------------------------------------------------------------------
# Worker pool (BS-2)
# ---------------------------------------------------------------------------


async def _run_layer(
    layer_idx: int,
    layer_specs: list[SceneSpec],
    *,
    concurrent_n: int,
    ontology: dict | None,
    ontology_path: Path | None,
    provider: LLMProvider,
    ontology_lock_factory: OntologyLockFactory | None,
    progress_print: bool,
) -> tuple[list[SceneOutcome], LayerStats]:
    started = time.monotonic()
    started_iso = datetime.now(timezone.utc).isoformat()
    queue: asyncio.Queue[SceneSpec] = asyncio.Queue()
    for spec in layer_specs:
        queue.put_nowait(spec)

    outcomes: list[SceneOutcome] = []
    outcomes_lock = asyncio.Lock()

    async def worker(worker_id: int) -> None:
        while True:
            try:
                spec = queue.get_nowait()
            except asyncio.QueueEmpty:
                return
            outcome = await _run_one_spec(
                spec=spec,
                layer_idx=layer_idx,
                ontology=ontology,
                ontology_path=ontology_path,
                provider=provider,
                ontology_lock_factory=ontology_lock_factory,
                progress_print=progress_print,
                worker_id=worker_id,
            )
            async with outcomes_lock:
                outcomes.append(outcome)
            queue.task_done()

    workers = [
        asyncio.create_task(worker(wid))
        for wid in range(min(concurrent_n, len(layer_specs)))
    ]
    if workers:
        await asyncio.gather(*workers)

    finished = time.monotonic()
    finished_iso = datetime.now(timezone.utc).isoformat()
    success_count = sum(1 for o in outcomes if o.success)
    failure_count = len(outcomes) - success_count
    stats = LayerStats(
        layer_idx=layer_idx,
        scene_count=len(layer_specs),
        started_at=started_iso,
        finished_at=finished_iso,
        elapsed_seconds=finished - started,
        success_count=success_count,
        failure_count=failure_count,
    )
    # Sort outcomes by declaration order within the layer for stable report shape.
    layer_order = {s.scene_id: idx for idx, s in enumerate(layer_specs)}
    outcomes.sort(key=lambda o: layer_order.get(o.scene_id, 0))
    return outcomes, stats


async def _run_one_spec(
    *,
    spec: SceneSpec,
    layer_idx: int,
    ontology: dict | None,
    ontology_path: Path | None,
    provider: LLMProvider,
    ontology_lock_factory: OntologyLockFactory | None,
    progress_print: bool,
    worker_id: int,
) -> SceneOutcome:
    started = time.monotonic()
    if progress_print:
        _LOG.info(
            "[layer %d / worker %d] start scene_id=%s",
            layer_idx,
            worker_id,
            spec.scene_id,
        )
    try:
        prior = load_prior_summaries(spec.prior_summary_paths)
    except Exception as exc:  # noqa: BLE001
        _LOG.exception(
            "failed to load prior_scene_summaries for %s", spec.scene_id
        )
        return SceneOutcome(
            scene_id=spec.scene_id,
            success=False,
            layer_idx=layer_idx,
            elapsed_seconds=time.monotonic() - started,
            cost_usd=0.0,
            scene_path=spec.scene_path,
            failure_reason="prior_summary_load_failed",
            failure_metadata={"exception_class": type(exc).__name__, "message": str(exc)},
        )

    if ontology is None:
        return SceneOutcome(
            scene_id=spec.scene_id,
            success=False,
            layer_idx=layer_idx,
            elapsed_seconds=time.monotonic() - started,
            cost_usd=0.0,
            scene_path=spec.scene_path,
            failure_reason="ontology_missing",
            failure_metadata={
                "exception_class": "ValueError",
                "message": "scheduler ran without an ontology dict",
            },
        )

    # generate_scene is sync (the strategy's per-call retry is
    # blocking); shoulder it onto a worker thread so the asyncio loop
    # stays responsive for the layer's other workers.
    try:
        result: SceneResult = await asyncio.to_thread(
            generate_scene,
            scene_setting=spec.scene_setting,
            target_beats=spec.target_beats,
            participating_npcs=spec.participating_npcs,
            ontology=ontology,
            provider=provider,
            prior_scene_summaries=prior,
            scene_path=spec.scene_path,
            ontology_path=ontology_path,
            chapter_id=spec.chapter_id,
            act_id=spec.act_id,
            generation_method="batch_scheduler",
            ontology_lock_factory=ontology_lock_factory,
        )
    except Exception as exc:  # noqa: BLE001 — generate_scene contract is "never raise"
        _LOG.exception("generate_scene raised for %s", spec.scene_id)
        return SceneOutcome(
            scene_id=spec.scene_id,
            success=False,
            layer_idx=layer_idx,
            elapsed_seconds=time.monotonic() - started,
            cost_usd=0.0,
            scene_path=spec.scene_path,
            failure_reason="provider_error",
            failure_metadata={
                "exception_class": type(exc).__name__,
                "message": str(exc),
            },
        )

    elapsed = time.monotonic() - started
    if progress_print:
        _LOG.info(
            "[layer %d / worker %d] %s scene_id=%s cost=$%.4f elapsed=%.1fs",
            layer_idx,
            worker_id,
            "ok" if result.success else f"fail({result.failure_reason})",
            spec.scene_id,
            result.total_cost_usd,
            elapsed,
        )
    return SceneOutcome(
        scene_id=spec.scene_id,
        success=result.success,
        layer_idx=layer_idx,
        elapsed_seconds=elapsed,
        cost_usd=result.total_cost_usd,
        scene_path=spec.scene_path,
        failure_reason=result.failure_reason,
        failure_metadata=result.failure_metadata,
        chapter_assignment=result.chapter_assignment,
        dep_index_path=result.dep_index_path,
        version_sidecar_path=result.version_sidecar_path,
    )


# ---------------------------------------------------------------------------
# Public entry: run_batch (BS-2)
# ---------------------------------------------------------------------------


async def run_batch(
    scenes: list[SceneSpec],
    *,
    provider: LLMProvider,
    ontology: dict,
    ontology_path: Path | None,
    out_root: Path,
    concurrent_n: int = DEFAULT_CONCURRENT_N,
    rpm: int = DEFAULT_RPM,
    batch_name: str = "batch",
    timestamp: str | None = None,
    rate_limit: bool = True,
    ontology_lock_factory: OntologyLockFactory | None = None,
    progress_print: bool = True,
) -> BatchResult:
    """Run `scenes` through the topology-aware worker pool.

    `provider` is wrapped with `RateLimitedProvider(rpm)` unless
    `rate_limit=False` (test injection knob — pass an already-wrapped
    or fake provider). The scheduler honours the wrapper transparently
    via `getattr(provider, "model_id", "unknown")` lookups inside
    `generate_scene` / inner strategy.

    `ontology_lock_factory` defaults to `make_shared_ontology_lock_factory()`
    so all workers serialise their `chapter_assembler` writes against
    the same mutex; tests can pass a no-op factory.
    """
    plan = plan_layers(scenes)
    if plan.cycle_remaining:
        _LOG.warning(
            "scenes_spec has %d unscheduled scenes (cycle): %s",
            len(plan.cycle_remaining),
            plan.cycle_remaining,
        )

    started = time.monotonic()
    started_iso = datetime.now(timezone.utc).isoformat()
    ts = timestamp or datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch_dir = out_root / f"{ts}_{batch_name}"
    batch_dir.mkdir(parents=True, exist_ok=True)

    if rate_limit:
        wrapped_provider: LLMProvider = RateLimitedProvider(provider, rpm=rpm)
    else:
        wrapped_provider = provider

    if ontology_lock_factory is None:
        ontology_lock_factory = make_shared_ontology_lock_factory()

    outcomes: list[SceneOutcome] = []
    layer_stats: list[LayerStats] = []
    for layer_idx, layer_specs in enumerate(plan.layers):
        layer_outcomes, stats = await _run_layer(
            layer_idx=layer_idx,
            layer_specs=layer_specs,
            concurrent_n=concurrent_n,
            ontology=ontology,
            ontology_path=ontology_path,
            provider=wrapped_provider,
            ontology_lock_factory=ontology_lock_factory,
            progress_print=progress_print,
        )
        outcomes.extend(layer_outcomes)
        layer_stats.append(stats)

    finished = time.monotonic()
    finished_iso = datetime.now(timezone.utc).isoformat()
    total_cost = sum(o.cost_usd for o in outcomes)
    result = BatchResult(
        batch_dir=batch_dir,
        outcomes=outcomes,
        layer_stats=layer_stats,
        plan=plan,
        total_cost_usd=total_cost,
        started_at=started_iso,
        finished_at=finished_iso,
    )
    _write_batch_artifacts(result)
    if progress_print:
        _LOG.info(
            "batch finished: %d/%d succeeded, total_cost=$%.4f, "
            "elapsed=%.1fs",
            sum(1 for o in outcomes if o.success),
            len(outcomes),
            total_cost,
            finished - started,
        )
    return result


# ---------------------------------------------------------------------------
# Batch summary writer (BS-8)
# ---------------------------------------------------------------------------


def _write_batch_artifacts(result: BatchResult) -> None:
    batch_dir = result.batch_dir
    batch_dir.mkdir(parents=True, exist_ok=True)

    # results.jsonl — one row per spec, in declaration / topological order.
    results_path = batch_dir / "scene_results.jsonl"
    with results_path.open("w", encoding="utf-8") as fh:
        for o in result.outcomes:
            payload = {
                "scene_id": o.scene_id,
                "success": o.success,
                "layer_idx": o.layer_idx,
                "elapsed_seconds": o.elapsed_seconds,
                "cost_usd": o.cost_usd,
                "scene_path": str(o.scene_path),
                "failure_reason": o.failure_reason,
                "failure_metadata": o.failure_metadata,
                "chapter_assignment": o.chapter_assignment,
                "dep_index_path": str(o.dep_index_path) if o.dep_index_path else None,
                "version_sidecar_path": (
                    str(o.version_sidecar_path) if o.version_sidecar_path else None
                ),
            }
            fh.write(json.dumps(payload, ensure_ascii=False) + "\n")

    summary_path = batch_dir / "batch_summary.md"
    summary_path.write_text(_render_batch_summary(result), encoding="utf-8")


def _render_batch_summary(result: BatchResult) -> str:
    success_count = sum(1 for o in result.outcomes if o.success)
    total = len(result.outcomes)
    success_rate = (success_count / total) if total else 0.0
    elapsed = (
        sum(o.elapsed_seconds for o in result.outcomes) / total
        if total
        else 0.0
    )
    failure_dist = Counter(
        o.failure_reason for o in result.outcomes if not o.success
    )
    lines: list[str] = [
        "# batch summary",
        "",
        f"- batch_dir: `{result.batch_dir}`",
        f"- started_at: `{result.started_at}`",
        f"- finished_at: `{result.finished_at}`",
        f"- scenes: {total}",
        f"- success_rate: {success_rate:.1%}  ({success_count}/{total})",
        f"- total_cost_usd: ${result.total_cost_usd:.4f}",
        f"- mean_elapsed_seconds_per_scene: {elapsed:.1f}",
        "",
        "## failure distribution",
        "",
    ]
    if failure_dist:
        for reason, count in failure_dist.most_common():
            lines.append(f"- `{reason}`: {count}")
    else:
        lines.append("- (none)")

    lines += ["", "## layer-wise stats", ""]
    if result.layer_stats:
        for stats in result.layer_stats:
            lines.append(
                f"- layer {stats.layer_idx}: {stats.scene_count} scenes, "
                f"{stats.success_count} ok / {stats.failure_count} fail, "
                f"elapsed={stats.elapsed_seconds:.1f}s "
                f"(start={stats.started_at}, end={stats.finished_at})"
            )
    else:
        lines.append("- (no layers)")

    if result.plan.unknown_dependencies:
        lines += ["", "## unknown dependency edges", ""]
        for sid, missing in sorted(result.plan.unknown_dependencies.items()):
            lines.append(f"- `{sid}` -> {missing}")
    if result.plan.cycle_remaining:
        lines += ["", "## scenes skipped due to cycles", ""]
        for sid in result.plan.cycle_remaining:
            lines.append(f"- `{sid}`")

    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# Dry-run + cost preview (BS-9)
# ---------------------------------------------------------------------------


def render_dry_run_plan(
    specs: list[SceneSpec],
    plan: LayerPlan,
    estimated_cost_per_scene: dict[str, float] | None = None,
) -> str:
    """Format the layer plan + optional per-scene cost estimate.

    Caller hands in `estimated_cost_per_scene` as a `scene_id -> usd`
    dict; we sum it for the totals row. When the estimate map is
    omitted, the dry-run skips cost mention entirely (a real provider
    isn't required for plan-only output).
    """
    lines: list[str] = ["# dry-run plan", ""]
    lines.append(f"- scenes: {len(specs)}")
    lines.append(f"- layers: {len(plan.layers)}")
    if plan.unknown_dependencies:
        lines.append("- unknown_dependencies:")
        for sid, missing in sorted(plan.unknown_dependencies.items()):
            lines.append(f"  - `{sid}` -> {missing}")
    if plan.cycle_remaining:
        lines.append(
            f"- cycle_remaining: {plan.cycle_remaining} (NOT scheduled)"
        )
    lines.append("")
    if estimated_cost_per_scene is not None:
        total = sum(estimated_cost_per_scene.values())
        lines.append(f"- estimated_total_cost_usd: ${total:.4f}")
        lines.append("")
    lines.append("## layers")
    lines.append("")
    for idx, layer in enumerate(plan.layers):
        lines.append(f"### layer {idx} ({len(layer)} scenes)")
        for spec in layer:
            cost_note = ""
            if estimated_cost_per_scene is not None:
                cost_note = (
                    f"  est_cost=${estimated_cost_per_scene.get(spec.scene_id, 0.0):.4f}"
                )
            group_note = (
                f"  group={spec.sequence_group}" if spec.sequence_group else ""
            )
            deps_note = (
                f"  deps={spec.depends_on_scene_ids}"
                if spec.depends_on_scene_ids
                else ""
            )
            lines.append(
                f"- `{spec.scene_id}` -> {spec.scene_path}"
                f"{group_note}{deps_note}{cost_note}"
            )
        lines.append("")
    return "\n".join(lines)


def estimate_specs_cost(
    specs: list[SceneSpec], provider: LLMProvider
) -> dict[str, float]:
    """Per-spec scene cost estimate via `estimate_scene_cost`.

    Sums skeleton + (expected node count × per-fill) cost using the
    provider's pricing. Used by the dry-run path to give the operator
    a rough total before the batch fires.
    """
    out: dict[str, float] = {}
    for spec in specs:
        expected_node_count = (
            spec.scene_setting.expected_node_count_min
            + spec.scene_setting.expected_node_count_max
        ) // 2
        out[spec.scene_id] = estimate_scene_cost(
            npc_count=len(spec.participating_npcs),
            beat_count=len(spec.target_beats),
            expected_node_count=expected_node_count,
            provider=provider,
        )
    return out


# ---------------------------------------------------------------------------
# CLI (BS-9)
# ---------------------------------------------------------------------------


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m generator.batch_scheduler",
        description=(
            "Run a batch of scene generations against the SceneSpec DAG "
            "scheduler (T-3.5; ADR-026). Use --dry-run to preview the "
            "topological layer plan + cost estimate without firing the "
            "provider."
        ),
    )
    parser.add_argument(
        "scenes_spec",
        type=Path,
        help="Path to a JSON document containing `scenes` + optional "
        "`out_root` / `ontology_path`.",
    )
    parser.add_argument(
        "--concurrent-n",
        type=int,
        default=None,
        help=(
            "Concurrent worker count. Defaults to env "
            "FORGEWRIGHT_BATCH_CONCURRENT_N or 3."
        ),
    )
    parser.add_argument(
        "--rpm",
        type=int,
        default=None,
        help=(
            "RateLimitedProvider RPM ceiling. Defaults to env "
            "FORGEWRIGHT_PROVIDER_RPM or 60."
        ),
    )
    parser.add_argument(
        "--out-root",
        type=Path,
        default=None,
        help=(
            "Override the spec's `out_root`. Default: spec value or "
            "`generator/experiments`."
        ),
    )
    parser.add_argument(
        "--batch-name",
        default="t35_batch",
        help="Label appended to the timestamped batch directory.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Print the resolved layer plan + cost estimate and exit "
            "without touching the LLM."
        ),
    )
    return parser


def resolve_concurrent_n(*, cli_override: int | None = None) -> int:
    """Resolve worker count. Precedence: CLI > env > default."""
    if cli_override is not None:
        return int(cli_override)
    raw = os.environ.get("FORGEWRIGHT_BATCH_CONCURRENT_N")
    if raw is None or raw == "":
        return DEFAULT_CONCURRENT_N
    return int(raw)


def main(argv: list[str] | None = None) -> int:
    logging.basicConfig(
        level=logging.INFO, format="%(levelname)s %(name)s: %(message)s"
    )
    args = _build_arg_parser().parse_args(argv)

    spec_doc = json.loads(args.scenes_spec.read_text(encoding="utf-8"))
    specs, ontology_path, default_out_root = load_scene_specs(spec_doc)
    out_root = args.out_root or default_out_root

    concurrent_n = resolve_concurrent_n(cli_override=args.concurrent_n)
    rpm = resolve_rpm(cli_override=args.rpm)

    plan = plan_layers(specs)

    if args.dry_run:
        # Build provider only when we *can* — operator may not have an
        # API key and still wants to see the plan. We try to import a
        # provider; fall back to a "no provider" plan that omits the
        # cost estimate.
        estimated = None
        try:
            from generator.providers import get_default_provider  # type: ignore

            provider = get_default_provider()
            estimated = estimate_specs_cost(specs, provider)
        except Exception as exc:  # noqa: BLE001
            _LOG.info(
                "dry-run skipping cost estimate (provider unavailable): %s",
                exc,
            )
        print(render_dry_run_plan(specs, plan, estimated_cost_per_scene=estimated))
        return 0

    # Real run — load ontology + instantiate provider lazily.
    if ontology_path is None:
        print(
            "error: scenes_spec must include `ontology_path` for a real "
            "run (dry-run is OK without it).",
            file=sys.stderr,
        )
        return 2
    if not ontology_path.exists():
        print(
            f"error: ontology_path does not exist: {ontology_path}",
            file=sys.stderr,
        )
        return 2
    ontology = json.loads(ontology_path.read_text(encoding="utf-8"))

    from dotenv import load_dotenv

    load_dotenv()
    from generator.providers import get_default_provider  # type: ignore

    provider = get_default_provider()

    daily = budget.daily_budget_usd()
    used = budget.today_total_usd()
    print(
        f"[budget] daily=${daily:.2f} used_today=${used:.4f} "
        f"remaining=${max(0.0, daily - used):.4f}"
    )

    result = asyncio.run(
        run_batch(
            specs,
            provider=provider,
            ontology=ontology,
            ontology_path=ontology_path,
            out_root=out_root,
            concurrent_n=concurrent_n,
            rpm=rpm,
            batch_name=args.batch_name,
        )
    )
    print(f"\nbatch dir: {result.batch_dir}")
    return 0 if result.success_rate > 0 else 1


__all__ = [
    "BatchResult",
    "DEFAULT_CONCURRENT_N",
    "LayerPlan",
    "LayerStats",
    "OntologyLockFactory",
    "SceneOutcome",
    "SceneSpec",
    "estimate_specs_cost",
    "load_prior_summaries",
    "load_scene_specs",
    "main",
    "make_shared_ontology_lock_factory",
    "plan_layers",
    "render_dry_run_plan",
    "resolve_concurrent_n",
    "run_batch",
]


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
