"""T-3.6b RUI-INT-1..4 endpoint tests + PR #48 review C-phase tests.

Covers each integration endpoint, the F13 degrade contract on
``/api/playtest/{scene_id}``, plus the C-phase regression matrix:

  * 3.1 — visual file path traversal: pin to ``visuals_dir`` + suffix
    whitelist (a manifest entry pointing at ``../../.env`` must 404 and
    must NOT leak file contents).
  * 4.1 — visual thumbnails read sidecar's ``visual_asset_ids_referenced``
    first; fall back to graph's ``character_refs`` / ``scene_anchor``
    only when the sidecar is absent.
  * 4.2 — playtest default path: when ``batch_dir.parent`` is named
    ``experiments``, the resolver walks up to that level so real T-3.4
    CLI output is found without extra config.
  * 4.3 — chapter view derives ``{scene_id: chapter_id, act_id}`` from
    sidecar primarily; ontology ``included_scenes`` lookup is only the
    fallback.

MVP routes still pass via ``test_api.py``.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from tools.review_ui.server import build_app


# ---------------------------------------------------------------------------
# Composition fixtures: PR #48 review §3.2 — path overrides go on
# ``app.state.t36b_*`` attrs, not on ``ReviewDataLoader``.
# ---------------------------------------------------------------------------


@pytest.fixture
def client_full(
    fixture_batch_with_playtest: Path,
    fixture_scenes_dir: Path,
    fixture_visuals: Path,
    fixture_ontology: Path,
) -> TestClient:
    """Loader + integrations wired via app.state — the supported shape
    after the §3.2 module-boundary fix."""
    app = build_app(batch_dir=fixture_batch_with_playtest, scenes_dir=fixture_scenes_dir)
    app.state.t36b_visuals_dir = fixture_visuals
    app.state.t36b_ontology_path = fixture_ontology
    return TestClient(app)


@pytest.fixture
def client_no_integrations(fixture_batch_dir: Path, fixture_scenes_dir: Path) -> TestClient:
    """No app.state overrides — exercises the F13 degrade routes
    (manifest absent, no playtest dirs, no chapters)."""
    app = build_app(batch_dir=fixture_batch_dir, scenes_dir=fixture_scenes_dir)
    return TestClient(app)


# ===========================================================================
# RUI-INT-1: visual asset thumbnails (+ finding 4.1: sidecar primary)
# ===========================================================================


def test_visuals_endpoint_uses_sidecar_visual_asset_ids(client_full: TestClient) -> None:
    """Finding 4.1: when the sidecar lists ``visual_asset_ids_referenced``,
    the endpoint must use that as the source of truth.  s_alpha's
    sidecar names ``img_char_x_neutral`` so the response carries that
    asset, with ``source=sidecar``."""
    r = client_full.get("/api/scene/s_alpha/visuals")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["manifest_loaded"] is True
    assert body["source"] == "sidecar"
    assert [a["asset_id"] for a in body["characters"]] == ["img_char_x_neutral"]


def test_visuals_endpoint_sidecar_excludes_decoy_manifest_entries(
    client_full: TestClient, fixture_visuals: Path
) -> None:
    """Finding 4.1 follow-up: a manifest entry that matches the scene's
    ``character_refs`` but is NOT in the sidecar's
    ``visual_asset_ids_referenced`` must NOT appear in the response.
    Without this guard the UI would show stale assets that the dep_index
    no longer claims as referenced."""
    manifest_path = fixture_visuals / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"]["img_char_x_decoy"] = {
        "asset_id": "img_char_x_decoy",
        "asset_kind": "character_sheet",
        "asset_role": "character_sheet",
        "target_type": "character",
        "target_ref": "char_x",
        "character_ref": "char_x",
        "location_ref": None,
        "format": "png",
        "width": 1,
        "height": 1,
        "file_path": "content/visuals/char_x/img_char_x_neutral.png",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    r = client_full.get("/api/scene/s_alpha/visuals")
    assert r.status_code == 200, r.text
    body = r.json()
    asset_ids = {a["asset_id"] for a in body["characters"]}
    assert "img_char_x_decoy" not in asset_ids, asset_ids
    assert asset_ids == {"img_char_x_neutral"}


def test_visuals_endpoint_falls_back_to_graph_when_sidecar_missing_field(
    client_full: TestClient, fixture_batch_with_playtest: Path
) -> None:
    """When the sidecar exists but lacks ``visual_asset_ids_referenced``,
    fall back to the graph's character_refs + scene_anchor lookup."""
    sidecar_path = fixture_batch_with_playtest / "deps" / "s_alpha.deps.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar.pop("visual_asset_ids_referenced", None)
    sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")
    r = client_full.get("/api/scene/s_alpha/visuals")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["source"] == "graph_fallback"
    assert {a["asset_id"] for a in body["characters"]} == {"img_char_x_neutral"}
    assert {a["asset_id"] for a in body["locations"]} == {"img_scene_alpha_bg"}


