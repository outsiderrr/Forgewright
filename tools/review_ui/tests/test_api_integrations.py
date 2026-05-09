"""T-3.6b RUI-INT-1..4 endpoint tests.

Covers each integration endpoint plus the F13 degrade contract on
``/api/playtest/{scene_id}`` (no playtest run → empty payload, never
404 / 500).  MVP routes still pass via ``test_api.py``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tools.review_ui.server import build_app


# ---------------------------------------------------------------------------
# Composition fixtures: each test wires the loader with the slice of paths
# it actually exercises, mirroring the CLI's resolution order.
# ---------------------------------------------------------------------------


@pytest.fixture
def client_full(
    fixture_batch_with_playtest: Path,
    fixture_scenes_dir: Path,
    fixture_visuals: Path,
    fixture_ontology: Path,
) -> TestClient:
    """Loader with all four integration sources wired."""
    from tools.review_ui.data import ReviewDataLoader

    loader = ReviewDataLoader(
        batch_dir=fixture_batch_with_playtest,
        scenes_dir=fixture_scenes_dir,
        visuals_dir=fixture_visuals,
        ontology_path=fixture_ontology,
    )
    app = build_app(batch_dir=fixture_batch_with_playtest, scenes_dir=fixture_scenes_dir)
    app.state.loader = loader  # override the default loader with our integrated one
    return TestClient(app)


@pytest.fixture
def client_no_integrations(fixture_batch_dir: Path, fixture_scenes_dir: Path) -> TestClient:
    """Loader without visuals / playtest / ontology paths — exercises the
    F13 degrade routes (manifest missing, no playtest dirs, no chapters)."""
    app = build_app(batch_dir=fixture_batch_dir, scenes_dir=fixture_scenes_dir)
    return TestClient(app)


# ---------------------------------------------------------------------------
# RUI-INT-1: visual asset thumbnails
# ---------------------------------------------------------------------------


def test_visuals_endpoint_returns_character_and_location(client_full: TestClient) -> None:
    r = client_full.get("/api/scene/s_alpha/visuals")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["scene_id"] == "s_alpha"
    assert body["scene_anchor"] == "scene_alpha"
    assert body["manifest_loaded"] is True
    # s_alpha's character_refs == ["char_x"]; manifest has one matching asset.
    assert [a["asset_id"] for a in body["characters"]] == ["img_char_x_neutral"]
    # scene_anchor == "scene_alpha"; manifest has one location asset.
    assert [a["asset_id"] for a in body["locations"]] == ["img_scene_alpha_bg"]
    # Each thumbnail row has the streaming URL pointing to /api/visual/<id>.
    assert body["characters"][0]["file_url"] == "/api/visual/img_char_x_neutral"


def test_visuals_endpoint_unknown_scene_404(client_full: TestClient) -> None:
    r = client_full.get("/api/scene/no_such_scene/visuals")
    assert r.status_code == 404


def test_visuals_endpoint_no_manifest_returns_empty_groups(
    client_no_integrations: TestClient,
) -> None:
    """When ``visuals_dir/manifest.json`` doesn't exist the endpoint must
    keep returning a structured payload with empty groups, not 404 — so
    the UI knows to render the placeholder rather than disappear."""
    r = client_no_integrations.get("/api/scene/s_alpha/visuals")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["manifest_loaded"] is False
    assert body["characters"] == []
    assert body["locations"] == []


def test_visual_file_streams_png_bytes(client_full: TestClient) -> None:
    r = client_full.get("/api/visual/img_char_x_neutral")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("image/png")
    # Verify PNG signature (first 8 bytes); confirms the file made it
    # through unmodified.
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_visual_file_unknown_asset_404(client_full: TestClient) -> None:
    r = client_full.get("/api/visual/img_does_not_exist")
    assert r.status_code == 404


def test_visual_file_traversal_rejected(
    client_full: TestClient, fixture_visuals: Path
) -> None:
    """Path traversal guard: a malicious manifest entry that escapes
    visuals_dir.parent must be rejected by the loader, not served.

    We simulate by writing a sibling secret outside the visuals tree
    and pointing a manifest entry at it via ``..``.  The endpoint should
    return 404, NOT the secret bytes.
    """
    secret = fixture_visuals.parent.parent / "secret.txt"  # outside scenes_dir.parent
    secret.write_text("top-secret", encoding="utf-8")
    manifest_path = fixture_visuals / "manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    payload["assets"]["evil"] = {
        "asset_id": "evil",
        "file_path": "../../secret.txt",
        "format": "txt",
        "target_type": "character",
        "target_ref": "char_x",
    }
    manifest_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    r = client_full.get("/api/visual/evil")
    assert r.status_code == 404


# ---------------------------------------------------------------------------
# RUI-INT-2: playtest panel (F13 degrade contract)
# ---------------------------------------------------------------------------


def test_playtest_endpoint_returns_run_when_present(client_full: TestClient) -> None:
    r = client_full.get("/api/playtest/s_alpha")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["playtest_run"] == "playtest_001"
    assert body["playtest_id"] == "playtest_001"
    # only the two s_alpha rows survive the scene_id filter.
    path_ids = [p["path_id"] for p in body["worst_paths"]]
    assert set(path_ids) == {"p001", "p002"}, path_ids
    # scene_summary picked up from worst_scenes.json
    assert body["scene_summary"]["scene_id"] == "s_alpha"
    assert body["scene_summary"]["critical_count"] == 1
    # steps[] was stripped to keep the payload small
    for p in body["worst_paths"]:
        assert "steps" not in p
        assert "step_count" in p


def test_playtest_endpoint_degrades_when_no_run_for_scene(
    client_full: TestClient,
) -> None:
    """F13: scene with no playtest run returns playtest_run=null + reason."""
    r = client_full.get("/api/playtest/s_other_scene")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["playtest_run"] is None
    assert "no playtest run" in body["reason"]
    # all_runs_scanned is still populated so the UI can show "scanned N runs"
    assert body["all_runs_scanned"] >= 1


def test_playtest_endpoint_degrades_when_no_runs_at_all(
    client_no_integrations: TestClient,
) -> None:
    r = client_no_integrations.get("/api/playtest/s_alpha")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["playtest_run"] is None
    assert body["reason"]


def test_playtest_endpoint_degrades_when_no_batch_dir(
    fixture_scenes_dir: Path,
) -> None:
    """No batch_dir at all → degrade still 200, not 500."""
    app = build_app(batch_dir=None, scenes_dir=fixture_scenes_dir)
    client = TestClient(app)
    r = client.get("/api/playtest/anything")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["playtest_run"] is None


# ---------------------------------------------------------------------------
# RUI-INT-3: stale list (lazy dep_propagate call)
# ---------------------------------------------------------------------------


def test_stale_endpoint_empty_inputs_returns_no_stale(client_full: TestClient) -> None:
    """No changes claimed → no stale scenes (sensible idle default)."""
    r = client_full.get("/api/stale")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["total_stale"] == 0
    assert body["stale_scenes"] == []
    assert body["report_schema_version"]


def test_stale_endpoint_ontology_id_match(client_full: TestClient) -> None:
    """demo_scene's sidecar lists char_vellin in ontology_ids_read.
    Claiming char_vellin changed should flag the scene."""
    r = client_full.get("/api/stale?changed_ontology_ids=char_vellin")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["total_stale"] == 1
    flagged = body["stale_scenes"][0]
    assert flagged["scene_id"] == "demo_scene"
    kinds = {r["kind"] for r in flagged["reasons"]}
    assert "ontology_id" in kinds


def test_stale_endpoint_state_path_prefix_match(client_full: TestClient) -> None:
    """state_path namespace wildcard should hit demo_scene (which reads
    faction.iron_oath.reputation)."""
    r = client_full.get("/api/stale?changed_state_paths=faction.iron_oath.*")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["total_stale"] == 1


def test_stale_endpoint_visual_and_clock_inputs(client_full: TestClient) -> None:
    r = client_full.get(
        "/api/stale?changed_visual_assets=img_vellin_neutral&changed_clocks=clk_seasons"
    )
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["total_stale"] == 1
    flagged = body["stale_scenes"][0]
    kinds = {r["kind"] for r in flagged["reasons"]}
    assert "visual_asset" in kinds
    assert "clock" in kinds


def test_stale_endpoint_since_response_carries_diff_error_field(
    client_full: TestClient,
) -> None:
    """The ``--since`` path must always carry a ``diff_error`` field —
    None when it succeeds, a string when dep_propagate raises.  We can
    only weakly assert the field is present (the underlying tmp_path
    ontology isn't tracked by any reachable git repo, so dep_propagate
    quietly degrades to "all entities are new" rather than raising).
    Relevant: the endpoint must not 500."""
    r = client_full.get("/api/stale?since=zzz_definitely_bad_revision_xyz")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "diff_error" in body
    # Whether diff_error is None or a string, total_stale should be 0
    # because no scene sidecar references char_x in its ontology_ids_read
    # (demo_scene only references char_vellin).
    assert body["summary"]["total_stale"] == 0


# ---------------------------------------------------------------------------
# RUI-INT-4: chapter grouping
# ---------------------------------------------------------------------------


def test_chapters_endpoint_returns_ontology_chapters(client_full: TestClient) -> None:
    r = client_full.get("/api/chapters")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ontology_loaded"] is True
    assert len(body["chapters"]) == 1
    chap = body["chapters"][0]
    assert chap["chapter_id"] == "chap_intro"
    assert chap["acts"][0]["act_id"] == "act_arrival"
    assert chap["acts"][0]["included_scenes"] == ["scene_alpha"]


def test_chapters_endpoint_missing_ontology_returns_empty(
    client_no_integrations: TestClient,
) -> None:
    """Default ontology path (state/ontology/waystation.json relative to cwd)
    won't exist under tmp test dirs → endpoint must return chapters=[] not 500."""
    r = client_no_integrations.get("/api/chapters")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chapters"] == []


def test_scenes_endpoint_carries_scene_anchor(client_full: TestClient) -> None:
    """T-3.6b extension to /api/scenes — scene_anchor is needed by the
    chapter-grouping nav.  Existing fields stay (verified by MVP tests)."""
    r = client_full.get("/api/scenes")
    assert r.status_code == 200, r.text
    by_id = {s["scene_id"]: s for s in r.json()["scenes"]}
    assert by_id["s_alpha"]["scene_anchor"] == "scene_alpha"
    assert by_id["demo_scene"]["scene_anchor"] == "scene_demo"
