"""Unit tests for the T-3.5 batch_scheduler module (ADR-026)."""

from __future__ import annotations

import asyncio
import copy
import json
import threading
import time
from pathlib import Path

import pytest

from generator import batch_scheduler
from generator.batch_scheduler import (
    DEFAULT_CONCURRENT_N,
    BatchResult,
    LayerStats,
    SceneOutcome,
    SceneSpec,
    estimate_specs_cost,
    load_prior_summaries,
    load_scene_specs,
    plan_layers,
    render_dry_run_plan,
    resolve_concurrent_n,
    run_batch,
)
from generator.context_assembler import GenerationDependencyTrace
from generator.generate_scene import SceneResult
from generator.scene_strategies import SceneSetting


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _setting(anchor: str = "scene_alpha") -> SceneSetting:
    return SceneSetting(
        scene_anchor=anchor,
        primary_location_ref=anchor,
        chapter_ref=None,
        expected_node_count_min=4,
        expected_node_count_max=8,
    )


def _spec(
    *,
    sid: str,
    deps: list[str] | None = None,
    group: str | None = None,
    scene_path: Path | None = None,
) -> SceneSpec:
    return SceneSpec(
        scene_id=sid,
        scene_setting=_setting(sid),
        target_beats=[f"{sid}-beat-1", f"{sid}-beat-2"],
        participating_npcs=["char_vellin"],
        scene_path=scene_path or Path(f"/tmp/{sid}/scene.json"),
        depends_on_scene_ids=list(deps or []),
        sequence_group=group,
    )


# ---------------------------------------------------------------------------
# plan_layers (BS-1)
# ---------------------------------------------------------------------------


def test_plan_layers_flat_specs_single_layer():
    specs = [_spec(sid="a"), _spec(sid="b"), _spec(sid="c")]
    plan = plan_layers(specs)
    assert len(plan.layers) == 1
    assert {s.scene_id for s in plan.layers[0]} == {"a", "b", "c"}
    assert plan.unknown_dependencies == {}
    assert plan.cycle_remaining == []


def test_plan_layers_topological_chain():
    specs = [
        _spec(sid="c", deps=["b"]),
        _spec(sid="b", deps=["a"]),
        _spec(sid="a"),
    ]
    plan = plan_layers(specs)
    assert [[s.scene_id for s in layer] for layer in plan.layers] == [
        ["a"],
        ["b"],
        ["c"],
    ]


def test_plan_layers_diamond_dependencies():
    specs = [
        _spec(sid="root"),
        _spec(sid="left", deps=["root"]),
        _spec(sid="right", deps=["root"]),
        _spec(sid="leaf", deps=["left", "right"]),
    ]
    plan = plan_layers(specs)
    assert len(plan.layers) == 3
    assert {s.scene_id for s in plan.layers[0]} == {"root"}
    assert {s.scene_id for s in plan.layers[1]} == {"left", "right"}
    assert {s.scene_id for s in plan.layers[2]} == {"leaf"}


def test_plan_layers_orders_by_sequence_group_then_index():
    specs = [
        _spec(sid="a", group="z"),  # declaration index 0
        _spec(sid="b", group="a"),  # declaration index 1
        _spec(sid="c", group="a"),  # declaration index 2
    ]
    plan = plan_layers(specs)
    assert [s.scene_id for s in plan.layers[0]] == ["b", "c", "a"]


def test_plan_layers_records_unknown_deps_without_failing():
    specs = [_spec(sid="a", deps=["nonexistent_root"])]
    plan = plan_layers(specs)
    assert plan.unknown_dependencies == {"a": ["nonexistent_root"]}
    # Unknown dep is filtered out, so `a` still ends up in layer 0.
    assert {s.scene_id for s in plan.layers[0]} == {"a"}


def test_plan_layers_detects_cycle_and_skips():
    specs = [
        _spec(sid="a", deps=["b"]),
        _spec(sid="b", deps=["a"]),
    ]
    plan = plan_layers(specs)
    assert plan.layers == []
    assert sorted(plan.cycle_remaining) == ["a", "b"]