def test_visuals_endpoint_unknown_scene_404(client_full: TestClient) -> None:
    r = client_full.get("/api/scene/no_such_scene/visuals")
    assert r.status_code == 404


def test_visuals_endpoint_no_manifest_returns_empty_groups(
    client_no_integrations: TestClient,
) -> None:
    r = client_no_integrations.get("/api/scene/s_alpha/visuals")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["manifest_loaded"] is False
    assert body["characters"] == []
    assert body["locations"] == []


# ---- visual file streaming + finding 3.1 hardening -------------------------


def test_visual_file_streams_png_bytes(client_full: TestClient) -> None:
    r = client_full.get("/api/visual/img_char_x_neutral")
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("image/png")
    assert r.content[:8] == b"\x89PNG\r\n\x1a\n"


def test_visual_file_unknown_asset_404(client_full: TestClient) -> None:
    r = client_full.get("/api/visual/img_does_not_exist")
    assert r.status_code == 404


def test_visual_file_traversal_via_dotdot_rejected(
    client_full: TestClient, fixture_visuals: Path
) -> None:
    """Finding 3.1 — a manifest entry pointing at ``../../.env`` (i.e.
    outside ``visuals_dir``) must 404 and the response body must NOT
    contain the secret bytes."""
    secret = fixture_visuals.parent.parent / "secret.env"
    secret.write_text("API_KEY=top-secret-do-not-leak", encoding="utf-8")
    manifest_path = fixture_visuals / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"]["evil_dotdot"] = {
        "asset_id": "evil_dotdot",
        "file_path": "../../secret.env",
        "format": "env",
        "target_type": "character",
        "target_ref": "char_x",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    r = client_full.get("/api/visual/evil_dotdot")
    assert r.status_code == 404
    assert b"top-secret-do-not-leak" not in r.content


def test_visual_file_traversal_inside_repo_root_rejected(
    client_full: TestClient, fixture_visuals: Path, fixture_scenes_dir: Path
) -> None:
    """Finding 3.1 — even a relative path that *stays* inside the repo
    root (would have passed the previous ``scenes_dir.parent`` guard)
    must be rejected if it escapes ``visuals_dir`` or has the wrong
    extension.  This is the actual exploit class the reviewer flagged:
    manifest pointing at ``content/secret.txt`` (inside repo root,
    outside visuals_dir)."""
    repo_root = fixture_scenes_dir.parent
    secret_in_repo = repo_root / "content" / "secret.txt"
    secret_in_repo.write_text("repo-internal-secret", encoding="utf-8")
    manifest_path = fixture_visuals / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"]["evil_in_repo"] = {
        "asset_id": "evil_in_repo",
        "file_path": "content/secret.txt",
        "format": "txt",
        "target_type": "character",
        "target_ref": "char_x",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    r = client_full.get("/api/visual/evil_in_repo")
    assert r.status_code == 404
    assert b"repo-internal-secret" not in r.content


