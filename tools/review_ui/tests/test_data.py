"""Unit tests for the read-only data layer (no FastAPI involved)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

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
    assert by_id["s_alpha"].reviewable is True
    assert by_id["s_alpha"].not_reviewable_reason is None

    failure = by_id["iter_1"]  # failure envelope falls back to "iter_<N>"
    assert failure.source == "batch"
    assert failure.success is False
    assert failure.failure_reason == "schema_validation"
    assert failure.reviewable is False
    assert failure.not_reviewable_reason is not None
    assert "failed batch row" in failure.not_reviewable_reason

    mech_fail = by_id["s_gamma"]
    assert mech_fail.success is True
    assert mech_fail.mechanical_pass is False
    assert mech_fail.reviewable is False
    assert "mechanical pre-check" in (mech_fail.not_reviewable_reason or "")

    demo = by_id["demo_scene"]
    assert demo.source == "content"
    assert demo.has_deps_sidecar is True
    assert demo.advisory is None  # no batch advisory for content scenes
    assert demo.reviewable is False
    assert "content/" in (demo.not_reviewable_reason or "")


def test_list_scenes_handles_missing_directories() -> None:
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
    assert detail["reviewable"] is True
    assert detail["not_reviewable_reason"] is None


def test_get_scene_detail_content_is_not_reviewable(fixture_scenes_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=None, scenes_dir=fixture_scenes_dir)
    detail = loader.get_scene_detail("demo_scene")
    assert detail is not None
    assert detail["source"] == "content"
    assert detail["graph"]["graph_id"] == "demo_scene"
    assert detail["deps"]["scene_id"] == "demo_scene"
    assert detail["graph_views_available"] == []
    assert detail["reviewable"] is False
    assert "content/" in (detail["not_reviewable_reason"] or "")


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


def test_graph_file_rejects_path_traversal(fixture_batch_dir: Path) -> None:
    """Review C-4.2: scene_id with .. must not escape graph_views/ root."""
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    # Plant a sibling file outside graph_views/ that traversal would expose.
    (fixture_batch_dir / "secret.mmd").write_text("secret", encoding="utf-8")
    assert loader.get_graph_file("../secret", "mermaid") is None
    assert loader.get_graph_file("..", "mermaid") is None
    assert loader.get_graph_file("../..", "mermaid") is None
    assert loader.graph_views_available("../secret") == []


def test_is_reviewable_matrix(fixture_batch_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    assert loader.is_reviewable("s_alpha", 0) == (True, None)

    ok, why = loader.is_reviewable("does_not_exist", None)
    assert ok is False and why and "not found" in why

    ok, why = loader.is_reviewable("iter_1", 1)  # failure envelope (no graph_id)
    assert ok is False and why and "failed batch row" in why

    ok, why = loader.is_reviewable("s_gamma", 2)
    assert ok is False and why and "mechanical pre-check" in why


def test_append_review_writes_compatible_record(fixture_batch_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    rec = loader.append_review(
        scene_id="s_alpha", iter_id=0, decision="accept", reason=None
    )
    assert rec["accepted"] is True
    assert rec["scene_id"] == "s_alpha"
    assert rec["iter_id"] == 0
    assert rec["topology_pass"] is True
    log = (fixture_batch_dir / "scene_review_log.jsonl").read_text(encoding="utf-8").strip()
    assert json.loads(log)["scene_id"] == "s_alpha"


def test_append_review_reject_carries_reason(fixture_batch_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    rec = loader.append_review(
        scene_id="s_alpha", iter_id=0, decision="reject", reason="pacing weak"
    )
    assert rec["accepted"] is False
    assert rec["reason"] == "pacing weak"


def test_append_review_skip_persists_with_accepted_null(fixture_batch_dir: Path) -> None:
    """Review C-3.2: [S] must persist with accepted=null + reason."""
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    rec = loader.append_review(
        scene_id="s_alpha", iter_id=0, decision="skip", reason="defer to next session"
    )
    assert rec["accepted"] is None
    assert rec["reason"] == "defer to next session"
    # Read back through review_status: must surface as "skipped" not "rejected".
    rows = {r.scene_id: r for r in loader.list_scenes()}
    assert rows["s_alpha"].review_status == "skipped"
    assert rows["s_alpha"].review_reason == "defer to next session"


def test_append_review_skip_requires_reason(fixture_batch_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    with pytest.raises(ValueError, match="requires a non-empty reason"):
        loader.append_review(scene_id="s_alpha", iter_id=0, decision="skip", reason="")
    with pytest.raises(ValueError, match="requires a non-empty reason"):
        loader.append_review(scene_id="s_alpha", iter_id=0, decision="skip", reason=None)


def test_append_review_reject_requires_reason(fixture_batch_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    with pytest.raises(ValueError, match="requires a non-empty reason"):
        loader.append_review(scene_id="s_alpha", iter_id=0, decision="reject", reason="")


def test_append_review_rejects_unknown_scene(fixture_batch_dir: Path) -> None:
    """Review C-3.1: unknown scene_id is not reviewable."""
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    with pytest.raises(ValueError, match="not reviewable"):
        loader.append_review(
            scene_id="not_in_batch", iter_id=99, decision="accept", reason=None
        )


def test_append_review_rejects_failed_batch_row(fixture_batch_dir: Path) -> None:
    """Review C-3.1: failed batch row cannot carry a review verdict."""
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    with pytest.raises(ValueError, match="failed batch row"):
        loader.append_review(scene_id="iter_1", iter_id=1, decision="accept", reason=None)


def test_append_review_rejects_mechanical_failure(fixture_batch_dir: Path) -> None:
    """Review C-3.1: success=True but mechanical_pass=False is not reviewable."""
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    with pytest.raises(ValueError, match="mechanical pre-check"):
        loader.append_review(scene_id="s_gamma", iter_id=2, decision="accept", reason=None)


def test_append_review_rejects_unknown_decision(fixture_batch_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    with pytest.raises(ValueError, match="must be 'accept', 'reject', or 'skip'"):
        loader.append_review(scene_id="s_alpha", iter_id=0, decision="maybe", reason=None)


def test_append_review_requires_batch_dir(tmp_path: Path) -> None:
    loader = ReviewDataLoader(batch_dir=None, scenes_dir=tmp_path)
    with pytest.raises(RuntimeError):
        loader.append_review(scene_id="x", iter_id=0, decision="accept", reason=None)


def test_review_status_reflects_log(fixture_batch_dir: Path) -> None:
    loader = ReviewDataLoader(batch_dir=fixture_batch_dir, scenes_dir=None)
    loader.append_review(scene_id="s_alpha", iter_id=0, decision="accept", reason=None)
    rows = {r.scene_id: r for r in loader.list_scenes()}
    assert rows["s_alpha"].review_status == "accepted"
