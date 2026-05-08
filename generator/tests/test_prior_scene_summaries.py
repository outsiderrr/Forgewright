"""T-3.3 (ADR-024) — long-conversation-consistency C-tier helpers.

Coverage:

  * `PriorSceneSummary` dataclass shape (required + optional fields).
  * `truncate_prior_scene_summaries` heuristics — empty / under cap /
    over cap with boundaries / over cap without boundaries / boundary-
    only over-saturation.
  * `_summary_source_hash` stability and field sensitivity.
  * `render_prior_scene_summaries_block` markdown shape.
  * `compute_prior_summary_token_metrics` consistency with the
    truncation heuristic + post-truncation byte counting.
  * `SceneGraphContext` field defaults stay backwards-compatible with
    pre-T-3.3 callers (test_generate_scene scenario 6 still passes).
  * `assemble_scene_context_block` surfaces the new section when the
    field is populated and stays silent when it isn't.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from generator.context_assembler import (
    PRIOR_SCENE_SUMMARY_CAP,
    PriorSceneSummary,
    SceneGraphContext,
    TokenMetrics,
    _summary_source_hash,
    assemble_scene_context_block,
    compute_prior_summary_token_metrics,
    render_prior_scene_summaries_block,
    truncate_prior_scene_summaries,
)
from generator.scene_strategies import SceneSetting


# ---------------------------------------------------------------------------
# Fixture builders
# ---------------------------------------------------------------------------


def _summary(scene_id: str, **kwargs) -> PriorSceneSummary:
    return PriorSceneSummary(
        scene_id=scene_id,
        summary=kwargs.pop("summary", f"summary-of-{scene_id}"),
        key_state_paths=list(kwargs.pop("key_state_paths", [])),
        chapter_id=kwargs.pop("chapter_id", None),
        act_id=kwargs.pop("act_id", None),
    )


def _scene_setting() -> SceneSetting:
    return SceneSetting(
        scene_anchor="scene_test",
        primary_location_ref="loc_test",
        chapter_ref="chap_test",
    )


# ---------------------------------------------------------------------------
# Dataclass shape
# ---------------------------------------------------------------------------


def test_prior_scene_summary_required_fields_only():
    """Three-field constructor (per task spec) must work; chapter/act
    default to None."""
    summary = PriorSceneSummary(
        scene_id="scene_a",
        summary="...",
        key_state_paths=["world.scene_count"],
    )
    assert summary.scene_id == "scene_a"
    assert summary.summary == "..."
    assert summary.key_state_paths == ["world.scene_count"]
    assert summary.chapter_id is None
    assert summary.act_id is None


def test_prior_scene_summary_optional_fields():
    """T-3.3: chapter_id / act_id are accepted on construction so the
    truncation heuristic can detect boundaries."""
    summary = PriorSceneSummary(
        scene_id="scene_a",
        summary="...",
        key_state_paths=[],
        chapter_id="chap_1",
        act_id="act_2",
    )
    assert summary.chapter_id == "chap_1"
    assert summary.act_id == "act_2"


# ---------------------------------------------------------------------------
# Truncation heuristic
# ---------------------------------------------------------------------------


def test_truncate_empty_returns_empty_with_none_reason():
    """PR #44 review §3.1: schema-aligned reason — empty input maps to
    the literal string `"none"`, not Python `None`."""
    kept, reason = truncate_prior_scene_summaries([])
    assert kept == []
    assert reason == "none"


def test_truncate_under_cap_keeps_everything():
    summaries = [_summary(f"s{i}") for i in range(PRIOR_SCENE_SUMMARY_CAP)]
    kept, reason = truncate_prior_scene_summaries(summaries)
    assert len(kept) == PRIOR_SCENE_SUMMARY_CAP
    assert kept == summaries
    assert reason == "none"


def test_truncate_over_cap_no_boundaries_keeps_recent_only():
    """7 summaries with no chapter/act metadata → keep last 5; reason
    collapses to the schema-aligned `summaries_over_5` bucket."""
    summaries = [_summary(f"s{i}") for i in range(7)]
    kept, reason = truncate_prior_scene_summaries(summaries)
    assert len(kept) == PRIOR_SCENE_SUMMARY_CAP
    assert [s.scene_id for s in kept] == ["s2", "s3", "s4", "s5", "s6"]
    assert reason == "summaries_over_5"


def test_truncate_preserves_chapter_boundary_with_recent_4():
    """Boundary at index 0 (first chapter), then 6 more in same chapter
    → boundary pinned; 4 most-recent non-boundary entries fill the
    remaining slots, so total = 5 (s0 + s3..s6)."""
    summaries = [
        _summary("s0", chapter_id="chap_a"),  # boundary
        _summary("s1", chapter_id="chap_a"),
        _summary("s2", chapter_id="chap_a"),
        _summary("s3", chapter_id="chap_a"),
        _summary("s4", chapter_id="chap_a"),
        _summary("s5", chapter_id="chap_a"),
        _summary("s6", chapter_id="chap_a"),
    ]
    kept, reason = truncate_prior_scene_summaries(summaries)
    kept_ids = [s.scene_id for s in kept]
    assert kept_ids == ["s0", "s3", "s4", "s5", "s6"]
    assert reason == "summaries_over_5"


def test_truncate_preserves_act_boundary():
    """Act boundary should trigger preservation independently of chapter.
    Two boundaries (s0 first scene, s4 act transition) get pinned; the
    remaining 3 slots fill with the most-recent non-boundary entries."""
    summaries = [
        _summary("s0", act_id="act_1"),
        _summary("s1", act_id="act_1"),
        _summary("s2", act_id="act_1"),
        _summary("s3", act_id="act_1"),
        _summary("s4", act_id="act_2"),  # act boundary
        _summary("s5", act_id="act_2"),
        _summary("s6", act_id="act_2"),
        _summary("s7", act_id="act_2"),
    ]
    kept, reason = truncate_prior_scene_summaries(summaries)
    kept_ids = [s.scene_id for s in kept]
    assert kept_ids == ["s0", "s4", "s5", "s6", "s7"]
    assert reason == "summaries_over_5"


def test_truncate_boundary_overflow_drops_oldest_boundaries():
    """When boundaries alone overflow the cap, the most-recent boundaries
    win and the oldest boundary entries are dropped (recency tie-break
    inside the boundary set itself, per ADR-024)."""
    summaries = [
        _summary("s0", chapter_id="chap_a"),  # boundary 1
        _summary("s1", chapter_id="chap_b"),  # boundary 2
        _summary("s2", chapter_id="chap_c"),  # boundary 3
        _summary("s3", chapter_id="chap_d"),  # boundary 4
        _summary("s4", chapter_id="chap_e"),  # boundary 5
        _summary("s5", chapter_id="chap_f"),  # boundary 6
        _summary("s6", chapter_id="chap_g"),  # boundary 7
    ]
    kept, reason = truncate_prior_scene_summaries(summaries)
    assert len(kept) == PRIOR_SCENE_SUMMARY_CAP
    kept_ids = [s.scene_id for s in kept]
    # Oldest boundaries (s0, s1) get dropped — five most-recent
    # boundaries kept.
    assert kept_ids == ["s2", "s3", "s4", "s5", "s6"]
    assert reason == "summaries_over_5"


def test_truncate_ignores_none_chapter_act():
    """Summaries with None chapter/act don't register as boundaries."""
    summaries = [
        _summary("s0"),  # no chapter / act
        _summary("s1"),
        _summary("s2"),
        _summary("s3"),
        _summary("s4"),
        _summary("s5"),
        _summary("s6"),
    ]
    kept, reason = truncate_prior_scene_summaries(summaries)
    assert reason == "summaries_over_5"
    assert [s.scene_id for s in kept] == ["s2", "s3", "s4", "s5", "s6"]


