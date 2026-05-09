"""Unit tests for the read-only data layer (no FastAPI involved)."""
from __future__ import annotations

import json
from pathlib import Path

from tools.review_ui.data import ReviewDataLoader


def test_list_scenes_merges_batch_and_content(fixture_batch_dir: Path, fixture_scenes_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=fixture_scenes_dir)
    rows = loader.list_scenes()
    by_id = {r.scene_id: r for r in rows}

    assert "s_alpha" in by_id
    assert by_id["s_alpha"].source == "batch"
    assert by_id["s_alpha"].success is True
    assert by_id["s_alpha"].topology_pass is True
    assert by_id["s_alpha"].sampling_pass is True  # 100/100 reached, 0 deadlocks
    assert by_id["s_alpha"].advisory == "accept"
    assert by_id["s_alpha"].graph_views_available == ["mermaid", "dot", "ascii"]

    failure = by_id["iter_1"]  # failure envelope falls back to "iter_<N>"
    assert failure.source == "batch"
    assert failure.success is False
    assert failure.failure_reason == "schema_validation"

    demo = by_id["demo_scene"]
    assert demo.source == "content"
    assert demo.has_deps_sidecar is True
    assert demo.advisory is None  # no batch advisory for content scenes


def test_list_scenes_handles_missing_directories(tmp_path: Path) -> None:
    loader = ReviewDataLoader(batch_dir=None, scenes_dir=None)
    assert loader.list_scenes() == []


def test_get_scene_detail_batch(fixture_batch_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    detail = loader.get_scene_detail("s_alpha")
    assert detail is not None
    assert detail["source"] == "batch"
    assert detail["graph"]["graph_id"] == "s_alpha"
    assert detail["validator_summaries"]["topology"]["pass"] is True
    assert detail["advisory"] == "accept"
    assert detail["advisory_rationale"]["lenient"] == "good vibes"
    assert detail["graph_views_available"] == ["mermaid", "dot", "ascii"]


def test_get_scene_detail_content(fixture_scenes_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=None, scenes_dir=fixture_scenes_dir)
    detail = loader.get_scene_detail("demo_scene")
    assert detail is not None
    assert detail["source"] == "content"
    assert detail["graph"]["graph_id"] == "demo_scene"
    assert detail["deps"]["scene_id"] == "demo_scene"
    assert detail["graph_views_available"] == []


def test_get_scene_detail_unknown(fixture_batch_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    assert loader.get_scene_detail("does_not_exist") is None


def test_graph_file_lookup(fixture_batch_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    text, ct = loader.get_graph_file("s_alpha", "mermaid")
    assert "flowchart TD" in text
    assert ct.startswith("text/plain")
    assert loader.get_graph_file("s_alpha", "ascii")[0].startswith("n_start")
    assert loader.get_graph_file("s_alpha", "missing") is None
    assert loader.get_graph_file("nope", "mermaid") is None


def test_append_review_writes_compatible_record(fixture_batch_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    rec = loader.append_review(
        scene_id="s_alpha", iter_id=0, decision="accept", reason=None
    )
    assert rec["accepted"] is True
    assert rec["scene_id"] == "s_alpha"
    assert rec["iter_id"] == 0
    assert rec["topology_pass"] is True
    # File was written and is parseable as JSONL with the same shape:
    log = (fixture_batch_dir / "scene_review_log.jsonl").read_text(encoding="utf-8").strip()
    assert json.loads(log)["scene_id"] == "s_alpha"


def test_append_review_reject_carries_reason(fixture_batch_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    rec = loader.append_review(
        scene_id="s_alpha", iter_id=0, decision="reject", reason="pacing weak"
    )
    assert rec["accepted"] is False
    assert rec["reason"] == "pacing weak"


def test_append_review_rejects_unknown_decision(fixture_batch_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    import pytest

    with pytest.raises(ValueError):
        loader.append_review(scene_id="s_alpha", iter_id=0, decision="maybe", reason=None)


def test_append_review_requires_batch_dir(tmp_path: Path) -> None:
    loader = ReviewDataLoader(batch_dir=None, scenes_dir=tmp_path)
    import pytest

    with pytest.raises(RuntimeError):
        loader.append_review(scene_id="x", iter_id=0, decision="accept", reason=None)


def test_review_status_reflects_log(fixture_batch_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    loader.append_review(scene_id="s_alpha", iter_id=0, decision="accept", reason=None)
    rows = loader.list_scenes()
    by_id = {r.scene_id: r for r in rows}
    assert by_id["s_alpha"].review_status == "accepted"