def test_visual_file_extension_whitelist_rejects_non_image(
    client_full: TestClient, fixture_visuals: Path
) -> None:
    """Finding 3.1 — even if a file lives inside ``visuals_dir`` but has
    a non-image extension (someone drops ``visuals/leaked.json``), the
    endpoint must refuse to serve it."""
    sneaky = fixture_visuals / "char_x" / "leaked.json"
    sneaky.write_text('{"api_key": "secret"}', encoding="utf-8")
    manifest_path = fixture_visuals / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["assets"]["evil_json"] = {
        "asset_id": "evil_json",
        "file_path": "content/visuals/char_x/leaked.json",
        "format": "json",
        "target_type": "character",
        "target_ref": "char_x",
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False), encoding="utf-8")
    r = client_full.get("/api/visual/evil_json")
    assert r.status_code == 404
    assert b"api_key" not in r.content


# ===========================================================================
# RUI-INT-2: playtest panel (F13 degrade) + finding 4.2 default path
# ===========================================================================


def test_playtest_endpoint_returns_run_when_present(client_full: TestClient) -> None:
    r = client_full.get("/api/playtest/s_alpha")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["playtest_run"] == "playtest_001"
    path_ids = {p["path_id"] for p in body["worst_paths"]}
    assert path_ids == {"p001", "p002"}, path_ids
    for p in body["worst_paths"]:
        assert "steps" not in p
        assert "step_count" in p


def test_playtest_endpoint_degrades_when_no_run_for_scene(
    client_full: TestClient,
) -> None:
    r = client_full.get("/api/playtest/s_other_scene")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["playtest_run"] is None
    assert "no playtest run" in body["reason"]
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
    app = build_app(batch_dir=None, scenes_dir=fixture_scenes_dir)
    client = TestClient(app)
    r = client.get("/api/playtest/anything")
    assert r.status_code == 200, r.text
    assert r.json()["playtest_run"] is None


def test_playtest_default_path_resolves_to_experiments_root(
    fixture_batch_with_playtest_at_experiments_root: tuple[Path, Path],
) -> None:
    """Finding 4.2 — when ``batch_dir.parent`` is named ``experiments``
    (T-3.4 CLI's actual layout), the playtest_root resolver must walk
    up one level so real CLI output is found without extra config."""
    batch_dir, experiments_root = fixture_batch_with_playtest_at_experiments_root
    app = build_app(batch_dir=batch_dir, scenes_dir=None)
    client = TestClient(app)
    r = client.get("/api/playtest/s_x")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["playtest_run"] == "playtest_001", body
    assert body["playtest_root"] == str(experiments_root.resolve())


def test_playtest_path_override_via_app_state(
    fixture_batch_dir: Path, fixture_scenes_dir: Path, tmp_path: Path
) -> None:
    """Operator override: ``app.state.t36b_playtest_root`` wins over the
    default heuristic so a custom layout still works."""
    custom_root = tmp_path / "custom_playtest"
    run_dir = custom_root / "playtest_007"
    run_dir.mkdir(parents=True)
    (run_dir / "run_manifest.json").write_text(
        json.dumps({"playtest_id": "playtest_007", "scenes_played": ["s_alpha"]}, ensure_ascii=False),
        encoding="utf-8",
    )
    (run_dir / "worst_paths.jsonl").write_text("", encoding="utf-8")
    (run_dir / "worst_scenes.json").write_text(
        json.dumps({"playtest_id": "playtest_007", "rubric_version": "test", "scenes": []}, ensure_ascii=False),
        encoding="utf-8",
    )
    app = build_app(batch_dir=fixture_batch_dir, scenes_dir=fixture_scenes_dir)
    app.state.t36b_playtest_root = custom_root
    client = TestClient(app)
    r = client.get("/api/playtest/s_alpha")
    assert r.status_code == 200, r.text
    assert r.json()["playtest_run"] == "playtest_007"


# ===========================================================================
# RUI-INT-3: stale list (lazy dep_propagate call)
# ===========================================================================