# ---------------------------------------------------------------------------
# Hash + render
# ---------------------------------------------------------------------------


def test_summary_source_hash_stable_and_schema_prefixed():
    """PR #44 review §3.1: hash is `sha256:<hex>` per dep_index schema
    pattern (^sha256:[a-f0-9]{64}$). Stable across calls."""
    s = _summary("scene_a", summary="prose", key_state_paths=["world.x"])
    digest = _summary_source_hash(s)
    assert digest == _summary_source_hash(s)
    assert digest.startswith("sha256:")
    assert len(digest) == len("sha256:") + 64
    assert all(c in "0123456789abcdef" for c in digest.removeprefix("sha256:"))


def test_summary_source_hash_field_sensitive():
    """Mutating any prompt-visible field flips the hash."""
    base = _summary("scene_a", summary="prose", key_state_paths=["world.x"])
    diff_id = _summary("scene_b", summary="prose", key_state_paths=["world.x"])
    diff_summary = _summary("scene_a", summary="other", key_state_paths=["world.x"])
    diff_paths = _summary("scene_a", summary="prose", key_state_paths=["world.y"])
    assert _summary_source_hash(base) != _summary_source_hash(diff_id)
    assert _summary_source_hash(base) != _summary_source_hash(diff_summary)
    assert _summary_source_hash(base) != _summary_source_hash(diff_paths)


