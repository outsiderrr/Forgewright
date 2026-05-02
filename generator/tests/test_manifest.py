"""Tests for generator.manifest (T-1.5.7).

Covers:
  - load_manifest on missing path → empty Manifest
  - save → load roundtrip preserves the payload byte-for-byte (modulo
    Pydantic's stable JSON encoding)
  - add_asset / remove_asset are non-mutating (return new instances)
  - duplicate add_asset raises (append-only invariant)
  - schema_version field is preserved through save / load
"""

from __future__ import annotations

import datetime as _dt
import json
from pathlib import Path

import pytest

from generator.manifest import (
    SCHEMA_VERSION,
    Manifest,
    add_asset,
    load_manifest,
    remove_asset,
    save_manifest,
)
from generator.models._generated.image_asset import ImageAsset


def _make_asset(asset_id: str = "img_test_neutral") -> ImageAsset:
    return ImageAsset(
        schema_version="0.2.0",
        asset_id=asset_id,
        asset_kind="character_sheet",
        target_ref="char_test",
        target_type="character",
        asset_role="character_sheet",
        character_ref="char_test",
        location_ref=None,
        source_mode="manual",
        format="png",
        width=1024,
        height=1024,
        file_size_bytes=12345,
        has_alpha=True,
        file_path=f"content/visuals/test/{asset_id}.png",
        prompt_hash="a" * 64,
        created_at=_dt.datetime(2026, 5, 1, 12, 0, 0, tzinfo=_dt.timezone.utc),
    )


def test_load_missing_returns_empty_manifest(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    m = load_manifest(path)
    assert m.schema_version == SCHEMA_VERSION
    assert m.assets == {}


def test_save_then_load_roundtrip(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    asset = _make_asset()
    m = Manifest(schema_version=SCHEMA_VERSION, assets={asset.asset_id: asset})
    save_manifest(m, path)

    assert path.exists()
    raw = json.loads(path.read_text(encoding="utf-8"))
    assert raw["schema_version"] == SCHEMA_VERSION
    assert asset.asset_id in raw["assets"]

    m2 = load_manifest(path)
    assert m2.schema_version == SCHEMA_VERSION
    assert set(m2.assets.keys()) == {asset.asset_id}
    # ImageAsset compares structurally
    assert m2.assets[asset.asset_id] == asset


def test_save_writes_trailing_newline(tmp_path: Path) -> None:
    """Convention shared with cost_log + ontology files: trailing newline.

    Catches drift if the JSON encoder is swapped for one that omits it.
    """
    path = tmp_path / "manifest.json"
    save_manifest(
        Manifest(schema_version=SCHEMA_VERSION, assets={}), path
    )
    assert path.read_text(encoding="utf-8").endswith("\n")


def test_add_asset_returns_new_instance(tmp_path: Path) -> None:
    asset = _make_asset()
    original = Manifest(schema_version=SCHEMA_VERSION, assets={})
    updated = add_asset(original, asset)
    # Original untouched
    assert original.assets == {}
    # New instance
    assert updated is not original
    assert updated.assets == {asset.asset_id: asset}


def test_add_asset_duplicate_raises() -> None:
    asset = _make_asset()
    m = Manifest(schema_version=SCHEMA_VERSION, assets={asset.asset_id: asset})
    with pytest.raises(ValueError, match="already present"):
        add_asset(m, asset)


def test_remove_asset_returns_new_instance() -> None:
    asset = _make_asset()
    m = Manifest(schema_version=SCHEMA_VERSION, assets={asset.asset_id: asset})
    updated = remove_asset(m, asset.asset_id)
    assert updated is not m
    assert m.assets == {asset.asset_id: asset}  # original untouched
    assert updated.assets == {}


def test_remove_asset_missing_is_noop() -> None:
    asset = _make_asset()
    m = Manifest(schema_version=SCHEMA_VERSION, assets={asset.asset_id: asset})
    updated = remove_asset(m, "img_does_not_exist")
    assert updated.assets == m.assets


def test_load_rejects_wrong_schema_version(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(
        json.dumps({"schema_version": "0.1.0", "assets": {}}) + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="schema_version"):
        load_manifest(path)


@pytest.mark.parametrize(
    "malformed_payload",
    [
        # Missing the `assets` key entirely.
        {"schema_version": "0.2.0"},
        # Explicit null.
        {"schema_version": "0.2.0", "assets": None},
        # Empty list (looks "empty" but isn't a dict).
        {"schema_version": "0.2.0", "assets": []},
        # Populated list (would silently lose data on `or {}` fallback).
        {"schema_version": "0.2.0", "assets": ["img_oops"]},
        # Wrong scalar type.
        {"schema_version": "0.2.0", "assets": "not a dict"},
    ],
)
def test_load_rejects_malformed_assets_shape(
    tmp_path: Path, malformed_payload: dict
) -> None:
    """Existing-on-disk manifest with broken `assets` must hard-fail rather
    than be silently treated as empty (review of T-1.5.7 #4.2)."""
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(malformed_payload) + "\n", encoding="utf-8")
    with pytest.raises(ValueError, match="assets"):
        load_manifest(path)


def test_load_rejects_drift_between_key_and_asset_id(tmp_path: Path) -> None:
    """Dict key must agree with embedded asset_id; otherwise the index is lying."""
    path = tmp_path / "manifest.json"
    asset = _make_asset()
    payload = asset.model_dump(mode="json")
    path.write_text(
        json.dumps(
            {
                "schema_version": SCHEMA_VERSION,
                "assets": {"img_other_key": payload},
            }
        )
        + "\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="does not match"):
        load_manifest(path)