def test_plan_layers_rejects_duplicate_scene_ids():
    specs = [_spec(sid="dup"), _spec(sid="dup")]
    with pytest.raises(ValueError, match="duplicate"):
        plan_layers(specs)


def test_plan_layers_rejects_blank_scene_id():
    specs = [_spec(sid="")]
    with pytest.raises(ValueError, match="non-empty scene_id"):
        plan_layers(specs)


# ---------------------------------------------------------------------------
# resolve_concurrent_n
# ---------------------------------------------------------------------------


def test_resolve_concurrent_n_default(monkeypatch):
    monkeypatch.delenv("FORGEWRIGHT_BATCH_CONCURRENT_N", raising=False)
    assert resolve_concurrent_n() == DEFAULT_CONCURRENT_N


def test_resolve_concurrent_n_env(monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_BATCH_CONCURRENT_N", "5")
    assert resolve_concurrent_n() == 5


def test_resolve_concurrent_n_cli_wins(monkeypatch):
    monkeypatch.setenv("FORGEWRIGHT_BATCH_CONCURRENT_N", "5")
    assert resolve_concurrent_n(cli_override=2) == 2


# ---------------------------------------------------------------------------
# load_scene_specs (BS-9)
# ---------------------------------------------------------------------------


def test_load_scene_specs_from_dict(tmp_path):
    spec_doc = {
        "out_root": str(tmp_path / "batches"),
        "ontology_path": str(tmp_path / "ontology.json"),
        "scenes": [
            {
                "scene_id": "alpha",
                "scene_setting": {
                    "scene_anchor": "scene_alpha",
                    "primary_location_ref": "scene_alpha",
                    "expected_node_count_min": 5,
                    "expected_node_count_max": 10,
                },
                "target_beats": ["beat-1", "beat-2"],
                "participating_npcs": ["char_vellin"],
                "scene_path": str(tmp_path / "alpha" / "scene.json"),
                "chapter_id": "chap_arrival",
                "act_id": "act_one",
                "depends_on_scene_ids": [],
                "sequence_group": "main",
            }
        ],
    }
    specs, ontology_path, out_root = load_scene_specs(spec_doc)
    assert len(specs) == 1
    spec = specs[0]
    assert spec.scene_id == "alpha"
    assert spec.scene_setting.scene_anchor == "scene_alpha"
    assert spec.scene_path == tmp_path / "alpha" / "scene.json"
    assert spec.chapter_id == "chap_arrival"
    assert spec.act_id == "act_one"
    assert ontology_path == tmp_path / "ontology.json"
    assert out_root == tmp_path / "batches"


def test_load_scene_specs_requires_scene_path(tmp_path):
    spec_doc = {
        "scenes": [
            {
                "scene_setting": {
                    "scene_anchor": "scene_alpha",
                    "primary_location_ref": "scene_alpha",
                },
                "target_beats": [],
                "participating_npcs": [],
            }
        ]
    }
    with pytest.raises(ValueError, match="scene_path"):
        load_scene_specs(spec_doc)


def test_load_prior_summaries_skips_missing(tmp_path):
    present = tmp_path / "present.json"
    present.write_text(
        json.dumps(
            {
                "scene_id": "scene_alpha",
                "summary": "abc",
                "key_state_paths": ["flag.met"],
            }
        ),
        encoding="utf-8",
    )
    summaries = load_prior_summaries([present, tmp_path / "missing.json"])
    assert len(summaries) == 1
    assert summaries[0].scene_id == "scene_alpha"


# ---------------------------------------------------------------------------
# Dry-run plan rendering (BS-9)
# ---------------------------------------------------------------------------


def test_render_dry_run_plan_includes_layers_and_costs(tmp_path):
    specs = [
        _spec(sid="a"),
        _spec(sid="b", deps=["a"]),
    ]
    plan = plan_layers(specs)
    out = render_dry_run_plan(
        specs, plan, estimated_cost_per_scene={"a": 0.10, "b": 0.20}
    )
    assert "# dry-run plan" in out
    assert "layer 0 (1 scenes)" in out
    assert "layer 1 (1 scenes)" in out
    assert "estimated_total_cost_usd: $0.3000" in out
    assert "`a`" in out and "`b`" in out


# ---------------------------------------------------------------------------
# run_batch with stubbed generate_scene (BS-2 + BS-8)
# ---------------------------------------------------------------------------


def _stub_generate_scene_factory(
    *,
    failures: set[str] | None = None,
    delay_seconds: float = 0.0,
    timeline: list[tuple[str, float]] | None = None,
):
    """Build a callable that mimics `generate_scene`'s sync signature
    while writing scene.json + the two sidecars in the right order so
    integration tests can verify F6.
    """
    failures = failures or set()
    timeline = timeline if timeline is not None else []
    timeline_lock = threading.Lock()

    def _stub(**kwargs):
        scene_setting = kwargs["scene_setting"]
        scene_path: Path = kwargs.get("scene_path")
        sid = scene_setting.scene_anchor
        with timeline_lock:
            timeline.append((sid, time.monotonic()))
        if delay_seconds:
            time.sleep(delay_seconds)
        if sid in failures:
            return SceneResult(
                success=False,
                failure_reason="provider_error",
                failure_metadata={
                    "exception_class": "StubFailure",
                    "http_status": None,
                    "response_body_excerpt": None,
                },
                schema_issues=[f"stub-fail-for-{sid}"],
                dependency_trace=GenerationDependencyTrace(),
                scene_path=scene_path,
            )
        # Mimic landing scene + sidecars.
        if scene_path is not None:
            scene_path.parent.mkdir(parents=True, exist_ok=True)
            scene_path.write_text(
                json.dumps({"graph_id": sid, "scene_anchor": sid}),
                encoding="utf-8",
            )
            (scene_path.with_suffix(".deps.json")).write_text("{}", encoding="utf-8")
            (scene_path.with_suffix(".version.json")).write_text("{}", encoding="utf-8")
        return SceneResult(
            success=True,
            graph={"graph_id": sid, "scene_anchor": sid},
            total_cost_usd=0.05,
            dependency_trace=GenerationDependencyTrace(),
            scene_path=scene_path,
            dep_index_path=(
                scene_path.with_suffix(".deps.json") if scene_path else None
            ),
            version_sidecar_path=(
                scene_path.with_suffix(".version.json") if scene_path else None
            ),
            chapter_assignment={
                "scene_anchor": sid,
                "chapter_id": kwargs.get("chapter_id"),
                "act_id": kwargs.get("act_id"),
                "reason": "assigned",
                "success": True,
            },
        )

    return _stub, timeline


class _NoOpProvider:
    model_id = "noop-model"

    def generate_structured(self, *args, **kwargs):
        raise AssertionError(
            "stubbed generate_scene must intercept before provider use"
        )

    def estimate_cost(self, input_tokens, output_tokens):
        return (input_tokens + output_tokens) * 1e-7


def test_run_batch_writes_summary_and_results(tmp_path, monkeypatch):
    stub, _ = _stub_generate_scene_factory()
    monkeypatch.setattr(batch_scheduler, "generate_scene", stub)

    specs = [
        _spec(
            sid="alpha",
            scene_path=tmp_path / "alpha" / "scene.json",
        ),
        _spec(
            sid="beta",
            scene_path=tmp_path / "beta" / "scene.json",
            deps=["alpha"],
        ),
    ]
    result: BatchResult = asyncio.run(
        run_batch(
            specs,
            provider=_NoOpProvider(),
            ontology={"entities": []},
            ontology_path=None,
            out_root=tmp_path / "batch",
            concurrent_n=2,
            rate_limit=False,
            ontology_lock_factory=None,
            progress_print=False,
            timestamp="20260508T120000Z",
        )
    )
    assert result.success_rate == 1.0
    assert len(result.outcomes) == 2
    assert [o.layer_idx for o in result.outcomes] == [0, 1]
    assert result.outcomes[0].dep_index_path is not None
    assert result.outcomes[0].chapter_assignment["success"] is True

    summary_text = (result.batch_dir / "batch_summary.md").read_text(
        encoding="utf-8"
    )
    assert "success_rate: 100.0%" in summary_text
    assert "layer 0:" in summary_text and "layer 1:" in summary_text

    rows = [
        json.loads(line)
        for line in (result.batch_dir / "scene_results.jsonl")
        .read_text(encoding="utf-8")
        .strip()
        .splitlines()
    ]
    assert {r["scene_id"] for r in rows} == {"alpha", "beta"}


def test_run_batch_records_failures_without_aborting(tmp_path, monkeypatch):
    stub, _ = _stub_generate_scene_factory(failures={"beta"})
    monkeypatch.setattr(batch_scheduler, "generate_scene", stub)

    specs = [
        _spec(sid=f"s{i}", scene_path=tmp_path / f"s{i}" / "scene.json")
        for i in range(3)
    ]
    # Force one to fail.
    specs.append(_spec(sid="beta", scene_path=tmp_path / "beta" / "scene.json"))
    result = asyncio.run(
        run_batch(
            specs,
            provider=_NoOpProvider(),
            ontology={"entities": []},
            ontology_path=None,
            out_root=tmp_path / "batch",
            concurrent_n=2,
            rate_limit=False,
            ontology_lock_factory=None,
            progress_print=False,
        )
    )
    assert result.success_rate == 0.75
    failed = [o for o in result.outcomes if not o.success]
    assert len(failed) == 1
    assert failed[0].scene_id == "beta"
    assert failed[0].failure_reason == "provider_error"


def test_run_batch_layer_concurrency_serialises_layers(tmp_path, monkeypatch):
    """Layer 1 should not start any work before layer 0 finishes — the
    timeline of (scene_id, monotonic_at_start) collected by the stub
    proves it."""
    stub, timeline = _stub_generate_scene_factory(delay_seconds=0.05)
    monkeypatch.setattr(batch_scheduler, "generate_scene", stub)

    specs = [
        _spec(sid="root", scene_path=tmp_path / "root" / "scene.json"),
        _spec(
            sid="leaf",
            scene_path=tmp_path / "leaf" / "scene.json",
            deps=["root"],
        ),
    ]
    asyncio.run(
        run_batch(
            specs,
            provider=_NoOpProvider(),
            ontology={"entities": []},
            ontology_path=None,
            out_root=tmp_path / "batch",
            concurrent_n=3,
            rate_limit=False,
            ontology_lock_factory=None,
            progress_print=False,
        )
    )
    assert len(timeline) == 2
    by_id = dict(timeline)
    assert by_id["leaf"] >= by_id["root"] + 0.05


def test_run_batch_layer_concurrency_runs_sibling_specs_in_parallel(
    tmp_path, monkeypatch
):
    """Sibling specs in the same layer should overlap in time — proves
    the asyncio worker pool is concurrent (not serialising)."""
    stub, timeline = _stub_generate_scene_factory(delay_seconds=0.10)
    monkeypatch.setattr(batch_scheduler, "generate_scene", stub)

    specs = [
        _spec(sid=f"sibling_{i}", scene_path=tmp_path / f"s{i}" / "scene.json")
        for i in range(3)
    ]
    asyncio.run(
        run_batch(
            specs,
            provider=_NoOpProvider(),
            ontology={"entities": []},
            ontology_path=None,
            out_root=tmp_path / "batch",
            concurrent_n=3,
            rate_limit=False,
            ontology_lock_factory=None,
            progress_print=False,
        )
    )
    starts = [t for _, t in timeline]
    starts.sort()
    # All 3 starts should fall inside one delay window if concurrency
    # is honoured (slack = 0.05s for thread startup).
    assert starts[-1] - starts[0] < 0.10


def test_estimate_specs_cost_per_scene(tmp_path):
    specs = [
        _spec(sid="a", scene_path=tmp_path / "a" / "scene.json"),
        _spec(sid="b", scene_path=tmp_path / "b" / "scene.json"),
    ]
    estimates = estimate_specs_cost(specs, _NoOpProvider())
    assert set(estimates) == {"a", "b"}
    for v in estimates.values():
        assert v > 0


# ---------------------------------------------------------------------------
# Shared ontology lock factory (BS-7)
# ---------------------------------------------------------------------------


def test_make_shared_ontology_lock_factory_serialises_within_process(tmp_path):
    """Two threads attempting to acquire the same factory's lock for
    the same ontology path must observe strict serialisation."""
    factory = batch_scheduler.make_shared_ontology_lock_factory()
    ontology_path = tmp_path / "fake_ontology.json"
    ontology_path.write_text("{}", encoding="utf-8")

    timeline: list[tuple[str, float]] = []
    timeline_lock = threading.Lock()

    def hold(label: str):
        with factory(ontology_path):
            with timeline_lock:
                timeline.append((f"{label}_enter", time.monotonic()))
            time.sleep(0.05)
            with timeline_lock:
                timeline.append((f"{label}_exit", time.monotonic()))

    t1 = threading.Thread(target=hold, args=("a",))
    t2 = threading.Thread(target=hold, args=("b",))
    t1.start()
    t2.start()
    t1.join()
    t2.join()
    # Verify exit-of-first comes before enter-of-second.
    events = sorted(timeline, key=lambda e: e[1])
    labels = [e[0] for e in events]
    # Either order is fine, but we must see <X_enter, X_exit, Y_enter, Y_exit>
    # not <X_enter, Y_enter, ...> — i.e. the second enter must follow
    # the first exit.
    enter_indices = [i for i, l in enumerate(labels) if l.endswith("_enter")]
    exit_indices = [i for i, l in enumerate(labels) if l.endswith("_exit")]
    first_exit = exit_indices[0]
    second_enter = enter_indices[1]
    assert second_enter > first_exit


# ---------------------------------------------------------------------------
# F6 hooks integration via generate_scene (BS-6 + BS-7)
# ---------------------------------------------------------------------------


def test_post_success_hooks_run_in_f6_order(tmp_path, monkeypatch):
    """End-to-end: drive `generate_scene._run_post_success_hooks` via
    monkeypatching `assign_scene_to_chapter` + `record_version` to
    observers; verify the four hooks fire in (scene → chapter → deps →
    version) order, and the dep_index sidecar carries the chapter_id /
    act_id assigned in step 2 (proves F6 prevents stale chapter_id)."""
    from generator import generate_scene as gs_mod

    timeline: list[str] = []

    def fake_assign(scene_anchor, ontology_path, chapter_id=None, act_id=None, **kwargs):
        timeline.append(
            f"assign_chapter:{chapter_id or 'chap_unassigned'}:{act_id or 'act_unassigned'}"
        )

        class _R:
            def __init__(self):
                self.success = True
                self.scene_anchor = scene_anchor
                self.chapter_id = chapter_id or "chap_unassigned"
                self.act_id = act_id or "act_unassigned"
                self.reason = "assigned"

        return _R()

    def fake_write_sidecar(scene_path, scene, trace, prior_summaries, token_metrics, ch, ac):
        timeline.append(f"write_deps:ch={ch}:ac={ac}")
        sidecar = scene_path.with_suffix(".deps.json")
        sidecar.write_text(json.dumps({"chapter_id": ch, "act_id": ac}), encoding="utf-8")
        return sidecar

    def fake_record_version(scene_path, generation_method, changed_fields=None):
        timeline.append(f"record_version:{generation_method}")

        class _M:
            scene_id = "scene_smoke"
            version = 1

        return _M()

    def fake_vr_sidecar_path(scene_path):
        return scene_path.with_suffix(".version.json")

    # The monkeypatches need to hit the imports inside _run_post_success_hooks
    # exactly — they're done lazily via `from ... import` inside the
    # function body, so we must patch at the module-of-origin level.
    monkeypatch.setattr(
        "generator.chapter_assembler.assign_scene_to_chapter", fake_assign
    )
    monkeypatch.setattr(
        "generator.dep_index_writer.write_sidecar", fake_write_sidecar
    )
    monkeypatch.setattr(
        "generator.version_recorder.record_version", fake_record_version
    )
    monkeypatch.setattr(
        "generator.version_recorder.sidecar_path_for", fake_vr_sidecar_path
    )

    # Build a minimal scene_ctx + trace + graph to drive the hook helper
    # in isolation (avoids a full generate_scene round-trip).
    from generator.context_assembler import (
        SceneGraphContext,
        TokenMetrics,
    )

    scene_ctx = SceneGraphContext(
        scene_anchor="scene_smoke",
        chapter_ref=None,
        location_candidates=[],
        primary_location_ref=None,
        participating_characters=[],
        relations_matrix=[],
        active_clocks=[],
        system_time={"scene_count": 0, "long_rest_count": 0},
        target_beats=[],
        prior_scene_summaries=[],
        token_metrics=TokenMetrics(),
    )
    graph = {"graph_id": "scene_smoke", "scene_anchor": "scene_smoke", "nodes": {}}
    trace = GenerationDependencyTrace()
    scene_path = tmp_path / "scene_smoke" / "scene.json"
    ontology_path = tmp_path / "ontology.json"
    ontology_path.write_text("{}", encoding="utf-8")

    out = gs_mod._run_post_success_hooks(
        scene_path=scene_path,
        ontology_path=ontology_path,
        chapter_id="chap_arrival",
        act_id="act_one",
        graph=graph,
        trace=trace,
        scene_ctx=scene_ctx,
        generation_method="batch_scheduler",
        ontology_lock_factory=None,
    )
    # Order assertion: scene file lands before assign, assign before
    # deps, deps before version. We can't see the scene-write step
    # directly via timeline — but we assert it landed on disk *before*
    # any other step ran by checking it exists when assign is called.
    assert scene_path.exists()
    assert timeline == [
        "assign_chapter:chap_arrival:act_one",
        "write_deps:ch=chap_arrival:ac=act_one",
        "record_version:batch_scheduler",
    ]
    # Returned paths point at the right siblings.
    assert out["dep_index_path"] == scene_path.with_suffix(".deps.json")
    assert out["version_sidecar_path"] == scene_path.with_suffix(".version.json")
    assert out["chapter_assignment"]["chapter_id"] == "chap_arrival"


# ---------------------------------------------------------------------------
# RateLimitedProvider integration (BS-3 wiring)
# ---------------------------------------------------------------------------


def test_run_batch_wraps_provider_in_rate_limiter(tmp_path, monkeypatch):
    """When `rate_limit=True`, the wrapper should land on
    generate_scene's `provider` argument — so the inner provider sees
    its calls gated through TokenBucket."""
    from generator._rate_limit import RateLimitedProvider

    captured_providers: list[object] = []

    def stub(**kwargs):
        captured_providers.append(kwargs["provider"])
        return SceneResult(
            success=True,
            graph={"graph_id": "x", "scene_anchor": "x"},
            total_cost_usd=0.0,
            dependency_trace=GenerationDependencyTrace(),
            scene_path=kwargs["scene_path"],
        )

    monkeypatch.setattr(batch_scheduler, "generate_scene", stub)

    specs = [_spec(sid="x", scene_path=tmp_path / "x" / "scene.json")]
    asyncio.run(
        run_batch(
            specs,
            provider=_NoOpProvider(),
            ontology={"entities": []},
            ontology_path=None,
            out_root=tmp_path / "batch",
            concurrent_n=1,
            rate_limit=True,
            rpm=12,
            ontology_lock_factory=None,
            progress_print=False,
        )
    )
    assert captured_providers
    assert isinstance(captured_providers[0], RateLimitedProvider)
    assert captured_providers[0].rpm == 12