def test_summary_source_hash_ignores_chapter_act():
    """chapter_id / act_id only feed truncation, not the prompt body —
    they shouldn't change the hash that pins the on-prompt content."""
    bare = _summary("scene_a", summary="prose", key_state_paths=["world.x"])
    decorated = _summary(
        "scene_a", summary="prose", key_state_paths=["world.x"],
        chapter_id="chap_a", act_id="act_b",
    )
    assert _summary_source_hash(bare) == _summary_source_hash(decorated)


def test_render_block_empty_returns_empty_string():
    assert render_prior_scene_summaries_block([]) == ""


def test_render_block_format_matches_spec():
    """Section header + per-summary bullets in caller-supplied order."""
    rendered = render_prior_scene_summaries_block(
        [
            _summary("s0", summary="开场冲突", key_state_paths=["flag.a"]),
            _summary("s1", summary="决策落地", key_state_paths=[]),
        ]
    )
    assert rendered.startswith("## 前置场景概要（按时间顺序）")
    assert "[s0] 开场冲突; 关键状态写入：flag.a" in rendered
    assert "[s1] 决策落地; 关键状态写入：（无）" in rendered


def test_render_block_flattens_newlines_in_summary():
    rendered = render_prior_scene_summaries_block(
        [_summary("s0", summary="line one\nline two")]
    )
    # Body sits on the bullet line — no embedded newline.
    assert "line one line two" in rendered
    assert "line one\nline two; 关键状态写入" not in rendered


# ---------------------------------------------------------------------------
# Token metrics
# ---------------------------------------------------------------------------


def test_compute_token_metrics_empty_input():
    """No summaries → schema-aligned `none` reason and zero estimate."""
    metrics = compute_prior_summary_token_metrics([])
    assert metrics == TokenMetrics(
        prompt_token_estimate=0,
        summaries_injected_count=0,
        summary_source_hashes=[],
        truncation_reason="none",
    )


def test_compute_token_metrics_under_cap_no_truncation():
    summaries = [_summary("s0"), _summary("s1")]
    metrics = compute_prior_summary_token_metrics(summaries)
    assert metrics.summaries_injected_count == 2
    assert len(metrics.summary_source_hashes) == 2
    assert metrics.truncation_reason == "none"
    # token_estimate must be > 0 because there's a non-empty rendered block.
    assert metrics.prompt_token_estimate > 0
    # All hashes carry the sha256: prefix per dep_index schema.
    assert all(h.startswith("sha256:") for h in metrics.summary_source_hashes)


def test_compute_token_metrics_over_cap_caps_count_and_records_reason():
    summaries = [_summary(f"s{i}") for i in range(8)]
    metrics = compute_prior_summary_token_metrics(summaries)
    assert metrics.summaries_injected_count == PRIOR_SCENE_SUMMARY_CAP
    assert len(metrics.summary_source_hashes) == PRIOR_SCENE_SUMMARY_CAP
    assert metrics.truncation_reason == "summaries_over_5"