def test_stale_endpoint_empty_inputs_returns_no_stale(client_full: TestClient) -> None:
    r = client_full.get("/api/stale")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["total_stale"] == 0
    assert body["stale_scenes"] == []
    assert body["report_schema_version"]


def test_stale_endpoint_ontology_id_match(client_full: TestClient) -> None:
    r = client_full.get("/api/stale?changed_ontology_ids=char_vellin")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["summary"]["total_stale"] == 1
    flagged = body["stale_scenes"][0]
    assert flagged["scene_id"] == "demo_scene"
    kinds = {r["kind"] for r in flagged["reasons"]}
    assert "ontology_id" in kinds


def test_stale_endpoint_state_path_prefix_match(client_full: TestClient) -> None:
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


def test_stale_endpoint_since_response_carries_diff_error_field(
    client_full: TestClient,
) -> None:
    r = client_full.get("/api/stale?since=zzz_definitely_bad_revision_xyz")
    assert r.status_code == 200, r.text
    body = r.json()
    assert "diff_error" in body
    assert body["summary"]["total_stale"] == 0


# ===========================================================================
# RUI-INT-4: chapter grouping + finding 4.3 (sidecar primary)
# ===========================================================================


def test_chapters_endpoint_returns_ontology_chapters(client_full: TestClient) -> None:
    r = client_full.get("/api/chapters")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["ontology_loaded"] is True
    assert len(body["chapters"]) == 1
    chap = body["chapters"][0]
    assert chap["chapter_id"] == "chap_intro"
    assert chap["acts"][0]["act_id"] == "act_arrival"


def test_chapters_endpoint_placement_uses_sidecar_when_present(
    client_full: TestClient,
) -> None:
    """Finding 4.3 — when a scene's sidecar carries chapter_id + act_id,
    that's the authoritative placement (NOT the ontology's
    included_scenes lookup).  s_alpha's sidecar names chap_intro /
    act_arrival explicitly."""
    r = client_full.get("/api/chapters")
    body = r.json()
    placements = body["scene_placements"]
    s_alpha = placements["s_alpha"]
    assert s_alpha["chapter_id"] == "chap_intro"
    assert s_alpha["act_id"] == "act_arrival"
    assert s_alpha["source"] == "sidecar"


def test_chapters_endpoint_placement_falls_back_to_ontology_anchor(
    client_full: TestClient, fixture_batch_with_playtest: Path
) -> None:
    """When the sidecar lacks chapter_id/act_id, the ontology's
    included_scenes (anchor-keyed) is the fallback.  Strip the sidecar
    fields and verify the placement source switches to
    ``ontology_anchor_lookup``."""
    sidecar_path = fixture_batch_with_playtest / "deps" / "s_alpha.deps.json"
    sidecar = json.loads(sidecar_path.read_text(encoding="utf-8"))
    sidecar.pop("chapter_id", None)
    sidecar.pop("act_id", None)
    sidecar_path.write_text(json.dumps(sidecar, ensure_ascii=False), encoding="utf-8")
    r = client_full.get("/api/chapters")
    body = r.json()
    s_alpha = body["scene_placements"]["s_alpha"]
    assert s_alpha["source"] == "ontology_anchor_lookup"
    assert s_alpha["chapter_id"] == "chap_intro"
    assert s_alpha["act_id"] == "act_arrival"


def test_chapters_endpoint_placement_summary_counts(client_full: TestClient) -> None:
    r = client_full.get("/api/chapters")
    summary = r.json()["placement_summary"]
    assert summary["from_sidecar"] >= 1
    assert summary["unplaced"] >= 1
    assert summary["total"] == summary["placed"] + summary["unplaced"]


def test_chapters_endpoint_missing_ontology_returns_empty(
    client_no_integrations: TestClient,
) -> None:
    r = client_no_integrations.get("/api/chapters")
    assert r.status_code == 200, r.text
    body = r.json()
    assert body["chapters"] == []
    # placements still computed from sidecars even without ontology;
    # since no scene has both sidecar chapter_id+act_id, all unplaced.
    assert body["placement_summary"]["placed"] == 0
