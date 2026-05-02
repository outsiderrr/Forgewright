"""manifest.json read/write for /content/visuals/ (T-1.5.7).

Single-file index keyed by `asset_id`; the import CLI does constant-time
membership checks before adding new rows. Wire format mirrors the
dataclass exactly:

    {
      "schema_version": "0.2.0",
      "assets": {
        "<asset_id>": <ImageAsset payload>,
        ...
      }
    }

`add_asset` / `remove_asset` return new `Manifest` instances rather than
mutating their argument so callers can hold a snapshot for diffing /
rollback. `save_manifest` writes via temp file + `os.replace` + fsync —
crash mid-write leaves the prior manifest intact.
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from generator.models._generated.image_asset import ImageAsset

DEFAULT_MANIFEST_PATH = Path("content/visuals/manifest.json")
SCHEMA_VERSION: Literal["0.2.0"] = "0.2.0"


@dataclass
class Manifest:
    schema_version: Literal["0.2.0"]
    assets: dict[str, ImageAsset]


def load_manifest(path: Path = DEFAULT_MANIFEST_PATH) -> Manifest:
    """Read manifest from disk; return empty Manifest if file does not exist.

    Empty == `Manifest(schema_version="0.2.0", assets={})`.
    """
    if not path.exists():
        return Manifest(schema_version=SCHEMA_VERSION, assets={})
    with path.open("r", encoding="utf-8") as f:
        raw = json.load(f)
    schema_version = raw.get("schema_version")
    if schema_version != SCHEMA_VERSION:
        raise ValueError(
            f"manifest schema_version {schema_version!r} does not match "
            f"expected {SCHEMA_VERSION!r}; refusing to load."
        )
    raw_assets = raw.get("assets") or {}
    if not isinstance(raw_assets, dict):
        raise ValueError(
            f"manifest 'assets' must be an object, got {type(raw_assets).__name__}"
        )
    assets: dict[str, ImageAsset] = {}
    for asset_id, payload in raw_assets.items():
        asset = ImageAsset.model_validate(payload)
        # Catches stale rows where the dict key drifted from the embedded
        # asset_id field — manifest is the index of record, so the two must
        # agree.
        if asset.asset_id != asset_id:
            raise ValueError(
                f"manifest asset key {asset_id!r} does not match embedded "
                f"asset.asset_id {asset.asset_id!r}"
            )
        assets[asset_id] = asset
    return Manifest(schema_version=SCHEMA_VERSION, assets=assets)


def save_manifest(
    manifest: Manifest, path: Path = DEFAULT_MANIFEST_PATH
) -> None:
    """Atomically write manifest with fsync.

    Writes a sibling temp file → fsync → os.replace → fsync parent dir.
    `os.replace` is atomic on POSIX so a mid-write crash leaves the prior
    file intact rather than half-written.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": manifest.schema_version,
        "assets": {
            aid: asset.model_dump(mode="json", exclude_none=False)
            for aid, asset in manifest.assets.items()
        },
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"

    fd, tmp_path = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=str(path.parent)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    except Exception:
        # mkstemp succeeded but write/replace failed; leftover tmp file would
        # accumulate — clean up best-effort.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise

    # fsync the directory so the rename itself is durable across crash.
    # Some platforms (Windows) can't open a directory; skip on EACCES/EBADF.
    try:
        dir_fd = os.open(str(path.parent), os.O_RDONLY)
    except OSError:
        return
    try:
        os.fsync(dir_fd)
    except OSError:
        pass
    finally:
        os.close(dir_fd)


def add_asset(manifest: Manifest, asset: ImageAsset) -> Manifest:
    """Return a new Manifest with `asset` appended.

    Raises if `asset.asset_id` already present — manifest is append-only;
    callers must `remove_asset` first to overwrite explicitly. This keeps
    re-runs of `image_import` from silently reformatting an already-imported
    row (T-1.5.7 idempotency: the CLI catches the collision and emits a
    rejection log row).
    """
    if asset.asset_id in manifest.assets:
        raise ValueError(
            f"asset_id {asset.asset_id!r} already present in manifest; "
            f"use remove_asset() first to overwrite explicitly."
        )
    new_assets = dict(manifest.assets)
    new_assets[asset.asset_id] = asset
    return Manifest(schema_version=manifest.schema_version, assets=new_assets)


def remove_asset(manifest: Manifest, asset_id: str) -> Manifest:
    """Return a new Manifest with `asset_id` removed. No-op if absent."""
    new_assets = {k: v for k, v in manifest.assets.items() if k != asset_id}
    return Manifest(schema_version=manifest.schema_version, assets=new_assets)


__all__ = [
    "DEFAULT_MANIFEST_PATH",
    "Manifest",
    "SCHEMA_VERSION",
    "add_asset",
    "load_manifest",
    "remove_asset",
    "save_manifest",
]