def test_compute_token_metrics_baseline_chars_added_to_estimate():
    """PR #44 review §4.1: when called with an `additional_chars`
    baseline (system prompt + scene context), the estimate folds that
    in alongside the summary block — no longer summary-only."""
    summaries = [_summary("s0", summary="content")]
    no_baseline = compute_prior_summary_token_metrics(summaries)
    with_baseline = compute_prior_summary_token_metrics(
        summaries, additional_chars=4_000
    )
    # 4000 chars / 4 chars-per-token = +1000 tokens on top of summary.
    assert with_baseline.prompt_token_estimate == (
        no_baseline.prompt_token_estimate + 1000
    )


def test_compute_token_metrics_baseline_chars_with_no_summaries():
    """Empty summary list + baseline → reflects baseline only; reason
    still `none` because no truncation triggered."""
    metrics = compute_prior_summary_token_metrics(
        [], additional_chars=2_000
    )
    assert metrics.summaries_injected_count == 0
    assert metrics.summary_source_hashes == []
    assert metrics.truncation_reason == "none"
    assert metrics.prompt_token_estimate == 500  # 2000 / 4


def test_compute_token_metrics_token_estimate_grows_with_summary_count():
    """More kept summaries → more rendered chars → higher estimate.
    Sanity check that the estimate correlates with the rendered block."""
    one = compute_prior_summary_token_metrics([_summary("s0")])
    three = compute_prior_summary_token_metrics(
        [_summary("s0"), _summary("s1"), _summary("s2")]
    )
    assert three.prompt_token_estimate > one.prompt_token_estimate


def test_compute_token_metrics_hashes_match_kept_set():
    """The kept order and hash list must agree — not e.g. hash full
    input but truncate the bullets."""
    summaries = [
        _summary("s0", chapter_id="chap_a"),
        _summary("s1", chapter_id="chap_a"),
        _summary("s2", chapter_id="chap_a"),
        _summary("s3", chapter_id="chap_a"),
        _summary("s4", chapter_id="chap_a"),
        _summary("s5", chapter_id="chap_a"),
        _summary("s6", chapter_id="chap_a"),
    ]
    metrics = compute_prior_summary_token_metrics(summaries)
    kept, _ = truncate_prior_scene_summaries(summaries)
    expected = [_summary_source_hash(s) for s in kept]
    assert metrics.summary_source_hashes == expected


# ---------------------------------------------------------------------------
# SceneGraphContext field defaults + renderer surface
# ---------------------------------------------------------------------------


def _bare_scene_ctx(prior=None, metrics=None) -> SceneGraphContext:
    kwargs: dict = {
        "scene_anchor": "scene_test",
        "chapter_ref": "chap_test",
        "location_candidates": [],
        "primary_location_ref": "loc_test",
        "participating_characters": [],
        "relations_matrix": [],
        "active_clocks": [],
        "system_time": {"scene_count": 0, "long_rest_count": 0},
        "target_beats": ["beat_a"],
    }
    if prior is not None:
        kwargs["prior_scene_summaries"] = prior
    if metrics is not None:
        kwargs["token_metrics"] = metrics
    return SceneGraphContext(**kwargs)


def test_scene_graph_context_defaults_back_compat():
    """A pre-T-3.3 caller building SceneGraphContext without the new
    fields must still get a usable object — empty list + schema-
    aligned default TokenMetrics (`truncation_reason='none'`)."""
    ctx = _bare_scene_ctx()
    assert ctx.prior_scene_summaries == []
    assert ctx.token_metrics == TokenMetrics()
    assert ctx.token_metrics.prompt_token_estimate == 0
    assert ctx.token_metrics.truncation_reason == "none"


def test_assemble_scene_context_block_omits_section_when_empty():
    rendered = assemble_scene_context_block(_bare_scene_ctx(), _scene_setting())
    assert "前置场景概要" not in rendered


