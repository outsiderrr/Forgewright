"""Unit tests for `accumulate_scene_context_trace` (T-3.5; ADR-023 §F5).

Covers the C-phase findings on PR #45:
  * 3.1 — `state_paths_read` must record every state path the LLM
    actually sees in the assembled prompt (system_time / clock
    tick_effects / prior-summary key_state_paths).
  * 3.2 — only the *post-truncation* prior summaries reach the prompt,
    so only their `key_state_paths` should land in the trace.
"""

from __future__ import annotations

from generator.context_assembler import (
    GenerationDependencyTrace,
    PriorSceneSummary,
    SceneGraphContext,
    TokenMetrics,
    accumulate_scene_context_trace,
)


def _ctx(**overrides) -> SceneGraphContext:
    base = dict(
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
    base.update(overrides)
    return SceneGraphContext(**base)


def test_trace_records_system_time_paths_unconditionally():
    trace = GenerationDependencyTrace()
    accumulate_scene_context_trace(trace, _ctx())
    assert "world.scene_count" in trace.state_paths_read
    assert "world.long_rest_count" in trace.state_paths_read


def test_trace_records_clock_tick_effect_paths():
    """Active clocks expose their tick_effects' paths to the prompt;
    the read-side trace must over-approx them so dep_propagate flips
    a scene stale when the clock spec mutates."""
    clocks = [
        {
            "id": "clk_pursuit",
            "scope": "faction",
            "tick_effects": [
                {"at_tick": 3, "effect_op": "set", "path": "flag.alarm_raised", "value": True},
                {"at_tick": 6, "effect_op": "inc", "path": "faction.iron_oath.heat", "value": 1},
            ],
        }
    ]
    trace = GenerationDependencyTrace()
    accumulate_scene_context_trace(trace, _ctx(active_clocks=clocks))
    assert "clk_pursuit" in trace.clock_ids_referenced
    assert "flag.alarm_raised" in trace.state_paths_read
    assert "faction.iron_oath.heat" in trace.state_paths_read
    # tick_effects' paths must NOT bleed into the write-side set
    # (this scene didn't write them — the clock will, eventually).
    assert "flag.alarm_raised" not in trace.state_paths_written
    assert "faction.iron_oath.heat" not in trace.state_paths_written


def test_trace_records_only_post_truncation_prior_summary_paths():
    """ADR-024 cap = 5; the trace must reflect only the kept summaries
    so it stays consistent with `summary_source_hashes` /
    `summaries_injected_count`."""
    summaries = [
        PriorSceneSummary(
            scene_id=f"scene_n{i:02d}",
            summary=f"summary {i}",
            key_state_paths=[f"flag.scene_{i}_resolved"],
        )
        for i in range(7)  # 7 entries → 5 kept after truncation
    ]
    trace = GenerationDependencyTrace()
    accumulate_scene_context_trace(
        trace, _ctx(prior_scene_summaries=summaries)
    )
    # 5 of the 7 paths land in the trace — the truncation drops 2.
    matched = [
        p for p in trace.state_paths_read
        if p.startswith("flag.scene_") and p.endswith("_resolved")
    ]
    assert len(matched) == 5


def test_trace_skips_invalid_path_entries_in_summaries():
    """Defensive: a summary with non-string / empty paths shouldn't
    blow up the trace accumulation."""
    summaries = [
        PriorSceneSummary(
            scene_id="scene_alpha",
            summary="x",
            key_state_paths=["flag.real_path", "", None],  # type: ignore[list-item]
        ),
    ]
    trace = GenerationDependencyTrace()
    accumulate_scene_context_trace(
        trace, _ctx(prior_scene_summaries=summaries)
    )
    assert "flag.real_path" in trace.state_paths_read
    assert "" not in trace.state_paths_read


def test_trace_records_visual_assets_and_chapter_ref():
    """Sanity check that the existing entity-side accumulation still
    fires after the C-phase additions (regression guard)."""
    chars = [
        {
            "id": "char_vellin",
            "type": "character",
            "visual_assets": [
                {"asset_id": "asset_vellin_portrait"},
            ],
        }
    ]
    trace = GenerationDependencyTrace()
    accumulate_scene_context_trace(
        trace,
        _ctx(
            chapter_ref="chap_arrival",
            participating_characters=chars,
        ),
    )
    assert "char_vellin" in trace.ontology_ids_read
    assert "chap_arrival" in trace.ontology_ids_read
    assert "asset_vellin_portrait" in trace.visual_asset_ids_referenced
