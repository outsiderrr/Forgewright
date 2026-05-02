"""Tests for generator.image_import CLI (T-1.5.7).

All five scenarios required by STAGE_1.5_TASKS.md T-1.5.7 §3:
  - test_import_one_character_asset
  - test_import_one_background_asset (target_type=location)
  - test_import_validation_fail (image_validator rejects)
  - test_dry_run (no disk mutation)
  - test_all_pending_partial_fail (3 stubs: 2 pass, 1 fails)

Plus targeted unit tests for:
  - mirror-field consistency (target_type=character missing character_ref)
  - meta.json missing required keys
  - duplicate asset_id in manifest (idempotency: skip + log + don't move)
  - asset_id_stub for missing pending dir is logged

Tests build their own tmp_path universe: pending_root / visuals_root /
manifest / ontology / import_log are all redirected. No production paths
are touched.
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path
from typing import Any

import pytest
from PIL import Image

from generator import image_import, import_log
from generator.image_import import run_import
from generator.manifest import Manifest, load_manifest


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict[str, Path]:
    """Build a fresh tmp universe and patch import_log to use it."""
    pending_root = tmp_path / "_pending"
    visuals_root = tmp_path / "visuals"
    manifest_path = visuals_root / "manifest.json"
    ontology_path = tmp_path / "waystation.json"
    import_log_path = tmp_path / "import_log.jsonl"

    pending_root.mkdir()
    visuals_root.mkdir()

    # Empty-skeleton manifest (matches the committed initial state).
    manifest_path.write_text(
        json.dumps({"schema_version": "0.2.0", "assets": {}}, indent=2) + "\n",
        encoding="utf-8",
    )

    # Ontology with three character entities + one scene entity, mirroring
    # the real waystation.json shape.
    ontology_payload: dict[str, Any] = {
        "entities": [
            {
                "id": "char_vellin",
                "display_name": "Vellin",
                "type": "character",
                "visual_assets": [],
            },
            {
                "id": "char_corvan",
                "display_name": "Corvan",
                "type": "character",
                "visual_assets": [],
            },
            {
                "id": "char_aelwin",
                "display_name": "Aelwin",
                "type": "character",
                "visual_assets": [],
            },
            {
                "id": "scene_waystation_of_iron_oath",
                "display_name": "Waystation of the Iron Oath",
                "type": "scene",
            },
            {
                "id": "loc_old_mill",
                "display_name": "Old Mill",
                "type": "location",
            },
        ]
    }
    ontology_path.write_text(
        json.dumps(ontology_payload, ensure_ascii=False, indent=4) + "\n",
        encoding="utf-8",
    )

    monkeypatch.setenv("FORGEWRIGHT_IMPORT_LOG", str(import_log_path))

    return {
        "pending_root": pending_root,
        "visuals_root": visuals_root,
        "manifest_path": manifest_path,
        "ontology_path": ontology_path,
        "import_log_path": import_log_path,
    }


def _write_png(
    path: Path, *, mode: str = "RGBA", size: tuple[int, int] = (1024, 1024)
) -> None:
    """Save a fresh PNG large enough to clear image_validator (min 768x768)."""
    img = Image.new(mode, size, color=(128, 128, 128, 255) if mode == "RGBA" else (128, 128, 128))
    img.save(path, format="PNG")


def _make_pending_stub(
    pending_root: Path,
    *,
    asset_id_stub: str,
    target_ref: str,
    target_type: str,
    asset_role: str,
    asset_kind: str,
    png_mode: str = "RGBA",
    png_size: tuple[int, int] = (1024, 1024),
    png_basename: str | None = None,
    extra_meta: dict[str, Any] | None = None,
    skip_meta: bool = False,
) -> Path:
    """Materialise the on-disk shape ManualImportProvider produces."""
    stub_dir = pending_root / asset_id_stub
    stub_dir.mkdir(parents=True, exist_ok=True)

    png_name = png_basename or f"{asset_id_stub}.png"
    _write_png(stub_dir / png_name, mode=png_mode, size=png_size)

    if skip_meta:
        return stub_dir

    if target_type == "character":
        char_ref: str | None = target_ref
        loc_ref: str | None = None
    else:
        char_ref = None
        loc_ref = target_ref

    meta: dict[str, Any] = {
        "asset_id_stub": asset_id_stub,
        "target_ref": target_ref,
        "target_type": target_type,
        "asset_role": asset_role,
        "asset_kind": asset_kind,
        "variant_label": "neutral",
        "size": list(png_size),
        "n": 1,
        "source_mode": "manual",
        "created_at": _dt.datetime(
            2026, 5, 1, 12, 0, 0, tzinfo=_dt.timezone.utc
        ).isoformat(),
        "prompt_hash": "a" * 64,
        "character_ref": char_ref,
        "location_ref": loc_ref,
    }
    if extra_meta:
        meta.update(extra_meta)
    (stub_dir / "meta.json").write_text(
        json.dumps(meta, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (stub_dir / "README.md").write_text("(test fixture)\n", encoding="utf-8")
    return stub_dir


# ---------------------------------------------------------------------------
# Required scenarios
# ---------------------------------------------------------------------------


def test_import_one_character_asset(env: dict[str, Path]) -> None:
    stub = _make_pending_stub(
        env["pending_root"],
        asset_id_stub="img_vellin_neutral",
        target_ref="char_vellin",
        target_type="character",
        asset_role="character_sheet",
        asset_kind="character_sheet",
        png_mode="RGBA",
    )

    outcomes = run_import(
        asset_id="img_vellin_neutral",
        all_pending=False,
        dry_run=False,
        pending_root=env["pending_root"],
        visuals_root=env["visuals_root"],
        manifest_path=env["manifest_path"],
        ontology_path=env["ontology_path"],
    )

    assert len(outcomes) == 1
    assert outcomes[0].status == "imported"
    assert outcomes[0].asset_id_stub == "img_vellin_neutral"

    # PNG moved to content/visuals/vellin/<stub>.png
    final_png = env["visuals_root"] / "vellin" / "img_vellin_neutral.png"
    assert final_png.exists()
    # Pending stub directory cleaned up
    assert not stub.exists()

    # Manifest updated
    m = load_manifest(env["manifest_path"])
    assert "img_vellin_neutral" in m.assets
    asset = m.assets["img_vellin_neutral"]
    assert asset.target_ref == "char_vellin"
    assert asset.file_path == "content/visuals/vellin/img_vellin_neutral.png"

    # Ontology entity has one visual_asset entry
    ontology = json.loads(env["ontology_path"].read_text(encoding="utf-8"))
    vellin = next(e for e in ontology["entities"] if e["id"] == "char_vellin")
    assert len(vellin["visual_assets"]) == 1
    assert vellin["visual_assets"][0]["asset_id"] == "img_vellin_neutral"
    # Sibling character entries untouched
    corvan = next(e for e in ontology["entities"] if e["id"] == "char_corvan")
    assert corvan["visual_assets"] == []
    # Scene entity untouched (no visual_assets field added)
    scene = next(
        e for e in ontology["entities"] if e["id"] == "scene_waystation_of_iron_oath"
    )
    assert "visual_assets" not in scene

    # Log row written
    rows = import_log.read_all()
    assert len(rows) == 1
    assert rows[0]["status"] == "imported"
    assert rows[0]["final_asset_id"] == "img_vellin_neutral"
    assert rows[0]["final_path"] == "content/visuals/vellin/img_vellin_neutral.png"


def test_import_one_background_asset(env: dict[str, Path]) -> None:
    """target_type=location: PNG goes under loc_old_mill/, ontology untouched."""
    stub = _make_pending_stub(
        env["pending_root"],
        asset_id_stub="img_old_mill_dawn",
        target_ref="loc_old_mill",
        target_type="location",
        asset_role="scene_background",
        asset_kind="scene_background",
        png_mode="RGB",  # backgrounds forbid alpha
    )

    outcomes = run_import(
        asset_id="img_old_mill_dawn",
        all_pending=False,
        dry_run=False,
        pending_root=env["pending_root"],
        visuals_root=env["visuals_root"],
        manifest_path=env["manifest_path"],
        ontology_path=env["ontology_path"],
    )

    assert outcomes[0].status == "imported"
    final_png = env["visuals_root"] / "loc_old_mill" / "img_old_mill_dawn.png"
    assert final_png.exists()
    assert not stub.exists()

    # Manifest updated
    m = load_manifest(env["manifest_path"])
    asset = m.assets["img_old_mill_dawn"]
    assert asset.target_type.value == "location"
    assert asset.file_path == "content/visuals/loc_old_mill/img_old_mill_dawn.png"

    # Ontology entirely unchanged (no visual_assets writes for non-character)
    ontology = json.loads(env["ontology_path"].read_text(encoding="utf-8"))
    location = next(e for e in ontology["entities"] if e["id"] == "loc_old_mill")
    # We don't add visual_assets to non-character entities
    assert "visual_assets" not in location
    # Character entries untouched
    for cid in ("char_vellin", "char_corvan", "char_aelwin"):
        ent = next(e for e in ontology["entities"] if e["id"] == cid)
        assert ent["visual_assets"] == []


def test_import_validation_fail(env: dict[str, Path]) -> None:
    """RGB PNG when asset_kind=character_sheet → ALPHA_REQUIRED → reject."""
    stub = _make_pending_stub(
        env["pending_root"],
        asset_id_stub="img_vellin_bad_alpha",
        target_ref="char_vellin",
        target_type="character",
        asset_role="character_sheet",
        asset_kind="character_sheet",
        png_mode="RGB",  # missing alpha → image_validator rejects
    )

    outcomes = run_import(
        asset_id="img_vellin_bad_alpha",
        all_pending=False,
        dry_run=False,
        pending_root=env["pending_root"],
        visuals_root=env["visuals_root"],
        manifest_path=env["manifest_path"],
        ontology_path=env["ontology_path"],
    )

    assert outcomes[0].status == "rejected"
    assert "ALPHA_REQUIRED" in (outcomes[0].validation_errors or [])

    # Stub moved to _rejected/
    rejected_dir = env["pending_root"] / "_rejected" / "img_vellin_bad_alpha"
    assert rejected_dir.exists()
    assert not stub.exists()

    # Manifest unchanged
    m = load_manifest(env["manifest_path"])
    assert m.assets == {}

    # Ontology unchanged
    ontology = json.loads(env["ontology_path"].read_text(encoding="utf-8"))
    for cid in ("char_vellin", "char_corvan", "char_aelwin"):
        ent = next(e for e in ontology["entities"] if e["id"] == cid)
        assert ent["visual_assets"] == []

    # Log row recorded with codes
    rows = import_log.read_all()
    assert len(rows) == 1
    assert rows[0]["status"] == "rejected"
    assert "ALPHA_REQUIRED" in rows[0]["validation_errors"]


def test_dry_run_does_not_mutate_disk(env: dict[str, Path]) -> None:
    stub = _make_pending_stub(
        env["pending_root"],
        asset_id_stub="img_vellin_neutral",
        target_ref="char_vellin",
        target_type="character",
        asset_role="character_sheet",
        asset_kind="character_sheet",
    )
    manifest_before = env["manifest_path"].read_text(encoding="utf-8")
    ontology_before = env["ontology_path"].read_text(encoding="utf-8")

    outcomes = run_import(
        asset_id="img_vellin_neutral",
        all_pending=False,
        dry_run=True,
        pending_root=env["pending_root"],
        visuals_root=env["visuals_root"],
        manifest_path=env["manifest_path"],
        ontology_path=env["ontology_path"],
    )

    assert outcomes[0].status == "dry_run"
    assert outcomes[0].final_path == "content/visuals/vellin/img_vellin_neutral.png"

    # Pending dir kept; PNG not moved
    assert stub.exists()
    assert (stub / "img_vellin_neutral.png").exists()
    # No vellin/ subdir created
    assert not (env["visuals_root"] / "vellin").exists()
    # Manifest + ontology byte-identical
    assert env["manifest_path"].read_text(encoding="utf-8") == manifest_before
    assert env["ontology_path"].read_text(encoding="utf-8") == ontology_before

    # Log row records the dry_run
    rows = import_log.read_all()
    assert len(rows) == 1
    assert rows[0]["status"] == "dry_run"


def test_all_pending_partial_fail(env: dict[str, Path]) -> None:
    """Three stubs: 2 valid (imported), 1 invalid (rejected); others unaffected."""
    _make_pending_stub(
        env["pending_root"],
        asset_id_stub="img_vellin_neutral",
        target_ref="char_vellin",
        target_type="character",
        asset_role="character_sheet",
        asset_kind="character_sheet",
    )
    _make_pending_stub(
        env["pending_root"],
        asset_id_stub="img_corvan_smile",
        target_ref="char_corvan",
        target_type="character",
        asset_role="character_sheet",
        asset_kind="character_sheet",
    )
    _make_pending_stub(
        env["pending_root"],
        asset_id_stub="img_aelwin_bad",
        target_ref="char_aelwin",
        target_type="character",
        asset_role="character_sheet",
        asset_kind="character_sheet",
        png_mode="RGB",  # forces validation failure
    )

    outcomes = run_import(
        asset_id=None,
        all_pending=True,
        dry_run=False,
        pending_root=env["pending_root"],
        visuals_root=env["visuals_root"],
        manifest_path=env["manifest_path"],
        ontology_path=env["ontology_path"],
        batch_name="vellin_run1",
    )

    by_id = {o.asset_id_stub: o for o in outcomes}
    assert by_id["img_vellin_neutral"].status == "imported"
    assert by_id["img_corvan_smile"].status == "imported"
    assert by_id["img_aelwin_bad"].status == "rejected"

    # Two assets in manifest; failed one absent
    m = load_manifest(env["manifest_path"])
    assert set(m.assets.keys()) == {"img_vellin_neutral", "img_corvan_smile"}

    # Ontology: vellin + corvan have one each; aelwin still empty
    ontology = json.loads(env["ontology_path"].read_text(encoding="utf-8"))

    def _va(cid: str) -> list[dict]:
        return next(e for e in ontology["entities"] if e["id"] == cid)["visual_assets"]

    assert len(_va("char_vellin")) == 1
    assert len(_va("char_corvan")) == 1
    assert _va("char_aelwin") == []

    # Failed stub in _rejected/, successful ones cleaned up
    assert (env["pending_root"] / "_rejected" / "img_aelwin_bad").exists()
    assert not (env["pending_root"] / "img_vellin_neutral").exists()
    assert not (env["pending_root"] / "img_corvan_smile").exists()

    # Log: three rows tagged with the batch
    rows = import_log.read_all(batch_name="vellin_run1")
    assert len(rows) == 3
    statuses = {r["asset_id_stub"]: r["status"] for r in rows}
    assert statuses == {
        "img_vellin_neutral": "imported",
        "img_corvan_smile": "imported",
        "img_aelwin_bad": "rejected",
    }


# ---------------------------------------------------------------------------
# Targeted unit tests
# ---------------------------------------------------------------------------


def test_meta_missing_required_keys_rejects(env: dict[str, Path]) -> None:
    """meta.json without prompt_hash → reject (ManualImportProvider always
    writes it; absence == upstream contract violation)."""
    stub_dir = env["pending_root"] / "img_vellin_no_hash"
    stub_dir.mkdir()
    _write_png(stub_dir / "img_vellin_no_hash.png")
    (stub_dir / "meta.json").write_text(
        json.dumps(
            {
                "asset_id_stub": "img_vellin_no_hash",
                "target_ref": "char_vellin",
                "target_type": "character",
                "asset_role": "character_sheet",
                "asset_kind": "character_sheet",
                "source_mode": "manual",
                "variant_label": "neutral",
                # prompt_hash missing on purpose
            }
        ),
        encoding="utf-8",
    )

    outcomes = run_import(
        asset_id="img_vellin_no_hash",
        all_pending=False,
        dry_run=False,
        pending_root=env["pending_root"],
        visuals_root=env["visuals_root"],
        manifest_path=env["manifest_path"],
        ontology_path=env["ontology_path"],
    )
    assert outcomes[0].status == "rejected"
    assert "prompt_hash" in (outcomes[0].rejected_reason or "")


def test_mirror_field_inconsistency_rejects(env: dict[str, Path]) -> None:
    """target_type=character but character_ref drifts from target_ref."""
    _make_pending_stub(
        env["pending_root"],
        asset_id_stub="img_vellin_drift",
        target_ref="char_vellin",
        target_type="character",
        asset_role="character_sheet",
        asset_kind="character_sheet",
        extra_meta={"character_ref": "char_someone_else"},  # drift
    )

    outcomes = run_import(
        asset_id="img_vellin_drift",
        all_pending=False,
        dry_run=False,
        pending_root=env["pending_root"],
        visuals_root=env["visuals_root"],
        manifest_path=env["manifest_path"],
        ontology_path=env["ontology_path"],
    )
    assert outcomes[0].status == "rejected"
    assert "character_ref" in (outcomes[0].rejected_reason or "")


def test_duplicate_asset_id_in_manifest_skips_without_moving(
    env: dict[str, Path],
) -> None:
    """Re-running the same stub when manifest already has it → reject log,
    pending dir preserved (not moved to _rejected/)."""
    # First import succeeds
    _make_pending_stub(
        env["pending_root"],
        asset_id_stub="img_vellin_neutral",
        target_ref="char_vellin",
        target_type="character",
        asset_role="character_sheet",
        asset_kind="character_sheet",
    )
    run_import(
        asset_id="img_vellin_neutral",
        all_pending=False,
        dry_run=False,
        pending_root=env["pending_root"],
        visuals_root=env["visuals_root"],
        manifest_path=env["manifest_path"],
        ontology_path=env["ontology_path"],
    )

    # Author re-creates the same stub (e.g. ran ManualImportProvider twice)
    stub2 = _make_pending_stub(
        env["pending_root"],
        asset_id_stub="img_vellin_neutral",
        target_ref="char_vellin",
        target_type="character",
        asset_role="character_sheet",
        asset_kind="character_sheet",
    )

    outcomes = run_import(
        asset_id="img_vellin_neutral",
        all_pending=False,
        dry_run=False,
        pending_root=env["pending_root"],
        visuals_root=env["visuals_root"],
        manifest_path=env["manifest_path"],
        ontology_path=env["ontology_path"],
    )

    assert outcomes[0].status == "rejected"
    assert "already in manifest" in (outcomes[0].rejected_reason or "")
    # Pending dir preserved (NOT moved to _rejected/)
    assert stub2.exists()
    assert not (env["pending_root"] / "_rejected" / "img_vellin_neutral").exists()

    # Manifest still has exactly one entry; ontology vellin still has one entry
    m = load_manifest(env["manifest_path"])
    assert len(m.assets) == 1
    ontology = json.loads(env["ontology_path"].read_text(encoding="utf-8"))
    vellin = next(e for e in ontology["entities"] if e["id"] == "char_vellin")
    assert len(vellin["visual_assets"]) == 1


def test_missing_pending_directory_logs_rejection(
    env: dict[str, Path],
) -> None:
    outcomes = run_import(
        asset_id="img_does_not_exist",
        all_pending=False,
        dry_run=False,
        pending_root=env["pending_root"],
        visuals_root=env["visuals_root"],
        manifest_path=env["manifest_path"],
        ontology_path=env["ontology_path"],
    )
    assert outcomes[0].status == "rejected"
    assert "missing" in (outcomes[0].rejected_reason or "").lower()
    rows = import_log.read_all()
    assert len(rows) == 1
    assert rows[0]["status"] == "rejected"


def test_character_target_with_no_ontology_entity_rejects(
    env: dict[str, Path],
) -> None:
    """target_type=character but the entity isn't in waystation.json."""
    _make_pending_stub(
        env["pending_root"],
        asset_id_stub="img_unknown_char",
        target_ref="char_unknown",
        target_type="character",
        asset_role="character_sheet",
        asset_kind="character_sheet",
    )
    outcomes = run_import(
        asset_id="img_unknown_char",
        all_pending=False,
        dry_run=False,
        pending_root=env["pending_root"],
        visuals_root=env["visuals_root"],
        manifest_path=env["manifest_path"],
        ontology_path=env["ontology_path"],
    )
    assert outcomes[0].status == "rejected"
    assert "char_unknown" in (outcomes[0].rejected_reason or "")


def test_cli_help_runs(monkeypatch: pytest.MonkeyPatch) -> None:
    """python -m generator.image_import --help exits 0 (catches arg parser drift)."""
    with pytest.raises(SystemExit) as exc:
        image_import.main(["--help"])
    assert exc.value.code == 0