def test_assemble_scene_context_block_renders_section_when_populated():
    summaries = [
        _summary("scene_a", summary="冲突一", key_state_paths=["flag.x"]),
        _summary("scene_b", summary="冲突二", key_state_paths=["world.x"]),
    ]
    rendered = assemble_scene_context_block(
        _bare_scene_ctx(prior=summaries), _scene_setting()
    )
    assert "前置场景概要" in rendered
    assert "[scene_a] 冲突一; 关键状态写入：flag.x" in rendered
    assert "[scene_b] 冲突二; 关键状态写入：world.x" in rendered


def test_assemble_scene_context_block_uses_truncated_set():
    """Renderer must apply the same truncation heuristic the strategy
    uses — otherwise the debug surface and the LLM-bound prompt would
    disagree about what got injected."""
    over = [_summary(f"s{i}") for i in range(7)]
    rendered = assemble_scene_context_block(
        _bare_scene_ctx(prior=over), _scene_setting()
    )
    # Most recent 5 (s2..s6) should appear; s0/s1 must not.
    assert "[s0]" not in rendered
    assert "[s1]" not in rendered
    for kept in ("s2", "s3", "s4", "s5", "s6"):
        assert f"[{kept}]" in rendered


# ---------------------------------------------------------------------------
# PR #44 review §3.1 — schema-bound TokenMetrics regression test
# ---------------------------------------------------------------------------


_DEP_INDEX_SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "schema"
    / "content_dependency_index.schema.json"
)


def _dep_index_validator():
    """Lazy-load the schema so the test module still imports cleanly
    even if the schema file ever moves; pytest skip marker handles
    the impossible case where the file is missing."""
    from jsonschema import Draft202012Validator

    if not _DEP_INDEX_SCHEMA_PATH.exists():
        pytest.skip("content_dependency_index.schema.json not present")
    schema = json.loads(_DEP_INDEX_SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def _envelope_for(token_metrics: TokenMetrics, scene_id: str = "scene_a") -> dict:
    """Wrap a `TokenMetrics` snapshot in the minimum-viable
    content_dependency_index sidecar envelope so the schema validator
    sees both the four ADR-024 fields and the surrounding context.
    """
    payload: dict = {
        "schema_version": "0.3.0",
        "scene_id": scene_id,
        "generated_at": "2026-05-08T12:00:00Z",
        "ontology_ids_read": [],
        "state_paths_read": [],
        "state_paths_written": [],
        "prompt_template_hash": "sha256:" + "0" * 64,
        # ADR-024 token metrics fields under test:
        "prompt_token_estimate": token_metrics.prompt_token_estimate,
        "summaries_injected_count": token_metrics.summaries_injected_count,
        "summary_source_hashes": list(token_metrics.summary_source_hashes),
        "truncation_reason": token_metrics.truncation_reason,
    }
    return payload


def test_pr44_review_3_1_token_metrics_under_cap_validates_against_schema():
    """PR #44 review §3.1: a SceneGraphContext-built TokenMetrics with
    ≤ 5 summaries serialises into a sidecar that passes
    `content_dependency_index.schema.json` without translation."""
    summaries = [
        _summary(f"scene_a_{i}", summary="prose", key_state_paths=["world.x"])
        for i in range(3)
    ]
    metrics = compute_prior_summary_token_metrics(summaries)
    envelope = _envelope_for(metrics)
    errors = sorted(
        _dep_index_validator().iter_errors(envelope),
        key=lambda e: list(e.absolute_path),
    )
    assert not errors, [e.message for e in errors]


def test_pr44_review_3_1_token_metrics_over_cap_validates_against_schema():
    """Eight summaries → cap-driven `summaries_over_5` reason must be
    a valid enum value per the schema; sha256-prefixed hashes must
    match the items pattern."""
    summaries = [
        _summary(f"scene_b_{i}", summary="prose", key_state_paths=["world.x"])
        for i in range(8)
    ]
    metrics = compute_prior_summary_token_metrics(summaries)
    envelope = _envelope_for(metrics)
    errors = sorted(
        _dep_index_validator().iter_errors(envelope),
        key=lambda e: list(e.absolute_path),
    )
    assert not errors, [e.message for e in errors]
    assert metrics.truncation_reason == "summaries_over_5"
    assert all(h.startswith("sha256:") for h in metrics.summary_source_hashes)
