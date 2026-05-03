"""T-2.0 R4 cleanup: GraphContext.location_candidates field shape.

These tests pin down the v1.0-修订 contract:

  * `GraphContext.location_candidates` is a `list[dict]` — defaulting to
    an empty list, never `None` — and `primary_location_ref` is a
    `str | None` defaulting to `None`. The field name unification (no more
    `location_card`) is a hard contract so SceneGraphContext (T-2.6) can
    share the shape.
  * `assemble_context_block` renders each candidate as a JSON code block,
    surfaces `primary_location_ref` when set, and falls back to the
    "ontology stub未提供" hint when the list is empty (so the prompt never
    crashes on an empty stub world).
"""
from __future__ import annotations

import json

from generator.context_assembler import (
    GraphContext,
    NodeRequirement,
    assemble_context_block,
)


def _req() -> NodeRequirement:
    return NodeRequirement(
        node_type="dialogue",
        expected_speaker_ref="char_demo",
        narrative_intent="测试用",
    )


# ---------------------------------------------------------------------------
# Field shape
# ---------------------------------------------------------------------------


def test_graph_context_default_field_shape():
    ctx = GraphContext(scene_anchor="scene_demo")
    assert ctx.location_candidates == []
    assert ctx.primary_location_ref is None
    # The other defaults shouldn't have shifted as a side effect of the rename.
    assert ctx.parent_chain == []
    assert ctx.involved_characters == []
    assert ctx.faction_clocks == {}


def test_graph_context_location_candidates_is_list_of_dict():
    ctx = GraphContext(
        scene_anchor="scene_demo",
        location_candidates=[
            {"location_id": "scene_a", "name": "甲"},
            {"location_id": "scene_b", "name": "乙"},
        ],
        primary_location_ref="scene_a",
    )
    assert isinstance(ctx.location_candidates, list)
    assert all(isinstance(c, dict) for c in ctx.location_candidates)
    assert ctx.primary_location_ref == "scene_a"


def test_graph_context_no_legacy_location_card_attr():
    """The rename is hard — `location_card` should be gone from GraphContext
    so we don't accidentally re-introduce it via copy-paste."""
    ctx = GraphContext(scene_anchor="scene_demo")
    assert not hasattr(ctx, "location_card")


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------


def test_assemble_context_block_renders_candidates_section():
    ctx = GraphContext(
        scene_anchor="scene_waystation_of_iron_oath",
        location_candidates=[
            {
                "location_id": "scene_waystation_of_iron_oath",
                "name": "铁誓驿站",
                "summary": "铁誓卫队的山道驿站。",
            },
            {
                "location_id": "scene_eastern_pasture_ruin",
                "name": "牧人废屋",
                "summary": "驿站东侧的废弃牧人小屋。",
            },
        ],
        primary_location_ref="scene_waystation_of_iron_oath",
    )

    block = assemble_context_block(ctx, _req())

    assert "## 候选地点" in block
    # Every candidate's location_id appears in the rendered block.
    assert "scene_waystation_of_iron_oath" in block
    assert "scene_eastern_pasture_ruin" in block
    # The primary_location_ref is announced as the suggested default.
    assert "主地点" in block
    # The block must instruct the model that picking outside the list is
    # invalid — that's the prompt-level R4 fix.
    assert "必须" in block or "禁止" in block


def test_assemble_context_block_omits_primary_marker_when_none():
    ctx = GraphContext(
        scene_anchor="scene_demo",
        location_candidates=[
            {"location_id": "scene_a", "name": "甲"},
            {"location_id": "scene_b", "name": "乙"},
        ],
        primary_location_ref=None,
    )
    block = assemble_context_block(ctx, _req())
    # Both candidates appear, but no "主地点（推荐...）" line.
    assert "scene_a" in block and "scene_b" in block
    assert "主地点" not in block


def test_assemble_context_block_handles_empty_candidates():
    ctx = GraphContext(scene_anchor="scene_demo")  # defaults: empty list, None primary
    block = assemble_context_block(ctx, _req())
    assert "## 候选地点" in block
    # Falls back to the "ontology stub" hint rather than crashing.
    assert "本体桩" in block or "未提供" in block


def test_assemble_context_block_candidates_emit_valid_json_blocks():
    """Each candidate dict is rendered as a JSON code block; parsing the
    block back out should produce the same dicts (sanity check that we
    didn't double-encode or strip non-ascii by accident)."""
    cands = [
        {"location_id": "scene_a", "name": "甲", "summary": "中文摘要"},
        {"location_id": "scene_b", "name": "乙"},
    ]
    ctx = GraphContext(scene_anchor="scene_demo", location_candidates=cands)
    block = assemble_context_block(ctx, _req())

    # Crude but deterministic: every candidate's full JSON serialisation
    # (with ensure_ascii=False, indent=2) is a substring of the rendered block.
    for cand in cands:
        assert json.dumps(cand, ensure_ascii=False, indent=2) in block
